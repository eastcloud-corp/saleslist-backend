
import calendar
from unittest import mock

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from ai_enrichment.redis_usage import UsageTracker


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class UsageTrackerTests(SimpleTestCase):
    @override_settings(POWERPLEXY_DAILY_RECORD_LIMIT=None)  # 未設定時は月間上限から導出されることを検証
    @mock.patch('ai_enrichment.redis_usage.get_redis_connection', new=None)
    def test_usage_tracker_with_cache_backend(self):
        tracker = UsageTracker()
        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.calls, 0)
        self.assertEqual(snapshot.cost, 0.0)

        updated = tracker.increment()
        self.assertEqual(updated.calls, 1)
        self.assertAlmostEqual(updated.cost, tracker.cost_per_call)

        self.assertAlmostEqual(tracker.cost_limit, 150.0)
        self.assertAlmostEqual(tracker.cost_per_call, 0.05)
        expected_call_limit = 0
        if tracker.cost_limit > 0 and tracker.cost_per_call > 0:
            expected_call_limit = int(tracker.cost_limit // tracker.cost_per_call)
        self.assertEqual(tracker.call_limit, expected_call_limit)
        now = timezone.now()
        current = timezone.localtime(now)
        days_in_month = calendar.monthrange(current.year, current.month)[1]
        expected_daily_limit = 0
        if expected_call_limit > 0 and days_in_month > 0:
            expected_daily_limit = max(expected_call_limit // days_in_month, 1)
        self.assertEqual(tracker.daily_limit, expected_daily_limit)

    @override_settings(
        POWERPLEXY_MONTHLY_COST_LIMIT=200.0,
        POWERPLEXY_COST_PER_REQUEST=0.1,
        POWERPLEXY_MONTHLY_CALL_LIMIT="1800",
        POWERPLEXY_DAILY_RECORD_LIMIT="80",
    )
    @mock.patch('ai_enrichment.redis_usage.get_redis_connection', new=None)
    def test_explicit_limits_override_derived_values(self):
        tracker = UsageTracker()
        self.assertEqual(tracker.call_limit, 1800)
        self.assertEqual(tracker.daily_limit, 80)
        self.assertAlmostEqual(tracker.cost_limit, 200.0)
        self.assertAlmostEqual(tracker.cost_per_call, 0.1)

    @override_settings(
        POWERPLEXY_MONTHLY_COST_LIMIT=150.0,
        POWERPLEXY_COST_PER_REQUEST=0.0,
        POWERPLEXY_MONTHLY_CALL_LIMIT=None,
        POWERPLEXY_DAILY_RECORD_LIMIT=None,
    )
    @mock.patch('ai_enrichment.redis_usage.get_redis_connection', new=None)
    def test_zero_cost_per_call_disables_limits(self):
        tracker = UsageTracker()
        self.assertEqual(tracker.call_limit, 0)
        self.assertEqual(tracker.daily_limit, 0)
