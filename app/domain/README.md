# domain - entities, value objects, business rules

The innermost layer. Pure Python: it must run and be tested without FastAPI, MongoDB or Redis.

## Tools used

- Python standard library only (`dataclasses`, `math`)
- pytest for unit tests

## Rules

- Imports nothing from the other layers or from third-party packages.
- PRR, 95% CI lower bound and chi-square are computed here (`signal_calculator.py`), not in MongoDB.
- Raises domain exceptions (`exceptions.py`); the presentation layer maps them to HTTP codes.

## Contents

| Item | Role |
|---|---|
| `entities/` | Drug, report, label, shortage, signal, user, alert |
| `value_objects/` | ContingencyTable (2x2), Rxcui, Quarter, ReactionTerm |
| `services/signal_calculator.py` | PRR, CI lower, chi-square, Evans rule (FR-04) |
| `services/emerging_signal_policy.py` | FR-06 |
| `services/label_gap_matcher.py` | FR-07 (full / partial / gap) |
| `services/alternative_ranker.py` | FR-10 ranking |
