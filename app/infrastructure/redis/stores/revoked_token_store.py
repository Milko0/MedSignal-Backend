from redis.asyncio import Redis

from app.application.ports.revoked_token_store import RevokedTokenStore
from app.infrastructure.redis import key_schema as k


class RedisRevokedTokenStore(RevokedTokenStore):
    """revoked:{jti} STRING with a TTL equal to the token's remaining lifetime, so the set never grows."""

    def __init__(self, r: Redis):
        self._r = r

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        await self._r.set(k.revoked_token(jti), "1", ex=max(1, ttl_seconds))

    async def is_revoked(self, jti: str) -> bool:
        return bool(await self._r.exists(k.revoked_token(jti)))
