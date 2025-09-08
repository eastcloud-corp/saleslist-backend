from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)
router.register(r'industries', views.IndustryViewSet)
router.register(r'statuses', views.StatusViewSet)
router.register(r'progress-statuses', views.ProjectProgressStatusViewSet)
router.register(r'media-types', views.MediaTypeViewSet)
router.register(r'meeting-statuses', views.RegularMeetingStatusViewSet)
router.register(r'list-availabilities', views.ListAvailabilityViewSet)
router.register(r'list-import-sources', views.ListImportSourceViewSet)
router.register(r'service-types', views.ServiceTypeViewSet)

router_slash = DefaultRouter(trailing_slash=True)
router_slash.register(r'industries', views.IndustryViewSet)
router_slash.register(r'statuses', views.StatusViewSet)
router_slash.register(r'progress-statuses', views.ProjectProgressStatusViewSet)
router_slash.register(r'media-types', views.MediaTypeViewSet)
router_slash.register(r'meeting-statuses', views.RegularMeetingStatusViewSet)
router_slash.register(r'list-availabilities', views.ListAvailabilityViewSet)
router_slash.register(r'list-import-sources', views.ListImportSourceViewSet)
router_slash.register(r'service-types', views.ServiceTypeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', include(router_slash.urls)),
    path('prefectures/', views.prefectures_list, name='prefectures'),
    path('prefectures', views.prefectures_list, name='prefectures_no_slash'),
    path('sales-statuses/', views.sales_statuses_list, name='sales_statuses'),
    path('sales-statuses', views.sales_statuses_list, name='sales_statuses_no_slash'),
]