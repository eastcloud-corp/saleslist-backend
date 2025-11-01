from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class JobDefinition:
    name: str
    task_path: str
    default_sources: List[str]
    beat_schedule_key: Optional[str] = None
    supports_company_options: bool = False
    supports_source_keys: bool = False


DATA_COLLECTION_JOBS: Dict[str, JobDefinition] = {
    "clone.corporate_number": JobDefinition(
        name="clone.corporate_number",
        task_path="companies.tasks.run_corporate_number_import_task",
        default_sources=["corporate_number_api"],
        supports_company_options=True,
        supports_source_keys=True,
    ),
    "clone.opendata": JobDefinition(
        name="clone.opendata",
        task_path="companies.tasks.run_opendata_ingestion_task",
        default_sources=["opendata"],
        supports_company_options=True,
        supports_source_keys=True,
    ),
    "clone.facebook_sync": JobDefinition(
        name="clone.facebook_sync",
        task_path="companies.tasks.dispatch_facebook_sync",
        default_sources=["facebook"],
        beat_schedule_key="sync-facebook-activity",
    ),
    "ai.enrich": JobDefinition(
        name="ai.enrich",
        task_path="ai_enrichment.tasks.run_ai_enrich",
        default_sources=["powerplexy"],
        beat_schedule_key="run-ai-enrich",
    ),
    "clone.ai_stub": JobDefinition(
        name="clone.ai_stub",
        task_path="companies.tasks.run_ai_ingestion_stub",
        default_sources=["ai_stub"],
    ),
}


def list_job_names() -> List[str]:
    return list(DATA_COLLECTION_JOBS.keys())


def get_job_definition(job_name: str) -> JobDefinition:
    return DATA_COLLECTION_JOBS[job_name]
