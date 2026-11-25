# Sharding design (NFR-07)

The brief says to "argue and, if needed, design" sharding. This is a design and an argument; nothing here is
implemented or deployed. The working system is one MongoDB replica set and one Redis primary with replicas
(see `cap-theorem.md` for how they behave).

**Position:** at the size of this project (a rolling window of 6 quarters) one replica set per database is enough, and
sharding would add operational cost without a measured need. The designs below are what we would do when the data
outgrows one node, and they were chosen so that the current code needs few changes. Measured on the cluster
(`db.reports.stats()`, 25 November 2026): `reports` holds 132,804 documents, 281 MB of data stored in 83 MB plus 27 MB
of indexes; the whole database is 416 MB of data in 141 MB plus 49 MB of indexes. Sizes marked *(estimate)* are
extrapolations from these numbers.

## 1. When sharding becomes worth it

Shard when one of these is true, not before:

- the working set (hot data plus indexes) no longer fits in the RAM of one node;
- write throughput of ingestion exceeds what one primary can journal;
- storage exceeds one disk.

The window is the lever. With 6 quarters, the full FAERS set (not our sample of 2 partitions per quarter) is on the order of 1-2 million reports *(estimate)*,
a few GB: it fits on one node. Dropping the window to keep history since 2004 would be roughly 15-20 times that
*(estimate)*, and that is the case that justifies a cluster.

## 2. MongoDB

### Which collections

| Collection | Size trend | Decision |
|---|---|---|
| `reports` | largest by far; grows with every quarter | **shard** |
| `signals` | one row per drug/reaction pair per quarter, derived, rebuildable | keep on one replica set until measured; same shard key rule below if needed |
| `ingredients`, `rx_concepts`, `products`, `labels`, `shortages`, `shortage_events`, `recalls`, `name_map` | thousands to tens of thousands of documents | do not shard; they live on the primary shard |
| `users`, `excluded_terms`, `ingestion_runs`, `sync_checkpoints` | small, need the unique indexes on `users` | do not shard |

Sharding a collection with unique indexes (`users.username_lower`, `email_lower`) is also restricted: a unique index
must contain the shard key. That is a second reason to leave `users` alone.

### Shard key for `reports`: hashed `_id` (the report id)

The queries on `reports` (indexes in `mongodb/indexes.py`) and what each key choice does to them:

| Query | by `quarter` | by an ingredient | hashed `_id` |
|---|---|---|---|
| `get` / admin by id | scatter | scatter | **targeted (1 shard)** |
| `pair_counts`, `statistics` (aggregations over a quarter) | targeted to few shards, **one shard does all the work** | scatter | scatter, **work split evenly, results merged** |
| `delete_quarter` (rolling window) | targeted | scatter | scatter (`deleteMany`, fine once a quarter) |
| drug page, `list_for_pair`, `monthly_trend`, `top_reactions` | scatter | targeted | scatter, each shard answers from its own `suspect_date` index |
| bulk ingestion | **all writes hit the newest quarter's shard (hot shard)** | skewed by popular drugs | **uniform across shards** |

Why not the other candidates:

- **`quarter`** (or `{quarter, _id}`): only 4-6 values, so chunks cannot split (jumbo chunks), and every insert goes to
  the current quarter: the textbook hot shard. Its one advantage, cheap `delete_quarter`, is real but small.
- **an ingredient id**: `suspect_ingredient_ids` is an array and a shard key cannot be multikey. It would need a
  denormalised scalar "main ingredient", and a drug like ibuprofen has far more reports than most, so one chunk
  would be a hot spot. It would also not be consistent for reports with several suspect drugs.
- **`receive_date`**: monotonically increasing, the same hot-shard problem as `quarter`.

Hashed `_id` is high-cardinality, never changes, and spreads inserts evenly. Its cost is that drug-centred queries
become scatter-gather. That is acceptable because: each shard still uses its local compound index; the lists are
small (`LIMIT 10-20`, merged by `mongos`); the aggregations that dominate cost (`pair_counts`, `statistics`) are
`$group` pipelines that each shard computes on its slice in parallel and `mongos` merges, so more shards means a
faster quarterly computation, not a slower one.

```
sh.enableSharding("medsignal")
sh.shardCollection("medsignal.reports", { _id: "hashed" })     // pre-splits chunks across the shards
```

### Topology

