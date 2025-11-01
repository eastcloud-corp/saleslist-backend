from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DataCollectionRunViewSet, DataCollectionTriggerView

router = DefaultRouter()
router.register(r"runs", DataCollectionRunViewSet, basename="data-collection-run")

urlpatterns = [
    path("", include(router.urls)),
    path("trigger", DataCollectionTriggerView.as_view(), name="data-collection-trigger"),
]
