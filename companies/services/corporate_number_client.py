import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class CorporateNumberAPIError(Exception):
    """Raised when the corporate number API call fails."""


def _normalize_spaces(value: str) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in value if not ch.isspace()).lower()


def _prefecture_to_code(prefecture: str) -> Optional[str]:
    """
    都道府県名をJIS X 0401都道府県コード（2桁）に変換
    
    Args:
        prefecture: 都道府県名（例: "東京都"）
    
    Returns:
        JIS都道府県コード（例: "13"）、変換できない場合はNone
    """
    prefecture_map = {
        "北海道": "01",
        "青森県": "02",
        "岩手県": "03",
        "宮城県": "04",
        "秋田県": "05",
        "山形県": "06",
        "福島県": "07",
        "茨城県": "08",
        "栃木県": "09",
        "群馬県": "10",
        "埼玉県": "11",
        "千葉県": "12",
        "東京都": "13",
        "神奈川県": "14",
        "新潟県": "15",
        "富山県": "16",
        "石川県": "17",
        "福井県": "18",
        "山梨県": "19",
        "長野県": "20",
        "岐阜県": "21",
        "静岡県": "22",
        "愛知県": "23",
        "三重県": "24",
        "滋賀県": "25",
        "京都府": "26",
        "大阪府": "27",
        "兵庫県": "28",
        "奈良県": "29",
        "和歌山県": "30",
        "鳥取県": "31",
        "島根県": "32",
        "岡山県": "33",
        "広島県": "34",
        "山口県": "35",
        "徳島県": "36",
        "香川県": "37",
        "愛媛県": "38",
        "高知県": "39",
        "福岡県": "40",
        "佐賀県": "41",
        "長崎県": "42",
        "熊本県": "43",
        "大分県": "44",
        "宮崎県": "45",
        "鹿児島県": "46",
        "沖縄県": "47",
    }
    return prefecture_map.get(prefecture.strip())


