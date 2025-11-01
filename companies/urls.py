from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)
router.register(r'reviews', views.CompanyReviewViewSet, basename='company-reviews')
router.register(r'executives', views.ExecutiveViewSet)
router.register(r'', views.CompanyViewSet)

router_slash = DefaultRouter(trailing_slash=True)
router_slash.register(r'reviews', views.CompanyReviewViewSet, basename='company-reviews-slash')
router_slash.register(r'executives', views.ExecutiveViewSet)
router_slash.register(r'', views.CompanyViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', include(router_slash.urls)),
]
