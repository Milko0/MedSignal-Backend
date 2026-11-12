"""openFDA NDC directory record -> Product with embedded packages."""
from collections.abc import Mapping

from app.application.ingestion.transformers.common import (
    blank_to_none,
    str_list,
    unique,
)
from app.domain.entities.enums import ProductType
from app.domain.entities.product import ActiveIngredient, Package, Product
from app.domain.exceptions import TransformError
from app.domain.services.date_parser import parse_day
from app.domain.value_objects.ndc import Ndc

_TYPE = {"HUMAN PRESCRIPTION DRUG": ProductType.RX, "HUMAN OTC DRUG": ProductType.OTC}


def transform_ndc_product(raw: dict, rx_to_ingredients: Mapping[str, list[str]] | None = None) -> Product:
    product_ndc = blank_to_none(raw.get("product_ndc"))
    if product_ndc is None:
        raise TransformError("NDC record without product_ndc")
    openfda = raw.get("openfda") or {}
    product_rxcuis = str_list(openfda.get("rxcui"))
    ingredients: list[str] = []
    for rx in product_rxcuis:
        ingredients += (rx_to_ingredients or {}).get(rx, [])

    packages: list[Package] = []
    for p in raw.get("packaging") or []:
        raw_ndc = blank_to_none(p.get("package_ndc"))
        if raw_ndc is None:
            continue
        try:
            ndc = Ndc.parse(raw_ndc)
            package_ndc, ndc11 = ndc.package_ndc, ndc.to_ndc11()
        except ValueError:
            package_ndc, ndc11 = raw_ndc, None
        packages.append(Package(
            package_ndc=package_ndc,
            ndc11=ndc11,
            description=blank_to_none(p.get("description")),
            marketing_start=parse_day(p.get("marketing_start_date")),  # YYYYMMDD or 01-MAY-26
        ))

    form = blank_to_none(raw.get("dosage_form"))
    return Product(
        product_ndc=product_ndc,
        generic_name=blank_to_none(raw.get("generic_name")),
        brand_name=blank_to_none(raw.get("brand_name")),
        labeler=blank_to_none(raw.get("labeler_name")),
        dosage_form=form.upper() if form else None,
        routes=[r.upper() for r in str_list(raw.get("route"))],
        product_type=_TYPE.get(str(raw.get("product_type") or "").upper(), ProductType.OTHER),
        marketing_category=blank_to_none(raw.get("marketing_category")),
        application_number=blank_to_none(raw.get("application_number")),  # may be M020 or 505G(a)(3)
        active_ingredients=[
            ActiveIngredient(name=str(a.get("name")).upper(), strength=blank_to_none(a.get("strength")))
            for a in raw.get("active_ingredients") or [] if a.get("name")
        ],
        packages=packages,
        spl_set_id=(str_list(openfda.get("spl_set_id")) or [None])[0],
        spl_id=blank_to_none(raw.get("spl_id")),
        product_rxcuis=product_rxcuis,
        ingredient_rxcuis=unique(ingredients),
    )
