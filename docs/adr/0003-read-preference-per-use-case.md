# ADR 0003: read preference chosen per use case

Status: accepted.

Every MongoDB write already waits for the majority (`w=majority`, NFR-03). Until now every read also went to the
primary, so the two secondaries only stored copies. The brief asks for replicas "managed in terms of eventual
consistency", so reads now use them where that is safe.

| Use case | Handle | Why |
|---|---|---|
| Signal explorer, emerging, trend, signal counts (`signals.search/trend/signal_count/latest_quarter`) | secondaries | Read-heavy, computed once per quarter; a result a few seconds old is indistinguishable. |
| Statistics, top reactions, monthly trend, reports behind a signal (`reports.statistics/top_reactions/monthly_trend/list_for_pair`) | secondaries | Aggregations over the biggest collection: this is the load worth spreading over three nodes. |
| Login, profile, registration (`users`) | primary | A new account or a password change must be visible to the very next request. |
| Signal computation (`reports.pair_counts`, `signals.previous_prrs`), `match_coverage`, `quarters`, `count`, `get` by id | primary | Batch jobs and admin CRUD read what they just wrote. A stale read would compute a signal from half-loaded data. |
| Medicine cabinet, alerts, follows (Redis) | Redis primary | Redis replicates asynchronously; the user must see the follow they just made. |
| Catalog (`ingredients`, `labels`, `products`, `shortages`, `recalls`) | primary | Small collections served by an index or an in-process cache; nothing to gain. |

How: `analytics_database()` (`mongodb/client.py`) returns the database with `SecondaryPreferred(max_staleness=90)`.
`create_database_container` hands it to the report and signal repositories as `read_db`; each method picks
`self.col` (primary) or `self.read` (analytics). Setting `MONGO_READ_SECONDARIES=false` sends everything back to the
primary, which is what the benchmark compares against.

Consequences:

- A signal or statistic can be older than the write that created it by the replication lag (normally milliseconds, never
  more than the 90 s staleness bound; past that the driver falls back to the primary).
- `secondaryPreferred` never fails when the secondaries are down: it reads the primary. Read availability is kept
  during a failover; only write availability is lost (see `docs/cap-theorem.md`).
- With a single `mongod` (`directConnection=true`) the preference has no effect, so development is unchanged.
- `tests/unit/infrastructure/test_read_routing.py` pins which handle each query uses.
