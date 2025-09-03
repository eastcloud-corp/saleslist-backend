from django.urls import path
from . import views

urlpatterns = [
    path('template/', views.template_view, name='ng_template'),
    path('template', views.template_view, name='ng_template_no_slash'),
    path('match/', views.match_view, name='ng_match'),
    path('match', views.match_view, name='ng_match_no_slash'),
]