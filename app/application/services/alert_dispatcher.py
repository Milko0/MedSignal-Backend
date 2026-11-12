"""Creates alerts for the followers of an ingredient when a signal, label, shortage or recall event happens."""
from app.application.ports.alert_store import AlertStore
from app.application.ports.follow_store import FollowStore
from app.application.ports.user_repository import UserRepository
from app.core.constants import ALERT_TTL_SECONDS
from app.domain.entities.alert import Alert
from app.domain.entities.enums import AlertType

_SETTING = {AlertType.SIGNAL: "new_signal", AlertType.LABEL: "label_updated",
            AlertType.SHORTAGE: "shortage_changed", AlertType.RECALL: "new_recall"}


class AlertDispatcher:
    def __init__(self, follows: FollowStore, alerts: AlertStore, users: UserRepository, clock) -> None:
        self.follows, self.alerts, self.users, self.clock = follows, alerts, users, clock

    async def dispatch(self, type: AlertType, ingredient_rxcui: str, ref_id: str, message: str,
                       ref_type: str | None = None) -> int:
        """Returns the number of NEW alerts. The id is deterministic, so a replayed event creates nothing new."""
        created = 0
        now = self.clock.now()
        for user_id in await self.follows.followers(ingredient_rxcui):
            user = await self.users.get_by_id(user_id)
            if user is not None and not getattr(user.settings, _SETTING[type]):
                continue  # the user switched this kind of alert off
            alert = Alert(alert_id=f"{type.value}:{ingredient_rxcui}:{ref_id}", user_id=user_id, type=type,
                          drug_rxcui=ingredient_rxcui, message=message, ref_type=ref_type, ref_id=ref_id,
                          created_at=now)
            if await self.alerts.add(alert, ALERT_TTL_SECONDS):
                created += 1
        return created
