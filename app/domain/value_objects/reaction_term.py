import re


def normalize_reaction(term: str) -> str:
    """Canonical MedDRA preferred term used everywhere: upper case, single spaces.

    Record fields use mixed case ("Drug ineffective") and count queries upper case, so every
    comparison and every stored term goes through this function.
    """
    return " ".join(str(term).strip().upper().split())


# MedDRA writes British spellings (ANAEMIA, DIARRHOEA, OEDEMA, TUMOUR); people type American ones (anemia, diarrhea).
_BRITISH_TO_AMERICAN = (("AE", "E"), ("OE", "E"), ("OUR", "OR"))


def reaction_search_pattern(text: str) -> str | None:
    """Regular expression that finds `text` anywhere inside a reaction term, in either spelling.

    The text is upper-cased and folded to American spelling, then every E may be preceded by A or O and every OR may
    read OUR: "anemia" -> AN[AO]?EMIA finds ANAEMIA and IRON DEFICIENCY ANAEMIA; "device" finds DEVICE ISSUE and
    COMPLICATION OF DEVICE INSERTION. Other characters are matched literally. None for blank text.
    """
    folded = normalize_reaction(text)
    if not folded:
        return None
    for british, american in _BRITISH_TO_AMERICAN:
        folded = folded.replace(british, american)
    out, i = [], 0
    while i < len(folded):
        if folded.startswith("OR", i):
            out.append("OU?R")
            i += 2
            continue
        ch = folded[i]
        out.append("[AO]?E" if ch == "E" else re.escape(ch))
        i += 1
    return "".join(out)
