from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from django.utils import timezone

from companies.models import Company


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

    # プロンプトの構築
    parts = [
        "以下の企業について、指定された情報を検索して抽出してください。",
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
        "【重要】",
        "- 情報が見つからないフィールドは空文字列（\"\"）にしてください",
        "- 部分的な情報でも構いません。1つでも情報が見つかれば記入してください",
        "- 検索結果を必ず確認し、該当企業の情報を抽出してください",
        "- 企業名が完全一致しなくても、部分一致や類似名でも該当企業として扱ってください",
        "",
        "【出力形式】",
        "以下のJSON形式のみを返してください。余計な文章や説明は不要です。",
        f"出力例:\n{target_json}",
    ])
    
    return "\n".join(parts) + "\n"


def build_system_prompt() -> str:
    """
    システムプロンプトを構築
    
    Returns:
        システムプロンプト文字列
    """
    return """あなたは日本の企業情報を正確に抽出する専門家です。
提供された企業名について、指定されたフィールドの情報を検索して抽出してください。
情報が見つからない場合は、そのフィールドは空文字列（\"\"）にしてください。
回答はJSON形式で、フィールド名をキー、値を値とする形式で返してください。
余計な説明や文章は不要です。JSONのみを返してください。"""


def apply_rule_based(company: Company, missing_fields: Sequence[str]) -> RuleBasedResult:
    return RuleBasedResult(values={}, metadata={"rule_checked_at": timezone.now().isoformat()})
