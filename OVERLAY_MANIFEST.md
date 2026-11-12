# How to merge this overlay into your repository

This zip contains only the files that were written or changed. Copy it over your `MedSignal-Backend` folder.
Files with the same path replace yours; new files are added. **Not included (yours, untouched):**
`app/infrastructure/mongodb/*`, `app/infrastructure/redis/*`, `app/infrastructure/sync/*`, `app/infrastructure/scheduling/*`,
`deploy/*`, `Dockerfile`, `scripts/download_faers.py`, `scripts/medsignal_api_check.py`, `scripts/load_sample.py`, `scripts/benchmark_indexes.py`.

## Delete from your repo (obsolete or duplicated)

| File | Why |
|---|---|
| `app/application/ports/drug_repository.py` | replaced by `ingredient_repository.py` |
| `app/application/ports/signal_calculator.py` | a domain service, it does not belong in ports |
| `app/application/use_cases/profile/{list_ingestion_runs,load_faers_bulk,update_labels_recalls,poll_shortages}.py` | copies of the ingestion use cases in the wrong folder |
| `app/core/security.py` setting name `jwt_expire_minutes` | now used by `create_access_token` (keep `JWT_EXPIRE_MINUTES` in `.env`) |

## Your files that must change to follow the new ports (team)

| File | Change |
|---|---|
| `infrastructure/redis/stores/shortage_status_store.py` | store `ShortageSummary` per ingredient |
| `infrastructure/redis/stores/alert_store.py` | new `Alert` fields (`type`, `drug_rxcui`, `message`, `expires_at`) |
| `infrastructure/redis/stores/{follow,counter}_store.py` | ids are ingredient rxcuis |
| `infrastructure/mongodb/repositories/*` | implement the new ports (see docs/PORT_CONTRACT.md); `drug_repository.py` -> `ingredient_repository.py`; add `product`, `rx_concept`, `name_map` repositories |
| `infrastructure/mongodb/pipelines/signal_counts.py` | return `PairCounts` (see `pair_counts` sketch) |
| `infrastructure/mongodb/indexes.py` | indexes of the PORT_CONTRACT table |
| `core/config.py` | merge `storage_backend`, `data_dir`, `cache_dir` and the client limits (keep your Mongo/Redis/Sentinel fields) |
| `app/main.py` | the lifespan now builds the container with `build_container(settings)`; keep your index creation inside the database container |

