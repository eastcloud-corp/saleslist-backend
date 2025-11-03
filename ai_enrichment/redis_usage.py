
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.core.cache import caches
from django.utils import timezone

try:
    from django_redis import get_redis_connection
except ImportError:  # pragma: no cover
    get_redis_connection = None


DEFAULT_COST_LIMIT = 150.0
DEFAULT_COST_PER_REQUEST = 0.05

_USAGE_KEY_TEMPLATE = "ai_usage:{year}-{month}:{metric}"


def _current_month(now: Optional[datetime] = None) -> tuple[int, int]:
    now = now or timezone.now()
    local = timezone.localtime(now)
    return local.year, local.month


def _key(metric: str, *, year: int, month: int) -> str:
    return _USAGE_KEY_TEMPLATE.format(year=year, month=str(month).zfill(2), metric=metric)


def _month_ttl(year: int, month: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    now = timezone.now()
    end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=0)
    seconds = int((end - now).total_seconds())
    return max(seconds, 3600)


def _to_int_or_none(value: Optional[object]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _derive_call_limit(cost_limit: float, cost_per_call: float) -> int:
    if cost_limit <= 0 or cost_per_call <= 0:
        return 0
    return max(int(cost_limit // cost_per_call), 0)


def _derive_daily_limit(call_limit: int, *, now: Optional[datetime] = None) -> int:
    if call_limit <= 0:
        return 0
    year, month = _current_month(now)
    days_in_month = calendar.monthrange(year, month)[1]
    if days_in_month <= 0:
        return call_limit
    per_day = call_limit // days_in_month
    return max(per_day, 1)


@dataclass
class UsageSnapshot:
    calls: int
    cost: float

    def can_execute(self, *, cost_limit: float, call_limit: int, cost_per_call: float) -> bool:
        return self.cost + cost_per_call <= cost_limit and self.calls + 1 <= call_limit


class UsageTracker:
    def __init__(
        self,
        *,
        connection_alias: str = "default",
        cost_limit: Optional[float] = None,
        call_limit: Optional[int] = None,
        cost_per_call: Optional[float] = None,
    ) -> None:
        self.connection_alias = connection_alias
        backend_name = settings.CACHES.get(connection_alias, {}).get("BACKEND", "")
        self._use_cache = (
            get_redis_connection is None
            or "django_redis" not in backend_name
        )
        self.cost_limit = cost_limit if cost_limit is not None else getattr(settings, "POWERPLEXY_MONTHLY_COST_LIMIT", DEFAULT_COST_LIMIT)
        self.cost_per_call = cost_per_call if cost_per_call is not None else getattr(settings, "POWERPLEXY_COST_PER_REQUEST", DEFAULT_COST_PER_REQUEST)

        if call_limit is not None:
            resolved_call_limit = call_limit
        else:
            explicit_call_limit = _to_int_or_none(getattr(settings, "POWERPLEXY_MONTHLY_CALL_LIMIT", None))
            if explicit_call_limit is not None and explicit_call_limit >= 0:
                resolved_call_limit = explicit_call_limit
            else:
                resolved_call_limit = _derive_call_limit(self.cost_limit, self.cost_per_call)
        self.call_limit = max(int(resolved_call_limit), 0)

        explicit_daily_limit = _to_int_or_none(getattr(settings, "POWERPLEXY_DAILY_RECORD_LIMIT", None))
        if explicit_daily_limit is not None and explicit_daily_limit >= 0:
            resolved_daily_limit = explicit_daily_limit
        else:
            resolved_daily_limit = _derive_daily_limit(self.call_limit)
        self.daily_limit = max(int(resolved_daily_limit), 0)

    @property
    def client(self):
        if self._use_cache:
            return caches[self.connection_alias]
        try:
            return get_redis_connection(self.connection_alias)
        except NotImplementedError:
            self._use_cache = True
            return caches[self.connection_alias]

    def snapshot(self, *, now: Optional[datetime] = None) -> UsageSnapshot:
        year, month = _current_month(now)
        if self._use_cache:
            cache = self.client
            calls = int(cache.get(_key("calls", year=year, month=month), 0))
            cost = float(cache.get(_key("cost", year=year, month=month), 0.0))
        else:
            calls = int(self.client.get(_key("calls", year=year, month=month)) or 0)
            cost_raw = self.client.get(_key("cost", year=year, month=month))
            cost = float(cost_raw) if cost_raw is not None else 0.0
        return UsageSnapshot(calls=calls, cost=cost)

    def can_execute(self) -> bool:
        usage = self.snapshot()
        return usage.can_execute(
            cost_limit=self.cost_limit,
            call_limit=self.call_limit,
            cost_per_call=self.cost_per_call,
        )

    def increment(self, *, calls: int = 1, cost: Optional[float] = None) -> UsageSnapshot:
        cost = cost if cost is not None else calls * self.cost_per_call
        year, month = _current_month()
        ttl = _month_ttl(year, month)
        if self._use_cache:
            cache = self.client
            call_key = _key("calls", year=year, month=month)
            cost_key = _key("cost", year=year, month=month)
            cache.set(call_key, int(cache.get(call_key, 0)) + calls, ttl)
            cache.set(cost_key, float(cache.get(cost_key, 0.0)) + cost, ttl)
        else:
            pipe = self.client.pipeline(True)
            pipe.incrby(_key("calls", year=year, month=month), calls)
            pipe.expire(_key("calls", year=year, month=month), ttl)
            pipe.incrbyfloat(_key("cost", year=year, month=month), cost)
            pipe.expire(_key("cost", year=year, month=month), ttl)
            pipe.execute()
        return self.snapshot()

    def remaining(self) -> UsageSnapshot:
        usage = self.snapshot()
        remaining_calls = max(self.call_limit - usage.calls, 0)
        remaining_cost = max(self.cost_limit - usage.cost, 0.0)
        return UsageSnapshot(calls=remaining_calls, cost=remaining_cost)
