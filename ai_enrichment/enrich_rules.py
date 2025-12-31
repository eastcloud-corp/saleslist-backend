from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from django.utils import timezone

from companies.models import Company
from companies.services.corporate_number_client import (
    CorporateNumberAPIClient,
    CorporateNumberAPIError,
)

# Phase 2: 相互補完設計
try:
    from .enrichment_context import EnrichmentContext
except ImportError:
    # 後方互換性のため
    EnrichmentContext = None

logger = logging.getLogger(__name__)


TARGET_FIELDS = {
    "contact_person_name": "担当者名",
    "contact_person_position": "担当者役職",
    "established_year": "設立年",
    "capital": "資本金",
    "employee_count": "従業員数",
    "prefecture": "所在地（都道府県）",
    "city": "所在地（市区町村・番地）",
    "business_description": "事業内容",
}

# Phase 2: AI出力に必須フィールドを追加（gBizINFO再探索用）
TARGET_FIELDS_WITH_HINTS = {
    **TARGET_FIELDS,
    "official_name_candidates": "正式法人名候補",
    "english_name": "英語名",
    "name_variants": "企業名のバリエーション",
}


@dataclass
class RuleBasedResult:
    values: Dict[str, str]
    metadata: Dict[str, str]


def detect_missing_fields(company: Company) -> List[str]:
    missing: List[str] = []
    for field in TARGET_FIELDS:
        value = getattr(company, field, None)
        if value in (None, "", 0):
            missing.append(field)
    return missing


def build_prompt(company: Company, missing_fields: Sequence[str]) -> str:
    """
    企業情報補完用のプロンプトを構築
    
    Args:
        company: 企業オブジェクト
        missing_fields: 補完が必要なフィールドのリスト
    
    Returns:
        構築されたプロンプト文字列
    """
    field_labels = TARGET_FIELDS
    
    # フィールドごとの詳細説明
    field_descriptions = {
        "contact_person_name": "担当者名（役職や括弧内の情報は除く）",
        "contact_person_position": "担当者役職",
        "established_year": "設立年（4桁の西暦、例: 2020）",
        "capital": "資本金（整数値のみ、単位は除く、例: 10000000）",
        "employee_count": "従業員数（整数値のみ、例: 100）",
        "prefecture": "都道府県",
        "city": "市区町村・番地",
        "business_description": "事業内容",
    }
    
    # ターゲットJSONの構築（値は空文字列の例）
    lines = []
    for field in missing_fields:
        if field in field_labels:
            lines.append(f'  "{field_labels[field]}": ""')
    
    if lines:
        target_json = "{\n" + ",\n".join(lines) + "\n}"
    else:
        target_json = "{}"
    
    # フィールド説明を別途追加
    field_explanations = []
    for field in missing_fields:
        if field in field_labels and field in field_descriptions:
            field_explanations.append(f"- {field_labels[field]}: {field_descriptions[field]}")

    # 企業情報の収集
    company_info_parts = [f"企業名: {company.name}"]
    
    if company.website_url:
        company_info_parts.append(f"URL: {company.website_url}")
    
    location_parts = []
    if company.prefecture:
        location_parts.append(company.prefecture)
    if company.city:
        location_parts.append(company.city)
    if location_parts:
        company_info_parts.append(f"所在地: {' '.join(location_parts)}")
    
    # 法人番号や業種があれば追加
    if hasattr(company, 'corporate_number') and company.corporate_number:
        company_info_parts.append(f"法人番号: {company.corporate_number}")
    
    if hasattr(company, 'industry') and company.industry:
        company_info_parts.append(f"業種: {company.industry}")
    
    # gBizINFOから取得した情報があれば追加（AI補完の精度向上のため）
    # これはbuild_prompt関数の引数として渡す必要があるが、現在はcompanyオブジェクトから取得できない
    # そのため、後で改善が必要

    # プロンプトの構築
    parts = [
        f"以下の企業「{company.name}」について、指定された情報をオンライン検索して抽出してください。",
        "",
        "【企業情報】",
        "\n".join(company_info_parts),
    ]
    
    if missing_fields:
        labels = [field_labels[f] for f in missing_fields if f in field_labels]
        if labels:
            parts.extend([
                "",
                "【抽出が必要な情報】",
                ", ".join(labels),
            ])
            # フィールドごとの説明を追加
            if field_explanations:
                parts.extend([
                    "",
                    "【各フィールドの説明】",
                    "\n".join(field_explanations),
                ])
    
    parts.extend([
        "",
        "【検索手順】",
        "1. 企業名「" + company.name + "」でオンライン検索を実行してください",
        "2. 企業の公式ウェブサイトを確認してください（会社概要、企業情報、About Us、代表者メッセージページ）",
        "3. 企業情報サイト（Wikipedia、コトバンク、全国法人データベース、企業情報DBなど）を確認してください",
        "4. ニュース記事やプレスリリースを確認してください",
        "5. SNS（Twitter、Facebook、LinkedIn）を確認してください",
        "6. 複数の検索キーワードを試してください（例：「" + company.name + " 会社概要」「" + company.name + " 代表者」「" + company.name + " 設立年」）",
        "",
        "【重要】",
        "- 必ずオンライン検索を実行してください（このモデルはオンライン検索機能を持っています）",
        "- 部分的な情報でも構いません。1つでも情報が見つかれば記入してください",
        "- 検索結果を必ず確認し、該当企業の情報を抽出してください",
        "- 企業名が完全一致しなくても、部分一致や類似名でも該当企業として扱ってください",
        "- 可能な限り多くの情報を抽出してください。情報が見つからないフィールドのみ空文字列（\"\"）にしてください",
        "- 推測や不確実な情報は含めないでください",
        "- 検索結果が空の場合でも、別の検索キーワードで再検索してください",
        "- 複数の情報源を確認し、信頼できる情報のみを抽出してください",
        "",
        "【出力形式】",
        "以下のJSON形式のみを返してください。余計な文章や説明は不要です。",
        f"出力例:\n{target_json}",
    ])
    
    return "\n".join(parts) + "\n"


