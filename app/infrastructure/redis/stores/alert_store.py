import json
from datetime import timedelta

from redis.asyncio import Redis

from app.application.ports.alert_store import AlertStore
from app.domain.entities.alert import Alert
from app.infrastructure.redis import key_schema as k


def _encode(alert: Alert) -> dict[str, str]:
    data = alert.model_dump(mode="json", exclude_none=True)
    return {f: json.dumps(v) if isinstance(v, bool) else str(v) for f, v in data.items()}


class RedisAlertStore(AlertStore):
    """alert:{userId}:{alertId} HASH with EXPIRE (30 days) + alerts:{userId} ZSET scored by creation time, so a
    user's alerts are listed without SCAN. The alert id is deterministic, so a replayed event hits the same key.

    `expires_at` is also stored in the hash and checked against the injected clock: Redis EXPIRE removes the key,
    the clock check keeps the behaviour exact (and testable) in between.
    """

    def __init__(self, r: Redis, clock) -> None:
        self._r, self.clock = r, clock

    async def _live(self, key: str) -> dict | None:
        data = await self._r.hgetall(key)
        if not data or ("expires_at" in data and Alert.model_validate(data).expires_at <= self.clock.now()):
            return None
        return data

    async def add(self, alert, ttl_seconds):
        key = k.alert(alert.user_id, alert.alert_id)
        if await self._live(key) is not None:
            return False                                              # replay: the live alert already exists
        stored = alert.model_copy(update={"expires_at": alert.created_at + timedelta(seconds=ttl_seconds)})
        async with self._r.pipeline(transaction=True) as p:
            p.delete(key)
            p.hset(key, mapping=_encode(stored))
            p.expire(key, ttl_seconds)
            p.zadd(k.alert_index(alert.user_id), {alert.alert_id: alert.created_at.timestamp()})
            await p.execute()
        return True

    async def list(self, user_id, limit=50):
        index = k.alert_index(user_id)
        ids = await self._r.zrevrange(index, 0, -1)
        out, gone = [], []
        for alert_id in ids:
            data = await self._live(k.alert(user_id, alert_id))
            if data is None:
                gone.append(alert_id)
            elif len(out) < limit:
                out.append(Alert.model_validate(data))
        if gone:
            await self._r.zrem(index, *gone)                         # prune the index on read
        return out

    async def dismiss(self, user_id, alert_id):
        async with self._r.pipeline(transaction=True) as p:
            p.delete(k.alert(user_id, alert_id))
            p.zrem(k.alert_index(user_id), alert_id)
            deleted, _ = await p.execute()
        return deleted == 1

    async def dismiss_all(self, user_id):
        index = k.alert_index(user_id)
        ids = await self._r.zrange(index, 0, -1)
        if ids:
            await self._r.delete(*(k.alert(user_id, a) for a in ids), index)
        return len(ids)
