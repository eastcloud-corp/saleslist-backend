from django.urls import path
from . import views

urlpatterns = [
    path('template/', views.template_view, name='ng_template'),
    path('match/', views.match_view, name='ng_match'),
]