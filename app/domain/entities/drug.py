from pydantic import BaseModel, Field


class DrugClass(BaseModel):
    """ATC class (levels 1-4 from RxClass)."""

    class_id: str
    name: str
    level: int = 4


class Drug(BaseModel):
    """The hub of the model: one RxNorm ingredient (TTY IN). Signals, follows, alerts and shortages hang here."""

    rxcui: str
    name: str
    synonyms: list[str] = Field(default_factory=list)
    uniis: list[str] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
    atc: list[DrugClass] = Field(default_factory=list)
