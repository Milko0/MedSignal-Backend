"""Creates alerts for the followers of a drug when a signal / label / shortage / recall event happens (FR-17, FR-30)."""

from app.application.ports.alert_store import AlertStore
from app.application.ports.follow_store import FollowStore


class AlertDispatcher:
    def __init__(self, follows: FollowStore, alerts: AlertStore):
        self._follows, self._alerts = follows, alerts

    async def dispatch(self, event_id: str, rxcui: str, payload: dict) -> int:
        """event_id makes the call idempotent: replaying a change event cannot duplicate alerts."""
        users = await self._follows.followers_of(rxcui)
        for user_id in users:
            await self._alerts.add(user_id, event_id, {**payload, "rxcui": rxcui})
        return len(users)
