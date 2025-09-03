from .settings import *

# Production overrides
DEBUG = False

# Enable static files serving in production
from django.core.management.utils import get_random_secret_key

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

# Whitenoise for static files serving
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
] + MIDDLEWARE[1:]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CSRF settings for HTTPS
CSRF_TRUSTED_ORIGINS = [
    'https://sales-navigator.east-cloud.jp',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_TZ = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/app/logs/django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'companies': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

