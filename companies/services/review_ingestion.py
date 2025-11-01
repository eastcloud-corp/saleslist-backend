import random
from datetime import timedelta
from typing import Callable, Iterable, List, Mapping, Optional, Sequence

from django.db import transaction
from django.utils import timezone

from ..models import (
    Company,
    CompanyReviewBatch,
    CompanyReviewItem,
    CompanyUpdateCandidate,
    ExternalSourceRecord,
)

SAMPLE_RULE_FIELDS = [
    "website_url",
    "contact_email",
    "phone",
    "prefecture",
    "city",
    "industry",
    "employee_count",
    "revenue",
    "capital",
    "established_year",
    "tob_toc_type",
    "notes",
    "business_description",
    "corporate_number",
]


def _default_normalizer(value: Optional[object]) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _normalize_corporate_number(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value).strip() if ch.isdigit())

def _normalize_numeric(value: Optional[object]) -> str:
    if value is None:
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits

def _normalize_phone(value: Optional[object]) -> str:
    if value is None:
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits


FIELD_NORMALIZERS: Mapping[str, Callable[[Optional[object]], str]] = {
    "corporate_number": _normalize_corporate_number,
    "employee_count": _normalize_numeric,
    "revenue": _normalize_numeric,
    "capital": _normalize_numeric,
    "established_year": _normalize_numeric,
    "phone": _normalize_phone,
}

DEFAULT_RULE_BASED_COOLDOWN_DAYS = 30

PREFECTURE_SAMPLES = [
    "東京都",
    "神奈川県",
    "大阪府",
    "愛知県",
    "福岡県",
    "北海道",
    "宮城県",
    "広島県",
    "京都府",
    "静岡県",
]

TOB_TOC_CHOICES = ["toB", "toC", "Both"]


def is_candidate_blocked(company: Company, field: str, candidate_value: str) -> bool:
    """否認済みで再提案ブロック対象かを判定する。"""

    value_hash = CompanyUpdateCandidate.make_value_hash(field, candidate_value or "")
    return CompanyUpdateCandidate.objects.filter(
        company=company,
        field=field,
        value_hash=value_hash,
        status=CompanyUpdateCandidate.STATUS_REJECTED,
        block_reproposal=True,
    ).exists()


def create_candidate_entry(
    *,
    company: Company,
    field: str,
    candidate_value: str,
    source_type: str = CompanyUpdateCandidate.SOURCE_RULE,
    source_detail: str = "",
    confidence: int = 100,
    source_company_name: str = "",
    source_corporate_number: str = "",
) -> Optional[CompanyUpdateCandidate]:
    """
    候補のレコードを生成する。再提案ブロック条件に該当する場合は None を返す。
    """

    normalized_value = candidate_value or ""
    if not isinstance(normalized_value, str):
        normalized_value = str(normalized_value)
    value_hash = CompanyUpdateCandidate.make_value_hash(field, normalized_value)

    blocked = CompanyUpdateCandidate.objects.filter(
        company=company,
        field=field,
        value_hash=value_hash,
        status=CompanyUpdateCandidate.STATUS_REJECTED,
        block_reproposal=True,
    ).exists()
    if blocked:
        return None

    return CompanyUpdateCandidate.objects.create(
        company=company,
        field=field,
        candidate_value=normalized_value,
        value_hash=value_hash,
        source_type=source_type,
        source_detail=source_detail,
        confidence=confidence,
        status=CompanyUpdateCandidate.STATUS_PENDING,
        collected_at=timezone.now(),
        source_company_name=source_company_name or company.name,
        source_corporate_number=_normalize_corporate_number(source_corporate_number or company.corporate_number),
    )


def ensure_review_batch(company: Company) -> CompanyReviewBatch:
    batch = (
        CompanyReviewBatch.objects.select_for_update()
        .filter(
            company=company,
            status__in=[
                CompanyReviewBatch.STATUS_PENDING,
                CompanyReviewBatch.STATUS_IN_REVIEW,
            ],
        )
        .first()
    )
    if not batch:
        batch = CompanyReviewBatch.objects.create(company=company, status=CompanyReviewBatch.STATUS_PENDING)
    return batch


class CorporateNumberEntry(dict):
    """Typed helper for corporate number ingestion."""


class RuleBasedEntry(dict):
    """Typed helper for generic rule-based ingestion."""


def _normalize_candidate_value(field: str, value: Optional[object]) -> str:
    normalizer = FIELD_NORMALIZERS.get(field, _default_normalizer)
    normalized = normalizer(value)
    return normalized if isinstance(normalized, str) else _default_normalizer(normalized)


def _normalize_current_value(field: str, value: Optional[object]) -> str:
    # 現在値未設定の場合は空文字扱い
    if value is None:
        return ""
    return _normalize_candidate_value(field, value)


