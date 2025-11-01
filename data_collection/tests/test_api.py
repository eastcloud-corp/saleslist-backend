
import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from ai_enrichment.redis_usage import UsageSnapshot
from data_collection.models import DataCollectionRun


class DataCollectionRunAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="password123",
            name="Admin",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.admin)

    @mock.patch('data_collection.views.UsageTracker')
    @mock.patch('data_collection.views.compute_next_schedules')
    def test_list_runs_returns_expected_payload(self, mock_compute, mock_usage):
        tracker = mock_usage.return_value
        tracker.snapshot.return_value = UsageSnapshot(calls=10, cost=0.04)
        tracker.remaining.return_value = UsageSnapshot(calls=4990, cost=19.96)
        tracker.call_limit = 5000
        tracker.cost_limit = 20.0
        tracker.cost_per_call = 0.004
        tracker.daily_limit = 500
        now = timezone.now()
        run1 = DataCollectionRun.objects.create(
            job_name="clone.corporate_number",
            data_source=["corporate_number_api"],
            status=DataCollectionRun.Status.SUCCESS,
            started_at=now - datetime.timedelta(hours=2),
            finished_at=now - datetime.timedelta(hours=1, minutes=30),
            inserted_count=10,
        )
        run2 = DataCollectionRun.objects.create(
            job_name="clone.opendata",
            data_source=["opendata"],
            status=DataCollectionRun.Status.RUNNING,
            started_at=now - datetime.timedelta(hours=1),
        )
        next_times = {
            "clone.facebook_sync": now + datetime.timedelta(hours=5),
            "clone.corporate_number": None,
            "clone.opendata": None,
            "ai.enrich": None,
            "clone.ai_stub": None,
            "earliest": now + datetime.timedelta(hours=5),
        }
        mock_compute.return_value = next_times

        url = reverse('data-collection-run-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body['results']), 2)
        self.assertEqual(body['results'][0]['execution_uuid'], str(run2.execution_uuid))
        expected_iso = (now + datetime.timedelta(hours=5)).astimezone(timezone.get_current_timezone()).isoformat()
        self.assertEqual(body['next_scheduled_for'], expected_iso)
        self.assertIn('clone.facebook_sync', body['schedules'])
        self.assertIn('ai_usage', body)
        self.assertEqual(body['ai_usage']['calls_this_month'], 10)
        self.assertEqual(body['ai_usage']['call_limit'], 5000)

    @mock.patch('data_collection.views.enqueue_job')
    @mock.patch('data_collection.views.has_active_run')
    @mock.patch('data_collection.views.compute_next_schedules')
    @mock.patch('data_collection.views.UsageTracker')
    def test_trigger_enqueues_job(self, mock_usage, mock_compute, mock_active, mock_enqueue):
        tracker = mock_usage.return_value
        tracker.snapshot.return_value = UsageSnapshot(calls=10, cost=0.04)
        tracker.remaining.return_value = UsageSnapshot(calls=4990, cost=19.96)
        tracker.call_limit = 5000
        tracker.cost_limit = 20.0
        tracker.cost_per_call = 0.004
        tracker.daily_limit = 500
        mock_active.return_value = False
        now = timezone.now()
        mock_compute.return_value = {
            "clone.facebook_sync": None,
            "clone.corporate_number": None,
            "clone.opendata": None,
            "ai.enrich": None,
            "clone.ai_stub": None,
            "earliest": None,
        }
        run = DataCollectionRun.objects.create(
            job_name="clone.corporate_number",
            data_source=["corporate_number_api"],
            status=DataCollectionRun.Status.QUEUED,
        )
        async_result = mock.Mock()
        async_result.id = "task-123"
        mock_enqueue.return_value = (run, async_result)

        url = reverse('data-collection-trigger')
        payload = {"job_name": "clone.corporate_number", "options": {"company_ids": [1, 2]}}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 202)
        mock_enqueue.assert_called_once_with(job_name="clone.corporate_number", options={"company_ids": [1, 2]})
        body = response.json()
        self.assertEqual(body['execution_uuid'], str(run.execution_uuid))
        self.assertEqual(body['task_id'], "task-123")
        self.assertIn('ai_usage', body)
        self.assertEqual(body['ai_usage']['calls_this_month'], 10)

    @mock.patch('data_collection.views.enqueue_job')
    @mock.patch('data_collection.views.has_active_run')
    @mock.patch('data_collection.views.compute_next_schedules')
    @mock.patch('data_collection.views.UsageTracker')
    def test_trigger_opendata_accepts_company_ids(self, mock_usage, mock_compute, mock_active, mock_enqueue):
        tracker = mock_usage.return_value
        tracker.snapshot.return_value = UsageSnapshot(calls=10, cost=0.04)
        tracker.remaining.return_value = UsageSnapshot(calls=4990, cost=19.96)
        tracker.call_limit = 5000
        tracker.cost_limit = 20.0
        tracker.cost_per_call = 0.004
        tracker.daily_limit = 500
        mock_active.return_value = False
        mock_compute.return_value = {
            "clone.facebook_sync": None,
            "clone.corporate_number": None,
            "clone.opendata": None,
            "ai.enrich": None,
            "clone.ai_stub": None,
            "earliest": None,
        }
        run = DataCollectionRun.objects.create(
            job_name="clone.opendata",
            data_source=["opendata"],
            status=DataCollectionRun.Status.QUEUED,
        )
        async_result = mock.Mock()
        async_result.id = "task-opendata"
        mock_enqueue.return_value = (run, async_result)

        url = reverse('data-collection-trigger')
        payload = {"job_name": "clone.opendata", "options": {"company_ids": [42]}}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 202)
        mock_enqueue.assert_called_once_with(job_name="clone.opendata", options={"company_ids": [42]})
        body = response.json()
        self.assertIn('ai_usage', body)
        self.assertEqual(body['execution_uuid'], str(run.execution_uuid))

    @mock.patch('data_collection.views.has_active_run')
    def test_trigger_rejects_active_job(self, mock_active):
        mock_active.return_value = True
        url = reverse('data-collection-trigger')
        response = self.client.post(url, {"job_name": "clone.corporate_number"}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_trigger_requires_valid_job(self):
        url = reverse('data-collection-trigger')
        response = self.client.post(url, {"job_name": "unknown.job"}, format='json')
        self.assertEqual(response.status_code, 400)
