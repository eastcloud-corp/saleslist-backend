"""Helpers for MFA login flow."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

try:  # pragma: no cover - optional dependency at runtime
    from sendgrid import SendGridAPIClient  # type: ignore
    from sendgrid.helpers.mail import Mail  # type: ignore
except Exception:  # pragma: no cover - sendgrid not installed in some envs
    SendGridAPIClient = None  # type: ignore
    Mail = None  # type: ignore

logger = logging.getLogger("security.auth")


class PendingAuthNotFound(Exception):
    """Raised when the pending MFA session does not exist or expired."""


class PendingAuthExpired(Exception):
    """Raised when the pending MFA session already expired."""


class TokenMismatch(Exception):
    """Raised when the submitted MFA token is invalid."""


class ResendNotAllowed(Exception):
    """Raised when resend constraints are violated."""


class MFAEmailError(Exception):
    """Raised when the confirmation code could not be sent."""


def _cache_key(pending_auth_id: str) -> str:
    return f"pending_auth:{pending_auth_id}"


def _now() -> datetime:
    return timezone.now()


def _to_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt


def _remaining_seconds(created_at: datetime) -> int:
    expires_at = created_at + timedelta(seconds=settings.MFA_TOKEN_TTL_SECONDS)
    remaining = int((expires_at - _now()).total_seconds())
    return max(remaining, 0)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(length: Optional[int] = None) -> str:
    digits = "0123456789"
    size = length or settings.MFA_TOKEN_LENGTH
    return "".join(secrets.choice(digits) for _ in range(size))


def _send_token_email(email: str, name: str, token: str) -> None:
    subject = settings.MFA_EMAIL_SUBJECT
    ttl_minutes = settings.MFA_TOKEN_TTL_SECONDS // 60
    body = settings.MFA_EMAIL_BODY_TEMPLATE.format(
        name=name or email,
        token=token,
        ttl_minutes=ttl_minutes,
    )

    api_key = getattr(settings, "SENDGRID_API_KEY", "")
    template_id = getattr(settings, "MFA_EMAIL_TEMPLATE_ID", "")
    from_email = getattr(settings, "MFA_EMAIL_FROM", "no-reply@saleslist.local")
    override_recipient = getattr(settings, "MFA_DEBUG_EMAIL_RECIPIENT", "")
    target_email = override_recipient or email

    if SendGridAPIClient and api_key:
        try:
            client = SendGridAPIClient(api_key)
            if template_id:
                message = Mail(from_email=from_email, to_emails=target_email)
                message.template_id = template_id
                message.dynamic_template_data = {
                    "name": name or email,
                    "token": token,
                    "ttl_minutes": ttl_minutes,
                }
            else:
                message = Mail(
                    from_email=from_email,
                    to_emails=target_email,
                    subject=subject,
                    plain_text_content=body,
                )
            client.send(message)
            logger.info("mfa.email.sendgrid_sent", extra={"email": target_email})
            return
        except Exception as exc:  # pragma: no cover - network failure path
            logger.warning(
                "mfa.email.send_failed",
                extra={"email": target_email, "error": str(exc)},
            )

    try:
        send_mail(subject, body, from_email, [target_email], fail_silently=False)
        logger.info("mfa.email.django_sent", extra={"email": target_email})
        return
    except Exception as exc:  # pragma: no cover - email backend failure
        logger.warning(
            "mfa.email.django_failed",
            extra={"email": target_email, "error": str(exc)},
        )
        raise MFAEmailError("確認コードの送信に失敗しました") from exc


def create_pending_auth(user, token: Optional[str] = None) -> Tuple[str, str]:
    """Create a pending auth session and send the initial token."""
    code = token or generate_token()
    pending_auth_id = str(uuid.uuid4())
    now = _now()
    value: Dict[str, Any] = {
        "user_id": user.id,
        "email": user.email,
        "name": getattr(user, "name", ""),
        "hashed_token": hash_token(code),
        "created_at": now.isoformat(),
        "resend_count": 0,
        "last_sent_at": now.isoformat(),
    }

    cache.set(_cache_key(pending_auth_id), value, timeout=settings.MFA_TOKEN_TTL_SECONDS)
    _send_token_email(user.email, getattr(user, "name", ""), code)

    logger.info(
        "mfa.pending.created",
        extra={"user_id": user.id, "email": user.email, "pending_auth_id": pending_auth_id},
    )
    return pending_auth_id, code


def get_pending_auth(pending_auth_id: str) -> Dict[str, Any]:
    data = cache.get(_cache_key(pending_auth_id))
    if not data:
        raise PendingAuthNotFound
    created_at = _to_datetime(data["created_at"])
    if _remaining_seconds(created_at) <= 0:
        cache.delete(_cache_key(pending_auth_id))
        raise PendingAuthExpired
    return data


def resend_token(pending_auth_id: str) -> None:
    data = get_pending_auth(pending_auth_id)
    now = _now()
    last_sent_at = _to_datetime(data["last_sent_at"])

    if (now - last_sent_at).total_seconds() < settings.MFA_RESEND_INTERVAL_SECONDS:
        raise ResendNotAllowed("RESEND_TOO_SOON")

    if data["resend_count"] >= settings.MFA_MAX_RESEND_COUNT:
        raise ResendNotAllowed("RESEND_LIMIT_REACHED")

    new_token = generate_token()
    data["hashed_token"] = hash_token(new_token)
    data["resend_count"] = data["resend_count"] + 1
    data["last_sent_at"] = now.isoformat()

    created_at = _to_datetime(data["created_at"])
    remaining = _remaining_seconds(created_at)
    if remaining <= 0:
        cache.delete(_cache_key(pending_auth_id))
        raise PendingAuthExpired

    cache.set(_cache_key(pending_auth_id), data, timeout=max(1, remaining))
    _send_token_email(data["email"], data.get("name", ""), new_token)
    logger.info(
        "mfa.pending.resent",
        extra={
            "pending_auth_id": pending_auth_id,
            "email": data["email"],
            "resend_count": data["resend_count"],
        },
    )


def verify_token(pending_auth_id: str, token: str) -> Dict[str, Any]:
    data = get_pending_auth(pending_auth_id)
    hashed = data["hashed_token"]
    if not secrets.compare_digest(hashed, hash_token(token)):
        raise TokenMismatch

    cache.delete(_cache_key(pending_auth_id))
    logger.info(
        "mfa.pending.verified",
        extra={"pending_auth_id": pending_auth_id, "email": data["email"]},
    )
    return data