- 2-3 shards, each a 3-member replica set (the current `rs0` becomes shard 1, so the data stays where it is);
- a 3-member config server replica set;
- 2 `mongos` routers; the API's `MONGO_URI` points to them instead of to `rs0` (no code change: same driver, same
  collections).
- On the 3 Virtual Lab VMs this means each VM runs one member of each replica set; it works but is tight on RAM,
  which is one more reason not to do it for the demo.

### What changes in the code

- `w=majority` and the read preferences (ADR 0003) apply per shard and keep working through `mongos`.
- Change streams (the Redis projector) work on a sharded collection through `mongos`.
- Aggregations that group over the whole collection get slower per request than on one node if the dataset is small,
  because of the scatter, and faster when it is large: this is why the choice must be re-evaluated with the
  `benchmark_indexes.py` and `benchmark_cluster.py` numbers at the new size.
- The rolling window could instead be implemented with one collection per quarter (`reports_2026Q1`) and
  `drop()` to expire it. That makes retention free and is worth considering with or without sharding, but it changes
  every report query to a multi-collection query, so it is not proposed here.

## 3. Redis

### Do we need Redis Cluster?

The Redis data is small: a set of drug ids per user, a few alerts per user with a 30-day TTL, one hash per drug and
one counter per (drug, reaction, quarter). Even for 100,000 users that is on the order of hundreds of MB *(estimate)*
and fits in one node's RAM; reads are cheap. Replication plus Sentinel (already deployed) gives the availability
the brief asks for. Redis Cluster would be for throughput or memory beyond one machine, so again it is a growth
design, not a need today.

### How the keys would be partitioned

Redis Cluster maps a key to one of 16,384 hash slots by CRC16 of the key, or of the part inside the first `{...}`
(a *hash tag*). Keys used together in a transaction must share a slot. The key families of `key_schema.py` fall into
two groups:

| Family | Natural key | Cluster key (with hash tag) |
|---|---|---|
| `follows`, `alert`, `alerts` (index) | user id | `follows:{u42}`, `alert:{u42}:ev1`, `alerts:{u42}`: all of a user's data in one slot, so reading a user's cabinet and alerts, and writing an alert plus its index (`MULTI/EXEC`), stay single-slot |
| `shortage`, `followers`, `count` | ingredient rxcui | `shortage:{198013}`, `followers:{198013}`, `count:{198013}:NAUSEA:2026Q1`: everything about a drug in one slot, so fan-out of one event reads `followers` and `shortage` from one node |
| `revoked` | token id (`jti`) | `revoked:{jti}`; independent single-key reads and writes, spread evenly by the hash |

Keying by user and by ingredient fits the access patterns: the cabinet is per user, the alert dispatcher is per
drug. A hot ingredient is one key family on one slot, which is fine (a `SMEMBERS` over its followers).

### The one real problem: `follow()` touches two families

`RedisFollowStore.follow` adds to `follows:{user}` and `followers:{rxcui}` in one `MULTI/EXEC`. In a cluster those are
two different slots and the transaction is rejected with `CROSSSLOT`. Options:

1. **Two single-slot writes, not atomic, with a repair path** (recommended). Write `follows:{user}` first (what the
   user reads), then `followers:{rxcui}` (what the dispatcher reads). A crash between them leaves a followed drug
   that does not raise alerts until repair. Reconcile would need a new step that rebuilds `followers` from `follows` (today it only
   rebuilds shortage summaries), and
   the writes are idempotent (`SADD`/`SREM`), so a retry is safe.
2. **Make MongoDB the source of truth for follows** (a `follows` array on the user document) and project both Redis
   sets from the change stream, like shortage summaries already are. Cleanest consistency story, most work.
3. **Drop the `followers` reverse index** and query MongoDB for followers when an alert fires. Simple, slower dispatch.

### Topology and client

- 3 masters and 3 replicas (the minimum for a majority-based failover); Redis Cluster does its own failover, so
  Sentinel is replaced, not combined.
- The client changes from `redis.asyncio.Redis` (via Sentinel) to `redis.asyncio.RedisCluster`; the stores take a
  `Redis`-like object, so the change is in `redis/client.py` plus the key tags in `key_schema.py` (the single place
  where key strings are built, which was the point of that rule), plus the `follow` change above.
- Cluster replication is still asynchronous, so the CAP position in `cap-theorem.md` does not change: sharding adds
  capacity, not stronger consistency.
