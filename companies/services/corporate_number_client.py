import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class CorporateNumberAPIError(Exception):
    """Raised when the corporate number API call fails."""


def _normalize_spaces(value: str) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in value if not ch.isspace()).lower()


class CorporateNumberAPIClient:
    """
    Minimal client for the National Tax Agency corporate number API.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_results: Optional[int] = None,
    ) -> None:
        self.token = token or settings.CORPORATE_NUMBER_API_TOKEN
        self.base_url = (base_url or settings.CORPORATE_NUMBER_API_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.CORPORATE_NUMBER_API_TIMEOUT
        self.max_results = max_results or settings.CORPORATE_NUMBER_API_MAX_RESULTS

    def search(
        self, name: str, prefecture: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if not self.token:
            raise CorporateNumberAPIError("CORPORATE_NUMBER_API_TOKEN is not configured.")

        if not name:
            return []

        endpoint = f"{self.base_url}/4/name"
        params: Dict[str, Any] = {
            "name": name,
            "type": "12",  # name search
            "target": "2",  # corporations only
            "token": self.token,
        }
        if prefecture:
            params["address"] = prefecture
        if limit or self.max_results:
            params["limit"] = str(limit or self.max_results)

        try:
            response = requests.get(endpoint, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.exception("corporate-number-api request failed")
            raise CorporateNumberAPIError("法人番号APIへの接続に失敗しました。") from exc

        if response.status_code != 200:
            logger.error(
                "corporate-number-api non-200 response: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise CorporateNumberAPIError("法人番号APIからエラーが返却されました。")

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("corporate-number-api invalid JSON: %s", response.text[:2000])
            raise CorporateNumberAPIError("法人番号APIのレスポンス解析に失敗しました。") from exc

        if str(data.get("status")) != "200":
            logger.warning("corporate-number-api status=%s message=%s", data.get("status"), data.get("message"))
            return []

        results = []
        for item in data.get("results", []):
            corporate_number = item.get("corporateNumber")
            if not corporate_number:
                continue
            results.append(
                {
                    "corporate_number": corporate_number,
                    "name": item.get("name"),
                    "name_normalized": _normalize_spaces(item.get("name")),
                    "prefecture": item.get("prefectureName"),
                    "address": item.get("prefectureName"),
                    "raw": item,
                }
            )
        return results


def select_best_match(
    candidates: List[Dict[str, Any]],
    company_name: str,
    prefecture: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Choose the best candidate based on name and prefecture."""
    if not candidates:
        return None

    normalized_target = _normalize_spaces(company_name)
    prefecture = (prefecture or "").strip()

    prefecture_matches = [
        item
        for item in candidates
        if item.get("prefecture") and prefecture and item["prefecture"] == prefecture
    ]
    name_matches = [
        item
        for item in (prefecture_matches or candidates)
        if item.get("name_normalized") == normalized_target
    ]
    if name_matches:
        return name_matches[0]

    # fallback to prefecture match if available
    if prefecture_matches:
        return prefecture_matches[0]

    return candidates[0]
