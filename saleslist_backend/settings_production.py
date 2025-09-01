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

ALLOWED_HOSTS = ['sales-navigator.east-cloud.jp', '153.120.128.27', 'localhost']

CORS_ALLOWED_ORIGINS = [
    "https://sales-navigator.east-cloud.jp",
]

CORS_ALLOW_ALL_ORIGINS = False