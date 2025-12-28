
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import BooleanField, Case, Value, When
from django.utils import timezone

from companies.models import Company, CompanyUpdateCandidate
from companies.services.review_ingestion import ingest_rule_based_candidates
from data_collection.tracker import track_data_collection_run

from .constants import AI_ENRICH_BATCH_SIZE, AI_ENRICH_API_DELAY_SECONDS
from .enrich_rules import TARGET_FIELDS, apply_rule_based, build_prompt, build_system_prompt, detect_missing_fields
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


def _unique_int_list(values: Sequence[int]) -> List[int]:
    seen = set()
    unique: List[int] = []
    for value in values:
        iv = int(value)
        if iv in seen:
            continue
        seen.add(iv)
        unique.append(iv)
    return unique


def _metadata_with_processed(base: Dict[str, object], processed_ids: Sequence[int]) -> Dict[str, object]:
    unique_ids = _unique_int_list(processed_ids)
    metadata: Dict[str, object] = {**base, "processed_count": len(unique_ids)}
    if unique_ids:
        metadata["processed_company_ids"] = unique_ids[:100]
        if len(unique_ids) > 100:
            metadata["processed_company_ids_truncated"] = True
    return metadata


def _reverse_field_map() -> Dict[str, str]:
    return {label: field for field, label in TARGET_FIELDS.items()}


def _normalize_candidate_value(field: str, value: object) -> str:
    if value is None:
        return ""
    if field in {"established_year", "employee_count", "capital"}:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return digits
    return str(value).strip()


def _companies_requiring_update(limit: int, company_ids: Optional[Sequence[int]] = None, offset: int = 0) -> List[Company]:
    """
    補完が必要な企業を取得する。
    
    Args:
        limit: 取得件数
        company_ids: 特定の企業IDのみを対象とする場合
        offset: スキップする件数（バッチ分割用）
    """
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
    skipped = 0
    for company in queryset.iterator():
        if detect_missing_fields(company):
            if skipped < offset:
                skipped += 1
                continue
            targets.append(company)
            if limit and len(targets) >= limit:
                break
    return targets


