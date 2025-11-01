from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class DataCollectionRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    execution_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    job_name = models.CharField(max_length=64, db_index=True)
    data_source = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    input_count = models.IntegerField(default=0)
    inserted_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    skip_breakdown = models.JSONField(null=True, blank=True)
    error_summary = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    next_scheduled_for = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["job_name", "-started_at"]),
        ]
        verbose_name = "Data Collection Run"
        verbose_name_plural = "Data Collection Runs"

    def _calculate_duration(self) -> int:
        if not self.started_at or not self.finished_at:
            return self.duration_seconds
        delta = self.finished_at - self.started_at
        return max(int(delta.total_seconds()), 0)

    def mark_running(self) -> None:
        now = timezone.now()
        self.status = self.Status.RUNNING
        self.started_at = now
        self.save(update_fields=["status", "started_at", "updated_at"])

    def mark_success(self) -> None:
        self.status = self.Status.SUCCESS
        self.finished_at = timezone.now()
        self.duration_seconds = self._calculate_duration()
        self.save(update_fields=[
            "status",
            "finished_at",
            "duration_seconds",
            "next_scheduled_for",
            "input_count",
            "inserted_count",
            "skipped_count",
            "error_count",
            "skip_breakdown",
            "error_summary",
            "metadata",
            "updated_at",
        ])

    def mark_failure(self, error_summary: str | None = None) -> None:
        self.status = self.Status.FAILURE
        self.finished_at = timezone.now()
        self.duration_seconds = self._calculate_duration()
        if error_summary:
            self.error_summary = error_summary
        self.save(update_fields=[
            "status",
            "finished_at",
            "duration_seconds",
            "next_scheduled_for",
            "input_count",
            "inserted_count",
            "skipped_count",
            "error_count",
            "skip_breakdown",
            "metadata",
            "error_summary",
            "updated_at",
        ])

    def __str__(self) -> str:
        return f"{self.job_name}:{self.execution_uuid}"
