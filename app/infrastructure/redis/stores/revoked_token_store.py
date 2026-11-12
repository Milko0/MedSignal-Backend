from datetime import datetime, timedelta

from redis.asyncio import Redis

from app.application.ports.revoked_token_store import RevokedTokenStore
from app.infrastructure.redis import key_schema as k


class RedisRevokedTokenStore(RevokedTokenStore):
    """revoked:{jti} STRING with a TTL equal to the token's remaining lifetime, so the set never grows. The value is
    the expiry instant, checked against the injected clock (exact and testable; EXPIRE does the cleanup)."""

    def __init__(self, r: Redis, clock) -> None:
        self._r, self.clock = r, clock

    async def revoke(self, jti, ttl_seconds):
        ttl = max(1, ttl_seconds)
        expires = self.clock.now() + timedelta(seconds=ttl)
        await self._r.set(k.revoked_token(jti), expires.isoformat(), ex=ttl)

    async def is_revoked(self, jti):
        value = await self._r.get(k.revoked_token(jti))
        return value is not None and datetime.fromisoformat(value) > self.clock.now()