def build_prompt_with_constraints(
    company: Company,
    missing_fields: Sequence[str],
    context: Optional["EnrichmentContext"] = None,
) -> str:
    """
    gBizINFOの結果を制約として含めたプロンプトを構築（Phase 2: 相互補完設計）
    
    Args:
        company: 企業オブジェクト
        missing_fields: 補完が必要なフィールドのリスト
        context: EnrichmentContext（オプション）
    
    Returns:
        構築されたプロンプト文字列
    """
    # 既存のbuild_promptをベースに
    prompt = build_prompt(company, missing_fields)
    
    # Phase 2: 制約条件を追加（gBizINFOの結果がある場合）
    if context and context.has_gbizinfo_constraints():
        constraints = context.get_constraints_for_prompt()
        if constraints:
            prompt += "\n【制約条件】\n"
            prompt += "\n".join(constraints)
            prompt += "\nこれらと一致しない情報は採用しないこと。\n"
            prompt += "制約条件に基づいて、正確な情報を抽出してください。\n"
    
    # Phase 2: AI出力に正式法人名候補を含めるよう指示（gBizINFO再探索用）
    prompt += "\n【追加出力項目】\n"
    prompt += "可能であれば、以下の情報もJSONに含めてください（見つからない場合は空文字列で構いません）：\n"
    prompt += '- "official_name_candidates": 正式法人名の候補（例: ["株式会社○○", "○○株式会社"]）\n'
    prompt += '- "english_name": 英語名（存在する場合）\n'
    prompt += "これらの情報は、より正確な企業情報の取得に使用されます。\n"
    
    return prompt


def build_system_prompt() -> str:
    """
    システムプロンプトを構築
    
    Returns:
        システムプロンプト文字列
    """
    return """あなたは日本の企業情報を正確に抽出する専門家です。
提供された企業名について、指定されたフィールドの情報をオンライン検索して積極的に抽出してください。

【検索方法】
- 必ずオンライン検索を実行してください（このモデルはオンライン検索機能を持っています）
- 企業名で検索し、公式ウェブサイトを見つけてください
- 企業の「会社概要」「企業情報」「About Us」「代表者メッセージ」「役員一覧」ページを確認してください
- 企業情報サイト（Wikipedia、コトバンク、企業情報データベース、全国法人データベース、帝国データバンクなど）を検索してください
- ニュース記事やプレスリリースを検索してください
- SNS（Twitter、Facebook、LinkedIn）を検索してください
- 複数の検索キーワードを試してください（例：「企業名 会社概要」「企業名 代表者」「企業名 設立年」「企業名 資本金」）
- 検索結果が空の場合でも、別の検索キーワードや企業名のバリエーションで再検索してください

【重要】
- 可能な限り多くの情報を抽出してください。情報が見つからないフィールドのみ空文字列（\"\"）にしてください
- 推測や不確実な情報は含めないでください
- 複数の情報源で確認できた情報のみを返してください
- 回答はJSON形式で、フィールド名をキー、値を値とする形式で返してください
- 余計な説明や文章は不要です。JSONのみを返してください。
- 必ず検索を実行し、情報が見つからない場合のみ空文字列を返してください。
- 検索結果が空の場合でも、別の検索キーワードで再検索してください。
- 積極的に情報を探し、可能な限り多くのフィールドを埋めてください。"""


