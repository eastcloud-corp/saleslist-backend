import uuid

from .logging_utils import client_ip_ctx, request_id_ctx, user_id_ctx


def _extract_client_ip(request) -> str | None:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class RequestContextMiddleware:
    """リクエストIDやクライアント情報をログコンテキストへ設定するミドルウェア"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        client_ip = _extract_client_ip(request)

        request.request_id = request_id

        request_id_token = request_id_ctx.set(request_id)
        client_ip_token = client_ip_ctx.set(client_ip)

        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            user_id_token = user_id_ctx.set(user.id)
        else:
            user_id_token = user_id_ctx.set(None)

        try:
            response = self.get_response(request)

            response['X-Request-ID'] = request_id
            return response
        finally:
            request_id_ctx.reset(request_id_token)
            client_ip_ctx.reset(client_ip_token)
            user_id_ctx.reset(user_id_token)
