import pytest

from app.domain.entities.enums import AgeGroup, DrugRole, ReactionOutcome, Sex
from app.domain.services import age_bucketer, code_dictionary
from app.domain.services.date_parser import Precision, parse_date, parse_day
from app.domain.services.drug_name_cleaner import (
    clean_name,
    is_junk,
    split_active_substances,
)
from app.domain.services.label_text_union import section_text, warnings_union
from app.domain.value_objects.ndc import Ndc
from app.domain.value_objects.quarter import Quarter
from app.domain.value_objects.reaction_term import normalize_reaction


@pytest.mark.parametrize("text,ndc11", [
    ("76420-241-12", "76420024112"),   # 5-3-2
    ("0338-0049-01", "00338004901"),   # 4-4-2
    ("71288-722-32", "71288072232"),   # 5-3-2
    ("50242-051-21", "50242005121"),   # 5-3-2
    ("12345-6789-1", "12345678901"),   # 5-4-1
    ("76420024112", "76420024112"),    # RxNav: already 11 digits
])
def test_ndc11(text, ndc11):
    assert Ndc.parse(text).to_ndc11() == ndc11


def test_ndc_product_and_errors():
    n = Ndc.parse("76420-241")
    assert n.product_ndc == "76420-241" and n.product11 == "764200241"
    with pytest.raises(ValueError):
        n.to_ndc11()
    with pytest.raises(ValueError):
        Ndc.parse("1234-56-7")


@pytest.mark.parametrize("value,iso,precision", [
    ("20240101", "2024-01-01", Precision.DAY),
    ("202212", "2022-12-01", Precision.MONTH),
    ("2023", "2023-01-01", Precision.YEAR),
    ("07/14/2023", "2023-07-14", Precision.DAY),
    ("01-MAY-26", "2026-05-01", Precision.DAY),
    ("31-JUL-27", "2027-07-31", Precision.DAY),
    ("Nov 09, 2026", "2026-11-09", Precision.DAY),
    ("2023-05-15", "2023-05-15", Precision.DAY),
])
def test_parse_date(value, iso, precision):
    p = parse_date(value)
    assert p.value.isoformat() == iso and p.precision is precision


@pytest.mark.parametrize("bad", [None, "", "N/A", "garbage", "20241341"])
def test_parse_date_invalid(bad):
    assert parse_date(bad) is None and parse_day(bad) is None


def test_name_cleaning():
    assert clean_name("ST MARY^S THISTLE") == "ST MARY'S THISTLE"
    assert split_active_substances("CALCIUM CARBONATE\\CHOLECALCIFEROL") == ["CALCIUM CARBONATE", "CHOLECALCIFEROL"]
    assert split_active_substances("UNSPECIFIED INGREDIENT") == []
    assert is_junk("unk") and is_junk("12345") and not is_junk("IBUPROFEN")


def test_age_and_codes():
    assert age_bucketer.to_years("59", "801") == 59
    assert round(age_bucketer.to_years("6", "802"), 2) == 0.5
    assert age_bucketer.to_years("200", "801") is None            # implausible
    assert age_bucketer.bucket(17.9) is AgeGroup.A0_17
    assert age_bucketer.bucket(45) is AgeGroup.A45_64
    assert age_bucketer.bucket(80) is AgeGroup.A75_PLUS
    assert age_bucketer.bucket(None, "3") is AgeGroup.A0_17        # child, no onset age
    assert age_bucketer.bucket(None, "5") is AgeGroup.UNKNOWN      # adult is too wide to bucket
    assert code_dictionary.sex("1") is Sex.MALE and code_dictionary.sex(None) is Sex.UNKNOWN
    assert code_dictionary.drug_role("1") is DrugRole.SUSPECT and code_dictionary.drug_role("4") is DrugRole.OTHER
    assert code_dictionary.reaction_outcome("5") is ReactionOutcome.FATAL
    assert code_dictionary.flag("1") is True and code_dictionary.flag("2") is False and code_dictionary.flag("9") is None


def test_label_text_and_terms():
    assert section_text(["a", " ", "b"]) == "a\nb" and section_text(None) == ""
    assert warnings_union({"warnings": ["W"], "precautions": ["P"]}) == "W\nP"
    assert normalize_reaction("Drug  ineffective ") == "DRUG INEFFECTIVE"
    assert Quarter.from_date(__import__("datetime").date(2026, 5, 1)) == Quarter(2026, 2)
    assert str(Quarter(2026, 1).previous()) == "2025Q4"
