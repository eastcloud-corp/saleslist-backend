from datetime import datetime
import importlib
import sys
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class HealthEndpointsTests(TestCase):
    def test_health_check_logs_success(self):
        with self.assertLogs('saleslist.health', level='INFO') as captured:
            response = self.client.get(reverse('health_check'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'saleslist-backend')
        self.assertTrue(data['timestamp'])
        datetime.fromisoformat(data['timestamp'])
        self.assertTrue(captured.output)
        self.assertIn('health_check.success', captured.output[0])

    def test_db_health_check_logs_success(self):
        with self.assertLogs('saleslist.health', level='INFO') as captured:
            response = self.client.get(reverse('db_health_check'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')
        datetime.fromisoformat(data['timestamp'])
        self.assertTrue(captured.output)
        self.assertIn('db_health_check.success', captured.output[0])

    def test_db_health_check_logs_failure(self):
        with mock.patch('django.db.connection.cursor', side_effect=Exception('db offline')):
            with self.assertLogs('saleslist.health', level='ERROR') as captured:
                response = self.client.get(reverse('db_health_check'))

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'unhealthy')
        self.assertEqual(data['database'], 'disconnected')
        datetime.fromisoformat(data['timestamp'])
        self.assertTrue(captured.output)
        self.assertIn('db_health_check.failure', captured.output[0])

    def test_cache_health_check_without_redis_logs_database_cache(self):
        with self.assertLogs('saleslist.health', level='INFO') as captured:
            response = self.client.get(reverse('cache_health_check'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['cache'], 'database_cache')
        datetime.fromisoformat(data['timestamp'])
        self.assertTrue(captured.output)
        self.assertIn('cache_health_check.database_cache', captured.output[0])

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://localhost:6379/0',
        }
    })
    def test_cache_health_check_with_redis_logs_success(self):
        patch_target = 'saleslist_backend.health_urls.redis.Redis.from_url'
        with mock.patch(patch_target) as mock_from_url:
            mock_instance = mock_from_url.return_value
            mock_instance.ping.return_value = True
            with self.assertLogs('saleslist.health', level='INFO') as captured:
                response = self.client.get(reverse('cache_health_check'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['cache'], 'connected')
        datetime.fromisoformat(data['timestamp'])
        self.assertTrue(captured.output)
        self.assertIn('cache_health_check.success', captured.output[0])
        mock_from_url.assert_called_once_with('redis://localhost:6379/0')
        mock_instance.ping.assert_called_once()

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://localhost:6379/1',
        }
    })
    def test_cache_health_check_with_redis_logs_failure(self):
        patch_target = 'saleslist_backend.health_urls.redis.Redis.from_url'
        with mock.patch(patch_target) as mock_from_url:
            mock_instance = mock_from_url.return_value
            mock_instance.ping.side_effect = RuntimeError('redis unreachable')
            with self.assertLogs('saleslist.health', level='ERROR') as captured:
                response = self.client.get(reverse('cache_health_check'))

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'unhealthy')
        self.assertEqual(data['cache'], 'disconnected')
        datetime.fromisoformat(data['timestamp'])
        self.assertTrue(captured.output)
        self.assertIn('cache_health_check.failure', captured.output[0])
        mock_from_url.assert_called_once_with('redis://localhost:6379/1')
        mock_instance.ping.assert_called_once()


class AsgiModuleTests(SimpleTestCase):
    def test_asgi_application_initialization_sets_project_settings(self):
        module_name = 'saleslist_backend.asgi'
        sys.modules.pop(module_name, None)

        with mock.patch('django.core.asgi.get_asgi_application') as mock_get_asgi_application:
            sentinel_application = object()
            mock_get_asgi_application.return_value = sentinel_application

            with mock.patch.dict('os.environ', {}, clear=True):
                module = importlib.import_module(module_name)

        self.assertEqual(module.application, sentinel_application)
        self.assertEqual(module.os.environ['DJANGO_SETTINGS_MODULE'], 'saleslist_backend.settings')
        mock_get_asgi_application.assert_called_once()

        # Reload without patches so the real application is restored for other tests.
        sys.modules.pop(module_name, None)
        importlib.import_module(module_name)