@transaction.atomic
def ingest_rule_based_candidates(entries: Sequence[dict]) -> List[CompanyReviewItem]:
    """
    ルールベース由来の候補をレビューキューに投入する。
    entries: [
        {
            "company_id": int,
            "field": str,
            "value": Any,
            "source_type": Optional[str],
            "source_detail": Optional[str],
            "confidence": Optional[int],
            "source_company_name": Optional[str],
            "source_corporate_number": Optional[str],
            "source": Optional[str],
            "metadata": Optional[dict],
            "cooldown_days": Optional[int],
        }
    ]
    """

    created_items: List[CompanyReviewItem] = []
    now = timezone.now()

    for raw_entry in entries:
        entry = RuleBasedEntry(raw_entry)
        company_id = entry.get("company_id")
        field = entry.get("field")
        if not company_id or not field:
            continue

        try:
            company = Company.objects.select_for_update().get(pk=company_id)
        except Company.DoesNotExist:
            continue

        normalized_value = _normalize_candidate_value(field, entry.get("value"))
        if normalized_value == "":
            # 空値はスキップ（将来値0等を扱う場合は拡張）
            continue

        current_value = getattr(company, field, None)
        value_hash = CompanyUpdateCandidate.make_value_hash(field, normalized_value)
        source_id = entry.get("source") or entry.get("source_detail") or "rule-based"
        cooldown_raw = entry.get("cooldown_days")
        if field == "corporate_number" and cooldown_raw in (None, ""):
            cooldown_days = 30
        else:
            cooldown_days = DEFAULT_RULE_BASED_COOLDOWN_DAYS if cooldown_raw in (None, "") else int(cooldown_raw)
        metadata = entry.get("metadata")

        record = (
            ExternalSourceRecord.objects.select_for_update()
            .filter(company=company, field=field, source=source_id)
            .first()
        )

        within_cooldown = False
        same_hash = False
        if record and record.last_fetched_at:
            within_cooldown = cooldown_days > 0 and (now - record.last_fetched_at) < timedelta(days=cooldown_days)
            same_hash = record.data_hash == value_hash

        normalized_current = _normalize_current_value(field, current_value)
        if normalized_current == normalized_value:
            # 既存値と同じ場合は候補にしないが取得履歴は更新
            if record is None:
                record = ExternalSourceRecord(company=company, field=field, source=source_id)
            record.last_fetched_at = now
            record.data_hash = value_hash
            if metadata is not None:
                record.metadata = metadata
            record.save(force_insert=record.pk is None)
            continue

        if record and within_cooldown and same_hash:
            # ハッシュ不変かつクールダウン期間内
            record.last_fetched_at = now
            record.data_hash = value_hash
            if metadata is not None:
                record.metadata = metadata
            record.save(update_fields=["last_fetched_at", "data_hash", "metadata", "updated_at"])
            continue

        if CompanyUpdateCandidate.objects.filter(
            company=company,
            field=field,
            value_hash=value_hash,
            status=CompanyUpdateCandidate.STATUS_PENDING,
        ).exists():
            # 既に同じ値でレビュー待ちがある場合は履歴のみ更新
            if record is None:
                record = ExternalSourceRecord(company=company, field=field, source=source_id)
            record.last_fetched_at = now
            record.data_hash = value_hash
            if metadata is not None:
                record.metadata = metadata
            record.save(force_insert=record.pk is None)
            continue

        candidate = create_candidate_entry(
            company=company,
            field=field,
            candidate_value=normalized_value,
            source_type=entry.get("source_type", CompanyUpdateCandidate.SOURCE_RULE),
            source_detail=entry.get("source_detail", ""),
            confidence=int(entry.get("confidence", 100)),
            source_company_name=entry.get("source_company_name", company.name),
            source_corporate_number=entry.get("source_corporate_number", company.corporate_number or ""),
        )
        if not candidate:
            if record is None:
                record = ExternalSourceRecord(company=company, field=field, source=source_id)
            record.last_fetched_at = now
            record.data_hash = value_hash
            if metadata is not None:
                record.metadata = metadata
            record.save(force_insert=record.pk is None)
            continue

        batch = ensure_review_batch(company)
        item = CompanyReviewItem.objects.create(
            batch=batch,
            candidate=candidate,
            field=field,
            current_value=normalized_current,
            candidate_value=normalized_value,
            confidence=candidate.confidence,
        )

        batch.status = CompanyReviewBatch.STATUS_PENDING
        batch.updated_at = now
        batch.save(update_fields=["status", "updated_at"])

        created_items.append(item)

        if record is None:
            record = ExternalSourceRecord(company=company, field=field, source=source_id)
        record.last_fetched_at = now
        record.data_hash = value_hash
        if metadata is not None:
            record.metadata = metadata
        record.save(force_insert=record.pk is None)

    return created_items


