try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    # celeryがインストールされていない場合（seed_data.py実行時など）
    celery_app = None
    __all__ = ()
