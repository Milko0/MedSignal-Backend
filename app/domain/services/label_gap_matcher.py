"""FR-07: match MedDRA reaction terms against label text (full / partial / gap). Start with term and stem matching."""


def match_reaction(term: str, label_text: str) -> str:
    """Return 'full', 'partial' or 'gap'. TODO: synonym handling (haemorrhage vs bleeding)."""
    term, text = term.lower(), label_text.lower()
    if term in text:
        return "full"
    stems = [w[:6] for w in term.replace("-", " ").split() if len(w) >= 6]
    return "partial" if any(s in text for s in stems) else "gap"
