from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"


class FacebookClientConfigurationError(RuntimeError):
    """Raised when Facebook client is misconfigured."""


class FacebookAPIError(RuntimeError):
    """Raised when Facebook API returns an error response."""


class FacebookClient:
    def __init__(
        self,
        access_token: Optional[str] = None,
        version: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.access_token = access_token or settings.FACEBOOK_ACCESS_TOKEN
        self.version = version or settings.FACEBOOK_GRAPH_API_VERSION
        self.timeout = timeout or settings.FACEBOOK_GRAPH_API_TIMEOUT

        if not self.access_token:
            raise FacebookClientConfigurationError("FACEBOOK_ACCESS_TOKEN is not configured")
        if not self.version:
            raise FacebookClientConfigurationError("FACEBOOK_GRAPH_API_VERSION is not configured")

    def _build_url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{GRAPH_API_BASE}/{self.version}/{path}"

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params.copy() if params else {}
        params.setdefault("access_token", self.access_token)
        url = self._build_url(path)

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise FacebookAPIError(f"Network error calling Facebook API: {exc}") from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            raise FacebookAPIError(f"Facebook API error ({response.status_code}): {payload}")

        try:
            return response.json()
        except ValueError as exc:
            raise FacebookAPIError(f"Invalid JSON response from Facebook API: {exc}") from exc

    def fetch_page_metrics(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieve fan count and latest post created time for the given page.
        Returns a dictionary containing friend_count, friend_count_fetched_at,
        latest_posted_at and latest_post_fetched_at (timestamps are ISO strings).
        """
        if not page_id:
            raise ValueError("page_id is required")

        fields = "fan_count,posts.limit(1){created_time}"
        payload = self._request(page_id, params={"fields": fields})

        friend_count = payload.get("fan_count")
        posts = (payload.get("posts") or {}).get("data") or []
        latest_post = posts[0].get("created_time") if posts else None
        now_iso = timezone.now().isoformat()

        metrics = {
            "friend_count": friend_count,
            "friend_count_fetched_at": now_iso,
            "latest_posted_at": latest_post,
            "latest_post_fetched_at": now_iso,
        }

        logger.debug("Fetched Facebook metrics for %s: %s", page_id, metrics)
        return metrics
