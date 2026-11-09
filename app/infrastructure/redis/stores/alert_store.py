from __future__ import annotations

import time

from redis.asyncio import Redis

from app.application.ports.alert_store import AlertStore
from app.core.constants import ALERT_TTL_SECONDS
from app.infrastructure.redis import key_schema as k


class RedisAlertStore(AlertStore):
    """Alert hash with TTL + sorted-set index (pruned on read) -> no SCAN needed to list a user's alerts."""

    def __init__(self, r: Redis):
        self._r = r

    async def add(self, user_id: str, event_id: str, payload: dict) -> None:
        now = time.time()
        key = k.alert(user_id, event_id)  # same event id -> same key -> replay-safe
        async with self._r.pipeline(transaction=True) as p:
            p.hset(key, mapping={**{f: str(v) for f, v in payload.items()}, "id": event_id, "created_at": str(now)})
            p.expire(key, ALERT_TTL_SECONDS)
            p.zadd(k.alert_index(user_id), {event_id: now})
            await p.execute()

    async def list(self, user_id: str) -> list[dict]:
        idx = k.alert_index(user_id)
        await self._r.zremrangebyscore(idx, "-inf", time.time() - ALERT_TTL_SECONDS)
        ids = await self._r.zrevrange(idx, 0, -1)
        out = []
        for event_id in ids:
            data = await self._r.hgetall(k.alert(user_id, event_id))
            if data:
                out.append(data)
            else:
                await self._r.zrem(idx, event_id)  # key expired, prune the index
        return out

    async def dismiss(self, user_id: str, event_id: str) -> None:
        await self._r.delete(k.alert(user_id, event_id))
        await self._r.zrem(k.alert_index(user_id), event_id)

    async def dismiss_all(self, user_id: str) -> None:
        for a in await self.list(user_id):
            await self.dismiss(user_id, a["id"])
