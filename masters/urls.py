from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'industries', views.IndustryViewSet)
router.register(r'statuses', views.StatusViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('prefectures/', views.prefectures_list, name='prefectures'),
    path('sales-statuses/', views.sales_statuses_list, name='sales_statuses'),
]