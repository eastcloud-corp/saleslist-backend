from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Sequence

from celery import shared_task, group
from django.conf import settings

from companies.facebook_client import (
    FacebookAPIError,
    FacebookClient,
    FacebookClientConfigurationError,
)
from companies.models import Company
from companies.services.facebook_activity import process_company_metrics
from companies.management.commands.import_corporate_numbers import run_corporate_number_import
from companies.services.opendata_sources import ingest_opendata_sources, load_opendata_configs
from data_collection.tracker import track_data_collection_run

logger = logging.getLogger(__name__)

CHUNK_SIZE = getattr(settings, "FACEBOOK_SYNC_CHUNK_SIZE", 500)


def _chunked(iterable: Sequence[int], size: int) -> Iterable[List[int]]:
    for index in range(0, len(iterable), size):
        yield list(iterable[index : index + size])


@shared_task(bind=True, ignore_result=True)
def dispatch_facebook_sync(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> int:
    payload = payload or {}
    metadata = {"options": payload}
    with track_data_collection_run(
        "clone.facebook_sync",
        metadata=metadata,
        execution_uuid=execution_uuid,
    ) as tracker:
        if not settings.FACEBOOK_ACCESS_TOKEN:
            logger.warning("FACEBOOK_ACCESS_TOKEN is not configured. Skip Facebook sync.")
            tracker.complete_success(
                input_count=0,
                inserted_count=0,
                skipped_count=0,
                metadata={**metadata, "skipped_reason": "missing_token"},
            )
            return 0

        company_ids = list(
            Company.objects.exclude(facebook_page_id__isnull=True)
            .exclude(facebook_page_id__exact="")
            .values_list("id", flat=True)
        )

        if not company_ids:
            logger.info("No companies configured with facebook_page_id. Skip sync.")
            tracker.complete_success(
                input_count=0,
                inserted_count=0,
                skipped_count=0,
                metadata={**metadata, "skipped_reason": "no_targets"},
            )
            return 0

        subtasks = [sync_facebook_chunk.s(chunk) for chunk in _chunked(company_ids, CHUNK_SIZE)]
        group(subtasks).apply_async()
        logger.info(
            "Dispatched Facebook sync chunks: total_companies=%s chunks=%s",
            len(company_ids),
            len(subtasks),
        )
        tracker.complete_success(
            input_count=len(company_ids),
            inserted_count=len(company_ids),
            skipped_count=0,
            metadata={**metadata, "chunks": len(subtasks)},
        )
        return len(company_ids)


@shared_task(bind=True, autoretry_for=(FacebookAPIError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_facebook_chunk(self, company_ids: Sequence[int]) -> int:
    if not company_ids:
        return 0

    try:
        client = FacebookClient()
    except FacebookClientConfigurationError as exc:
        logger.error("Facebook client misconfigured: %s", exc)
        return 0

    processed = 0
    for company in Company.objects.filter(id__in=company_ids):
        if not company.facebook_page_id:
            continue

        try:
            metrics = client.fetch_page_metrics(company.facebook_page_id)
        except FacebookAPIError as exc:
            logger.warning("Facebook API error for company=%s: %s", company.id, exc)
            raise
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.exception("Unexpected error fetching Facebook metrics for company=%s: %s", company.id, exc)
            continue

        try:
            updated = process_company_metrics(company, metrics, source="celery")
            processed += 1
            logger.debug("Updated company=%s updated=%s", company.id, updated)
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to process Facebook metrics for company=%s: %s", company.id, exc)

    logger.info("Completed Facebook sync chunk: size=%s processed=%s", len(company_ids), processed)
    return processed


@shared_task(bind=True, ignore_result=True)
def run_ai_ingestion_stub(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> str:
    """
    AI連携用のプレースホルダータスク。
    将来的には実際のLLM呼び出しやスクレイピング処理に置き換える。
    """
    payload = payload or {}
    metadata = {"options": payload}
    with track_data_collection_run(
        "clone.ai_stub",
        metadata=metadata,
        execution_uuid=execution_uuid,
    ) as tracker:
        logger.info("AI ingestion stub invoked. payload=%s", payload)
        tracker.complete_success(metadata={**metadata, "result": "accepted"})
        return "accepted"


@shared_task(bind=True)
def run_corporate_number_import_task(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> dict:
    payload = payload or {}
    options = payload.copy()
    allow_missing_token = options.pop("allow_missing_token", False)
    tracker_metadata = {"options": payload}

    with track_data_collection_run(
        "clone.corporate_number",
        metadata=tracker_metadata,
        execution_uuid=execution_uuid,
    ) as tracker:
        result = run_corporate_number_import(allow_missing_token=allow_missing_token, **options)
        stats = result.get("stats", {})
        skip_breakdown = {
            "skipped_prefecture": int(stats.get("skipped_prefecture", 0)),
            "skipped_name": int(stats.get("skipped_name", 0)),
            "skipped_cooldown": int(stats.get("skipped_cooldown", 0)),
            "skipped_rate_limit": int(stats.get("skipped_rate_limit", 0)),
        }
        skipped_count = sum(skip_breakdown.values())
        tracker.complete_success(
            input_count=int(stats.get("checked", 0)),
            inserted_count=int(result.get("created_count", 0)),
            skipped_count=skipped_count,
            error_count=int(stats.get("errors", 0)),
            skip_breakdown=skip_breakdown,
            metadata={
                **tracker_metadata,
                "summary": result.get("summary"),
                "batch_ids": result.get("batch_ids"),
                "skipped": result.get("skipped", False),
                "skipped_reason": result.get("skipped_reason"),
            },
        )
        logger.info("Corporate number import completed. summary=%s", result.get("summary"))
        return result


@shared_task(bind=True)
def run_opendata_ingestion_task(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> dict:
    payload = payload or {}
    options = payload.copy()
    source_keys = options.get("source_keys")
    if isinstance(source_keys, str):
        source_keys = [source_keys]
    if source_keys is not None:
        options["source_keys"] = source_keys
    raw_company_ids = options.get("company_ids")
    company_ids: Optional[List[int]] = None
    if raw_company_ids is not None:
        if isinstance(raw_company_ids, (int, str)):
            raw_company_ids = [raw_company_ids]
        cleaned_ids: List[int] = []
        for value in raw_company_ids:
            try:
                cleaned_value = int(str(value).strip())
            except (TypeError, ValueError):
                logger.warning("Invalid company_id provided to OpenData ingestion: %s", value)
                continue
            cleaned_ids.append(cleaned_value)
        if cleaned_ids:
            company_ids = cleaned_ids
            options["company_ids"] = cleaned_ids
        else:
            options.pop("company_ids", None)
    tracker_metadata = {"options": payload}

    with track_data_collection_run(
        "clone.opendata",
        data_source=source_keys,
        metadata=tracker_metadata,
        execution_uuid=execution_uuid,
    ) as tracker:
        configs = load_opendata_configs()
        result = ingest_opendata_sources(
            source_keys=source_keys,
            company_ids=company_ids,
            limit=options.get("limit"),
            dry_run=options.get("dry_run", False),
            config_map=configs,
        )
        rows = int(result.get("rows", 0))
        created = int(result.get("created", 0))
        skipped = rows - created if rows > created else 0
        tracker.complete_success(
            input_count=rows,
            inserted_count=created,
            skipped_count=skipped,
            error_count=0,
            skip_breakdown={"unmatched": skipped},
            metadata={**tracker_metadata, "result": result},
        )
        logger.info(
            "Open data ingestion finished. sources=%s rows=%s matched=%s created=%s",
            result.get("processed_sources"),
            result.get("rows"),
            result.get("matched"),
            result.get("created"),
        )
        return result
