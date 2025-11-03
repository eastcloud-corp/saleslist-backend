import contextvars
import json
import logging
from typing import Any, Dict, Iterable, Mapping


request_id_ctx = contextvars.ContextVar('request_id', default=None)
client_ip_ctx = contextvars.ContextVar('client_ip', default=None)
user_id_ctx = contextvars.ContextVar('user_id', default=None)


class RequestContextFilter(logging.Filter):
    """ログレコードにリクエストコンテキスト情報を付与するフィルター"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.client_ip = client_ip_ctx.get()
        record.user_id = user_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """ログをJSON形式でフォーマットするフォーマッター"""

    RESERVED_ATTRIBUTES = {
        'name',
        'msg',
        'args',
        'levelname',
        'levelno',
        'pathname',
        'filename',
        'module',
        'exc_info',
        'exc_text',
        'stack_info',
        'lineno',
        'funcName',
        'created',
        'msecs',
        'relativeCreated',
        'thread',
        'threadName',
        'processName',
        'process',
        'message',
        'request_id',
        'client_ip',
        'user_id',
        'asctime',
    }

    @staticmethod
    def _make_json_safe(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Mapping):
            return {str(k): JsonFormatter._make_json_safe(v) for k, v in value.items()}

        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return [JsonFormatter._make_json_safe(v) for v in value]

        return str(value)

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        for key in ('request_id', 'client_ip', 'user_id'):
            value = getattr(record, key, None)
            if value:
                log_record[key] = self._make_json_safe(value)

        for key, value in record.__dict__.items():
            if key in self.RESERVED_ATTRIBUTES:
                continue
            if key.startswith('_'):
                continue
            log_record[key] = self._make_json_safe(value)

        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)
