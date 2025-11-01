
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from .job_definitions import get_job_definition
from .models import DataCollectionRun
from .services import compute_next_schedules


@dataclass
class DataCollectionRunTracker:
    job_name: str
    data_source: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_uuid: Optional[str] = None

    run: DataCollectionRun = field(init=False)
    completed: bool = field(init=False, default=False)

    def __post_init__(self):
        definition = get_job_definition(self.job_name)
        data_source = self.data_source or definition.default_sources
        metadata = self.metadata or {}
        now = timezone.now()

        with transaction.atomic():
            if self.execution_uuid:
                run, created = DataCollectionRun.objects.select_for_update().get_or_create(
                    execution_uuid=self.execution_uuid,
                    defaults={
                        "job_name": self.job_name,
                        "data_source": data_source,
                        "metadata": metadata,
                        "status": DataCollectionRun.Status.QUEUED,
                    },
                )
                run.job_name = self.job_name
                run.data_source = data_source
                if metadata:
                    run.metadata = metadata
                run.status = DataCollectionRun.Status.RUNNING
                run.started_at = now
                run.save(update_fields=["job_name", "data_source", "metadata", "status", "started_at", "updated_at"])
            else:
                run = DataCollectionRun.objects.create(
                    job_name=self.job_name,
                    data_source=data_source,
                    metadata=metadata,
                    status=DataCollectionRun.Status.RUNNING,
                    started_at=now,
                )
        self.run = run

    def update_progress(self, **fields: Any) -> None:
        if not fields:
            return
        for key, value in fields.items():
            setattr(self.run, key, value)
        update_fields = list(fields.keys()) + ["updated_at"]
        self.run.save(update_fields=update_fields)

    def complete_success(self, **fields: Any) -> None:
        self.completed = True
        if fields:
            self.update_progress(**fields)
        self.run.next_scheduled_for = self._next_schedule()
        self.run.mark_success()

    def complete_failure(self, error_summary: str, **fields: Any) -> None:
        self.completed = True
        if fields:
            self.update_progress(**fields)
        self.run.next_scheduled_for = self._next_schedule()
        self.run.mark_failure(error_summary=error_summary[:512] if error_summary else None)

    def _next_schedule(self) -> Optional[datetime]:
        schedules = compute_next_schedules()
        return schedules.get(self.job_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            message = str(exc_val) if exc_val else ""
            self.complete_failure(message)
            return False
        if not self.completed:
            self.complete_success()
        return False


def track_data_collection_run(
    job_name: str,
    *,
    data_source: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    execution_uuid: Optional[str] = None,
) -> DataCollectionRunTracker:
    return DataCollectionRunTracker(
        job_name=job_name,
        data_source=data_source,
        metadata=metadata,
        execution_uuid=execution_uuid,
    )
