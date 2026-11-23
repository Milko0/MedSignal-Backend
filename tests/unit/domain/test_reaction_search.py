import re

import pytest

from app.domain.value_objects.reaction_term import reaction_search_pattern


@pytest.mark.parametrize("typed, term", [
    ("anemia", "IRON DEFICIENCY ANAEMIA"), ("Anaemia", "ANAEMIA"), ("diarrhea", "DIARRHOEA"),
    ("edema", "OEDEMA PERIPHERAL"), ("tumor", "TUMOUR LYSIS SYNDROME"), ("device", "COMPLICATION OF DEVICE INSERTION"),
    ("  nausea ", "NAUSEA"), ("a+b", "A+B"),
])
def test_finds_the_text_anywhere_in_either_spelling(typed, term):
    assert re.search(reaction_search_pattern(typed), term)


def test_does_not_match_other_terms_and_ignores_blank_text():
    assert not re.search(reaction_search_pattern("nausea"), "VOMITING")
    assert reaction_search_pattern("   ") is None
