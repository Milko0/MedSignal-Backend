from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.application.dtos.common import Meta


class FollowRequest(BaseModel):
    rxcui: str


class FollowedDrug(BaseModel):
    rxcui: str
    name: str
    drug_class: str | None = None
    dosage_form: str | None = None
    chip: Literal["in_shortage", "new_signal", "label_updated", "new_recall", "no_changes"] = "no_changes"
    detail: str | None = None
    alternatives_available: int | None = None


class AlertItem(BaseModel):
    id: str
    type: Literal["signal", "label", "shortage", "recall"]
    rxcui: str
    title: str
    detail: str
    created_at: datetime


class CabinetResponse(BaseModel):
    meta: Meta = Meta()
    followed: list[FollowedDrug]


class AlertListResponse(BaseModel):
    alerts: list[AlertItem]
