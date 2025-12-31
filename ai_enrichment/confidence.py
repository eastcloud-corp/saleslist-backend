"""
信頼度計算（Phase 2: 相互補完設計）

情報源ごとの信頼度を計算する
"""
from typing import Dict

from .enrichment_context import EnrichmentContext


def calculate_confidence(context: EnrichmentContext) -> Dict[str, float]:
    """
    情報源ごとの信頼度を計算（最小構成）
    
    信頼度:
    - gBizINFO: 1.0
    - 公式サイト: 0.8
    - 複数一致: 0.7
    - 単一言及: 0.5
    
    Args:
        context: EnrichmentContext
    
    Returns:
        フィールドごとの信頼度の辞書
    """
    confidence: Dict[str, float] = {}
    
    # gBizINFOから取得した情報は信頼度1.0
    if context.gbizinfo_corporate_number:
        confidence["corporate_number"] = 1.0
    if context.gbizinfo_official_name:
        confidence["official_name"] = 1.0
    if context.gbizinfo_address:
        confidence["address"] = 1.0
    if context.gbizinfo_prefecture:
        confidence["prefecture"] = 1.0
    
    # AI補完の結果（最小構成）
    if context.ai_person_name:
        if context.gbizinfo_success:
            # gBizINFOとAIの両方で情報がある場合（相互補完）
            confidence["person_name"] = 1.0
        elif context.ai_website_url:
            # 公式サイトから取得
            confidence["person_name"] = 0.8
        else:
            # 単一言及
            confidence["person_name"] = 0.5
    
    if context.ai_role:
        if context.gbizinfo_success:
            # gBizINFOとAIの両方で情報がある場合
            confidence["role"] = 1.0
        elif context.ai_website_url:
            # 公式サイトから取得
            confidence["role"] = 0.8
        else:
            # 単一言及
            confidence["role"] = 0.5
    
    # Phase 2改善: gBizINFO再探索で成功した場合、信頼度を上げる
    if context.gbizinfo_corporate_number and context.ai_official_name_candidates:
        # AIのヒントでgBizINFO再探索が成功した場合、相互補完が成功している
        confidence["corporate_number"] = 1.0
        if context.gbizinfo_official_name:
            confidence["official_name"] = 1.0
    
    if context.ai_website_url:
        confidence["website_url"] = 0.8  # 公式サイト
    
    # その他のAI補完結果
    if context.ai_findings:
        for field in ["established_year", "capital", "employee_count", "business_description"]:
            if field in context.ai_findings and context.ai_findings[field]:
                if context.gbizinfo_success:
                    confidence[field] = 0.7  # 複数ソースで一致
                elif context.ai_website_url:
                    confidence[field] = 0.8  # 公式サイト
                else:
                    confidence[field] = 0.5  # 単一言及
    
    return confidence
