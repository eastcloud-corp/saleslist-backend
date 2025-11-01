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
    field_labels = TARGET_FIELDS
    lines = [f'  "{field_labels[field]}": ""' for field in missing_fields if field in field_labels]
    if lines:
        target_json = "{\n" + "\n".join(lines) + "\n}"
    else:
        target_json = "{}"

    parts = [
        "次の企業の不足している情報を調査し、JSON形式で回答してください。",
        f"企業名: {company.name}",
        f"URL: {company.website_url or '不明'}",
        f"所在地: {company.prefecture or ''}{company.city or ''}",
    ]
    if missing_fields:
        labels = [field_labels[f] for f in missing_fields if f in field_labels]
        if labels:
            parts.append("欠損項目: " + ", ".join(labels))
    parts.append("出力形式として以下のJSONだけを返してください。余計な文章は不要です。")
    parts.append(f"出力例:\n{target_json}")
    return "\n".join(parts) + "\n"


def apply_rule_based(company: Company, missing_fields: Sequence[str]) -> RuleBasedResult:
    return RuleBasedResult(values={}, metadata={"rule_checked_at": timezone.now().isoformat()})
