
from unittest import mock

from django.test import TestCase, override_settings

from companies.models import Company, CompanyUpdateCandidate

from ai_enrichment.redis_usage import UsageSnapshot
from ai_enrichment.tasks import run_ai_enrich


@override_settings(POWERPLEXY_API_KEY='dummy-key')
class RunAIEnrichTaskTests(TestCase):
    def setUp(self) -> None:
        self.company = Company.objects.create(
            name="テスト株式会社",
            website_url="https://example.com",
            prefecture="",
            city="",
        )

    @mock.patch('ai_enrichment.tasks.PowerplexyClient')
    @mock.patch('ai_enrichment.tasks.UsageTracker')
    def test_task_creates_candidates(self, mock_tracker, mock_client_cls):
        tracker_instance = mock_tracker.return_value
        tracker_instance.snapshot.side_effect = [UsageSnapshot(calls=0, cost=0.0), UsageSnapshot(calls=1, cost=0.004)]
        tracker_instance.can_execute.return_value = True

        client_instance = mock_client_cls.return_value
        client_instance.extract_json.return_value = {
            '担当者名': '田中 太郎',
            '所在地（都道府県）': '東京都',
        }

        result = run_ai_enrich()

        self.assertEqual(result['status'], 'ok')
        created = CompanyUpdateCandidate.objects.filter(
            company=self.company,
            source_type=CompanyUpdateCandidate.SOURCE_AI,
        )
        self.assertGreater(created.count(), 0)
        tracker_instance.increment.assert_called()
        company = Company.objects.get(id=self.company.id)
        self.assertIsNotNone(company.ai_last_enriched_at)

    @mock.patch('ai_enrichment.tasks.PowerplexyClient')
    @mock.patch('ai_enrichment.tasks.UsageTracker')
    def test_task_filters_by_company_ids(self, mock_tracker, mock_client_cls):
        tracker_instance = mock_tracker.return_value
        tracker_instance.snapshot.side_effect = [UsageSnapshot(calls=0, cost=0.0), UsageSnapshot(calls=1, cost=0.004)]
        tracker_instance.can_execute.return_value = True

        client_instance = mock_client_cls.return_value
        client_instance.extract_json.return_value = {
            '担当者名': '田中 太郎',
        }

        other = Company.objects.create(
            name="別会社",
            website_url="https://other.example.com",
        )

        run_ai_enrich({"company_ids": [self.company.id]})

        self.assertTrue(
            CompanyUpdateCandidate.objects.filter(
                company=self.company,
                source_type=CompanyUpdateCandidate.SOURCE_AI,
            ).exists()
        )
        self.assertFalse(
            CompanyUpdateCandidate.objects.filter(
                company=other,
                source_type=CompanyUpdateCandidate.SOURCE_AI,
            ).exists()
        )
        client_instance.extract_json.assert_called_once()

    @mock.patch('ai_enrichment.tasks.UsageTracker')
    def test_task_skips_when_limit_reached(self, mock_tracker):
        tracker_instance = mock_tracker.return_value
        tracker_instance.snapshot.return_value = UsageSnapshot(calls=5000, cost=20.0)
        tracker_instance.can_execute.return_value = False

        result = run_ai_enrich()
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'usage_limit')
