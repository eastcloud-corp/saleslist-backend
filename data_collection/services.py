
from __future__ import annotations

import importlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from celery.result import AsyncResult
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .job_definitions import DATA_COLLECTION_JOBS, JobDefinition, get_job_definition
from .models import DataCollectionRun


def _get_schedule_for_job(definition: JobDefinition):
    if not definition.beat_schedule_key:
        return None
    schedule_def = settings.CELERY_BEAT_SCHEDULE.get(definition.beat_schedule_key)
    if not schedule_def:
        return None
    return schedule_def.get("schedule")


def compute_next_schedules(reference_time: Optional[datetime] = None) -> Dict[str, Optional[datetime]]:
    reference_time = reference_time or timezone.now()
    results: Dict[str, Optional[datetime]] = {}
    earliest_dt: Optional[datetime] = None
    tz = timezone.get_current_timezone()

    for job_name, definition in DATA_COLLECTION_JOBS.items():
        schedule = _get_schedule_for_job(definition)
        if not schedule:
            results[job_name] = None
            continue
        remaining = schedule.remaining_estimate(reference_time)
        if isinstance(remaining, timedelta):
            next_time = reference_time + remaining
            if timezone.is_naive(next_time):
                next_time = timezone.make_aware(next_time, timezone.utc)
            localized = next_time.astimezone(tz)
            results[job_name] = localized
            if earliest_dt is None or localized < earliest_dt:
                earliest_dt = localized
        else:
            results[job_name] = None
    results["earliest"] = earliest_dt
    return results


def _import_task(task_path: str):
    module_name, attr = task_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def has_active_run(job_name: str) -> bool:
    return DataCollectionRun.objects.filter(
        job_name=job_name,
        status__in=[DataCollectionRun.Status.QUEUED, DataCollectionRun.Status.RUNNING],
    ).exists()


def enqueue_job(job_name: str, options: Dict[str, Any]) -> Tuple[DataCollectionRun, Optional[AsyncResult]]:
    definition = get_job_definition(job_name)
    source_keys = options.get("source_keys")
    if isinstance(source_keys, str):
        source_keys = [source_keys]
    data_source = source_keys or definition.default_sources
    metadata = {"options": options}

    with transaction.atomic():
        run = DataCollectionRun.objects.create(
            job_name=job_name,
            data_source=data_source,
            metadata=metadata,
            status=DataCollectionRun.Status.QUEUED,
        )

    task = _import_task(definition.task_path)
    async_result = task.apply_async(kwargs={
        "payload": options,
        "execution_uuid": str(run.execution_uuid),
    })
    return run, async_result
