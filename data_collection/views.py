
from __future__ import annotations

from typing import Any, Dict

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .job_definitions import get_job_definition, list_job_names
from .models import DataCollectionRun
from .serializers import DataCollectionRunSerializer
from .services import compute_next_schedules, enqueue_job, has_active_run


def _to_iso(value):
    if not value:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.astimezone(timezone.get_current_timezone()).isoformat()


class DataCollectionRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = DataCollectionRunSerializer
    lookup_field = "execution_uuid"

    def get_queryset(self):
        queryset = DataCollectionRun.objects.all()
        job_name = self.request.query_params.get("job_name")
        status_filter = self.request.query_params.get("status")
        started_after = self.request.query_params.get("started_after")
        started_before = self.request.query_params.get("started_before")

        if job_name:
            queryset = queryset.filter(job_name=job_name)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if started_after:
            dt = parse_datetime(started_after)
            if dt:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                queryset = queryset.filter(started_at__gte=dt)
        if started_before:
            dt = parse_datetime(started_before)
            if dt:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                queryset = queryset.filter(started_at__lte=dt)
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        schedules = compute_next_schedules()
        earliest_dt = schedules.pop("earliest", None)
        response.data = {
            "next_scheduled_for": _to_iso(earliest_dt),
            "schedules": {name: _to_iso(dt) for name, dt in schedules.items()},
            "count": response.data["count"],
            "next": response.data["next"],
            "previous": response.data["previous"],
            "results": response.data["results"],
        }
        return response


class DataCollectionTriggerView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        payload: Dict[str, Any] = request.data or {}
        job_name = payload.get("job_name")
        options = payload.get("options") or {}

        if not job_name or job_name not in list_job_names():
            return Response({"error": "job_name が未指定、もしくは不正です"}, status=status.HTTP_400_BAD_REQUEST)

        if has_active_run(job_name):
            return Response({"error": "対象ジョブが実行中のため開始できません"}, status=status.HTTP_409_CONFLICT)

        definition = get_job_definition(job_name)
        if options.get("company_ids") and not definition.supports_company_options:
            return Response({"error": "company_ids オプションはこのジョブではサポートされていません"}, status=status.HTTP_400_BAD_REQUEST)
        if options.get("source_keys") and not definition.supports_source_keys:
            return Response({"error": "source_keys オプションはこのジョブではサポートされていません"}, status=status.HTTP_400_BAD_REQUEST)

        run, async_result = enqueue_job(job_name=job_name, options=options)
        serializer = DataCollectionRunSerializer(run, context={"request": request})
        schedules = compute_next_schedules()
        earliest_dt = schedules.pop("earliest", None)
        schedule_response = {name: _to_iso(dt) for name, dt in schedules.items()}

        return Response(
            {
                "execution_uuid": str(run.execution_uuid),
                "task_id": async_result.id if async_result else None,
                "next_scheduled_for": _to_iso(earliest_dt),
                "run": serializer.data,
                "schedules": schedule_response,
            },
            status=status.HTTP_202_ACCEPTED,
        )