class CorporateNumberAPIClient:
    """
    Client for gBizINFO (経済産業省) corporate number API.
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
        """
        企業名と都道府県から法人番号APIを検索（gBizINFO API）
        
        Args:
            name: 企業名
            prefecture: 都道府県名（オプション、JIS都道府県コードに変換される）
            limit: 取得件数上限（オプション）
        
        Returns:
            企業情報のリスト
        """
        if not self.token:
            raise CorporateNumberAPIError("CORPORATE_NUMBER_API_TOKEN is not configured.")

        if not name:
            return []

        # gBizINFO APIのエンドポイント
        # API仕様: https://info.gbiz.go.jp/hojin/swagger-ui/index.html
        # サーバーURL: /hojin
        # パス: /v1/hojin
        # 完全なURL: https://api.info.gbiz.go.jp/hojin/v1/hojin
        # 注意: エンドポイントの末尾にスラッシュ（/）があるとエラーになる
        if "api.info.gbiz.go.jp" in self.base_url:
            # base_urlが https://api.info.gbiz.go.jp の場合
            endpoint = f"{self.base_url}/hojin/v1/hojin"
        elif "info.gbiz.go.jp" in self.base_url:
            # base_urlが https://info.gbiz.go.jp の場合、api.info.gbiz.go.jpに変換
            endpoint = "https://api.info.gbiz.go.jp/hojin/v1/hojin"
        else:
            # その他の場合
            endpoint = f"{self.base_url}/hojin/v1/hojin"
        
        # 末尾のスラッシュを削除（API仕様でエラーになるため）
        endpoint = endpoint.rstrip("/")
        
        # Phase 0.5: URLエンコードを明示的に行い、curlと完全一致させる
        # パターンB: クエリ文字列を自前で組み立てる（curlと完全一致）
        # 注意: urlencode()は自動的にエンコードするので、quote()は不要
        query_params: Dict[str, str] = {}
        
        # 企業名をそのまま設定（urlencode()が自動的にエンコードする）
        query_params["name"] = name
        
        # 都道府県コードに変換
        if prefecture:
            prefecture_code = _prefecture_to_code(prefecture)
            if prefecture_code:
                query_params["prefecture"] = prefecture_code
        
        # クエリ文字列を組み立て（urlencode()が自動的にエンコード）
        query_string = urlencode(query_params, doseq=True)
        full_url = f"{endpoint}?{query_string}"
        
        # デバッグ用: エンコードされた企業名を確認（urlencode()の結果から抽出）
        encoded_name = query_string.split("name=")[1].split("&")[0] if "name=" in query_string else ""

        headers = {
            "X-hojinInfo-api-token": self.token,  # gBizINFO APIの認証ヘッダー
        }

        # デバッグ用: 完全なURLをログに出力（curlと比較可能）
        logger.info(
            "corporate-number-api request: full_url=%s, encoded_name=%s",
            full_url,
            encoded_name,
        )
        
        try:
            # デバッグ用: リクエスト詳細をログに出力
            logger.info(
                "corporate-number-api request: full_url=%s, headers=%s",
                full_url,
                {k: v[:10] + "..." if len(v) > 10 else v for k, v in headers.items()},
            )
            # 完全なURLを直接使用（paramsは使わない）
            response = requests.get(full_url, headers=headers, timeout=self.timeout)
            # 実際のリクエストURLをログに出力（curlと比較可能）
            logger.info(
                "corporate-number-api actual URL: %s, status=%d",
                response.url if hasattr(response, 'url') else full_url,
                response.status_code,
            )
        except requests.RequestException as exc:
            logger.exception("corporate-number-api request failed")
            raise CorporateNumberAPIError("法人番号APIへの接続に失敗しました。") from exc

        if response.status_code != 200:
            error_body = response.text[:500]
            logger.error(
                "corporate-number-api non-200 response: status=%s url=%s body=%s",
                response.status_code,
                response.url if hasattr(response, 'url') else full_url,
                error_body,
            )
            # 404エラーの場合は空のリストを返す（エラーをスローしない）
            # これにより、gBizINFO APIで見つからなくてもAI補完を継続できる
            if response.status_code == 404:
                logger.warning(
                    "corporate-number-api 404: 企業が見つかりませんでした。AI補完を継続します。",
                    extra={"company_name": name, "prefecture": prefecture},
                )
                return []  # 空のリストを返して処理を継続
            else:
                raise CorporateNumberAPIError(f"法人番号APIからエラーが返却されました（ステータス: {response.status_code}）。")

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("corporate-number-api invalid JSON: %s", response.text[:2000])
            raise CorporateNumberAPIError("法人番号APIのレスポンス解析に失敗しました。") from exc

        # gBizINFO APIのレスポンス構造: {"hojin-infos": [...], "message": "...", ...}
        results = []
        if not isinstance(data, dict):
            logger.warning("corporate-number-api unexpected response format: %s", type(data))
            return results

        # エラーチェック
        if data.get("errors"):
            logger.warning("corporate-number-api errors in response: %s", data.get("errors"))
            return results

        # hojin-infos 配列から企業情報を取得
        items = data.get("hojin-infos", [])
        if not isinstance(items, list):
            logger.warning("corporate-number-api hojin-infos is not a list: %s", type(items))
            return results

        for item in items:
            if not isinstance(item, dict):
                continue
            
            corporate_number = item.get("corporate_number")
            if not corporate_number:
                continue
            
            company_name = item.get("name", "")
            location = item.get("location", "")
            
            # locationから都道府県を抽出（例: "東京都千代田区..." → "東京都"）
            prefecture_name = ""
            if location:
                for pref in ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
                            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
                            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
                            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
                            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
                            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
                            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]:
                    if location.startswith(pref):
                        prefecture_name = pref
                        break
            
            results.append(
                {
                    "corporate_number": str(corporate_number).strip(),
                    "name": company_name,
                    "name_normalized": _normalize_spaces(company_name),
                    "prefecture": prefecture_name,
                    "address": location,
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
