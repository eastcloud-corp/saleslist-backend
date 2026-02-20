"""
URL configuration for saleslist_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .health_urls import health_check, db_health_check, cache_health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/clients/', include('clients.urls')),
    path('api/v1/companies/', include('companies.urls')),
    path('api/v1/projects/', include('projects.urls')),
    path('api/v1/master/', include('masters.urls')),
    path('api/v1/dashboard/', include('dashboard.urls')),
    path('api/v1/saved_filters/', include('filters.urls')),
    path('api/v1/executives/', include('executives.urls')),
    path('api/v1/ng-companies/', include('ng_companies.urls')),
    path('api/v1/data-collection/', include('data_collection.urls')),
    path('api/v1/dm-assistant/', include('dm_assistant.urls')),
    
    # Health check endpoints
    path('health', health_check, name='health_check'),
    path('api/health/db', db_health_check, name='db_health_check'),
    path('api/health/cache', cache_health_check, name='cache_health_check'),
]

# Static files serving (production only)
if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
