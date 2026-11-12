"""FR-10: rank substitutes by recalls, then signal profile. Same ingredient comes before same class."""
from app.domain.entities.enums import MatchType, SignalProfile
from app.domain.entities.shortage import SubstituteSuggestion

_PROFILE_ORDER = {SignalProfile.LOW: 0, SignalProfile.MODERATE: 1, SignalProfile.HIGH: 2}
_MATCH_ORDER = {MatchType.SAME_INGREDIENT: 0, MatchType.SAME_CLASS: 1}


def profile_from_signal_count(n_signals: int) -> SignalProfile:
    """Heuristic used for the UI badge: how many signals (Evans criteria) the ingredient has in the latest quarter."""
    if n_signals == 0:
        return SignalProfile.LOW
    return SignalProfile.MODERATE if n_signals <= 5 else SignalProfile.HIGH


def rank_alternatives(candidates: list[SubstituteSuggestion]) -> list[SubstituteSuggestion]:
    available = [c for c in candidates if c.products_available > 0]
    ordered = sorted(available, key=lambda c: (_MATCH_ORDER[c.match_type], c.recall_count,
                                               _PROFILE_ORDER[c.signal_profile], c.name))
    return [c.model_copy(update={"rank": i + 1}) for i, c in enumerate(ordered)]
