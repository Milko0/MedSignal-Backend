"""openFDA label record -> DrugLabel (text only; the *_table HTML fields are dropped)."""
from collections.abc import Mapping
from datetime import UTC, datetime

from app.application.ingestion.transformers.common import (
    blank_to_none,
    str_list,
    to_int,
    unique,
)
from app.domain.entities.enums import ProductType
from app.domain.entities.label import DrugLabel, LabelHistoryEntry
from app.domain.exceptions import TransformError
from app.domain.services.date_parser import parse_day
from app.domain.services.label_text_union import section_text, warnings_union

_TYPE = {"HUMAN PRESCRIPTION DRUG": ProductType.RX, "HUMAN OTC DRUG": ProductType.OTC}
_PLAIN_SECTIONS = ("adverse_reactions", "boxed_warning", "indications_and_usage", "contraindications",
                   "drug_interactions", "pregnancy", "pediatric_use")


def transform_label(
    raw: dict,
    rx_to_ingredients: Mapping[str, list[str]] | None = None,
    now: datetime | None = None,
) -> DrugLabel:
    set_id = blank_to_none(raw.get("set_id"))
    if set_id is None:
        raise TransformError("label without set_id")
    now = now or datetime.now(UTC)
    openfda = raw.get("openfda") or {}

    sections: dict[str, str] = {}
    for key in _PLAIN_SECTIONS:
        text = section_text(raw.get(key))
        if text:
            sections[key] = text
    union = warnings_union(raw)  # warnings_and_cautions + warnings + precautions
    if union:
        sections["warnings"] = union

    ingredients: list[str] = []
    for rx in str_list(openfda.get("rxcui")):
        ingredients += (rx_to_ingredients or {}).get(rx, [])

    version = to_int(raw.get("version"), 1) or 1
    effective = parse_day(raw.get("effective_time"))
    product_type = _TYPE.get((str_list(openfda.get("product_type")) or [""])[0].upper(), ProductType.OTHER)
    return DrugLabel(
        set_id=set_id.lower(),
        spl_id=blank_to_none(raw.get("id")),
        product_type=product_type,
        version=version,
        effective_date=effective,
        has_boxed_warning="boxed_warning" in sections,
        product_ndcs=str_list(openfda.get("product_ndc")),
        ingredient_rxcuis=unique(ingredients),
        sections=sections,
        history=[LabelHistoryEntry(version=version, effective_date=effective, detected_at=now)],
    )
