import pytest

from app.application.ingestion.resolution import NameResolution
from app.application.ingestion.transformers import (
    rxnorm,
    transform_label,
    transform_ndc_product,
    transform_recall,
    transform_report,
    transform_shortage,
)
from app.application.ingestion.transformers.report import normalize_reportduplicate
from app.application.ingestion.transformers.shortage import normalize_availability
from app.domain.entities.enums import (
    AgeGroup,
    Availability,
    DrugRole,
    LinkStatus,
    MatchMethod,
    ProductType,
    RecallClass,
    ShortageStatus,
)
from app.domain.exceptions import TransformError
from tests.fixtures import raw


def test_report_harmonised_and_roles():
    rep = transform_report(raw.faers(1, 2, [raw._drug("IBUPROFEN", "1", "197805"), raw._drug("OMEPRAZOLE", "2")],
                                     ["Rash", "rash", "Nausea"], age="59"), {"197805": ["5640"]})
    assert rep.report_id == "10000001" and rep.quarter == "2026Q1" and rep.version == 1
    assert rep.reaction_pts == ["NAUSEA", "RASH"] and len(rep.reactions) == 3
    assert rep.patient.age_group is AgeGroup.A45_64 and rep.seriousness.serious is True
    suspect, other = rep.drugs
    assert suspect.match_method is MatchMethod.HARMONIZED and suspect.ingredient_rxcuis == ["5640"]
    assert suspect.route_code == "048"                      # keeps the leading zero
    assert other.role is DrugRole.CONCOMITANT and other.match_method is MatchMethod.UNMATCHED
    assert rep.suspect_ingredient_ids == ["5640"] and rep.all_ingredient_ids == ["5640"]


def test_report_name_resolution_rules():
    drug = raw._drug("ULTRAM", "1", None, substance="TRAMADOL")
    r = transform_report(raw.faers(2, 1, [drug], ["X"]), {}, {"TRAMADOL": NameResolution(MatchMethod.EXACT, ["10689"], True)})
    assert r.drugs[0].match_method is MatchMethod.EXACT and r.suspect_ingredient_ids == ["10689"]
    # approximate candidates never feed signals unless accepted
    cand = {"TRAMADOL": NameResolution(MatchMethod.APPROXIMATE, ["10689"], False)}
    r = transform_report(raw.faers(3, 1, [drug], ["X"]), {}, cand)
    assert r.drugs[0].match_method is MatchMethod.APPROXIMATE and r.suspect_ingredient_ids == []
    ok = {"TRAMADOL": NameResolution(MatchMethod.APPROXIMATE, ["10689"], True)}
    assert transform_report(raw.faers(4, 1, [drug], ["X"]), {}, ok).suspect_ingredient_ids == ["10689"]


def test_report_quirks():
    d = raw._drug("X", "4", None, substance="CALCIUM CARBONATE\\CHOLECALCIFEROL")
    r = transform_report({**raw.faers(5, 3, [d], ["Y"]), "reportduplicate": {"duplicatesource": "A", "duplicatenumb": "1"}})
    assert r.drugs[0].active_substances == ["CALCIUM CARBONATE", "CHOLECALCIFEROL"]
    assert r.drugs[0].role is DrugRole.OTHER and r.duplicate is True and r.all_ingredient_ids == []
    assert normalize_reportduplicate([{"a": 1}]) == [{"a": 1}] and normalize_reportduplicate({"a": 1}) == [{"a": 1}]
    with pytest.raises(TransformError):
        transform_report({"safetyreportid": "9"})
    with pytest.raises(TransformError):
        transform_report({"receivedate": "20260101"})


def test_shortage():
    rec = transform_shortage(raw.shortages()[0], rx_to_ingredients={"198013": ["7258"]}, now=None)
    assert rec.status is ShortageStatus.CURRENT and rec.availability is Availability.UNAVAILABLE  # "Unvailable"
    assert rec.package_ndc == "0338-0049-01" and rec.ndc11 == "00338004901" and rec.product_ndc == "0338-0049"
    assert rec.ingredient_rxcuis == ["7258"] and rec.dosage_form == "TABLET" and rec.routes == ["ORAL"]
    assert rec.initial_posting_date.isoformat() == "2023-07-14"
    for text, expected in [("Limited Availalbility", Availability.LIMITED), ("Limited Supply Available. Next Delivery",
                            Availability.LIMITED), ("Available", Availability.AVAILABLE), ("", Availability.UNKNOWN),
                           (None, Availability.UNKNOWN)]:
        assert normalize_availability(text) is expected
    with pytest.raises(TransformError):
        transform_shortage({**raw.shortages()[0], "status": "Weird"})
    # product-NDC fallback when the record has no openFDA ids
    bare = {**raw.shortages()[0], "openfda": {}}
    assert transform_shortage(bare, product_ingredients={"0338-0049": ["7258"]}).ingredient_rxcuis == ["7258"]


