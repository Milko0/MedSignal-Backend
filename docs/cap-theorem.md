# CAP, consistency and performance on the cluster

The brief asks for the application to be analysed against the CAP theorem after deployment, with statistics and
performance tests of reads and writes. This file is the analysis; `scripts/benchmark_cluster.py` produces the numbers.
Design decisions behind it: ADR 0001 (self-hosted databases), ADR 0003 (read preference per use case).

> **Status of the numbers.** Everything in section 5 was measured on a **local test cluster on one laptop**
> (3 `mongod` 7.0.14 as a replica set and a Redis 5.0.14 primary + 2 replicas + 3 Sentinels, all on loopback), one run
> each. It proves the script and the behaviours (what is lost, what pauses, who serves reads); the absolute speeds
> are not representative of the real 3+3 cluster or the Virtual Lab, because there is no network latency and all
> nodes share one CPU. Re-run on the real cluster and replace the tables. Raw output: `docs/perf-local-results.json`.

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
  (read-your-writes). During an election those requests fail, which the frontend shows as a retryable error.

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

`py scripts/benchmark_cluster.py <suite>` (details and flags in the script header). Everything runs in the scratch
database `medsignal_bench` and `bench:*` Redis keys, deleted at the end.

| Suite | Question | How |
|---|---|---|
| `mongo-writes` | What does durability cost? | `insert_one` and 100-document `insert_many` with `w=1`, `w=1+journal`, `majority`, `w=3`. Throughput and p50/p95/p99. |
| `mongo-reads` | What do secondaries buy? | Point lookup, signal-explorer query and a statistics aggregation with `primary`, `secondaryPreferred`, `secondary`, `nearest`. Also prints which node served the point lookups, which proves secondaries were used. |
| `staleness` | How eventual is "eventual"? | Write, then read at once from a secondary. Share of reads that miss it for `w=1`, `majority`, `majority` read concern, and a causally consistent session (read-your-writes). |
| `redis` | Redis vs MongoDB, and the price of `WAIT` | `SET` alone vs `SET`+`WAIT 1`/`WAIT 2`; the app's follow transaction; `GET` on master vs replica; `SISMEMBER`; MongoDB `find_one` by `_id` as the comparison. Also counts `WAIT`s that returned fewer acknowledgements than asked. |
| `mongo-failover` | What happens to writes in an election? | Writes and secondary reads run continuously; `replSetStepDown` (or `--manual`: stop the container). Reports the longest write pause, write errors, how long until writes resume, secondary-read pause, and **acknowledged writes lost** (verified with a majority read afterwards). Run with `--w majority` and `--w 1`. |
| `redis-failover` | What does async replication lose? | Concurrent writers, `SENTINEL FAILOVER` (or `--manual`: `docker pause redis-primary`, which is closer to a real failure). Reports pause, errors and **acknowledged writes missing on the new master**. Run with `--wait 0` and `--wait 1`. |

Run order on the cluster (about 5 minutes without the failovers):

```bash
export MONGO_URI="mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0"
export REDIS_SENTINELS="sentinel-1:26379,sentinel-2:26379,sentinel-3:26379"
py scripts/benchmark_cluster.py all --out docs/perf-results.json
py scripts/benchmark_cluster.py mongo-failover --w majority --out docs/perf-mongo-failover-majority.json
py scripts/benchmark_cluster.py mongo-failover --w 1 --manual      # stop mongo1 when told to
py scripts/benchmark_cluster.py redis-failover --wait 0 --manual   # docker pause redis-primary when told to
py scripts/benchmark_cluster.py redis-failover --wait 1 --manual
```

The numbers from the local test run, and how to read them, are in section 5.

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

## 5. Measured results (local test cluster, one run each)

Setup: see the status note at the top. 16 operations in flight, 2,000 operations per row, 20,000 documents or keys
for the read tests. Differences below roughly 15-20% are inside the noise of a single run on a shared laptop and
are not claimed as findings.

**MongoDB writes** (`insert_one`, ops/s; p95 in ms)

| Write concern | ops/s | p95 ms | 100-doc `insert_many`, docs/s |
|---|---|---|---|
| `w=1` | 1,952 | 11.9 | 45,044 |
| `w=1` + journal | 1,697 | 13.4 | 55,749 |
| `w=majority` (what the app uses) | 1,610 | 13.1 | 35,679 |
| `w=3` (all nodes) | 2,206 | 11.5 | 34,730 |

Reading: majority costs about 17% on single inserts and about 21% on bulk inserts against `w=1`; the other
differences (`w=3` faster than `w=1`, journal faster in bulk) are noise. On a real network the majority penalty is one
round trip to a secondary, so it should be larger.

**MongoDB reads by read preference** (ops/s)

