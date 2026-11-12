from pydantic import BaseModel, Field

from app.domain.entities.enums import Tty


class RxConcept(BaseModel):
    """A product-level RxNorm concept (SCD or SBD) and the ingredients it contains."""

    rxcui: str
    tty: Tty = Tty.OTHER
    name: str = ""
    ingredient_rxcuis: list[str] = Field(default_factory=list)
