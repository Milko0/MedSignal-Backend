# CAP, consistency and performance on the cluster

The brief asks for the application to be analysed against the CAP theorem after deployment, with statistics and
performance tests of reads and writes. This file is the analysis; `scripts/benchmark_cluster.py` produces the numbers.
Design decisions behind it: ADR 0001 (self-hosted databases), ADR 0003 (read preference per use case).

> **Status of the numbers.** Section 5 was measured on the **Docker 3 + 3 cluster** of
> `deploy/docker-compose.local.yml` (MongoDB 7 replica set, Redis 7.4 primary + 2 replicas + 3 Sentinels) on one
> laptop, one run each, on 25 November 2026. The behaviours (what is lost, what pauses, who serves reads) are the
> results; the absolute speeds would be higher on separate machines such as the Virtual Lab, where the same script
> can be re-run. Raw output: `docs/perf-cluster-*.json`.

## 1. The cluster

| | MongoDB 7 | Redis 7 |
|---|---|---|
| Nodes | replica set `rs0`, 3 members, `mongo1` priority 2 | 1 primary + 2 replicas, 3 Sentinels (quorum 2) |
| Replication | oplog, asynchronous to members, but the *client* can wait for the majority | asynchronous, no wait unless the client calls `WAIT` |
| Failure detection | heartbeat, election after `electionTimeoutMillis` (10 s default) | Sentinel `down-after-milliseconds 5000`, `failover-timeout 10000` |
| Durability | journal | AOF (`appendonly yes`) |
| What it holds | reports, signals, catalog, users: the source of truth | follows, alerts, shortage summaries, counters, revoked tokens |

## 2. What each store does during a network partition

CAP says that during a partition a system keeps either consistency or availability. The answer is different for each
store and, for MongoDB, for each operation.

### MongoDB: writes are CP, analytic reads are tuned towards AP

- **Writes use `w=majority`** (`mongodb/client.py`). A write is acknowledged only when 2 of 3 members have it. If the
  primary ends up on the minority side of a partition it cannot reach a majority: it steps down and its writes fail
  or time out. The majority side elects a new primary (a pause of roughly the election timeout) and carries on.
  Nothing acknowledged is lost, because every acknowledged write is on at least one member of the majority that
  elects the next primary. **Consistency kept, availability of writes given up on the minority side.**
- **With `w=1` the answer flips.** The isolated primary keeps accepting writes, then rolls them back when it rejoins.
  The client was told "ok" for data that is gone. That is why the app never uses `w=1`; the benchmark measures how
  much speed the safe setting costs.
- **Analytic reads use `secondaryPreferred` with `maxStalenessSeconds=90`** (ADR 0003). They keep working while the
  primary is being elected, because a secondary can answer, and they may be a little behind (eventual
  consistency). If no secondary is within the staleness bound and there is no primary, the read fails. So reads are
  "available unless the whole set is down or too stale", not unconditionally available.
- **Accounts and batch jobs read the primary**, so a login or a signal computation sees what was just written
  (read-your-writes). During an election (11-12 s measured) those requests fail after the API's 3 s server
  selection timeout and succeed when repeated.

Not partitioned (PACELC "else" branch): majority writes cost one extra round trip to a secondary, and secondary reads
return results that are milliseconds old but take load off the primary. The benchmark measures both ends of that
trade.

### Redis with Sentinel: AP-leaning

- Replication is asynchronous: the primary answers the client before the replicas have the write. If the primary
  dies, the replica Sentinel promotes may not have the latest writes; they are lost. If the primary is only
  *partitioned* (alive on the minority side), it keeps accepting writes until it is demoted, and those writes are
  discarded when it rejoins as a replica (a short split-brain). **Availability kept, consistency given up.**
- It can be pushed towards CP at a cost. The client can call `WAIT 1 <ms>` after a write to learn that at least one
  replica has it (this shrinks the loss window but does not close it: `WAIT` is not consensus). The server can refuse
  writes when it has lost its replicas with `min-replicas-to-write 1` and `min-replicas-max-lag 10`, which bounds the
  split-brain window but makes writes unavailable on a lone primary. `deploy/redis` sets neither today.
