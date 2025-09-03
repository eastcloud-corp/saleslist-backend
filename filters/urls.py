from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)
router.register(r'', views.SavedFilterViewSet)

router_slash = DefaultRouter(trailing_slash=True)
router_slash.register(r'', views.SavedFilterViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', include(router_slash.urls)),
]