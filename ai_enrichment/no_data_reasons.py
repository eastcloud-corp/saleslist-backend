"""
no_data理由の分類（Phase 3-②）

no_dataを構造化された診断結果にする
"""
from enum import Enum
from typing import Optional


class NoDataReasonCode(str, Enum):
    """no_data理由コード"""
    GBIZ_NOT_FOUND = "gbiz_not_found"  # gBizINFOに候補が存在しない
    AI_NO_FIELD_RESULT = "ai_no_field_result"  # AIは応答したがフィールドが0
    NO_OFFICIAL_SITE = "no_official_site"  # 公式サイトが見つからない
    NAME_VARIANT_INSUFFICIENT = "name_variant_insufficient"  # 表記揺れ不足
    PRIVATE_OR_UNDISCLOSED = "private_or_undisclosed"  # 非公開・個人事業的
    RETRY_EXHAUSTED = "retry_exhausted"  # 再探索条件を満たさない


class RetryStrategy(str, Enum):
    """再探索戦略"""
    NONE = "none"  # 再探索しない
    RELAX_PREFECTURE = "relax_prefecture"  # 都道府県条件を緩和
    NAME_VARIANT_EXPANSION = "name_variant_expansion"  # 表記揺れを拡張
    ENGLISH_NAME_SEARCH = "english_name_search"  # 英語名で検索
    OFFICIAL_SITE_FOCUSED = "official_site_focused"  # 公式サイトに集中


# reason_code → retry_strategy のマッピング
REASON_TO_STRATEGY = {
    NoDataReasonCode.NAME_VARIANT_INSUFFICIENT: RetryStrategy.NAME_VARIANT_EXPANSION,
    NoDataReasonCode.AI_NO_FIELD_RESULT: RetryStrategy.OFFICIAL_SITE_FOCUSED,
    NoDataReasonCode.NO_OFFICIAL_SITE: RetryStrategy.ENGLISH_NAME_SEARCH,
    NoDataReasonCode.PRIVATE_OR_UNDISCLOSED: RetryStrategy.NONE,
    NoDataReasonCode.RETRY_EXHAUSTED: RetryStrategy.NONE,
    NoDataReasonCode.GBIZ_NOT_FOUND: RetryStrategy.RELAX_PREFECTURE,  # デフォルト戦略
}


def get_reason_message(reason_code: NoDataReasonCode) -> str:
    """reason_codeに対応するメッセージを取得"""
    messages = {
        NoDataReasonCode.GBIZ_NOT_FOUND: "gBizINFOに候補が存在しませんでした",
        NoDataReasonCode.AI_NO_FIELD_RESULT: "AI応答はあったが、補完可能なフィールドが見つかりませんでした",
        NoDataReasonCode.NO_OFFICIAL_SITE: "公式サイトが見つかりませんでした",
        NoDataReasonCode.NAME_VARIANT_INSUFFICIENT: "表記揺れが不足しており、gBizINFOで見つかりませんでした",
        NoDataReasonCode.PRIVATE_OR_UNDISCLOSED: "非公開または個人事業主の可能性があります",
        NoDataReasonCode.RETRY_EXHAUSTED: "再探索条件を満たさず、探索を終了しました",
    }
    return messages.get(reason_code, "理由不明")


def get_retry_strategy(reason_code: NoDataReasonCode) -> RetryStrategy:
    """reason_codeに対応するretry_strategyを取得"""
    return REASON_TO_STRATEGY.get(reason_code, RetryStrategy.NONE)
