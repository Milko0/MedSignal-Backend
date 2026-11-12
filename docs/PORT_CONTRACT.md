# Port contract: handoff for the MongoDB and Redis adapters

Everything the API does goes through the ports in `app/application/ports`. The in-memory adapters in
`app/infrastructure/memory` are the **reference behaviour**. A database adapter is correct when
`tests/conformance/test_port_contract.py` passes with it (add a builder to `ADAPTERS`) and the API tests pass with
`STORAGE_BACKEND=databases`.

Domain models are Pydantic: store `model.model_dump(mode="json")`, read with `Model.model_validate(doc)`. Keep the
natural id as `_id` (mapping below); do not store derived values the model recomputes.

## Mapping of ids

| Collection | `_id` | Notes |
|---|---|---|
| `reports` | `report_id` | upsert keeps the HIGHEST `version` (older versions arriving later are ignored) |
| `ingredients` | `rxcui` | |
| `rx_concepts` | `rxcui` | an empty `ingredient_rxcuis` is a remembered RxNav miss: keep it |
| `products` | `product_ndc` | packages embedded |
| `labels` | `set_id` | lower case |
| `shortages` | `package_ndc` | **current** state only; `replace_current` removes records that left the list |
| `shortage_events` | generated | append only |
| `recalls` | `recall_number` | |
| `name_map` | `(key_type, normalized)` | compound `_id` or unique index |
| `signals` | `signal_id` = `quarter\|ingredient\|reaction\|role_filter` | upsert |
| `users` | `user_id` | unique indexes on `username` and `email` (case-insensitive: store lower-case copies) |
| `excluded_terms` | `term` | upper case |
| `ingestion_runs` | `run_id` | |

## Behaviour that is easy to get wrong

| Port method | Contract |
|---|---|
| `ReportRepository.pair_counts(quarter, role_filter, excluded_terms)` | One aggregation pass. `total` = **every** report of the quarter (also those with no resolved drug); `per_drug` / `per_pair` use `suspect_ingredient_ids` for `SUSPECT`, `all_ingredient_ids` for `ALL`; `per_reaction` and `per_pair` skip excluded terms. Each report counts once per drug, once per reaction, once per pair. |
| `ReportRepository.top_reactions` | Suspect reports of the ingredient, excluded terms removed, ordered by count desc then term. |
| `ReportRepository.monthly_trend` | Window of `months` months ending at the ingredient's latest report month; zero-filled; only the requested reactions. |
| `ReportRepository.statistics("age_group", ...)` | Canonical order `0-17, 18-44, 45-64, 65-74, 75+, UNKNOWN`; other groups by value desc; `quarter` chronological. |
| `ReportRepository.match_coverage(quarter)` | Reports with at least one `all_ingredient_ids` / all reports. |
| `SignalRepository.search` | Sorted by `prr` desc, `a` desc. `only_signals` -> `is_signal`; `only_emerging` -> `is_emerging`; returns `(page, total)`. |
| `SignalRepository.previous_prrs / trend` | Same ingredient and reaction, ascending by quarter; `previous_prrs` returns the last `n` quarters strictly before the given one. |
| `IngredientRepository.search` | Typo tolerant over name, synonyms and brand names. Memory: exact 1.0, prefix 0.9, else difflib ratio >= 0.75. Mongo: a text index plus a fuzzy step (for example trigram or edit distance in the adapter) is enough; the conformance test only needs `ibuprofin -> ibuprofen` and a brand-name hit. |
| `RecallRepository.find_by_ingredient(accepted_only=True)` | Only `link.status == ACCEPTED`. `linked_share` = accepted / all recalls. |
| `AlertStore.add` | Idempotent on `(user_id, alert_id)`; returns `False` if a live alert exists; an expired id may be created again. TTL 30 days. |
| `CounterStore.set_count` | Overwrite, never increment. |
| `ReportRepository.delete_quarter` / `SignalRepository.delete_quarter` | Rolling window (`ApplyRetentionWindow`): delete every document of the quarter, return how many (Mongo: `delete_many({quarter: q})` on the `{quarter: 1}` index). |
| `RevokedTokenStore` | Logout. `revoke(jti, ttl)` is idempotent; the entry expires with the token (Redis `SET revoked:{jti} 1 EX ttl`). |
| `ShortageStatusStore` | Holds `ShortageSummary` per **ingredient**; TTL is a cache TTL (the value can always be rebuilt). |

