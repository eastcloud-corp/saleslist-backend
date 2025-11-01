
from unittest import mock

from django.test import SimpleTestCase, override_settings

from ai_enrichment.redis_usage import UsageTracker


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class UsageTrackerTests(SimpleTestCase):
    @mock.patch('ai_enrichment.redis_usage.get_redis_connection', new=None)
    def test_usage_tracker_with_cache_backend(self):
        tracker = UsageTracker()
        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.calls, 0)
        self.assertEqual(snapshot.cost, 0.0)

        updated = tracker.increment()
        self.assertEqual(updated.calls, 1)
        self.assertAlmostEqual(updated.cost, tracker.cost_per_call)
