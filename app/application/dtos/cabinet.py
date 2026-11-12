from pydantic import BaseModel


class FollowRequest(BaseModel):
    rxcui: str

    model_config = {"json_schema_extra": {"examples": [{"rxcui": "1991302"}]}}


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
