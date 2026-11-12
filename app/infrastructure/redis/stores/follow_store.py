from redis.asyncio import Redis

from app.application.ports.follow_store import FollowStore
from app.infrastructure.redis import key_schema as k


class RedisFollowStore(FollowStore):
    def __init__(self, r: Redis):
        self._r = r

    async def follow(self, user_id: str, rxcui: str) -> None:
        async with self._r.pipeline(transaction=True) as p:
            p.sadd(k.follows(user_id), rxcui)
            p.sadd(k.followers(rxcui), user_id)
            await p.execute()

    async def unfollow(self, user_id: str, rxcui: str) -> None:
        async with self._r.pipeline(transaction=True) as p:
            p.srem(k.follows(user_id), rxcui)
            p.srem(k.followers(rxcui), user_id)
            await p.execute()

    async def list_followed(self, user_id: str) -> set[str]:
        return set(await self._r.smembers(k.follows(user_id)))

    async def followers(self, rxcui: str) -> set[str]:
        return set(await self._r.smembers(k.followers(rxcui)))

    async def is_following(self, user_id: str, rxcui: str) -> bool:
        return bool(await self._r.sismember(k.follows(user_id), rxcui))
