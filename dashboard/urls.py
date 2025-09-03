from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.dashboard_stats, name='dashboard_stats'),
    path('stats', views.dashboard_stats, name='dashboard_stats_no_slash'),
    path('recent-projects/', views.recent_projects, name='recent_projects'),
    path('recent-projects', views.recent_projects, name='recent_projects_no_slash'),
    path('recent-companies/', views.recent_companies, name='recent_companies'),
    path('recent-companies', views.recent_companies, name='recent_companies_no_slash'),
]