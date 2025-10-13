from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from companies.models import Company, CompanyFacebookSnapshot

logger = logging.getLogger(__name__)


def _normalize_datetime(value: Optional[Any]) -> Optional[timezone.datetime]:
    if value is None:
        return None
    if isinstance(value, timezone.datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone=timezone.get_current_timezone())
        return value
    if isinstance(value, str) and value.strip():
        parsed = parse_datetime(value.strip())
        if parsed is not None:
            if timezone.is_naive(parsed):
                return timezone.make_aware(parsed, timezone=timezone.get_current_timezone())
            return parsed
    return None


def process_company_metrics(
    company: Company,
    metrics: Dict[str, Any],
    *,
    source: str = "celery",
) -> bool:
    """
    Apply fetched Facebook metrics to a company.

    Returns True if latest_activity_at was updated.
    """
    friend_count = metrics.get("friend_count")
    friend_count_fetched_at = _normalize_datetime(metrics.get("friend_count_fetched_at")) or timezone.now()
    latest_posted_at = _normalize_datetime(metrics.get("latest_posted_at"))
    latest_post_fetched_at = _normalize_datetime(metrics.get("latest_post_fetched_at")) or timezone.now()

    now = timezone.now()
    should_update_activity = False

    with transaction.atomic():
        previous_snapshot = (
            company.facebook_snapshots.order_by("-created_at").select_for_update().first()
        )

        if friend_count is not None:
            previous_friend_count = previous_snapshot.friend_count if previous_snapshot else None
            if previous_friend_count is None or friend_count > previous_friend_count:
                should_update_activity = True
            company.facebook_friend_count = friend_count

        if latest_posted_at is not None:
            previous_post_at = previous_snapshot.latest_posted_at if previous_snapshot else None
            if previous_post_at is None or latest_posted_at > previous_post_at:
                should_update_activity = True
            company.facebook_latest_post_at = latest_posted_at

        company.facebook_data_synced_at = now

        update_fields = ['facebook_data_synced_at']
        if friend_count is not None:
            update_fields.append('facebook_friend_count')
        if latest_posted_at is not None:
            update_fields.append('facebook_latest_post_at')
        if should_update_activity:
            company.latest_activity_at = now
            update_fields.append('latest_activity_at')

        company.save(update_fields=update_fields)

        CompanyFacebookSnapshot.objects.create(
            company=company,
            friend_count=friend_count,
            friend_count_fetched_at=friend_count_fetched_at,
            latest_posted_at=latest_posted_at,
            latest_post_fetched_at=latest_post_fetched_at,
            source=source,
        )

    logger.debug(
        "Processed Facebook metrics for company=%s updated=%s metrics=%s",
        company.id,
        should_update_activity,
        metrics,
    )
    return should_update_activity
