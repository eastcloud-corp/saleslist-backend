from __future__ import annotations

import logging
from typing import Iterable, List, Sequence

from celery import shared_task, group
from django.conf import settings

from companies.facebook_client import (
    FacebookAPIError,
    FacebookClient,
    FacebookClientConfigurationError,
)
from companies.models import Company
from companies.services.facebook_activity import process_company_metrics

logger = logging.getLogger(__name__)

CHUNK_SIZE = getattr(settings, "FACEBOOK_SYNC_CHUNK_SIZE", 500)


def _chunked(iterable: Sequence[int], size: int) -> Iterable[List[int]]:
    for index in range(0, len(iterable), size):
        yield list(iterable[index : index + size])


@shared_task(bind=True, ignore_result=True)
def dispatch_facebook_sync(self) -> int:
    if not settings.FACEBOOK_ACCESS_TOKEN:
        logger.warning("FACEBOOK_ACCESS_TOKEN is not configured. Skip Facebook sync.")
        return 0

    company_ids = list(
        Company.objects.exclude(facebook_page_id__isnull=True)
        .exclude(facebook_page_id__exact="")
        .values_list("id", flat=True)
    )

    if not company_ids:
        logger.info("No companies configured with facebook_page_id. Skip sync.")
        return 0

    subtasks = [sync_facebook_chunk.s(chunk) for chunk in _chunked(company_ids, CHUNK_SIZE)]
    group(subtasks).apply_async()
    logger.info("Dispatched Facebook sync chunks: total_companies=%s chunks=%s", len(company_ids), len(subtasks))
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