@transaction.atomic
def ingest_corporate_number_candidates(entries: Sequence[dict]) -> List[CompanyReviewItem]:
    """法人番号の候補をレビューキューに投入する。"""

    normalized_entries = []
    for raw_entry in entries:
        entry = CorporateNumberEntry(raw_entry)
        normalized_entries.append(
            {
                "company_id": entry.get("company_id"),
                "field": "corporate_number",
                "value": entry.get("corporate_number"),
                "source_type": CompanyUpdateCandidate.SOURCE_RULE,
                "source_detail": entry.get("source_detail", "corporate-number-import"),
                "confidence": entry.get("confidence", 100),
                "source_company_name": entry.get("source_company_name"),
                "source_corporate_number": entry.get("source_corporate_number"),
                "source": entry.get("source", "corporate-number-import"),
                "metadata": entry.get("metadata"),
                "cooldown_days": entry.get("cooldown_days"),
            }
        )

    return ingest_rule_based_candidates(normalized_entries)


def _generate_sample_value(field: str, company: Company) -> str:
    """ダミー候補値を生成（開発用）"""
    suffix = timezone.now().strftime("%m%d%H%M")
    if field == "website_url":
        return f"https://www.{company.name.lower().replace(' ', '')}-{suffix}.co.jp"
    if field == "contact_email":
        local = company.name.lower().replace(" ", "_")
        return f"{local}-{suffix}@example.com"
    if field == "phone":
        return f"03-{random.randint(1111, 9999)}-{random.randint(1000, 9999)}"
    if field == "prefecture":
        return random.choice(PREFECTURE_SAMPLES)
    if field == "city":
        return f"{random.choice(['中央区', '渋谷区', '港区', '北区', '中区', '南区'])}{random.randint(1, 9)}丁目"
    if field == "industry":
        return random.choice(
            [
                "IT・ソフトウェア",
                "マーケティング・広告",
                "製造業",
                "人材・派遣",
                "金融・保険",
                "コンサルティング",
            ]
        )
    if field == "employee_count":
        return str(random.choice([25, 48, 120, 230, 480, 1000]))
    if field == "revenue":
        return str(random.choice([5_000_0000, 12_000_0000, 25_000_0000, 60_000_0000]))
    if field == "capital":
        return str(random.choice([5_000_000, 10_000_000, 50_000_000]))
    if field == "established_year":
        return str(random.randint(1975, timezone.now().year))
    if field == "tob_toc_type":
        return random.choice(TOB_TOC_CHOICES)
    if field == "notes":
        return f"{timezone.now():%Y-%m-%d} 時点のヒアリングメモ"
    if field == "business_description":
        return f"{company.name} は最新テクノロジーを活用したサービスを提供しています（{suffix}）"
    if field == "corporate_number":
        return f"{random.randint(10**12, 10**13 - 1)}"
    return f"{company.name} 更新候補 {suffix}"


@transaction.atomic
def generate_sample_candidates(
    *,
    company: Optional[Company] = None,
    fields: Optional[Iterable[str]] = None,
) -> List[CompanyReviewItem]:
    """
    開発用: ダミーの補完候補を生成してレビューに投入する。
    """
    if company is None:
        company = Company.objects.order_by("-updated_at").first()
    if not company:
        raise ValueError("企業データが存在しません。先に企業を登録してください。")

    target_fields = list(fields) if fields else SAMPLE_RULE_FIELDS
    created_items: List[CompanyReviewItem] = []

    batch = (
        CompanyReviewBatch.objects.select_for_update()
        .filter(
            company=company,
            status__in=[
                CompanyReviewBatch.STATUS_PENDING,
                CompanyReviewBatch.STATUS_IN_REVIEW,
            ],
        )
        .first()
    )
    if not batch:
        batch = CompanyReviewBatch.objects.create(company=company, status=CompanyReviewBatch.STATUS_PENDING)

    for field in target_fields:
        if field not in SAMPLE_RULE_FIELDS:
            continue

        current_value = getattr(company, field, None)
        candidate_value = _generate_sample_value(field, company)

        candidate = create_candidate_entry(
            company=company,
            field=field,
            candidate_value=candidate_value,
            source_type=CompanyUpdateCandidate.SOURCE_RULE,
            source_detail="sample-rule-generator",
            confidence=100,
            source_company_name=company.name,
            source_corporate_number=company.corporate_number,
        )
        if not candidate:
            continue

        item = CompanyReviewItem.objects.create(
            batch=batch,
            candidate=candidate,
            field=field,
            current_value=str(current_value or ""),
            candidate_value=candidate_value,
            confidence=candidate.confidence,
        )
        created_items.append(item)

    batch.status = CompanyReviewBatch.STATUS_PENDING
    batch.updated_at = timezone.now()
    batch.save(update_fields=["status", "updated_at"])
    return created_items
