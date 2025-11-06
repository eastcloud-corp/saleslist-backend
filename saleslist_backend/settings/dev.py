"""
Development settings.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + ["localhost", "127.0.0.1", "0.0.0.0"]))  # type: ignore[name-defined]

CORS_ALLOW_ALL_ORIGINS = True  # type: ignore[name-defined]

_dev_origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3010",
    "http://127.0.0.1:3010",
}

CORS_ALLOWED_ORIGINS = list(set(CORS_ALLOWED_ORIGINS).union(_dev_origins))  # type: ignore[name-defined]
CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS).union(_dev_origins))  # type: ignore[name-defined]

ENABLE_REVIEW_SAMPLE_API = True
