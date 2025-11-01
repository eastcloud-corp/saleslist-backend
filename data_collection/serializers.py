from rest_framework import serializers

from .models import DataCollectionRun


class DataCollectionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCollectionRun
        fields = [
            "execution_uuid",
            "job_name",
            "data_source",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "input_count",
            "inserted_count",
            "skipped_count",
            "error_count",
            "skip_breakdown",
            "error_summary",
            "metadata",
            "next_scheduled_for",
            "created_at",
            "updated_at",
        ]