## Files in this overlay
- app/__init__.py
- app/__pycache__/__init__.py
- app/application/__init__.py
- app/application/__pycache__/__init__.py
- app/application/container.py
- app/application/dtos/__init__.py
- app/application/dtos/__pycache__/__init__.py
- app/application/dtos/admin.py
- app/application/dtos/auth.py
- app/application/dtos/cabinet.py
- app/application/dtos/common.py
- app/application/dtos/drugs.py
- app/application/dtos/profile.py
- app/application/dtos/shortages.py
- app/application/dtos/signals.py
- app/application/ingestion/__init__.py
- app/application/ingestion/__pycache__/__init__.py
- app/application/ingestion/resolution.py
- app/application/ingestion/transformers/__init__.py
- app/application/ingestion/transformers/__pycache__/__init__.py
- app/application/ingestion/transformers/common.py
- app/application/ingestion/transformers/label.py
- app/application/ingestion/transformers/ndc_product.py
- app/application/ingestion/transformers/recall.py
- app/application/ingestion/transformers/report.py
- app/application/ingestion/transformers/rxnorm.py
- app/application/ingestion/transformers/shortage.py
- app/application/ports/__init__.py
- app/application/ports/__pycache__/__init__.py
- app/application/ports/alert_store.py
- app/application/ports/clock.py
- app/application/ports/counter_store.py
- app/application/ports/drug_normalizer.py
- app/application/ports/excluded_term_repository.py
- app/application/ports/external_data_source.py
- app/application/ports/follow_store.py
- app/application/ports/ingestion_run_repository.py
- app/application/ports/ingredient_repository.py
- app/application/ports/label_repository.py
- app/application/ports/name_map_repository.py
- app/application/ports/product_repository.py
- app/application/ports/recall_repository.py
- app/application/ports/report_repository.py
- app/application/ports/rx_concept_repository.py
- app/application/ports/shortage_repository.py
- app/application/ports/shortage_status_store.py
- app/application/ports/signal_repository.py
- app/application/ports/user_repository.py
- app/application/services/__init__.py
- app/application/services/__pycache__/__init__.py
- app/application/services/alert_dispatcher.py
- app/application/services/ingredient_resolver.py
- app/application/use_cases/__init__.py
- app/application/use_cases/__pycache__/__init__.py
- app/application/use_cases/admin/__init__.py
- app/application/use_cases/admin/manage_excluded_terms.py
- app/application/use_cases/auth/__init__.py
- app/application/use_cases/auth/login.py
- app/application/use_cases/auth/register.py
- app/application/use_cases/cabinet/__init__.py
- app/application/use_cases/cabinet/dismiss_alert.py
- app/application/use_cases/cabinet/follow_drug.py
- app/application/use_cases/cabinet/list_alerts.py
- app/application/use_cases/cabinet/list_followed.py
- app/application/use_cases/cabinet/unfollow_drug.py
- app/application/use_cases/drugs/__init__.py
- app/application/use_cases/drugs/__pycache__/__init__.py
- app/application/use_cases/drugs/get_drug_360.py
- app/application/use_cases/drugs/get_label_gaps.py
- app/application/use_cases/drugs/get_reaction_trend.py
- app/application/use_cases/drugs/search_drug.py
- app/application/use_cases/ingestion/__init__.py
- app/application/use_cases/ingestion/__pycache__/__init__.py
- app/application/use_cases/ingestion/build_clean_dataset.py
- app/application/use_cases/ingestion/compute_quarter_signals.py
- app/application/use_cases/ingestion/link_recalls.py
- app/application/use_cases/ingestion/list_ingestion_runs.py
- app/application/use_cases/ingestion/load_faers_bulk.py
- app/application/use_cases/ingestion/normalize_drug_names.py
- app/application/use_cases/ingestion/poll_shortages.py
- app/application/use_cases/ingestion/update_labels_recalls.py
- app/application/use_cases/profile/__init__.py
- app/application/use_cases/profile/manage_profile.py
- app/application/use_cases/shortages/__init__.py
- app/application/use_cases/shortages/__pycache__/__init__.py
- app/application/use_cases/shortages/recommend_alternatives.py
- app/application/use_cases/signals/__init__.py
- app/application/use_cases/signals/emerging_signals.py
- app/application/use_cases/signals/list_signals.py
- app/application/use_cases/signals/signal_reports.py
- app/application/use_cases/signals/statistics.py
- app/application/use_cases/sync/__init__.py
- app/application/use_cases/sync/project_change_event.py
- app/application/use_cases/sync/reconcile.py
- app/core/__init__.py
- app/core/__pycache__/__init__.py
- app/core/config.py
- app/core/constants.py
- app/core/security.py
- app/domain/__init__.py
- app/domain/__pycache__/__init__.py
- app/domain/entities/__init__.py
- app/domain/entities/__pycache__/__init__.py
- app/domain/entities/alert.py
- app/domain/entities/drug.py
- app/domain/entities/enums.py
- app/domain/entities/excluded_term.py
- app/domain/entities/ingestion_run.py
- app/domain/entities/label.py
- app/domain/entities/name_mapping.py
- app/domain/entities/product.py
- app/domain/entities/recall.py
- app/domain/entities/report.py
- app/domain/entities/rx_concept.py
- app/domain/entities/shortage.py
- app/domain/entities/signal.py
- app/domain/entities/user.py
- app/domain/exceptions.py
- app/domain/services/__init__.py
- app/domain/services/__pycache__/__init__.py
- app/domain/services/age_bucketer.py
- app/domain/services/alternative_ranker.py
- app/domain/services/code_dictionary.py
- app/domain/services/date_parser.py
- app/domain/services/drug_name_cleaner.py
- app/domain/services/emerging_signal_policy.py
- app/domain/services/label_gap_matcher.py
- app/domain/services/label_text_union.py
- app/domain/services/shortage_diff.py
- app/domain/services/shortage_summary.py
- app/domain/services/signal_calculator.py
- app/domain/value_objects/__init__.py
- app/domain/value_objects/__pycache__/__init__.py
- app/domain/value_objects/contingency_table.py
- app/domain/value_objects/ndc.py
- app/domain/value_objects/pair_counts.py
- app/domain/value_objects/quarter.py
- app/domain/value_objects/reaction_term.py
- app/domain/value_objects/rxcui.py
- app/domain/value_objects/set_id.py
- app/domain/value_objects/unii.py
- app/infrastructure/__init__.py
- app/infrastructure/__pycache__/__init__.py
- app/infrastructure/clock.py
- app/infrastructure/container_factory.py
- app/infrastructure/external/__init__.py
- app/infrastructure/external/__pycache__/__init__.py
- app/infrastructure/external/dailymed_client.py
- app/infrastructure/external/file_feeds.py
- app/infrastructure/external/http.py
- app/infrastructure/external/openfda_client.py
- app/infrastructure/external/rxnorm_client.py
- app/infrastructure/external/rxnorm_normalizer.py
- app/infrastructure/memory/__init__.py
- app/infrastructure/memory/__pycache__/__init__.py
- app/infrastructure/memory/dataset.py
- app/infrastructure/memory/factory.py
- app/infrastructure/memory/repositories.py
- app/infrastructure/memory/stores.py
- app/main.py
- app/presentation/__init__.py
- app/presentation/api/__init__.py
- app/presentation/api/dependencies.py
- app/presentation/api/error_handlers.py
- app/presentation/api/responses.py
- app/presentation/api/router.py
- app/presentation/api/routers/__init__.py
- app/presentation/api/routers/admin/__init__.py
- app/presentation/api/routers/admin/crud_factory.py
- app/presentation/api/routers/admin/excluded_terms.py
- app/presentation/api/routers/admin/ingestion.py
- app/presentation/api/routers/admin/reconciliation.py
- app/presentation/api/routers/auth.py
- app/presentation/api/routers/cabinet.py
- app/presentation/api/routers/drugs.py
- app/presentation/api/routers/health.py
- app/presentation/api/routers/profile.py
- app/presentation/api/routers/shortages.py
- app/presentation/api/routers/signals.py
- app/presentation/api/routers/statistics.py
- app/worker.py
- docs/PORT_CONTRACT.md
- scripts/__init__.py
- scripts/build_clean_dataset.py
- scripts/download_raw.py
- tests/__init__.py
- tests/conformance/__init__.py
- tests/conformance/test_port_contract.py
- tests/conftest.py
- tests/fixtures/__init__.py
- tests/fixtures/fakes.py
- tests/fixtures/raw.py
- tests/integration/__init__.py
- tests/integration/test_api.py
- tests/integration/test_dataset_roundtrip.py
- tests/unit/__init__.py
- tests/unit/application/__init__.py
- tests/unit/application/test_pipeline.py
- tests/unit/application/test_transformers.py
- tests/unit/domain/__init__.py
- tests/unit/domain/test_parsers.py
- tests/unit/domain/test_signals_and_rules.py
- tests/unit/infrastructure/__init__.py
- tests/unit/infrastructure/test_http_and_feeds.py
- .env.example
- .gitignore
- OVERLAY_MANIFEST.md
- README.md
- pytest.ini
- requirements-dev.txt
- requirements.txt
