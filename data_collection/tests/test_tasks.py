
import uuid
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from companies.tasks import run_corporate_number_import_task, run_opendata_ingestion_task, run_ai_ingestion_stub
from data_collection.models import DataCollectionRun


class DataCollectionTaskLoggingTests(TestCase):
    @mock.patch('companies.tasks.run_corporate_number_import')
    @mock.patch('data_collection.tracker.compute_next_schedules', return_value={'clone.corporate_number': None, 'earliest': None})
    def test_corporate_number_task_updates_run(self, mock_schedule, mock_import):
        mock_import.return_value = {
            'stats': {
                'checked': 5,
                'matched': 3,
                'not_found': 2,
                'errors': 1,
                'skipped_prefecture': 1,
                'skipped_name': 1,
                'skipped_cooldown': 0,
                'skipped_rate_limit': 0,
            },
            'created_count': 2,
            'summary': 'done',
            'batch_ids': [1],
            'skipped': False,
            'skipped_reason': None,
        }
        execution_uuid = str(uuid.uuid4())
        run = DataCollectionRun.objects.create(
            execution_uuid=execution_uuid,
            job_name='clone.corporate_number',
            data_source=['corporate_number_api'],
            status=DataCollectionRun.Status.QUEUED,
        )

        result = run_corporate_number_import_task.run(payload={'company_ids': [1]}, execution_uuid=execution_uuid)
        self.assertEqual(result['summary'], 'done')
        run.refresh_from_db()
        self.assertEqual(run.status, DataCollectionRun.Status.SUCCESS)
        self.assertEqual(run.input_count, 5)
        self.assertEqual(run.inserted_count, 2)
        self.assertEqual(run.error_count, 1)
        self.assertEqual(run.skipped_count, 2)
        self.assertIsNone(run.next_scheduled_for)

    @mock.patch('companies.tasks.ingest_opendata_sources')
    @mock.patch('data_collection.tracker.compute_next_schedules', return_value={'clone.opendata': None, 'earliest': None})
    def test_opendata_task_updates_run(self, mock_schedule, mock_ingest):
        mock_ingest.return_value = {
            'processed_sources': 1,
            'rows': 10,
            'matched': 6,
            'created': 4,
        }
        result = run_opendata_ingestion_task.run(payload={'source_keys': ['tokyo']}, execution_uuid=None)
        self.assertEqual(result['created'], 4)
        run = DataCollectionRun.objects.latest('created_at')
        self.assertEqual(run.job_name, 'clone.opendata')
        self.assertEqual(run.inserted_count, 4)
        self.assertEqual(run.skipped_count, 6)
        self.assertEqual(run.status, DataCollectionRun.Status.SUCCESS)

    @mock.patch('data_collection.tracker.compute_next_schedules', return_value={'ai.enrich': None, 'clone.ai_stub': None, 'earliest': None})
    def test_ai_stub_creates_run(self, mock_schedule):
        result = run_ai_ingestion_stub.run(payload={'foo': 'bar'})
        self.assertEqual(result, 'accepted')
        run = DataCollectionRun.objects.latest('created_at')
        self.assertEqual(run.job_name, 'clone.ai_stub')
        self.assertEqual(run.status, DataCollectionRun.Status.SUCCESS)
        self.assertEqual(run.metadata.get('options'), {'foo': 'bar'})
