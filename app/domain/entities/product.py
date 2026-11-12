from datetime import date

from pydantic import BaseModel, Field

from app.domain.entities.enums import ProductType


class ActiveIngredient(BaseModel):
    name: str
    strength: str | None = None


class Package(BaseModel):
    package_ndc: str
    ndc11: str | None = None
    description: str | None = None
    marketing_start: date | None = None


class Product(BaseModel):
    """NDC product. Packages are embedded; one product has several."""

    product_ndc: str
    generic_name: str | None = None
    brand_name: str | None = None
    labeler: str | None = None
    dosage_form: str | None = None
    routes: list[str] = Field(default_factory=list)
    product_type: ProductType = ProductType.OTHER
    marketing_category: str | None = None
    application_number: str | None = None
    active_ingredients: list[ActiveIngredient] = Field(default_factory=list)
    packages: list[Package] = Field(default_factory=list)
    spl_set_id: str | None = None
    spl_id: str | None = None
    product_rxcuis: list[str] = Field(default_factory=list)
    ingredient_rxcuis: list[str] = Field(default_factory=list)
