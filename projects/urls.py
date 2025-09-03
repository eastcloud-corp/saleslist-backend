from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)
router.register(r'', views.ProjectViewSet)

router_slash = DefaultRouter(trailing_slash=True)
router_slash.register(r'', views.ProjectViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', include(router_slash.urls)),
    path('<int:project_id>/companies/<int:company_id>', views.project_company_detail, name='project_company_detail'),
    path('<int:project_id>/companies/<int:company_id>/', views.project_company_detail, name='project_company_detail_slash'),
    path('<int:project_id>/companies/<int:company_id>/detail/', views.sales_target_company_detail, name='sales_target_company_detail'),
    path('<int:project_id>/companies/<int:company_id>/history/', views.sales_history, name='sales_history'),
    path('<int:project_id>/companies/<int:company_id>/history/<int:history_id>', views.sales_history_detail, name='sales_history_detail'),
]