def test_ndc_product_dates_and_packages():
    p = raw.ndc_products()[0]
    p["packaging"].append({"package_ndc": "71288-722-99", "marketing_start_date": "01-MAY-26", "description": "x"})
    prod = transform_ndc_product(p, {"197805": ["5640"]})
    assert prod.ingredient_rxcuis == ["5640"] and prod.product_type is ProductType.RX and prod.dosage_form == "TABLET"
    assert [x.ndc11 for x in prod.packages] == ["71288072232", "71288072299"]
    assert prod.packages[1].marketing_start.isoformat() == "2026-05-01"


def test_label_text_only():
    lb = transform_label(raw.labels()[0], {"197805": ["5640"]})
    assert lb.set_id == "aaaaaaaa-0000-4000-8000-000000000001" and lb.version == 3 and lb.has_boxed_warning
    assert "warnings" in lb.sections and "adverse_reactions_table" not in lb.sections
    assert lb.product_type is ProductType.RX and lb.ingredient_rxcuis == ["5640"] and lb.history[0].version == 3
    otc = transform_label(raw.labels()[1])
    assert otc.product_type is ProductType.OTC and otc.sections["warnings"].startswith("Warnings Liver")


def test_recall_link_and_blanks():
    linked = transform_recall(raw.recalls()[0], {"198013": ["7258"]})
    assert linked.classification is RecallClass.CLASS_II and linked.termination_date is None   # "" -> None
    assert linked.link.status is LinkStatus.ACCEPTED and linked.link.ingredient_rxcuis == ["7258"]
    unlinked = transform_recall(raw.recalls()[1])
    assert unlinked.link.status is LinkStatus.UNREVIEWED and unlinked.link.ingredient_rxcuis == []


def test_rxnorm_parsers_with_real_shapes():
    assert rxnorm.parse_exact({"idGroup": {}}) == [] and rxnorm.parse_exact({"idGroup": {"rxnormId": ["4301"]}}) == ["4301"]
    related = {"relatedGroup": {"rxcui": None, "conceptGroup": [
        {"tty": "BN", "conceptProperties": [{"rxcui": "218986", "name": "Oxycontin", "tty": "BN"}]},
        {"tty": "IN", "conceptProperties": [{"rxcui": "7804", "name": "oxycodone", "tty": "IN"}]}]}}
    assert rxnorm.parse_related(related, "IN") == [("7804", "oxycodone")] and rxnorm.parse_related({}, "IN") == []
    approx = {"approximateGroup": {"inputTerm": None, "candidate": [
        {"rxcui": "1", "score": "9.5", "source": "DRUGBANK", "name": "x"},
        {"rxcui": "2", "score": "12.1", "source": "RXNORM", "name": "gliclazide"},
        {"rxcui": "2", "score": "11.0", "source": "RXNORM", "name": "dup"}]}}
    cands = rxnorm.parse_approximate(approx)
    assert [(c.rxcui, c.score) for c in cands] == [("2", 12.1)]
    atc = {"rxclassDrugInfoList": {"rxclassDrugInfo": [{"rxclassMinConceptItem": {"classId": "N02AA", "className": "Natural opium alkaloids", "classType": "ATC1-4"}}]}}
    assert rxnorm.parse_atc(atc)[0].class_id == "N02AA" and rxnorm.parse_atc({}) == []
    assert rxnorm.parse_ndcs({"ndcGroup": {"ndcList": {}}}) == [] and rxnorm.parse_ndcs({"ndcGroup": {"ndcList": {"ndc": ["59011041010"]}}}) == ["59011041010"]
    assert rxnorm.parse_properties({"properties": {"rxcui": "5640", "name": "ibuprofen", "tty": "IN"}}).tty.value == "IN"
