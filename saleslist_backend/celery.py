import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleslist_backend.settings")

app = Celery("saleslist_backend")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Debug task executed: {self.request!r}")