- **Why AP is acceptable here.** What Redis holds is mostly rebuildable or low value: shortage summaries and
  counters are recomputed from MongoDB (Reconcile, the projector); alerts are rebuilt by replaying the change stream
  (their ids are deterministic); a follow lost in a failover is one click to redo. The one item with a security
  flavour is `revoked:{jti}`: a revoked token written just before a failover can become valid again until it expires
  (at most `JWT_EXPIRE_MINUTES`, 60 by default). If that matters, revoke with `WAIT 1`, or keep revocations in
  MongoDB.
- **The cabinet reads the Redis primary**, not replicas, so a user sees the follow they just made. Replica reads
  would be stale by the replication lag and cannot give read-your-writes.

### Summary

| Data | Store and mode | In a partition | Loss on failover |
|---|---|---|---|
| Reports, signals, catalog (writes) | MongoDB `w=majority` | CP: minority side cannot write | none acknowledged |
| Statistics, signal explorer, trends (reads) | MongoDB secondaries, max 90 s stale | stays available, may be stale | n/a |
| Users, login, admin | MongoDB primary | CP | none acknowledged |
| Follows, alerts (cabinet) | Redis primary, async replication | AP: both sides may accept writes | last few writes |
| Shortage summaries, counters | Redis, recomputed from MongoDB | AP, self-healing | repaired by Reconcile |
| Revoked tokens | Redis | AP | possible; bounded by token lifetime |

Overall: **MongoDB, the system of record, is CP for writes with tunable stale reads; Redis, the speed layer, is AP and
holds only data that can be rebuilt or is cheap to lose.** That split is the design, not an accident of tooling.

## 3. What the benchmark measures

`scripts/benchmark_cluster.py <suite>` (details and flags in the script header; how to run it below). Everything runs in the scratch
database `medsignal_bench` and `bench:*` Redis keys, deleted at the end.

| Suite | Question | How |
|---|---|---|
| `mongo-writes` | What does durability cost? | `insert_one` and 100-document `insert_many` with `w=1`, `w=1+journal`, `majority`, `w=3`. Throughput and p50/p95/p99. |
| `mongo-reads` | What do secondaries buy? | Point lookup, signal-explorer query and a statistics aggregation with `primary`, `secondaryPreferred`, `secondary`, `nearest`. Also prints which node served the point lookups, which proves secondaries were used. |
| `staleness` | How eventual is "eventual"? | Write, then read at once from a secondary. Share of reads that miss it for `w=1`, `majority`, `majority` read concern, and a causally consistent session (read-your-writes). |
| `redis` | Redis vs MongoDB, and the price of `WAIT` | `SET` alone vs `SET`+`WAIT 1`/`WAIT 2`; the app's follow transaction; `GET` on master vs replica; `SISMEMBER`; MongoDB `find_one` by `_id` as the comparison. Also counts `WAIT`s that returned fewer acknowledgements than asked. |
| `mongo-failover` | What happens to writes in an election? | Writes and secondary reads run continuously; `replSetStepDown` (or `--manual`: kill the primary container yourself). Reports the longest write pause, write errors, how long until writes resume, secondary-read pause, and **acknowledged writes lost** (verified with a majority read afterwards). Run with `--w majority` and `--w 1`. |
| `redis-failover` | What does async replication lose? | Concurrent writers, `SENTINEL FAILOVER` (or `--manual`: stop or isolate the master yourself). Reports pause, errors and **acknowledged writes missing on the new master**. Run with `--wait 0` and `--wait 1`. |

