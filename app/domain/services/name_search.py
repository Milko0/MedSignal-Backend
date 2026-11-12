"""Typo-tolerant drug name scoring (FR-01), shared by every IngredientRepository adapter so they rank alike."""
import difflib

FUZZY_THRESHOLD = 0.75


def normalize_query(text: str) -> str:
    return " ".join(text.upper().split())


def name_score(query: str, text: str) -> float | None:
    """query is normalised. 1.0 exact, 0.9 prefix or whole word, else the difflib ratio when >= 0.75."""
    t = text.upper()
    if t == query:
        return 1.0
    if t.startswith(query) or query in t.split():
        return 0.9
    score = difflib.SequenceMatcher(None, query, t).ratio()
    return score if score >= FUZZY_THRESHOLD else None


def best_matches(query: str, candidates, limit: int) -> list[tuple[str, str, float]]:
    """candidates: iterable of (id, display name, texts). Returns (id, matched text, score), best first,
    ties broken by display name."""
    best: dict[str, tuple[float, str, str]] = {}
    for key, name, texts in candidates:
        for text in texts:
            score = name_score(query, text)
            if score is not None and (key not in best or score > best[key][0]):
                best[key] = (score, text, name)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[1][2]))[:limit]
    return [(key, text, score) for key, (score, text, _) in ranked]
