from redis.asyncio import Redis

from app.application.ports.counter_store import CounterStore
from app.infrastructure.redis import key_schema as k


class RedisCounterStore(CounterStore):
    """Counters are overwritten with SET after recomputing from MongoDB (INCRBY would double count on replay)."""

    def __init__(self, r: Redis):
        self._r = r

    async def set_count(self, ingredient_rxcui, reaction, quarter, value):
        await self._r.set(k.counter(ingredient_rxcui, reaction, quarter), value)

    async def get_count(self, ingredient_rxcui, reaction, quarter):
        v = await self._r.get(k.counter(ingredient_rxcui, reaction, quarter))
        return int(v) if v is not None else None
