from redis.asyncio import Redis

from app.application.ports.shortage_status_store import ShortageStatusStore
from app.infrastructure.redis import key_schema as k


class RedisShortageStatusStore(ShortageStatusStore):
    def __init__(self, r: Redis):
        self._r = r

    async def get(self, rxcui: str) -> dict | None:
        data = await self._r.hgetall(k.shortage(rxcui))
        return data or None

    async def set(self, rxcui: str, status: dict, ttl_seconds: int | None = None) -> None:
        key = k.shortage(rxcui)
        await self._r.hset(key, mapping={f: str(v) for f, v in status.items() if v is not None})
        if ttl_seconds:
            await self._r.expire(key, ttl_seconds)
