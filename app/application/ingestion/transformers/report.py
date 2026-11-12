"""FAERS raw report -> compact AdverseReport. Pure: ingredient lookups are passed in as dictionaries."""
from collections.abc import Mapping

from app.application.ingestion.resolution import NameResolution
from app.application.ingestion.transformers.common import (
    as_list,
    blank_to_none,
    str_list,
    to_float,
    to_int,
    unique,
)
from app.domain.entities.enums import DrugRole, MatchMethod
from app.domain.entities.report import (
    AdverseReport,
    Patient,
    Reaction,
    ReportedDrug,
    Seriousness,
)
from app.domain.exceptions import TransformError
from app.domain.services import age_bucketer, code_dictionary
from app.domain.services.date_parser import parse_day
from app.domain.services.drug_name_cleaner import (
    clean_name,
    is_junk,
    split_active_substances,
)
from app.domain.value_objects.quarter import Quarter
from app.domain.value_objects.reaction_term import normalize_reaction


def normalize_reportduplicate(value) -> list[dict]:
    """reportduplicate is an array in some reports and an object in others."""
    return [v for v in as_list(value) if isinstance(v, dict)]


def _transform_drug(
    raw: dict,
    rx_to_ingredients: Mapping[str, list[str]],
    name_resolutions: Mapping[str, NameResolution],
) -> ReportedDrug:
    raw_name = clean_name(raw.get("medicinalproduct")) or None
    substances = split_active_substances((raw.get("activesubstance") or {}).get("activesubstancename"))
    openfda = raw.get("openfda") or {}  # a missing key and {} both mean "not harmonised"
    product_rxcuis = str_list(openfda.get("rxcui"))

    ingredients: list[str] = []
    method = MatchMethod.UNMATCHED

    for rx in product_rxcuis:
        ingredients += rx_to_ingredients.get(rx, [])
    if ingredients:
        method = MatchMethod.HARMONIZED
    else:
        # activesubstancename first, medicinalproduct last
        names = substances or ([raw_name] if raw_name and not is_junk(raw_name) else [])
        saw_approximate = False
        for n in names:
            res = name_resolutions.get(n)
            if res is None:
                continue
            if res.usable:
                ingredients += res.ingredient_rxcuis
                method = MatchMethod.EXACT if res.method is MatchMethod.EXACT else MatchMethod.APPROXIMATE
            elif res.method is MatchMethod.APPROXIMATE:
                saw_approximate = True
        if not ingredients and saw_approximate:
            method = MatchMethod.APPROXIMATE  # candidates exist but nobody accepted them: no ingredient ids

    return ReportedDrug(
        raw_name=raw_name,
        active_substances=substances,
        role=code_dictionary.drug_role(raw.get("drugcharacterization")),
        indication=blank_to_none(raw.get("drugindication")),
        route_code=blank_to_none(raw.get("drugadministrationroute")),  # codes keep leading zeros: strings
        product_rxcuis=product_rxcuis,
        ingredient_rxcuis=unique(ingredients),
        match_method=method,
    )


def transform_report(
    raw: dict,
    rx_to_ingredients: Mapping[str, list[str]] | None = None,
    name_resolutions: Mapping[str, NameResolution] | None = None,
) -> AdverseReport:
    rx_map = rx_to_ingredients or {}
    name_map = name_resolutions or {}

    report_id = blank_to_none(raw.get("safetyreportid"))
    if report_id is None:
        raise TransformError("report without safetyreportid")
    received = parse_day(raw.get("receivedate"))
    if received is None:
        raise TransformError(f"report {report_id} without a valid receivedate")

    patient_raw = raw.get("patient") or {}
    age_years = age_bucketer.to_years(patient_raw.get("patientonsetage"), patient_raw.get("patientonsetageunit"))
    patient = Patient(
        sex=code_dictionary.sex(patient_raw.get("patientsex")),
        age_years=round(age_years, 2) if age_years is not None else None,
        age_group=age_bucketer.bucket(age_years, patient_raw.get("patientagegroup")),
        weight_kg=to_float(patient_raw.get("patientweight")),
    )

    reactions: list[Reaction] = []
    for r in as_list(patient_raw.get("reaction")):
        pt = normalize_reaction(r.get("reactionmeddrapt") or "")
        if pt:
            reactions.append(Reaction(pt=pt, outcome=code_dictionary.reaction_outcome(r.get("reactionoutcome"))))

    drugs = [_transform_drug(d, rx_map, name_map) for d in as_list(patient_raw.get("drug")) if isinstance(d, dict)]

    suspect = sorted({i for d in drugs if d.role is DrugRole.SUSPECT for i in d.ingredient_rxcuis})
    counted = sorted({i for d in drugs if d.role is not DrugRole.OTHER for i in d.ingredient_rxcuis})
    source = raw.get("primarysource") or {}

    return AdverseReport(
        report_id=str(report_id),
        version=to_int(raw.get("safetyreportversion"), 1) or 1,
        receive_date=received,
        quarter=str(Quarter.from_date(received)),
        report_type=code_dictionary.report_type(raw.get("reporttype")),
        reporter_qualification=code_dictionary.reporter_qualification(source.get("qualification")),
        seriousness=Seriousness(
            serious=code_dictionary.flag(raw.get("serious")),
            death=code_dictionary.flag(raw.get("seriousnessdeath")),
            hospitalization=code_dictionary.flag(raw.get("seriousnesshospitalization")),
            life_threatening=code_dictionary.flag(raw.get("seriousnesslifethreatening")),
            disabling=code_dictionary.flag(raw.get("seriousnessdisabling")),
            congenital_anomaly=code_dictionary.flag(raw.get("seriousnesscongenitalanomali")),
            other=code_dictionary.flag(raw.get("seriousnessother")),
        ),
        patient=patient,
        country=blank_to_none(raw.get("occurcountry") or source.get("reportercountry") or raw.get("primarysourcecountry")),
        duplicate=str(raw.get("duplicate")) == "1" or bool(normalize_reportduplicate(raw.get("reportduplicate"))),
        reactions=reactions,
        reaction_pts=sorted({r.pt for r in reactions}),
        drugs=drugs,
        suspect_ingredient_ids=suspect,
        all_ingredient_ids=counted,
    )
