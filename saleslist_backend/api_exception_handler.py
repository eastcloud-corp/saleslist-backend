import logging
from typing import Any

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler as drf_exception_handler


rate_limit_logger = logging.getLogger('security.rate_limit')


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    """DRF例外ハンドラー。レートリミット発生時に監査ログへ記録する"""
    response = drf_exception_handler(exc, context)

    if isinstance(exc, Throttled):
        view = context.get('view')
        scope = getattr(view, 'throttle_scope', None) or getattr(exc, 'scope', None)
        request = context.get('request')
        rate_limit_logger.warning('api.throttled', extra={
            'scope': scope,
            'wait_seconds': exc.wait,
            'detail': getattr(exc, 'detail', None),
            'path': request.get_full_path() if request else None,
            'method': request.method if request else None,
        })

    return response