## Suggested MongoDB indexes (validate each with `explain()`, scripts/benchmark_indexes.py)

| Collection | Index | Serves |
|---|---|---|
| `reports` | `{quarter: 1}` | `pair_counts`, statistics |
| `reports` | `{suspect_ingredient_ids: 1, reaction_pts: 1}` (multikey) | reports behind a signal, top reactions, trend |
| `reports` | `{suspect_ingredient_ids: 1, receive_date: -1}` | monthly trend |
| `signals` | `{quarter: 1, is_signal: 1, prr: -1}` | signal explorer |
| `signals` | `{ingredient_rxcui: 1, reaction_term: 1, quarter: 1}` (unique with `role_filter`) | history, trend |
| `labels` | `{ingredient_rxcuis: 1, product_type: 1}` | label gaps |
| `products` | `{ingredient_rxcuis: 1, routes: 1, dosage_form: 1}` | alternatives |
| `shortages` | `{ingredient_rxcuis: 1}` and `{status: 1}` | Drug 360, alternatives |
| `recalls` | `{"link.ingredient_rxcuis": 1, "link.status": 1}` | Drug 360 |
| `ingredients` | `{"atc.class_id": 1}`, text index on `name`, `synonyms`, `brand_names` | same-class alternatives, search |
| `users` | unique `username`, unique `email` | auth |

Sharding candidate for `reports`: hashed `report_id` (never `receive_date` alone).

## Pipeline sketch for `pair_counts`

```
[{ $match: {quarter: Q} },
 { $facet: {
     total:   [{ $count: "n" }],
     drugs:   [{ $unwind: "$suspect_ingredient_ids" }, { $group: {_id: "$suspect_ingredient_ids", n: {$sum: 1}} }],
     reacts:  [{ $unwind: "$reaction_pts" }, { $match: {reaction_pts: {$nin: EXCLUDED}} }, { $group: {_id: "$reaction_pts", n: {$sum: 1}} }],
     pairs:   [{ $unwind: "$suspect_ingredient_ids" }, { $unwind: "$reaction_pts" }, { $match: {reaction_pts: {$nin: EXCLUDED}} },
               { $group: {_id: {d: "$suspect_ingredient_ids", r: "$reaction_pts"}, n: {$sum: 1}} }] } }]
```
`reaction_pts` and the id arrays are already de-duplicated per report by the transformer, so `$unwind` counts each report once.
For very large quarters, run the `pairs` facet as its own `$merge` into a temporary collection.

## Redis changes versus the first skeleton

- Shortage key is per **ingredient** and holds a `ShortageSummary` (`status`, `packages_in_shortage`, `packages_total`, `dosage_forms`).
- `Alert` fields: `alert_id` (deterministic), `type`, `drug_rxcui`, `message`, `ref_type`, `ref_id`, `created_at`, `expires_at`.
  Store as HASH with `EXPIRE` 30 days; keep the `alerts:{userId}` ZSET index and prune on read.
- Follows and counters keep the key shapes, but the id is the **ingredient** rxcui.
- `follows` and `alerts` are the source of truth for those entities (not rebuilt from MongoDB): AOF persistence and replicas.

## Phase 5 checklist

1. Mongo repositories + indexes; run the conformance suite against them.
2. Redis stores; run the conformance suite.
3. `app/infrastructure/database_container.py` with `build_database_container(settings) -> Container`.
4. Load `data/clean/*.jsonl` (`mongoimport --jsonArray` is not needed: the files are JSON Lines).
5. Change-stream projector: overwrite `ShortageSummary` and counters from MongoDB, create alerts with `AlertDispatcher`, save the resume token; `Reconcile` is the fallback.
6. Run `tests/integration/test_api.py` with `STORAGE_BACKEND=databases`.
