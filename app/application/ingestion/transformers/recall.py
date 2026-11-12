"""openFDA enforcement record -> Recall with an initial, auditable link."""
from collections.abc import Mapping

from app.application.ingestion.transformers.common import (
    blank_to_none,
    str_list,
    unique,
)
from app.domain.entities.enums import LinkMethod, LinkStatus, RecallClass, RecallStatus
from app.domain.entities.recall import Recall, RecallLink
from app.domain.exceptions import TransformError
from app.domain.services.date_parser import parse_day

_CLASS = {"CLASS I": RecallClass.CLASS_I, "CLASS II": RecallClass.CLASS_II, "CLASS III": RecallClass.CLASS_III}
_STATUS = {"ONGOING": RecallStatus.ONGOING, "COMPLETED": RecallStatus.COMPLETED, "TERMINATED": RecallStatus.TERMINATED}


def transform_recall(raw: dict, rx_to_ingredients: Mapping[str, list[str]] | None = None) -> Recall:
    number = blank_to_none(raw.get("recall_number"))
    if number is None:
        raise TransformError("recall without recall_number")
    ingredients: list[str] = []
    for rx in str_list((raw.get("openfda") or {}).get("rxcui")):
        ingredients += (rx_to_ingredients or {}).get(rx, [])
    ingredients = unique(ingredients)
    # Only 14% of recalls carry openFDA ids. The rest stay UNREVIEWED until LinkRecalls proposes candidates.
    link = (RecallLink(status=LinkStatus.ACCEPTED, method=LinkMethod.OPENFDA_RXCUI, ingredient_rxcuis=ingredients)
            if ingredients else RecallLink())
    return Recall(
        recall_number=number,
        event_id=blank_to_none(raw.get("event_id")),
        classification=_CLASS.get(str(raw.get("classification") or "").strip().upper(), RecallClass.NOT_CLASSIFIED),
        status=_STATUS.get(str(raw.get("status") or "").strip().upper(), RecallStatus.UNKNOWN),
        reason=blank_to_none(raw.get("reason_for_recall")),
        product_description=blank_to_none(raw.get("product_description")),
        recalling_firm=blank_to_none(raw.get("recalling_firm")),
        initiation_date=parse_day(raw.get("recall_initiation_date")),
        report_date=parse_day(raw.get("report_date")),
        termination_date=parse_day(raw.get("termination_date")),
        link=link,
    )
