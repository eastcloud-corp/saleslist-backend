from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.CompanyViewSet)
router.register(r'executives', views.ExecutiveViewSet)

urlpatterns = [
    path('', include(router.urls)),
]