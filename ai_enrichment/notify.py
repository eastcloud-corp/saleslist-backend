
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def notify_success(message: str, *, extra: Optional[dict] = None) -> None:
    logger.info("ai_enrich.success: %s", message, extra=extra or {})


def notify_warning(message: str, *, extra: Optional[dict] = None) -> None:
    logger.warning("ai_enrich.warning: %s", message, extra=extra or {})


def notify_error(message: str, *, extra: Optional[dict] = None) -> None:
    logger.error("ai_enrich.error: %s", message, extra=extra or {})
