"""
Development settings.
"""

from datetime import timedelta

from celery.schedules import crontab

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + ["localhost", "127.0.0.1", "0.0.0.0"]))  # type: ignore[name-defined]

CORS_ALLOW_ALL_ORIGINS = True  # type: ignore[name-defined]

_dev_origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3010",
    "http://127.0.0.1:3010",
    "http://localhost:3020",
    "http://127.0.0.1:3020",
}

CORS_ALLOWED_ORIGINS = list(set(CORS_ALLOWED_ORIGINS).union(_dev_origins))  # type: ignore[name-defined]
CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS).union(_dev_origins))  # type: ignore[name-defined]

# 開発環境ではメールをコンソールに出力
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ENABLE_REVIEW_SAMPLE_API = True

# 開発環境ではAI補完タスクを30分ごとに実行（テスト用）
CELERY_BEAT_SCHEDULE = {
    "sync-facebook-activity": {
        "task": "companies.tasks.dispatch_facebook_sync",
        "schedule": crontab(hour=2, minute=0),
    },
    "run-ai-enrich": {
        "task": "ai_enrichment.tasks.run_ai_enrich_scheduled",
        "schedule": timedelta(minutes=30),  # 開発環境では30分ごとに実行
    },
}
