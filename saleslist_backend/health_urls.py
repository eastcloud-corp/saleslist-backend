import logging

from django.conf import settings
from django.db import connection
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

import redis


logger = logging.getLogger('saleslist.health')


def _timestamp():
    return timezone.now().isoformat()


def _log_and_respond(event, payload, status=200, level=logging.INFO):
    logger.log(level, event, extra={'payload': payload, 'http_status': status})
    return Response(payload, status=status)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def health_check(request):
    """アプリケーションのヘルスチェック"""
    payload = {
        'status': 'healthy',
        'service': 'saleslist-backend',
        'timestamp': _timestamp(),
    }
    return _log_and_respond('health_check.success', payload)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def db_health_check(request):
    """データベース接続チェック"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        payload = {
            'status': 'healthy',
            'database': 'connected',
            'timestamp': _timestamp(),
        }
        return _log_and_respond('db_health_check.success', payload)
    except Exception as e:
        payload = {
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': _timestamp(),
        }
        return _log_and_respond('db_health_check.failure', payload, status=500, level=logging.ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def cache_health_check(request):
    """Redisキャッシュ接続チェック"""
    try:
        # Redis接続テスト（設定されている場合のみ）
        if hasattr(settings, 'CACHES') and 'redis' in str(settings.CACHES.get('default', {}).get('BACKEND', '')):
            r = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
            r.ping()
            payload = {
                'status': 'healthy',
                'cache': 'connected',
                'timestamp': _timestamp(),
            }
            return _log_and_respond('cache_health_check.success', payload)
        else:
            payload = {
                'status': 'healthy',
                'cache': 'database_cache',
                'timestamp': _timestamp(),
            }
            return _log_and_respond('cache_health_check.database_cache', payload)
    except Exception as e:
        payload = {
            'status': 'unhealthy',
            'cache': 'disconnected',
            'error': str(e),
            'timestamp': _timestamp(),
        }
        return _log_and_respond('cache_health_check.failure', payload, status=500, level=logging.ERROR)


health_check.throttle_scope = 'health'
db_health_check.throttle_scope = 'health'
cache_health_check.throttle_scope = 'health'
