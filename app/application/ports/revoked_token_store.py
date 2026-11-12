"""Port: key-value: ids (jti) of access tokens revoked by a logout, kept only until the token would expire anyway."""
from abc import ABC, abstractmethod


class RevokedTokenStore(ABC):
    @abstractmethod
    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        """Idempotent. The entry disappears after ttl_seconds (the token is expired by then)."""

    @abstractmethod
    async def is_revoked(self, jti: str) -> bool: ...
