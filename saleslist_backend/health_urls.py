from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import redis


def health_check(request):
    """アプリケーションのヘルスチェック"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'saleslist-backend',
        'timestamp': '2025-09-01T00:00:00Z'
    })


def db_health_check(request):
    """データベース接続チェック"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': '2025-09-01T00:00:00Z'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': '2025-09-01T00:00:00Z'
        }, status=500)


def cache_health_check(request):
    """Redisキャッシュ接続チェック"""
    try:
        # Redis接続テスト（設定されている場合のみ）
        if hasattr(settings, 'CACHES') and 'redis' in str(settings.CACHES.get('default', {}).get('BACKEND', '')):
            import redis
            r = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
            r.ping()
            return JsonResponse({
                'status': 'healthy',
                'cache': 'connected',
                'timestamp': '2025-09-01T00:00:00Z'
            })
        else:
            return JsonResponse({
                'status': 'healthy',
                'cache': 'database_cache',
                'timestamp': '2025-09-01T00:00:00Z'
            })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'cache': 'disconnected',
            'error': str(e),
            'timestamp': '2025-09-01T00:00:00Z'
        }, status=500)