from typing import Literal

from pydantic import BaseModel

from app.application.dtos.common import Meta


class AlternativeItem(BaseModel):
    rxcui: str
    product: str
    match: str  # "Same active ingredient" | "Same class (penicillins)"
    dosage_form: str
    recalls: int
    signal_profile: Literal["low", "moderate", "high"]
    status: Literal["available", "in_shortage"] = "available"


class RippleInfo(BaseModel):
    same_class_total: int = 0
    same_class_in_shortage: int = 0


class AlternativesResponse(BaseModel):
    meta: Meta = Meta()
    rxcui: str
    ripple: RippleInfo = RippleInfo()
    alternatives: list[AlternativeItem]
