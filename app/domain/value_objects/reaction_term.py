def normalize_reaction(term: str) -> str:
    """Canonical MedDRA preferred term used everywhere: upper case, single spaces.

    Record fields use mixed case ("Drug ineffective") and count queries upper case, so every
    comparison and every stored term goes through this function.
    """
    return " ".join(str(term).strip().upper().split())
