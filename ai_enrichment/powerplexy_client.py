
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

import requests
from django.conf import settings

from .exceptions import (
    PowerplexyConfigurationError,
    PowerplexyRateLimitError,
    PowerplexyResponseError,
)

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar-pro"  # オンライン検索対応モデル（llama-3.1-sonar-large-128k-onlineは2025年2月に非推奨）
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_TOKENS = 1000


class PowerplexyClient:
    """Thin wrapper around the PowerPlexy API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_tokens: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "POWERPLEXY_API_KEY", "")
        if not self.api_key:
            raise PowerplexyConfigurationError("POWERPLEXY_API_KEY is not configured")

        self.endpoint = endpoint or getattr(settings, "POWERPLEXY_API_ENDPOINT", DEFAULT_ENDPOINT)
        self.model = model or getattr(settings, "POWERPLEXY_MODEL", DEFAULT_MODEL)
        self.timeout = timeout or getattr(settings, "POWERPLEXY_TIMEOUT", DEFAULT_TIMEOUT)
        self.max_tokens = max_tokens or getattr(settings, "POWERPLEXY_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        self.session = session or requests.Session()

    def query(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Perplexity AI APIにリクエストを送信
        
        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
        
        Returns:
            APIレスポンスのJSON
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,  # 低い温度で一貫性のある結果を取得
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        def _post(request_payload: Dict[str, Any]) -> requests.Response:
            try:
                return self.session.post(
                    self.endpoint,
                    headers=headers,
                    data=json.dumps(request_payload),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise PowerplexyResponseError(f"PowerPlexy request failed: {exc}") from exc

        response = _post(payload)

        if response.status_code == 429:
            raise PowerplexyRateLimitError("PowerPlexy rate limit reached")

        if response.status_code >= 500:
            raise PowerplexyResponseError(
                f"PowerPlexy service error ({response.status_code})",
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code >= 400:
            # Perplexity側のモデル名変更に追随できるように、invalid modelの場合は1回だけ安全なデフォルトで再試行する。
            # 例: "Invalid model 'sonar-medium' ..."
            if (
                response.status_code == 400
                and "Invalid model" in response.text
                and self.model != DEFAULT_MODEL
            ):
                logger.warning(
                    "PowerPlexy invalid model %r; retrying with default model %r",
                    self.model,
                    DEFAULT_MODEL,
                )
                payload_retry = {**payload, "model": DEFAULT_MODEL}
                response = _post(payload_retry)

                if response.status_code == 429:
                    raise PowerplexyRateLimitError("PowerPlexy rate limit reached")
                if response.status_code >= 500:
                    raise PowerplexyResponseError(
                        f"PowerPlexy service error ({response.status_code})",
                        status_code=response.status_code,
                        response_body=response.text,
                    )
                if response.status_code >= 400:
                    raise PowerplexyResponseError(
                        f"PowerPlexy rejected the request ({response.status_code}): {response.text}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

            raise PowerplexyResponseError(
                f"PowerPlexy rejected the request ({response.status_code}): {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise PowerplexyResponseError(
                "PowerPlexy returned invalid JSON",
                status_code=response.status_code,
                response_body=response.text[:2000] if response.text else None,
            ) from exc

        return data

    def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        プロンプトを送信し、レスポンスからJSONを抽出
        
        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
        
        Returns:
            抽出されたJSON辞書
        """
        data = self.query(prompt, system_prompt)
        logger.debug("PowerPlexy raw response: %s", data)
        parsed, _usage = self._extract_parsed_and_usage(data)
        return parsed

    def extract_json_with_usage(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        extract_json と同様にJSONを抽出しつつ、Perplexityの usage を返す。

        Returns:
            (parsed_json, usage_dict)
        """
        data = self.query(prompt, system_prompt)
        logger.debug("PowerPlexy raw response: %s", data)
        return self._extract_parsed_and_usage(data)

    def _extract_parsed_and_usage(
        self, data: object
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        usage: Dict[str, Any] = {}
        if isinstance(data, dict):
            raw_usage = data.get("usage")
            if isinstance(raw_usage, dict):
                usage = raw_usage

            # Chat completions response: {"choices":[{"message":{"content":"..."}}, ...]}
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                content = message.get("content")
                if isinstance(content, str):
                    logger.debug("PowerPlexy content extracted: %s", content[:500])
                    parsed = self._parse_json_blob(content)
                    logger.debug("PowerPlexy parsed JSON: %s", parsed)
                    return parsed, usage
            # Legacy response fallback
            for key in ("answer", "output", "text", "result"):
                if key in data and isinstance(data[key], str):
                    logger.debug("PowerPlexy legacy response key '%s': %s", key, data[key][:500])
                    parsed = self._parse_json_blob(data[key])
                    logger.debug("PowerPlexy parsed JSON: %s", parsed)
                    return parsed, usage
        logger.error("PowerPlexy unexpected response structure: %s", data)
        raise PowerplexyResponseError("Unexpected PowerPlexy response structure")

    @staticmethod
    def _parse_json_blob(blob: str) -> Dict[str, Any]:
        """
        JSON文字列をパース（コードブロックやマークダウン記号を除去）
        
        Args:
            blob: JSONを含む可能性のある文字列
        
        Returns:
            パースされたJSON辞書
        """
        blob = blob.strip()
        if not blob:
            return {}
        
        # コードブロックを除去
        if blob.startswith("```"):
            lines = [line for line in blob.splitlines() if not line.startswith("```")]
            if lines:
                blob = "\n".join(lines)
        
        # 正規表現でJSONを抽出（テキスト内にJSONが埋め込まれている場合に対応）
        json_match = re.search(r'\{.*\}', blob, re.DOTALL)
        if json_match:
            blob = json_match.group()
        
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError as exc:
            raise PowerplexyResponseError("Failed to parse JSON from PowerPlexy output") from exc
        if not isinstance(parsed, dict):
            raise PowerplexyResponseError("PowerPlexy output is not a JSON object")
        return parsed

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"PowerplexyClient(endpoint={self.endpoint!r}, model={self.model!r})"
