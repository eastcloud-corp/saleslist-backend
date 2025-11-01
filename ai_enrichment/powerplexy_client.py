
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

from .exceptions import (
    PowerplexyConfigurationError,
    PowerplexyRateLimitError,
    PowerplexyResponseError,
)

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://api.perplexity.ai/query"
DEFAULT_MODEL = "sonar-medium"
DEFAULT_TIMEOUT = 30


class PowerplexyClient:
    """Thin wrapper around the PowerPlexy API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "POWERPLEXY_API_KEY", "")
        if not self.api_key:
            raise PowerplexyConfigurationError("POWERPLEXY_API_KEY is not configured")

        self.endpoint = endpoint or getattr(settings, "POWERPLEXY_API_ENDPOINT", DEFAULT_ENDPOINT)
        self.model = model or getattr(settings, "POWERPLEXY_MODEL", DEFAULT_MODEL)
        self.timeout = timeout or getattr(settings, "POWERPLEXY_TIMEOUT", DEFAULT_TIMEOUT)
        self.session = session or requests.Session()

    def query(self, prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "query": prompt,
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PowerplexyResponseError(f"PowerPlexy request failed: {exc}") from exc

        if response.status_code == 429:
            raise PowerplexyRateLimitError("PowerPlexy rate limit reached")

        if response.status_code >= 500:
            raise PowerplexyResponseError(
                f"PowerPlexy service error ({response.status_code})"
            )

        if response.status_code >= 400:
            raise PowerplexyResponseError(
                f"PowerPlexy rejected the request ({response.status_code}): {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise PowerplexyResponseError("PowerPlexy returned invalid JSON") from exc

        return data

    def extract_json(self, prompt: str) -> Dict[str, Any]:
        data = self.query(prompt)
        if isinstance(data, dict):
            for key in ("answer", "output", "text", "result"):
                if key in data and isinstance(data[key], str):
                    return self._parse_json_blob(data[key])
        raise PowerplexyResponseError("Unexpected PowerPlexy response structure")

    @staticmethod
    def _parse_json_blob(blob: str) -> Dict[str, Any]:
        blob = blob.strip()
        if not blob:
            return {}
        if blob.startswith("```"):
            lines = [line for line in blob.splitlines() if not line.startswith("```")]
            if lines:
                blob = "\n".join(lines)
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError as exc:
            raise PowerplexyResponseError("Failed to parse JSON from PowerPlexy output") from exc
        if not isinstance(parsed, dict):
            raise PowerplexyResponseError("PowerPlexy output is not a JSON object")
        return parsed

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"PowerplexyClient(endpoint={self.endpoint!r}, model={self.model!r})"
