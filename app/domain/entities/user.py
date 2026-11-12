from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.enums import Role


class AlertSettings(BaseModel):
    new_signal: bool = True
    label_updated: bool = True
    shortage_changed: bool = True
    new_recall: bool = True
    min_reports: int = 20


class User(BaseModel):
    user_id: str
    username: str
    email: str
    password_hash: str
    role: Role = Role.USER
    settings: AlertSettings = Field(default_factory=AlertSettings)
    created_at: datetime | None = None
