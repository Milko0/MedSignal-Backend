# Port contract of the storage adapters

Everything the API does goes through the ports in `app/application/ports`. The in-memory adapters in
`app/infrastructure/memory` are the **reference behaviour**; the MongoDB (`infrastructure/mongodb`) and Redis
(`infrastructure/redis`) adapters reproduce it. `tests/conformance/test_port_contract.py` runs the same assertions on
both (the database run uses `medsignal_test` and Redis db 15, and is skipped when the databases are not running).
Change a contract here, in the memory adapter, in the database adapter and in the conformance test together.

Domain models are Pydantic: documents are `model.model_dump(mode="json", exclude_none=True)` with the natural id moved
to `_id` (`mongodb/documents.py`), read back with `Model.model_validate`. Dates are ISO strings, which sort correctly.

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
| `name_map` | `"KEY_TYPE|normalized"` | the compound key as one string |
| `signals` | `signal_id` = `quarter\|ingredient\|reaction\|role_filter` | upsert |
| `users` | `user_id` | unique indexes on the lower-case copies `username_lower`, `email_lower` |
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
| `IngredientRepository.search` | Typo tolerant over name, synonyms and brand names. Memory: exact 1.0, prefix 0.9, else difflib ratio >= 0.75. Both adapters use `domain/services/name_search.py`; the Mongo adapter scores a cached name list (MongoDB Community has no edit-distance index). |
| `RecallRepository.find_by_ingredient(accepted_only=True)` | Only `link.status == ACCEPTED`. `linked_share` = accepted / all recalls. |
| `AlertStore.add` | Idempotent on `(user_id, alert_id)`; returns `False` if a live alert exists; an expired id may be created again. TTL 30 days. |
| `CounterStore.set_count` | Overwrite, never increment. |
| `ReportRepository.delete_quarter` / `SignalRepository.delete_quarter` | Rolling window (`ApplyRetentionWindow`): delete every document of the quarter, return how many (Mongo: `delete_many({quarter: q})` on the `{quarter: 1}` index). |
| `RevokedTokenStore` | Logout. `revoke(jti, ttl)` is idempotent; the entry expires with the token (Redis `SET revoked:{jti} 1 EX ttl`). |
| `ShortageStatusStore` | Holds `ShortageSummary` per **ingredient**; TTL is a cache TTL (the value can always be rebuilt). |

## MongoDB indexes and pipelines

Indexes live in `infrastructure/mongodb/indexes.py`, each with the query it serves; `scripts/benchmark_indexes.py`
prints `explain()` with and without each one. A compound index may hold only ONE array field, so the reports index is
`{suspect_ingredient_ids, receive_date, _id}` (the reaction filter is applied on the fetched documents).
Sharding candidate for `reports`: hashed `report_id` (never `receive_date` alone).

`pair_counts` runs three pipelines (`mongodb/pipelines/signal_counts.py`): per drug, per reaction, per pair, each starting
with `$match {quarter}`. Not one `$facet`: its output is one document (16 MB cap) and a quarter has ~100k pairs.
Excluded terms are removed after `$unwind`, so a report keeps its other reactions.

## Redis

| Key | Port | Notes |
|---|---|---|
| `shortage:{ingredient}` HASH | `ShortageStatusStore` | `ShortageSummary`, `dosage_forms` comma-joined; cache TTL, rebuilt by `Reconcile` |
| `follows:{user}` / `followers:{ingredient}` SET | `FollowStore` | both directions in one MULTI; source of truth |
| `alert:{user}:{alertId}` HASH + `alerts:{user}` ZSET | `AlertStore` | `EXPIRE` 30 days; `expires_at` also checked against the clock; index pruned on read |
| `count:{ingredient}:{reaction}:{quarter}` STRING | `CounterStore` | SET by the projector from the signal's `a`, never INCR |
| `revoked:{jti}` STRING | `RevokedTokenStore` | value = expiry instant, `EX` = token's remaining life |

## Event sync

The worker (`app/worker.py`) runs `infrastructure/sync/change_stream_projector.py` on a replica set: it watches `signals`
and `shortages` and calls `ProjectChangeEvent` (counter SET + signal alerts honouring the user's `min_reports`; shortage
summary overwrite). The resume token is saved in `sync_checkpoints` every 200 changes and when the stream is quiet.
On a standalone `mongod` there are no change streams: the worker runs `Reconcile` every 10 minutes instead.
