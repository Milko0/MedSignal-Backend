from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.enums import AlertType


class Alert(BaseModel):
    """Notification kept 30 days. ref_type and ref_id say what it is about (signal, label, shortage, recall)."""

    alert_id: str  # deterministic: type + ingredient + event id, so replays cannot duplicate it
    user_id: str
    type: AlertType
    drug_rxcui: str
    message: str
    ref_type: str | None = None
    ref_id: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    dismissed: bool = False
