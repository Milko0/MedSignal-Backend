from pydantic import BaseModel, Field


class AlternativeRow(BaseModel):
    match_type: str       # SAME_INGREDIENT | SAME_CLASS
    rxcui: str
    name: str
    dosage_form: str | None = None
    routes: list[str] = Field(default_factory=list)
    recalls: int = 0
    signal_profile: str   # LOW | MODERATE | HIGH
    products_available: int = 0
    rank: int = 0


class AlternativesData(BaseModel):
    target_dosage_form: str | None = None
    target_routes: list[str] = Field(default_factory=list)
    items: list[AlternativeRow]
