
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import BooleanField, Case, Value, When
from django.utils import timezone

from companies.models import Company, CompanyUpdateCandidate
from companies.services.review_ingestion import ingest_rule_based_candidates
from data_collection.tracker import track_data_collection_run

from .enrich_rules import TARGET_FIELDS, apply_rule_based, build_prompt, detect_missing_fields
from .normalizers import normalize_candidate_value
from .exceptions import (
    PowerplexyConfigurationError,
    PowerplexyError,
    PowerplexyRateLimitError,
)
from .notify import notify_error, notify_success, notify_warning
from .powerplexy_client import PowerplexyClient
from .redis_usage import UsageTracker

logger = logging.getLogger(__name__)

AI_SOURCE_DETAIL = "powerplexy"
DEFAULT_DAILY_LIMIT = 500


def _reverse_field_map() -> Dict[str, str]:
    return {label: field for field, label in TARGET_FIELDS.items()}


def _normalize_candidate_value(field: str, value: object) -> str:
    if value is None:
        return ""
    if field in {"established_year", "employee_count", "capital"}:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return digits
    return str(value).strip()


def _companies_requiring_update(limit: int, company_ids: Optional[Sequence[int]] = None) -> List[Company]:
    queryset = Company.objects.all()
    if company_ids:
        queryset = queryset.filter(id__in=company_ids)
    queryset = queryset.annotate(
        never_enriched=Case(
            When(ai_last_enriched_at__isnull=True, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by("-never_enriched", "ai_last_enriched_at", "id")
    targets: List[Company] = []
    for company in queryset.iterator():
        if detect_missing_fields(company):
            targets.append(company)
        if limit and len(targets) >= limit:
            break
    return targets


@shared_task(bind=True, autoretry_for=(PowerplexyRateLimitError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_ai_enrich(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> dict:
    payload = payload or {}
    tracker_metadata = {"options": payload}

    daily_limit = payload.get(
        "limit", getattr(settings, "POWERPLEXY_DAILY_RECORD_LIMIT", DEFAULT_DAILY_LIMIT)
    )

    raw_company_ids = payload.get("company_ids")
    company_ids: Optional[List[int]] = None
    if raw_company_ids is not None:
        if isinstance(raw_company_ids, (int, str)):
            raw_company_ids = [raw_company_ids]
        cleaned: List[int] = []
        for value in raw_company_ids:
            try:
                cleaned.append(int(str(value).strip()))
            except (TypeError, ValueError):
                logger.warning("Invalid company_id provided to AI enrichment: %s", value)
        if cleaned:
            company_ids = cleaned

    with track_data_collection_run(
        "ai.enrich",
        metadata=tracker_metadata,
        execution_uuid=execution_uuid,
    ) as run_tracker:
        usage_tracker = UsageTracker()
        usage_snapshot = usage_tracker.snapshot()
        usage_snapshot_dict = {"calls": usage_snapshot.calls, "cost": usage_snapshot.cost}
        if not usage_tracker.can_execute():
            notify_warning("PowerPlexy月次上限に達したためAI補完をスキップ", extra={
                "usage_calls": usage_snapshot.calls,
                "usage_cost": usage_snapshot.cost,
            })
            run_tracker.complete_success(metadata={
                "result": "skipped",
                "reason": "usage_limit",
                "usage": usage_snapshot_dict,
            })
            return {
                "status": "skipped",
                "reason": "usage_limit",
                "usage": usage_snapshot_dict,
            }

        try:
            client = PowerplexyClient()
        except PowerplexyConfigurationError as exc:
            notify_error("PowerPlexyの設定が不完全なためAI補完をスキップ", extra={"error": str(exc)})
            run_tracker.complete_success(metadata={
                "result": "skipped",
                "reason": "missing_api_key",
            })
            return {"status": "skipped", "reason": "missing_api_key"}

        companies = _companies_requiring_update(daily_limit, company_ids)
        if not companies:
            logger.info("No companies require AI enrichment")
            run_tracker.complete_success(metadata={
                "result": "ok",
                "processed": 0,
                "created_candidates": 0,
            })
            return {"status": "ok", "processed": 0, "created_candidates": 0}

        reverse_map = _reverse_field_map()
        total_candidates = 0
        calls_made = 0

        for company in companies:
            missing_fields = detect_missing_fields(company)
            if not missing_fields:
                continue

            rule_result = apply_rule_based(company, missing_fields)
            provisional_values = dict(rule_result.values)

            remaining = [field for field in missing_fields if field not in provisional_values]
            ai_values: Dict[str, str] = {}
            if remaining:
                prompt = build_prompt(company, remaining)
                try:
                    completion = client.extract_json(prompt)
                except PowerplexyRateLimitError:
                    raise
                except PowerplexyError as exc:
                    notify_error("PowerPlexy呼び出しに失敗しました", extra={"company_id": company.id, "error": str(exc)})
                    continue

                mapped: Dict[str, str] = {}
                for label, value in completion.items():
                    field = reverse_map.get(label)
                    if not field:
                        continue
                    normalized = normalize_candidate_value(field, value)
                    if normalized:
                        mapped[field] = normalized
                ai_values = mapped
                if mapped:
                    usage_tracker.increment()
                    calls_made += 1

            combined: Dict[str, str] = {}
            combined.update({field: value for field, value in provisional_values.items() if value})
            combined.update({field: value for field, value in ai_values.items() if value})
            if not combined:
                continue

            normalized_entries: Dict[str, str] = {}
            for field, raw_value in combined.items():
                normalized = normalize_candidate_value(field, raw_value)
                if normalized:
                    normalized_entries[field] = normalized
                else:
                    logger.debug(
                        "Skipping candidate due to normalization failure",
                        extra={"field": field, "raw_value": raw_value, "company_id": company.id},
                    )

            if not normalized_entries:
                continue

            entry_records = []
            for field, value in normalized_entries.items():
                entry_records.append(
                    {
                        "company_id": company.id,
                        "field": field,
                        "value": value,
                        "source_type": CompanyUpdateCandidate.SOURCE_AI,
                        "source_detail": AI_SOURCE_DETAIL,
                        "confidence": 85 if field in ai_values else 100,
                        "metadata": {
                            "rule_metadata": getattr(rule_result, "metadata", {}),
                            "ai": field in ai_values,
                        },
                    }
                )
            if entry_records:
                ingested = ingest_rule_based_candidates(entry_records)
                total_candidates += len(ingested)
                Company.objects.filter(id=company.id).update(
                    ai_last_enriched_at=timezone.now(),
                    ai_last_enriched_source="ai" if ai_values else "rule",
                )

        usage_after = usage_tracker.snapshot()
        usage_after_dict = {"calls": usage_after.calls, "cost": usage_after.cost}
        notify_success(
            "AI補完バッチが完了しました",
            extra={
                "companies": len(companies),
                "candidates": total_candidates,
                "calls": calls_made,
                "usage": usage_after_dict,
            },
        )

        run_tracker.complete_success(
            metadata={
                "result": "ok",
                "processed": len(companies),
                "created_candidates": total_candidates,
                "calls": calls_made,
                "usage_before": usage_snapshot_dict,
                "usage_after": usage_after_dict,
            },
            input_count=len(companies),
            inserted_count=total_candidates,
            skipped_count=0,
            error_count=0,
        )

        return {
            "status": "ok",
            "processed": len(companies),
            "created_candidates": total_candidates,
            "calls": calls_made,
        }
