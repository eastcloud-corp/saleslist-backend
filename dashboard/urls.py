from django.urls import path
from . import views

urlpatterns = [
    path('stats', views.dashboard_stats, name='dashboard_stats'),
    path('recent-projects', views.recent_projects, name='recent_projects'),
    path('recent-companies', views.recent_companies, name='recent_companies'),
]