from pydantic import BaseModel


class FollowRequest(BaseModel):
    rxcui: str


class FollowedDrug(BaseModel):
    rxcui: str
    name: str
    shortage_status: str | None = None
    packages_in_shortage: int = 0


class AlertItem(BaseModel):
    alert_id: str
    type: str
    drug_rxcui: str
    message: str
    created_at: str
