"""Reference adapters of the key-value ports (shortage summary, follows, alerts, counters)."""
import time
from datetime import timedelta

from app.application.ports.alert_store import AlertStore
from app.application.ports.counter_store import CounterStore
from app.application.ports.follow_store import FollowStore
from app.application.ports.revoked_token_store import RevokedTokenStore
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.entities.alert import Alert
from app.domain.entities.shortage import ShortageSummary


class MemoryShortageStatusStore(ShortageStatusStore):
    def __init__(self) -> None:
        self._d: dict[str, tuple[ShortageSummary, float | None]] = {}

    async def get(self, ingredient_rxcui):
        item = self._d.get(ingredient_rxcui)
        if item is None:
            return None
        summary, expires = item
        if expires is not None and time.monotonic() > expires:
            del self._d[ingredient_rxcui]
            return None
        return summary

    async def set(self, summary, ttl_seconds=None):
        self._d[summary.ingredient_rxcui] = (summary, time.monotonic() + ttl_seconds if ttl_seconds else None)

    async def delete(self, ingredient_rxcui):
        self._d.pop(ingredient_rxcui, None)


class MemoryFollowStore(FollowStore):
    def __init__(self) -> None:
        self._by_user: dict[str, set[str]] = {}
        self._by_drug: dict[str, set[str]] = {}

    async def follow(self, user_id, ingredient_rxcui):
        self._by_user.setdefault(user_id, set()).add(ingredient_rxcui)
        self._by_drug.setdefault(ingredient_rxcui, set()).add(user_id)

    async def unfollow(self, user_id, ingredient_rxcui):
        self._by_user.get(user_id, set()).discard(ingredient_rxcui)
        self._by_drug.get(ingredient_rxcui, set()).discard(user_id)

    async def list_followed(self, user_id):
        return set(self._by_user.get(user_id, set()))

    async def followers(self, ingredient_rxcui):
        return set(self._by_drug.get(ingredient_rxcui, set()))

    async def is_following(self, user_id, ingredient_rxcui):
        return ingredient_rxcui in self._by_user.get(user_id, set())


class MemoryAlertStore(AlertStore):
    def __init__(self, clock) -> None:
        self._d: dict[tuple[str, str], Alert] = {}
        self.clock = clock

    def _live(self, user_id):
        now = self.clock.now()
        return [a for (u, _), a in self._d.items() if u == user_id and (a.expires_at is None or a.expires_at > now)]

    async def add(self, alert, ttl_seconds):
        key = (alert.user_id, alert.alert_id)
        existing = self._d.get(key)
        if existing is not None and (existing.expires_at is None or existing.expires_at > self.clock.now()):
            return False
        self._d[key] = alert.model_copy(update={"expires_at": alert.created_at + timedelta(seconds=ttl_seconds)})
        return True

    async def list(self, user_id, limit=50):
        return sorted(self._live(user_id), key=lambda a: a.created_at, reverse=True)[:limit]

    async def dismiss(self, user_id, alert_id):
        return self._d.pop((user_id, alert_id), None) is not None

    async def dismiss_all(self, user_id):
        keys = [k for k in self._d if k[0] == user_id]
        for k in keys:
            del self._d[k]
        return len(keys)


class MemoryCounterStore(CounterStore):
    def __init__(self) -> None:
        self._d: dict[tuple[str, str, str], int] = {}

    async def set_count(self, ingredient_rxcui, reaction, quarter, value):
        self._d[(ingredient_rxcui, reaction, quarter)] = value

    async def get_count(self, ingredient_rxcui, reaction, quarter):
        return self._d.get((ingredient_rxcui, reaction, quarter))


class MemoryRevokedTokenStore(RevokedTokenStore):
    def __init__(self, clock) -> None:
        self._d: dict[str, object] = {}
        self.clock = clock

    async def revoke(self, jti, ttl_seconds):
        self._d[jti] = self.clock.now() + timedelta(seconds=max(1, ttl_seconds))

    async def is_revoked(self, jti):
        expires = self._d.get(jti)
        if expires is None:
            return False
        if expires <= self.clock.now():
            del self._d[jti]
            return False
        return True