def apply_rule_based(
    company: Company,
    missing_fields: Sequence[str],
    *,
    corporate_number_api_stats: Optional[Dict[str, int]] = None,
    return_best_match: bool = False,  # Phase 2: best_matchを返すオプション
) -> RuleBasedResult:
    """
    ルールベースの補完を適用する。
    
    Args:
        company: 企業オブジェクト
        missing_fields: 補完が必要なフィールドのリスト
        corporate_number_api_stats: 法人番号APIの統計情報を追跡する辞書（呼び出し回数、成功数、失敗数）
    
    Returns:
        RuleBasedResult: 補完結果
    """
    values: Dict[str, str] = {}
    metadata: Dict[str, str] = {"rule_checked_at": timezone.now().isoformat()}
    
    # 法人番号が不足している場合、法人番号APIを呼び出す
    if not company.corporate_number and settings.CORPORATE_NUMBER_API_TOKEN:
        if corporate_number_api_stats is None:
            corporate_number_api_stats = {"calls": 0, "success": 0, "failed": 0}
        
        try:
            client = CorporateNumberAPIClient()
            corporate_number_api_stats["calls"] += 1
            
            candidates = client.search(company.name, prefecture=company.prefecture)
            
            if candidates:
                # 最適な候補を選択
                from companies.services.corporate_number_client import select_best_match
                best_match = select_best_match(candidates, company.name, prefecture=company.prefecture)
                
                if best_match and best_match.get("corporate_number"):
                    # 法人番号を取得できた場合、補完情報として記録
                    # 実際の更新は別のプロセスで行うが、補完情報として通知に含める
                    corporate_number = best_match["corporate_number"]
                    metadata["corporate_number_found"] = corporate_number
                    # Phase 2: best_matchの正式法人名もmetadataに保存
                    if best_match.get("name"):
                        metadata["gbizinfo_official_name"] = best_match["name"]
                    # 補完情報として記録（corporate_numberはTARGET_FIELDSに含まれていないが、補完情報として記録）
                    values["corporate_number"] = corporate_number
                    
                    # gBizINFOから取得した情報をmetadataに保存（AI補完のプロンプトに含めるため）
                    if best_match.get("address"):
                        metadata["gbizinfo_address"] = best_match["address"]
                    if best_match.get("prefecture"):
                        metadata["gbizinfo_prefecture"] = best_match["prefecture"]
                    
                    # Phase 2: return_best_matchがTrueの場合、best_matchをmetadataに保存
                    if return_best_match:
                        metadata["best_match"] = best_match
                    
                    corporate_number_api_stats["success"] += 1
                    logger.info(
                        "[AI_ENRICH][CORPORATE_NUMBER_API] 法人番号を取得",
                        extra={
                            "company_id": company.id,
                            "corporate_number": best_match["corporate_number"],
                            "address": best_match.get("address"),
                            "prefecture": best_match.get("prefecture"),
                        },
                    )
                else:
                    corporate_number_api_stats["failed"] += 1
                    metadata["gbizinfo_reason"] = "適切な候補が見つかりませんでした"
                    logger.debug(
                        "[AI_ENRICH][CORPORATE_NUMBER_API] 適切な候補が見つかりませんでした",
                        extra={"company_id": company.id},
                    )
            else:
                corporate_number_api_stats["failed"] += 1
                metadata["gbizinfo_reason"] = "gBizINFO APIで候補が見つかりませんでした"
                logger.debug(
                    "[AI_ENRICH][CORPORATE_NUMBER_API] 候補が見つかりませんでした",
                    extra={"company_id": company.id},
                )
        except CorporateNumberAPIError as exc:
            corporate_number_api_stats["failed"] += 1
            error_msg = str(exc)
            # 404エラーは既に空のリストを返しているため、ここには来ない
            # その他のエラーの場合のみ記録
            metadata["gbizinfo_reason"] = f"gBizINFO APIエラー: {error_msg[:50]}"
            logger.warning(
                "[AI_ENRICH][CORPORATE_NUMBER_API] 法人番号API呼び出しに失敗",
                extra={"company_id": company.id, "error": str(exc)},
            )
        except Exception as exc:
            corporate_number_api_stats["failed"] += 1
            error_msg = str(exc)
            metadata["gbizinfo_reason"] = f"gBizINFO APIエラー: {error_msg[:50]}"
            logger.warning(
                "[AI_ENRICH][CORPORATE_NUMBER_API] 予期しないエラー",
                extra={"company_id": company.id, "error": str(exc)},
                exc_info=True,
            )
    
    return RuleBasedResult(values=values, metadata=metadata)
