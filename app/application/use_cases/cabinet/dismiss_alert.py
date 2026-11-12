"""FR-18: dismiss one alert or all of them."""
from app.application.ports.alert_store import AlertStore
from app.domain.exceptions import NotFoundError


class DismissAlert:
    def __init__(self, alerts: AlertStore) -> None:
        self.alerts = alerts

    async def execute(self, user_id: str, alert_id: str | None = None) -> int:
        if alert_id is None:
            return await self.alerts.dismiss_all(user_id)
        if not await self.alerts.dismiss(user_id, alert_id):
            raise NotFoundError("Alert not found")
        return 1
