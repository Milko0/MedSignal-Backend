from redis.asyncio import Redis

from app.application.ports.counter_store import CounterStore
from app.infrastructure.redis import key_schema as k


class RedisCounterStore(CounterStore):
    """Counters are overwritten with SET after recomputing from MongoDB (INCRBY would double count on replay)."""

    def __init__(self, r: Redis):
        self._r = r

    async def set(self, rxcui: str, reaction: str, quarter: str, value: int) -> None:
        await self._r.set(k.counter(rxcui, reaction, quarter), value)

    async def get(self, rxcui: str, reaction: str, quarter: str) -> int | None:
        v = await self._r.get(k.counter(rxcui, reaction, quarter))
        return int(v) if v is not None else None
