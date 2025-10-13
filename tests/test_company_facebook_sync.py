from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from companies.models import Company, CompanyFacebookSnapshot
from companies.services.facebook_activity import process_company_metrics
from companies.tasks import dispatch_facebook_sync, sync_facebook_chunk


class ProcessCompanyMetricsTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="テスト企業",
            industry="IT",
            facebook_page_id="1234567890",
        )

    def test_updates_latest_activity_on_friend_growth(self):
        metrics = {
            "friend_count": 150,
            "friend_count_fetched_at": timezone.now().isoformat(),
            "latest_posted_at": timezone.now().isoformat(),
            "latest_post_fetched_at": timezone.now().isoformat(),
        }
        updated = process_company_metrics(self.company, metrics, source="test")
        self.company.refresh_from_db()

        self.assertTrue(updated)
        self.assertEqual(self.company.facebook_friend_count, 150)
        self.assertIsNotNone(self.company.latest_activity_at)
        self.assertEqual(CompanyFacebookSnapshot.objects.filter(company=self.company).count(), 1)

    def test_does_not_update_latest_activity_when_no_change(self):
        previous = CompanyFacebookSnapshot.objects.create(
            company=self.company,
            friend_count=200,
            friend_count_fetched_at=timezone.now(),
            latest_posted_at=timezone.now(),
            latest_post_fetched_at=timezone.now(),
            source="seed",
        )
        self.company.facebook_friend_count = previous.friend_count
        self.company.facebook_latest_post_at = previous.latest_posted_at
        self.company.save(update_fields=['facebook_friend_count', 'facebook_latest_post_at'])

        metrics = {
            "friend_count": 200,
            "friend_count_fetched_at": timezone.now().isoformat(),
            "latest_posted_at": previous.latest_posted_at.isoformat(),
            "latest_post_fetched_at": timezone.now().isoformat(),
        }
        updated = process_company_metrics(self.company, metrics, source="test")
        self.company.refresh_from_db()

        self.assertFalse(updated)
        self.assertEqual(self.company.facebook_friend_count, 200)
        self.assertIsNone(self.company.latest_activity_at)
        self.assertEqual(CompanyFacebookSnapshot.objects.filter(company=self.company).count(), 2)


class CeleryTaskTests(TestCase):
    @override_settings(FACEBOOK_ACCESS_TOKEN='token')
    def test_dispatch_returns_zero_when_no_companies(self):
        with mock.patch('companies.tasks.group') as mock_group:
            count = dispatch_facebook_sync()
        self.assertEqual(count, 0)
        mock_group.assert_not_called()

    @override_settings(FACEBOOK_ACCESS_TOKEN='token')
    def test_dispatch_groups_companies(self):
        companies = [
            Company.objects.create(name=f"Company {idx}", industry="IT", facebook_page_id=str(idx))
            for idx in range(1, 4)
        ]

        with mock.patch('companies.tasks.group') as mock_group:
            mock_group.return_value.apply_async = mock.Mock()
            count = dispatch_facebook_sync()

        self.assertEqual(count, len(companies))
        mock_group.assert_called_once()
        args, _ = mock_group.call_args
        subtasks = args[0]
        self.assertGreater(len(subtasks), 0)

    @override_settings(FACEBOOK_ACCESS_TOKEN='token')
    @mock.patch('companies.tasks.FacebookClient')
    def test_sync_chunk_updates_companies(self, mock_client_class):
        company = Company.objects.create(
            name="Chunk Company",
            industry="IT",
            facebook_page_id="chunk123",
        )
        now = timezone.now()
        mock_client = mock.Mock()
        mock_client.fetch_page_metrics.return_value = {
            "friend_count": 321,
            "friend_count_fetched_at": now.isoformat(),
            "latest_posted_at": now.isoformat(),
            "latest_post_fetched_at": now.isoformat(),
        }
        mock_client_class.return_value = mock_client

        result = sync_facebook_chunk.run([company.id])

        self.assertEqual(result, 1)
        company.refresh_from_db()
        self.assertEqual(company.facebook_friend_count, 321)
        self.assertIsNotNone(company.facebook_latest_post_at)
        self.assertEqual(CompanyFacebookSnapshot.objects.filter(company=company).count(), 1)
