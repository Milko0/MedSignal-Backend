from redis.asyncio import Redis

from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.entities.shortage import ShortageSummary
from app.infrastructure.redis import key_schema as k


class RedisShortageStatusStore(ShortageStatusStore):
    """shortage:{ingredientRxcui} HASH holding a ShortageSummary. A cache: it can always be rebuilt from MongoDB
    (Reconcile, FR-27), so a TTL is fine. dosage_forms is stored comma-joined."""

    def __init__(self, r: Redis):
        self._r = r

    async def get(self, ingredient_rxcui):
        data = await self._r.hgetall(k.shortage(ingredient_rxcui))
        if not data:
            return None
        forms = data.pop("dosage_forms", "")
        return ShortageSummary.model_validate({**data, "dosage_forms": forms.split(",") if forms else []})

    async def set(self, summary, ttl_seconds=None):
        data = summary.model_dump(mode="json", exclude_none=True)
        data["dosage_forms"] = ",".join(data.get("dosage_forms", []))
        key = k.shortage(summary.ingredient_rxcui)
        async with self._r.pipeline(transaction=True) as p:
            p.delete(key)                                        # no stale fields from the previous summary
            p.hset(key, mapping={f: str(v) for f, v in data.items()})
            if ttl_seconds:
                p.expire(key, ttl_seconds)
            await p.execute()

    async def delete(self, ingredient_rxcui):
        await self._r.delete(k.shortage(ingredient_rxcui))