| | point lookup | signal explorer | statistics aggregation |
|---|---|---|---|
| `primary` | 4,227 | 3,340 | 2,728 |
| `secondaryPreferred` | 3,266 | 3,289 | 3,414 |
| `secondary` | 4,251 | 3,599 | 3,173 |
| `nearest` | 4,260 | 3,543 | 3,001 |

Served by (point lookups, 2,000 each): `primary` 100% on `:27117`; `secondaryPreferred` and `secondary` split
50/50 over the two secondaries; `nearest` spread over all three. So the routing in ADR 0003 does reach the
secondaries. On one machine the speeds are the same within noise, because the three nodes share one CPU: the benefit
of secondaries (more CPU and I/O for aggregations) can only show on separate machines.

**Eventual consistency** (300 write-then-read-from-secondary trials)

| Write / read | Reads that missed the fresh write | Time until visible |
|---|---|---|
| `w=1`, read secondary | **300 of 300 (100%)** | mean 4.0 ms, max 23.6 ms |
| `w=majority`, read secondary | 0 | |
| `w=majority`, read concern majority | 0 | |
| causal session (read-your-writes) | 0 | |

A read straight after a `w=1` write always missed it here; the data arrived 4 ms later on average. With majority
writes, on loopback, the secondary the read lands on already has it. That is a property of the local network (the
acknowledgement and the read are both slower than replication), not a guarantee: only the causal session
guarantees it. For the app this means the analytics reads are at worst a few milliseconds old.

**Redis vs MongoDB, and replication** (Sentinel deployment)

| | ops/s | mean ms | p95 ms |
|---|---|---|---|
| `SET`, async replication | 7,554 | 2.05 | 2.29 |
| `SET` + `WAIT 1` | 5,624 | 2.84 | 3.54 |
| `SET` + `WAIT 2` | 6,006 | 2.66 | 3.01 |
| `follow()` (MULTI/EXEC of 2 `SADD`) | 6,969 | 2.29 | 2.86 |
| `GET`, master | 12,295 | 1.30 | 1.51 |
| `GET`, replica | 10,022 | 1.54 | 1.80 |
| `SISMEMBER` (is following) | 12,430 | 1.28 | 1.71 |
| MongoDB `find_one` by `_id` (primary) | 4,517 | 3.53 | 4.42 |

Reading: `WAIT` for replicas costs about 0.7 ms per write here (a replica round trip) and every `WAIT` returned the
full number of acknowledgements. A Redis point read is about 2.7 times faster than the same read from MongoDB, which
is the reason the cabinet and shortage summaries live in Redis. A replica serves the same data about as fast as the
master.

**Failover** (MongoDB: 3 nodes; Redis: Sentinel with `down-after-milliseconds 5000`)

| Test | Longest write pause | Errors | Acknowledged writes lost | Reads during it |
|---|---|---|---|---|
| Mongo, `replSetStepDown`, `w=majority` | 10.7 s | 0 (client waited) | **0** | secondaries kept answering (longest gap 0.04 s) |
| Mongo, primary process killed, `w=majority` | 16.4 s | 0 (client waited) | **0** | longest gap 0.03 s |
| Mongo, primary process killed, `w=1` | 14.8 s | 0 | **3 of 978** | longest gap 0.04 s |
| Redis, master killed, no `WAIT` | 6.4 s | 64 | 0 of 307,519 | n/a |
| Redis, master killed, `WAIT 1` | 6.6 s | 64 | 0 of 128,852 | n/a |

Reading:

- MongoDB: with `w=majority` nothing acknowledged was lost, while `w=1` lost 3 acknowledged writes in the same
  test. This is the CP behaviour of section 2 shown with data. Writes were unavailable for 10-16 s (the election);
  secondary reads were not interrupted.
- Redis: Sentinel promoted a replica after about 6 s and the client reconnected by itself; 64 writes failed during
  the gap. **No acknowledged write was lost, but this test cannot show the AP weakness**: killing a process on one
  machine means its replicas had already received everything it sent. The loss window of asynchronous replication
  only opens on a real partition or a machine crash, where the old master keeps accepting writes that the
  replicas never get. Reproducing it needs `docker pause`/network rules on separate hosts; the `redis-failover`
  suite will count it when run there. Until then the Redis AP claim rests on the documented behaviour of Redis
  replication, not on a measurement of ours.

**Other finding.** An index build on a collection waits for *all* voting members by default. With one MongoDB node
down, `create_index` in the first version of the benchmark blocked indefinitely. The benchmark now sends
`createIndexes` with `commitQuorum: "majority"`. The application's `ensure_indexes` has the same exposure when a
new index must be built while a node is down (it is a no-op when the indexes already exist); worth knowing for a
deployment during an outage, not changed here.
