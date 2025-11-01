
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


DEFAULT_COST_LIMIT = 20.0
DEFAULT_CALL_LIMIT = 5000
DEFAULT_COST_PER_REQUEST = 0.004

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
        self._use_cache = get_redis_connection is None
        self.cost_limit = cost_limit if cost_limit is not None else getattr(settings, "POWERPLEXY_MONTHLY_COST_LIMIT", DEFAULT_COST_LIMIT)
        self.call_limit = call_limit if call_limit is not None else getattr(settings, "POWERPLEXY_MONTHLY_CALL_LIMIT", DEFAULT_CALL_LIMIT)
        self.cost_per_call = cost_per_call if cost_per_call is not None else getattr(settings, "POWERPLEXY_COST_PER_REQUEST", DEFAULT_COST_PER_REQUEST)

    @property
    def client(self):
        if self._use_cache:
            return caches[self.connection_alias]
        return get_redis_connection(self.connection_alias)

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
