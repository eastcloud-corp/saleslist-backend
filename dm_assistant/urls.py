from django.urls import path

from . import views

urlpatterns = [
    path("generate", views.DmGenerateView.as_view(), name="dm-assistant-generate"),
]
