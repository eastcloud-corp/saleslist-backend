from .settings import *

# Production overrides
DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'saleslist_production',
        'USER': 'saleslist_prod_user',
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': 'db',
        'PORT': '5432',
    }
}

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='sales-navigator.east-cloud.jp,localhost').split(',')

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='https://sales-navigator.east-cloud.jp').split(',')

CORS_ALLOW_ALL_ORIGINS = False

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = '/app/static'

# Media files configuration  
MEDIA_URL = '/media/'
MEDIA_ROOT = '/app/media'

# Static files serving
STATICFILES_DIRS = []