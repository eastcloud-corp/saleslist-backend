import logging
import time
from collections import Counter
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from companies.models import Company, CompanyReviewItem, CompanyUpdateCandidate, ExternalSourceRecord
from companies.services.corporate_number_client import (
    CorporateNumberAPIClient,
    CorporateNumberAPIError,
    select_best_match,
)
from companies.services.review_ingestion import ingest_corporate_number_candidates, ingest_rule_based_candidates

STAT_KEYS = (
    "checked",
    "matched",
    "not_found",
    "errors",
    "skipped_prefecture",
    "skipped_name",
    "skipped_cooldown",
    "skipped_rate_limit",
)

logger = logging.getLogger(__name__)

DEFAULT_DAILY_LIMIT = getattr(settings, "CORPORATE_NUMBER_API_DAILY_LIMIT", 5000)
DEFAULT_INTERVAL_SECONDS = getattr(settings, "CORPORATE_NUMBER_API_INTERVAL_SECONDS", 2)
DEFAULT_COMPANY_COOLDOWN_DAYS = getattr(settings, "CORPORATE_NUMBER_API_COMPANY_COOLDOWN_DAYS", 30)

_CACHE_PREFIX = "corporate_number_api"
_CACHE_LAST_CALL_KEY = f"{_CACHE_PREFIX}:last_call"


def _seconds_until_tomorrow(now: timezone.datetime) -> int:
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - now).total_seconds()), 1)


def _get_daily_counter_key(now: timezone.datetime) -> str:
    return f"{_CACHE_PREFIX}:daily:{now:%Y%m%d}"


def _get_daily_count(now: timezone.datetime) -> Tuple[str, int]:
    key = _get_daily_counter_key(now)
    count = cache.get(key)
    if count is None:
        cache.add(key, 0, timeout=_seconds_until_tomorrow(now))
        count = cache.get(key) or 0
    return key, int(count)


def _set_daily_count(key: str, value: int, now: timezone.datetime) -> None:
    cache.set(key, value, timeout=_seconds_until_tomorrow(now))


def _respect_interval(last_call: Optional[timezone.datetime], interval_seconds: int, now: timezone.datetime) -> timezone.datetime:
    if interval_seconds <= 0:
        cache.set(_CACHE_LAST_CALL_KEY, now, timeout=interval_seconds * 2 if interval_seconds else 5)
        return now
    if last_call is not None:
        elapsed = (now - last_call).total_seconds()
        if elapsed < interval_seconds:
            time.sleep(interval_seconds - elapsed)
    cache.set(_CACHE_LAST_CALL_KEY, timezone.now(), timeout=interval_seconds * 2)
    return cache.get(_CACHE_LAST_CALL_KEY)


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in (value or "") if not ch.isspace()).lower()


def _normalize_numeric_string(value: Optional[str]) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _extract_rule_entries_from_candidate(
    *,
    company: Company,
    candidate: Dict[str, object],
    source_detail: str,
    cooldown_days: int,
) -> List[dict]:
    raw = candidate.get("raw") or {}
    if not isinstance(raw, dict):
        raw = {}

    entries: List[dict] = []
    metadata = {"raw": raw, "source": source_detail}

    def push(field: str, value: Optional[str]) -> None:
        normalized = (value or "").strip()
        if not normalized:
            return
        entries.append(
            {
                "company_id": company.id,
                "field": field,
                "value": normalized,
                "source_type": CompanyUpdateCandidate.SOURCE_RULE,
                "source_detail": source_detail,
                "source": source_detail,
                "confidence": 100,
                "metadata": metadata,
                "cooldown_days": cooldown_days,
                "source_company_name": candidate.get("name") or company.name,
                "source_corporate_number": candidate.get("corporate_number") or company.corporate_number or "",
            }
        )

    prefecture = raw.get("prefectureName") or candidate.get("prefecture")
    push("prefecture", prefecture)

    city_parts = [
        raw.get("cityName"),
        raw.get("streetNumber"),
        raw.get("blockNumber"),
        raw.get("buildingName"),
    ]
    city = "".join(str(part) for part in city_parts if part)
    push("city", city)

    capital_stock = raw.get("capitalStock")
    if capital_stock:
        push("capital", _normalize_numeric_string(capital_stock))

    phone_number = raw.get("phoneNumber")
    if phone_number:
        push("phone", _normalize_numeric_string(phone_number))

    return entries