Run on the Docker cluster through the `bench` service (it runs inside the compose network, where the member names
and Sentinel's addresses resolve, and mounts `docs/` for `--out`). About 5 minutes without the failovers:

```bash
docker compose -f deploy/docker-compose.local.yml --profile bench build bench
B="docker compose -f deploy/docker-compose.local.yml --profile bench run --rm -e PYTHONUNBUFFERED=1 bench"
$B all --out docs/perf-cluster-results.json
$B mongo-failover --w majority --out docs/perf-cluster-mongo-stepdown.json     # automatic replSetStepDown
$B mongo-failover --w 1 --manual                                              # kill the primary when told to:
#   docker compose -f deploy/docker-compose.local.yml kill mongo1   (then: ... start mongo1)
$B mongo-failover --w majority --manual                                       # same kill, majority writes
$B redis-failover --wait 0 --out docs/perf-cluster-redis-failover.json        # automatic SENTINEL FAILOVER
$B redis-failover --wait 1 --out docs/perf-cluster-redis-failover-wait1.json
```

It cannot run from the host: `mongo1..3` and the Redis addresses Sentinel returns (172.29.0.x) only resolve inside
the compose network. `PYTHONUNBUFFERED=1` makes the "stop the primary now" line appear at the right moment.

The numbers from the cluster run, and how to read them, are in section 5.

## 4. Eventual consistency in the application

The brief wants the replicas "managed in terms of eventual consistency". The application does it as follows
(code: `mongodb/client.py` `analytics_database`, `report_repository.py`, `signal_repository.py`; test:
`tests/unit/infrastructure/test_read_routing.py`):

- Writes are majority-acknowledged, so a secondary that has not applied a write yet is always a minority of the set.
- Analytic reads are served by secondaries and can lag the primary by the replication delay, bounded at 90 s by the
  driver (a staler secondary is skipped). The data they read changes once per quarter or on a daily poll, so users
  cannot see the difference.
- Anything that must see its own write (accounts, signal computation, admin edits) reads the primary.
- `MONGO_READ_SECONDARIES=false` restores primary-only reads, which is the baseline for the benchmark.
- The database conformance suite (24 tests) passes against a real replica set and Redis both with primary-only reads and
  with the analytics handle on the secondaries. That run found a bug the unit test with fakes could not: a PyMongo
  collection cannot be used in `col or default` (it refuses `bool()`), now fixed.

## 5. Measured results (Docker 3 + 3 cluster, 25 November 2026)

Setup: `deploy/docker-compose.local.yml` on one Windows laptop with Docker Desktop: MongoDB 7 replica set `rs0`
(3 members), Redis 7.4 primary + 2 replicas + 3 Sentinels, each in its own container on the compose network. The
benchmark ran inside that network (`bench` service), 16 operations in flight, 2,000 operations per row, 20,000
documents or keys for the read tests, one run each. All containers share the laptop's CPU and disk, so absolute
speeds are lower than on separate machines and differences below roughly 15-20% are noise. What is lost, what
pauses and which node serves a read do not depend on that. Raw output: `docs/perf-cluster-*.json`. The first run on
a bare-metal laptop cluster (no containers) is kept in `docs/perf-local-results.json`; it showed the same behaviour.

**MongoDB writes** (`insert_one`, ops/s; p95 in ms)

| Write concern | ops/s | p95 ms | 100-doc `insert_many`, docs/s |
|---|---|---|---|
| `w=1` | 1,053 | 18.2 | 34,227 |
| `w=1` + journal | 1,064 | 20.9 | 21,165 |
| `w=majority` (what the app uses) | 955 | 22.9 | 17,305 |
| `w=3` (all nodes) | 1,126 | 17.0 | 17,531 |

Reading: on single inserts majority costs about 10%, inside the noise. On bulk inserts, where the wait for the
secondaries is not hidden by the per-request overhead, majority halves the throughput (34,227 -> 17,305 docs/s).
That is the price of the durability the failover tests below show. `w=3` costs the same as majority here because
all three nodes are healthy; it would stop writes entirely with one node down.

**MongoDB reads by read preference** (ops/s)

| | point lookup | signal explorer | statistics aggregation |
|---|---|---|---|
| `primary` | 1,773 | 1,542 | 1,469 |
| `secondaryPreferred` (what the analytics use) | 1,339 | 1,392 | 1,509 |
| `secondary` | 1,636 | 1,444 | 1,127 |
| `nearest` | 1,540 | 1,210 | 1,205 |

Served by (point lookups, 2,000 each): `primary` 100% `mongo1`; `secondaryPreferred` and `secondary` 1,000 each on
`mongo2` and `mongo3`; `nearest` about one third on each node. The routing of ADR 0003 does reach the secondaries.
The speeds are equal within noise because the three containers share one CPU: moving the aggregations off the
primary pays off only when the nodes are separate machines, where it frees the primary for writes and logins.

**Eventual consistency** (300 write-then-read-from-secondary trials)

| Write / read | Reads that missed the fresh write | Time until visible |
|---|---|---|
| `w=1`, read secondary | **289 of 300 (96%)** | mean 1.4 ms, max 30 ms |
| `w=majority`, read secondary | 0 | |
| `w=majority`, read concern majority | 0 | |
| causal session (read-your-writes) | 0 | |

With `w=1` a read sent straight to a secondary almost always misses the write; it arrives about 1.4 ms later. With
majority writes the secondary that answers already had it in every trial. That is a property of this run, not a
guarantee (with two secondaries, majority waits for one of them; the other may still be behind): only a causal
session guarantees read-your-writes. For the app, analytics reads are at worst milliseconds old, and the data
they read changes once per quarter or on a daily poll.

**Redis vs MongoDB, and replication** (Sentinel deployment)

| | ops/s | mean ms | p95 ms |
|---|---|---|---|
| `SET`, async replication | 4,063 | 3.89 | 5.55 |
| `SET` + `WAIT 1` | 2,500 | 6.38 | 8.03 |
| `SET` + `WAIT 2` | 2,370 | 6.74 | 9.00 |
| `follow()` (MULTI/EXEC of 2 `SADD`) | 2,794 | 5.70 | 9.73 |
| `GET`, master | 4,232 | 3.77 | 4.85 |
| `GET`, replica | 4,293 | 3.71 | 4.34 |
| `SISMEMBER` (is following) | 4,353 | 3.66 | 4.54 |
| MongoDB `find_one` by `_id` (primary) | 1,818 | 8.78 | 9.96 |

Reading: waiting for one replica costs about 2.5 ms per write (about 40% of the throughput), and every `WAIT` got
the acknowledgements it asked for while the cluster was healthy. A Redis point read is about 2.3 times faster than
the same read from MongoDB (3.8 ms against 8.8 ms, most of it the container network), which is why the cabinet,
follows and shortage summaries live in Redis.

**Failover** (MongoDB: 3 nodes, election; Redis: Sentinel, `down-after-milliseconds 5000`)

| Test | Longest write pause | Write errors | Acknowledged writes lost | Reads during it |
|---|---|---|---|---|
| MongoDB, `replSetStepDown`, `w=majority` | 10.9 s | 0 (client waited) | **0 of 1,699** | secondary reads never stopped (longest gap 0.03 s) |
| MongoDB, primary container killed, `w=majority` | 12.0 s | 0 (client waited) | **0 of 1,543** | longest gap 0.03 s |
| MongoDB, primary container killed, `w=1` | 11.1 s | 0 | **10 of 2,789** | longest gap 0.03 s |
| Redis, `SENTINEL FAILOVER`, no `WAIT` | 0.1 s | 16 | **48,926 of 147,854** | n/a |
| Redis, `SENTINEL FAILOVER`, `WAIT 1` | 0.3 s | 16 | **818 of 49,641** | n/a |

Reading:

- **MongoDB is CP for writes.** With `w=majority` no acknowledged write was lost, whether the primary stepped down
  or was killed. With `w=1` the same kill lost 10 writes the client had been told were stored: the killed primary
  had them, no secondary did, and they were gone once the new primary took over. Writes were unavailable for 11-12 s
  (the election); the benchmark client waited for the new primary (20 s server selection timeout). The API uses
  3 s, so requests that need the primary fail during an election and succeed when repeated afterwards (the
  cluster check saw the same). Secondary reads, which serve the analytics, were never interrupted.
- **Redis is AP, and the test shows the loss.** During a Sentinel failover the writers kept writing to the old
  master, which kept accepting (no pause, only 16 errors) after a replica had been promoted. When Sentinel then
  turned the old master into a replica of the new one, it discarded its data and resynchronised: a third of the
  acknowledged writes disappeared. `WAIT 1` shrinks the loss sixty-fold but does not remove it, because once the
  old master's replicas have moved to the new master, `WAIT` returns 0 after its timeout and the write is still
  acknowledged. This is the split-brain window of section 2, measured.
- **What it means for MedSignal.** The Redis data written in such a window is a follow, an alert or a revoked token.
  Alerts are recreated by the projector (deterministic ids, Reconcile); a lost follow is one click to redo; a lost
  revocation lets a logged-out token work until it expires (at most 60 minutes). The app accepts this in exchange
  for Redis staying writable. If it were not acceptable, the options are `min-replicas-to-write 1` with
  `min-replicas-max-lag` (refuse writes on a master that lost its replicas, which bounds the window), checking the
  value returned by `WAIT`, or moving revocations to MongoDB.

**Other finding.** An index build on a collection waits for *all* voting members by default. With one MongoDB node
down, `create_index` in the first version of the benchmark blocked indefinitely. The benchmark now sends
`createIndexes` with `commitQuorum: "majority"`. The application's `ensure_indexes` has the same exposure when a
new index must be built while a node is down (it is a no-op when the indexes already exist); worth knowing for a
deployment during an outage, not changed here.