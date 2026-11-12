"""Log out: the access token stops working before it expires (JWTs are stateless, so its id is revoked)."""
from datetime import datetime

from app.application.ports.clock import Clock
from app.application.ports.revoked_token_store import RevokedTokenStore


class Logout:
    def __init__(self, revoked: RevokedTokenStore, clock: Clock) -> None:
        self.revoked, self.clock = revoked, clock

    async def execute(self, jti: str, expires_at: datetime) -> None:
        remaining = int((expires_at - self.clock.now()).total_seconds())
        if remaining > 0:
            await self.revoked.revoke(jti, remaining)
