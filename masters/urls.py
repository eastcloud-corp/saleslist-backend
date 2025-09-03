from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)
router.register(r'industries', views.IndustryViewSet)
router.register(r'statuses', views.StatusViewSet)

router_slash = DefaultRouter(trailing_slash=True)
router_slash.register(r'industries', views.IndustryViewSet)
router_slash.register(r'statuses', views.StatusViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', include(router_slash.urls)),
    path('prefectures/', views.prefectures_list, name='prefectures'),
    path('prefectures', views.prefectures_list, name='prefectures_no_slash'),
    path('sales-statuses/', views.sales_statuses_list, name='sales_statuses'),
    path('sales-statuses', views.sales_statuses_list, name='sales_statuses_no_slash'),
]