@shared_task(bind=True, autoretry_for=(PowerplexyRateLimitError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_ai_enrich_scheduled(self) -> dict:
    """
    Celery Beat 用のスケジュール実行ラッパー。
    必ず enqueue_job 経由で AI 補完を実行する。
    
    200件以上でも安全に流せるよう、バッチ分割して実行する。
    1バッチ = AI_ENRICH_BATCH_SIZE件（デフォルト25件）
    """
    from data_collection.services import enqueue_job

    daily_limit = getattr(settings, "POWERPLEXY_DAILY_RECORD_LIMIT", None)
    if daily_limit is None:
        daily_limit = 3 if settings.DEBUG else DEFAULT_DAILY_LIMIT

    batch_size = AI_ENRICH_BATCH_SIZE
    total_batches = (daily_limit + batch_size - 1) // batch_size  # 切り上げ

    logger.info(
        "[AI_ENRICH][SCHEDULED] enqueue_job start (batch mode)",
        extra={
            "total_limit": daily_limit,
            "batch_size": batch_size,
            "total_batches": total_batches,
        },
    )

    try:
        runs = []
        async_results = []
        execution_uuid = None

        # バッチごとに分割してenqueue_jobを呼び出す
        for batch_index in range(total_batches):
            offset = batch_index * batch_size
            batch_limit = min(batch_size, daily_limit - offset)

            if batch_limit <= 0:
                break

            options = {
                "limit": batch_limit,
                "offset": offset,
            }

            run, async_result = enqueue_job(
                job_name="ai.enrich",
                options=options,
            )

            # 最初のバッチのexecution_uuidを記録（全バッチで同一になる想定だが念のため）
            if execution_uuid is None:
                execution_uuid = str(run.execution_uuid)

            runs.append(run)
            if async_result:
                async_results.append(async_result)

            logger.info(
                "[AI_ENRICH][SCHEDULED] batch enqueued",
                extra={
                    "batch_index": batch_index + 1,
                    "total_batches": total_batches,
                    "batch_limit": batch_limit,
                    "offset": offset,
                    "run_id": str(run.id),
                    "execution_uuid": str(run.execution_uuid),
                    "task_id": async_result.id if async_result else None,
                },
            )

        logger.info(
            "[AI_ENRICH][SCHEDULED] all batches enqueued",
            extra={
                "total_batches": len(runs),
                "execution_uuid": execution_uuid,
                "total_task_ids": len(async_results),
            },
        )

        return {
            "status": "queued",
            "total_batches": len(runs),
            "execution_uuid": execution_uuid,
            "run_ids": [str(run.id) for run in runs],
            "task_ids": [ar.id for ar in async_results if ar],
            "total_limit": daily_limit,
        }
    except Exception as exc:
        logger.error(
            "[AI_ENRICH][SCHEDULED] enqueue_job failed",
            extra={"error": str(exc)},
            exc_info=True,
        )
        notify_error("AI補完タスクのスケジュール実行に失敗しました", extra={"error": str(exc)})
        raise


@shared_task(bind=True, autoretry_for=(PowerplexyRateLimitError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_ai_enrich(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> dict:
    """
    AI補完タスクのメイン処理。
    
    注意: このタスクは enqueue_job 経由でのみ実行されることを想定しています。
    execution_uuid が None の場合は RuntimeError を発生させます。
    """
    if execution_uuid is None:
        raise RuntimeError(
            "run_ai_enrich must be executed via enqueue_job. "
            "Use run_ai_enrich_scheduled for Celery Beat, or enqueue_job for manual execution."
        )

    payload = payload or {}
    tracker_metadata = {"options": payload}
    processed_company_ids: List[int] = []

    daily_limit = payload.get(
        "limit", getattr(settings, "POWERPLEXY_DAILY_RECORD_LIMIT", DEFAULT_DAILY_LIMIT)
    )
    offset = payload.get("offset", 0)

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
            run_tracker.complete_success(metadata=_metadata_with_processed(
                {
                    "result": "skipped",
                    "reason": "usage_limit",
                    "usage": usage_snapshot_dict,
                },
                [],
            ))
            return {
                "status": "skipped",
                "reason": "usage_limit",
                "processed_company_ids": [],
                "usage": usage_snapshot_dict,
            }

        try:
            client = PowerplexyClient()
        except PowerplexyConfigurationError as exc:
            notify_error("PowerPlexyの設定が不完全なためAI補完をスキップ", extra={"error": str(exc)})
            run_tracker.complete_success(metadata=_metadata_with_processed(
                {
                    "result": "skipped",
                    "reason": "missing_api_key",
                },
                [],
            ))
            return {"status": "skipped", "reason": "missing_api_key", "processed_company_ids": []}

        companies = _companies_requiring_update(daily_limit, company_ids, offset=offset)
        processed_company_ids = [company.id for company in companies]
        if not companies:
            logger.info("No companies require AI enrichment")
            run_tracker.complete_success(metadata=_metadata_with_processed(
                {
                    "result": "ok",
                    "processed": 0,
                    "created_candidates": 0,
                },
                [],
            ))
            return {"status": "ok", "processed": 0, "created_candidates": 0, "processed_company_ids": []}

        reverse_map = _reverse_field_map()
        total_candidates = 0
        calls_made = 0
        success_company_ids: List[int] = []
        failed_company_ids: List[int] = []
        error_details: List[Dict[str, Any]] = []

        for company in companies:
            try:
                missing_fields = detect_missing_fields(company)
                if not missing_fields:
                    success_company_ids.append(company.id)
                    continue

                rule_result = apply_rule_based(company, missing_fields)
                provisional_values = dict(rule_result.values)

                remaining = [field for field in missing_fields if field not in provisional_values]
                ai_values: Dict[str, str] = {}
                if remaining:
                    prompt = build_prompt(company, remaining)
                    system_prompt = build_system_prompt()
                    logger.info(
                        "[AI_ENRICH][SYSTEM_PROMPT]",
                        extra={
                            "company_id": company.id,
                            "system_prompt": system_prompt,
                            "system_prompt_length": len(system_prompt),
                        },
                    )
                    try:
                        completion = client.extract_json(prompt=prompt, system_prompt=system_prompt)
                    except PowerplexyRateLimitError:
                        # Rate Limitは再スローしてCelery retryに任せる
                        raise
                    except PowerplexyError as exc:
                        logger.warning(
                            "[AI_ENRICH][FAILED] PowerPlexy呼び出しに失敗",
                            extra={
                                "company_id": company.id,
                                "error": str(exc),
                                "execution_uuid": execution_uuid,
                            },
                        )
                        failed_company_ids.append(company.id)
                        error_details.append({
                            "company_id": company.id,
                            "error_type": "PowerPlexyError",
                            "error": str(exc),
                        })
                        continue
                    
                    # Rate Limit対策: API呼び出し間隔を空ける
                    if calls_made > 0:
                        time.sleep(AI_ENRICH_API_DELAY_SECONDS)

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
                    success_company_ids.append(company.id)
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
                    success_company_ids.append(company.id)
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
                    success_company_ids.append(company.id)
                else:
                    success_company_ids.append(company.id)
            except Exception as exc:
                # 予期しないエラーも記録（部分成功前提）
                logger.warning(
                    "[AI_ENRICH][FAILED] 予期しないエラー",
                    extra={
                        "company_id": company.id,
                        "error": str(exc),
                        "execution_uuid": execution_uuid,
                    },
                    exc_info=True,
                )
                failed_company_ids.append(company.id)
                error_details.append({
                    "company_id": company.id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

        usage_after = usage_tracker.snapshot()
        usage_after_dict = {"calls": usage_after.calls, "cost": usage_after.cost}
        
        # 失敗した会社IDをmetadataに保存（再実行用）
        metadata_base = {
            "result": "ok",
            "processed": len(companies),
            "success_count": len(success_company_ids),
            "failed_count": len(failed_company_ids),
            "created_candidates": total_candidates,
            "calls": calls_made,
            "usage_before": usage_snapshot_dict,
            "usage_after": usage_after_dict,
        }
        
        if failed_company_ids:
            metadata_base["failed_company_ids"] = failed_company_ids
            metadata_base["error_details"] = error_details[:10]  # 最初の10件のみ保存
            notify_warning(
                "AI補完バッチが完了しました（一部失敗）",
                extra={
                    "companies": len(companies),
                    "success": len(success_company_ids),
                    "failed": len(failed_company_ids),
                    "failed_company_ids": failed_company_ids,
                    "candidates": total_candidates,
                    "calls": calls_made,
                    "usage": usage_after_dict,
                },
            )
        else:
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
            metadata=_metadata_with_processed(
                metadata_base,
                processed_company_ids,
            ),
            input_count=len(companies),
            inserted_count=total_candidates,
            skipped_count=0,
            error_count=len(failed_company_ids),
        )

        return {
            "status": "ok",
            "processed": len(companies),
            "success_count": len(success_company_ids),
            "failed_count": len(failed_company_ids),
            "failed_company_ids": failed_company_ids,
            "created_candidates": total_candidates,
            "calls": calls_made,
            "processed_company_ids": processed_company_ids,
        }
