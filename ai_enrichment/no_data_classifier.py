"""
no_data理由の分類ロジック（Phase 3-②）

no_dataを構造化された診断結果にする
"""
from typing import Optional

from .enrichment_context import EnrichmentContext
from .no_data_reasons import NoDataReasonCode, RetryStrategy, get_reason_message, get_retry_strategy


def classify_no_data_reason(
    context: EnrichmentContext,
    gbiz_initial_404: bool,
    gbiz_retry_404: bool,
    ai_attempted: bool,
    ai_fields_empty: bool,
    has_official_site: bool,
) -> tuple[NoDataReasonCode, str, RetryStrategy]:
    """
    no_data理由を分類する
    
    Args:
        context: EnrichmentContext
        gbiz_initial_404: 初期gBizINFO検索が404だったか
        gbiz_retry_404: gBizINFO再探索が404だったか
        ai_attempted: AI補完を試みたか
        ai_fields_empty: AI補完の結果が空だったか
        has_official_site: 公式サイトが見つかったか
    
    Returns:
        (reason_code, reason_message, retry_strategy) のタプル
    """
    # 1. NAME_VARIANT_INSUFFICIENT: gBizINFO初期・再探索ともに404、かつAI候補あり
    if (
        gbiz_initial_404
        and gbiz_retry_404
        and context.ai_official_name_candidates
    ):
        reason_code = NoDataReasonCode.NAME_VARIANT_INSUFFICIENT
    # 2. AI_NO_FIELD_RESULT: gBizINFO初期・再探索ともに404、かつAI応答はあったがフィールドが空
    elif (
        gbiz_initial_404
        and gbiz_retry_404
        and ai_attempted
        and ai_fields_empty
    ):
        reason_code = NoDataReasonCode.AI_NO_FIELD_RESULT
    # 3. NO_OFFICIAL_SITE: 公式サイトが見つからない
    elif not has_official_site and ai_attempted:
        reason_code = NoDataReasonCode.NO_OFFICIAL_SITE
    # 4. PRIVATE_OR_UNDISCLOSED: すべてのソースを試したが情報が見つからない
    elif (
        gbiz_initial_404
        and (not context.ai_official_name_candidates or gbiz_retry_404)
        and ai_attempted
        and ai_fields_empty
    ):
        reason_code = NoDataReasonCode.PRIVATE_OR_UNDISCLOSED
    # 5. GBIZ_NOT_FOUND: gBizINFOに候補が存在しない（基本ケース）
    elif gbiz_initial_404 and not context.gbizinfo_success:
        reason_code = NoDataReasonCode.GBIZ_NOT_FOUND
    # 6. RETRY_EXHAUSTED: 再探索条件を満たさない
    else:
        reason_code = NoDataReasonCode.RETRY_EXHAUSTED
    
    reason_message = get_reason_message(reason_code)
    retry_strategy = get_retry_strategy(reason_code)
    
    return reason_code, reason_message, retry_strategy
