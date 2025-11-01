from django.contrib import admin

from .models import DataCollectionRun


@admin.register(DataCollectionRun)
class DataCollectionRunAdmin(admin.ModelAdmin):
    list_display = (
        "execution_uuid",
        "job_name",
        "status",
        "started_at",
        "finished_at",
        "inserted_count",
        "skipped_count",
    )
    list_filter = ("job_name", "status")
    search_fields = ("execution_uuid", "job_name")
    ordering = ("-started_at",)