def run_corporate_number_import(
    *,
    company_ids: Optional[List[int]] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    prefecture_strict: bool = False,
    allow_missing_token: bool = False,
    force_refresh: bool = False,
) -> Dict[str, object]:
    """
    法人番号APIからデータを取得し、レビュー候補を投入する共通処理。
    コマンド／APIの双方から利用できるよう関数化している。
    """
    if not settings.CORPORATE_NUMBER_API_TOKEN:
        if allow_missing_token:
            stats_dict = {key: 0 for key in STAT_KEYS}
            summary = "法人番号APIトークンが未設定のため処理をスキップしました。"
            return {
                "stats": stats_dict,
                "entries_count": 0,
                "created_count": 0,
                "batch_ids": [],
                "dry_run": True,
                "summary": summary,
                "skipped": True,
                "skipped_reason": "missing_token",
                "force_refresh": force_refresh,
            }
        raise CommandError("CORPORATE_NUMBER_API_TOKEN が設定されていません。")

    queryset = Company.objects.all()
    if company_ids:
        queryset = queryset.filter(id__in=company_ids)
    else:
        queryset = queryset.filter(Q(corporate_number__isnull=True) | Q(corporate_number__exact=""))

    if limit:
        queryset = queryset.order_by("id")[:limit]

    client = CorporateNumberAPIClient()

    entries: List[Dict[str, object]] = []
    rule_entries: List[dict] = []
    stats = Counter()
    now = timezone.now()
    base_daily_limit = DEFAULT_DAILY_LIMIT if DEFAULT_DAILY_LIMIT and DEFAULT_DAILY_LIMIT > 0 else None
    daily_limit = None if force_refresh else base_daily_limit
    interval_seconds = 0 if force_refresh else max(DEFAULT_INTERVAL_SECONDS, 0)
    company_cooldown_days = 0 if force_refresh else max(DEFAULT_COMPANY_COOLDOWN_DAYS, 0)

    daily_key, current_daily_count = _get_daily_count(now)
    last_call = cache.get(_CACHE_LAST_CALL_KEY)
    daily_limit_reached = False

    for company in queryset:
        stats["checked"] += 1

        if company_cooldown_days > 0 and not force_refresh:
            record = ExternalSourceRecord.objects.filter(
                company=company,
                field="corporate_number",
                source__in=["nta-api", "corporate-number-import"],
            ).first()
            if record and record.last_fetched_at and now - record.last_fetched_at < timedelta(days=company_cooldown_days):
                stats["skipped_cooldown"] += 1
                continue

        if daily_limit is not None and current_daily_count >= daily_limit:
            stats["skipped_rate_limit"] += 1
            daily_limit_reached = True
            break

        try:
            last_call = _respect_interval(last_call, interval_seconds, timezone.now())
            candidates = client.search(company.name, prefecture=company.prefecture)
            last_call = timezone.now()
            current_daily_count += 1
            _set_daily_count(daily_key, current_daily_count, last_call)
        except CorporateNumberAPIError as exc:
            logger.warning("法人番号API取得失敗 company_id=%s name=%s error=%s", company.id, company.name, exc)
            stats["errors"] += 1
            continue

        if not candidates:
            stats["not_found"] += 1
            continue

        candidate = select_best_match(candidates, company.name, prefecture=company.prefecture)
        if not candidate:
            stats["not_found"] += 1
            continue

        if prefecture_strict and company.prefecture and candidate.get("prefecture") != company.prefecture:
            stats["skipped_prefecture"] += 1
            continue

        if candidate.get("name_normalized") and candidate["name_normalized"] != _normalize_name(company.name):
            stats["skipped_name"] += 1
            continue

        entries.append(
            {
                "company_id": company.id,
                "corporate_number": candidate["corporate_number"],
                "source_company_name": candidate.get("name"),
                "source_detail": candidate.get("raw", {}).get("sequenceNumber", "nta-api"),
                "source": "nta-api",
                "cooldown_days": 0 if force_refresh else company_cooldown_days,
                "metadata": {
                    "prefecture": candidate.get("prefecture"),
                    "raw": candidate.get("raw"),
                },
            }
        )
        stats["matched"] += 1

        rule_entries.extend(
            _extract_rule_entries_from_candidate(
                company=company,
                candidate=candidate,
                source_detail="nta-api",
                cooldown_days=0 if force_refresh else company_cooldown_days,
            )
        )

    created_corporate_items: List[CompanyReviewItem] = []
    created_rule_items: List[CompanyReviewItem] = []
    if not dry_run:
        with transaction.atomic():
            if entries:
                created_corporate_items = ingest_corporate_number_candidates(entries)
            if rule_entries:
                created_rule_items = ingest_rule_based_candidates(rule_entries)

    created_items = created_corporate_items + created_rule_items

    stats_dict = {key: int(stats.get(key, 0)) for key in STAT_KEYS}
    batch_ids = sorted({item.batch_id for item in created_items})
    created_count = len(created_items)
    summary_parts = [
        "法人番号取得 完了:",
        f"checked={stats_dict['checked']}",
        f"matched={stats_dict['matched']}",
        f"not_found={stats_dict['not_found']}",
        f"errors={stats_dict['errors']}",
        f"skipped_prefecture={stats_dict['skipped_prefecture']}",
        f"skipped_name={stats_dict['skipped_name']}",
        f"skipped_cooldown={stats_dict['skipped_cooldown']}",
        f"skipped_rate_limit={stats_dict['skipped_rate_limit']}",
        f"created={created_count}",
    ]
    if daily_limit_reached:
        summary_parts.append("日次制限に達したため取得を停止しました。")
    summary = " ".join(summary_parts)

    return {
        "stats": stats_dict,
        "entries_count": len(entries),
        "rule_entries_count": len(rule_entries),
        "created_count": created_count,
        "batch_ids": batch_ids,
        "dry_run": dry_run,
        "summary": summary,
        "skipped": False,
        "force_refresh": force_refresh,
        "daily_rate_limit_reached": daily_limit_reached,
    }


class Command(BaseCommand):
    help = "法人番号APIから法人番号を取得し、レビュー候補として投入します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=int,
            action="append",
            dest="company_ids",
            help="対象企業ID。複数指定可。",
        )
        parser.add_argument(
            "--limit",
            type=int,
            dest="limit",
            help="処理対象件数の上限。",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="候補を投入せず結果のみ表示します。",
        )
        parser.add_argument(
            "--prefecture-strict",
            action="store_true",
            dest="prefecture_strict",
            help="都道府県が一致する候補のみ採用します。",
        )

    def handle(self, *args, **options):
        result = run_corporate_number_import(
            company_ids=options.get("company_ids"),
            limit=options.get("limit"),
            dry_run=options.get("dry_run", False),
            prefecture_strict=options.get("prefecture_strict", False),
        )

        self.stdout.write(self.style.SUCCESS(result["summary"]))
        if result["dry_run"]:
            self.stdout.write(self.style.WARNING("dry-run のため候補は投入していません。"))
