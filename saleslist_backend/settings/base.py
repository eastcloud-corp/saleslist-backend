"""
Base settings shared by all environments.
"""

import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import Csv, config
from django.utils import timezone

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Core configuration
SECRET_KEY = config("DJANGO_SECRET_KEY", default="django-insecure-change-me")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = list(
    config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    # Local apps
    "accounts",
    "clients",
    "companies",
    "projects",
    "masters",
    "dashboard",
    "filters",
    "executives",
    "ng_companies",
    "data_collection",
    "ai_enrichment",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "saleslist_backend.middleware.RequestContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "saleslist_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "saleslist_backend.wsgi.application"
ASGI_APPLICATION = "saleslist_backend.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="saleslist_dev"),
        "USER": config("DB_USER", default="saleslist_user"),
        "PASSWORD": config("DB_PASSWORD", default="saleslist_password"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5442"),
    }
}

if os.environ.get("USE_SQLITE_FOR_TESTS") == "1":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test-db.sqlite3",
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email configuration
EMAIL_BACKEND_DEFAULT = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_BACKEND = config("EMAIL_BACKEND", default=EMAIL_BACKEND_DEFAULT)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=30, cast=int)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@saleslist.local")

# REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("DRF_THROTTLE_ANON", default="60/min"),
        "user": config("DRF_THROTTLE_USER", default="600/min"),
        "auth_login": config("DRF_THROTTLE_LOGIN", default="10/min"),
        "auth_refresh": config("DRF_THROTTLE_REFRESH", default="30/min"),
        "auth_mfa_resend": config("DRF_THROTTLE_MFA_RESEND", default="5/min"),
        "auth_mfa_verify": config("DRF_THROTTLE_MFA_VERIFY", default="20/min"),
        "health": config("DRF_THROTTLE_HEALTH", default="120/min"),
    },
    "EXCEPTION_HANDLER": "saleslist_backend.api_exception_handler.custom_exception_handler",
}

JWT_ACCESS_TOKEN_LIFETIME_HOURS = config("JWT_ACCESS_TOKEN_LIFETIME_HOURS", default=72, cast=int)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=JWT_ACCESS_TOKEN_LIFETIME_HOURS),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

MFA_TOKEN_TTL_SECONDS = config("MFA_TOKEN_TTL_SECONDS", default=1800, cast=int)
MFA_RESEND_INTERVAL_SECONDS = config("MFA_RESEND_INTERVAL_SECONDS", default=30, cast=int)
MFA_MAX_RESEND_COUNT = config("MFA_MAX_RESEND_COUNT", default=5, cast=int)
MFA_TOKEN_LENGTH = config("MFA_TOKEN_LENGTH", default=6, cast=int)
SENDGRID_API_KEY = config("SENDGRID_API_KEY", default="")
MFA_EMAIL_FROM = config("MFA_EMAIL_FROM", default="no-reply@saleslist.local")
MFA_EMAIL_SUBJECT = config("MFA_EMAIL_SUBJECT", default="【セールスナビゲーター】ログイン確認コードのお知らせ")
MFA_EMAIL_BODY_TEMPLATE = config(
    "MFA_EMAIL_BODY_TEMPLATE",
    default=(
        "{name} 様\n"
        "セールスナビゲーターへのログインを確認するため、以下の確認コードを入力してください。\n\n"
        "確認コード: {token}\n"
        "有効期限: 発行から{ttl_minutes}分\n\n"
        "このメールに心当たりがない場合は破棄してください。"
    ),
)
MFA_EMAIL_TEMPLATE_ID = config("MFA_EMAIL_TEMPLATE_ID", default="")
MFA_DEBUG_EMAIL_RECIPIENT = config("MFA_DEBUG_EMAIL_RECIPIENT", default="")

# PowerPlexy AI enrichment configuration
POWERPLEXY_API_KEY = config("POWERPLEXY_API_KEY", default="")
POWERPLEXY_API_ENDPOINT = config("POWERPLEXY_API_ENDPOINT", default="https://api.perplexity.ai/chat/completions")
POWERPLEXY_MODEL = config("POWERPLEXY_MODEL", default="sonar-pro")
POWERPLEXY_TIMEOUT = config("POWERPLEXY_TIMEOUT", default=30, cast=int)
POWERPLEXY_MONTHLY_COST_LIMIT = config("POWERPLEXY_MONTHLY_COST_LIMIT", default=150.0, cast=float)
_powerplexy_monthly_call_limit = config("POWERPLEXY_MONTHLY_CALL_LIMIT", default=None)
POWERPLEXY_MONTHLY_CALL_LIMIT = (
    int(_powerplexy_monthly_call_limit)
    if _powerplexy_monthly_call_limit not in (None, "")
    else None
)
POWERPLEXY_COST_PER_REQUEST = config("POWERPLEXY_COST_PER_REQUEST", default=0.05, cast=float)
_powerplexy_daily_record_limit = config("POWERPLEXY_DAILY_RECORD_LIMIT", default=None)
POWERPLEXY_DAILY_RECORD_LIMIT = (
    int(_powerplexy_daily_record_limit)
    if _powerplexy_daily_record_limit not in (None, "")
    else None
)
ENABLE_REVIEW_SAMPLE_API = config("ENABLE_REVIEW_SAMPLE_API", default=False, cast=bool)

# Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "Asia/Tokyo"
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_TIME_LIMIT", default=1800, cast=int)
CELERY_TASK_DEFAULT_QUEUE = config("CELERY_TASK_DEFAULT_QUEUE", default="default")
CELERY_BEAT_SCHEDULE = {
    "sync-facebook-activity": {
        "task": "companies.tasks.dispatch_facebook_sync",
        "schedule": crontab(hour=2, minute=0, nowfun=timezone.now),
    },
    "run-ai-enrich": {
        "task": "ai_enrichment.tasks.run_ai_enrich",
        "schedule": crontab(hour=3, minute=0, nowfun=timezone.now),
    },
}

# Facebook API
FACEBOOK_GRAPH_API_VERSION = config("FACEBOOK_GRAPH_API_VERSION", default="v19.0")
FACEBOOK_ACCESS_TOKEN = config("FACEBOOK_ACCESS_TOKEN", default="")
FACEBOOK_GRAPH_API_TIMEOUT = config("FACEBOOK_GRAPH_API_TIMEOUT", default=10, cast=int)
FACEBOOK_SYNC_CHUNK_SIZE = config("FACEBOOK_SYNC_CHUNK_SIZE", default=500, cast=int)

# Corporate Number API
CORPORATE_NUMBER_API_BASE_URL = config(
    "CORPORATE_NUMBER_API_BASE_URL",
    default="https://api.houjin-bangou.nta.go.jp",
)
CORPORATE_NUMBER_API_TOKEN = config("CORPORATE_NUMBER_API_TOKEN", default="")
CORPORATE_NUMBER_API_TIMEOUT = config("CORPORATE_NUMBER_API_TIMEOUT", default=10, cast=int)
CORPORATE_NUMBER_API_MAX_RESULTS = config(
    "CORPORATE_NUMBER_API_MAX_RESULTS",
    default=5,
    cast=int,
)

# CORS / CSRF
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,http://localhost:3002,"
    "http://127.0.0.1:3000,http://127.0.0.1:3002,"
    "https://saleslist-front.vercel.app"
)
CORS_ALLOWED_ORIGINS = list(
    config("CORS_ALLOWED_ORIGINS", default=DEFAULT_CORS_ORIGINS, cast=Csv())
)
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = list(
    config(
        "CSRF_TRUSTED_ORIGINS",
        default="http://localhost:3000,http://localhost:3002",
        cast=Csv(),
    )
)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Database cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "social_navigator_cache",
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    }
}

# Snapshot retention
SNAPSHOT_RETENTION_DAYS = config("SNAPSHOT_RETENTION_DAYS", default=7, cast=int)

# Logging
configured_log_dir = config("PROJECT_LOG_DIR", default="")
LOG_DIR = Path(configured_log_dir) if configured_log_dir else Path.home() / ".saleslist_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "saleslist_backend.logging_utils.JsonFormatter",
        },
        "console": {
            "format": "[%(levelname)s] %(message)s",
        },
    },
    "filters": {
        "request_context": {
            "()": "saleslist_backend.logging_utils.RequestContextFilter",
        },
    },
    "handlers": {
        "projects_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "projects.log"),
            "when": "midnight",
            "backupCount": 14,
            "encoding": "utf-8",
            "formatter": "structured",
            "filters": ["request_context"],
        },
        "companies_import_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "companies_import.log"),
            "when": "midnight",
            "backupCount": 14,
            "encoding": "utf-8",
            "formatter": "structured",
            "filters": ["request_context"],
        },
        "security_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "security.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "formatter": "structured",
            "filters": ["request_context"],
        },
        "health_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "health.log"),
            "when": "midnight",
            "backupCount": 14,
            "encoding": "utf-8",
            "formatter": "structured",
            "filters": ["request_context"],
        },
        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "formatter": "structured",
            "filters": ["request_context"],
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["request_context"],
        },
    },
    "loggers": {
        "projects.activities": {
            "handlers": ["projects_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "companies.import": {
            "handlers": ["companies_import_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "security.auth": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "security.rate_limit": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "saleslist.health": {
            "handlers": ["health_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# Sessions
SESSION_ENGINE = "django.contrib.sessions.backends.db"

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
