"""FR-17, FR-18: list the alerts of a user (expired alerts are already gone)."""
from app.application.dtos.cabinet import AlertItem
from app.application.ports.alert_store import AlertStore


class ListAlerts:
    def __init__(self, alerts: AlertStore) -> None:
        self.alerts = alerts

    async def execute(self, user_id: str) -> list[AlertItem]:
        return [AlertItem(alert_id=a.alert_id, type=a.type.value, drug_rxcui=a.drug_rxcui, message=a.message,
                          created_at=a.created_at.isoformat()) for a in await self.alerts.list(user_id)]
