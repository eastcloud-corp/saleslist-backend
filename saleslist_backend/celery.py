import logging
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleslist_backend.settings.prod")

app = Celery("saleslist_backend")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.on_after_configure.connect
def check_powerplexy_api_key_on_configure(sender, **kwargs):
    """④ 起動時に POWERPLEXY_API_KEY の存在をチェックし、未設定時は警告を出す"""
    try:
        from django.conf import settings
        key = getattr(settings, "POWERPLEXY_API_KEY", "") or ""
        if not str(key).strip():
            logging.getLogger(__name__).warning(
                "POWERPLEXY_API_KEY が設定されていません。環境変数または .env に POWERPLEXY_API_KEY を設定してください。AI補完タスク実行時にスキップされます。"
            )
    except Exception:
        pass  # 設定読み込み前などでは無視


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Debug task executed: {self.request!r}")
