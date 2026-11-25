# CAP, consistency and performance on the cluster

The brief asks for the application to be analysed against the CAP theorem after deployment, with statistics and
performance tests of reads and writes. This file is the analysis; `scripts/benchmark_cluster.py` produces the numbers.
Design decisions behind it: ADR 0001 (self-hosted databases), ADR 0003 (read preference per use case).

> **Status of the numbers.** The script and the analysis are written. The measured tables (section 5) are empty until
> the script is run on the 3+3 cluster (local compose or the Virtual Lab). The MongoDB suites have not been run
> against a replica set yet; only the Redis suite was run, on a single Redis 5 without replicas, which proves the
> script works but says nothing about replication.

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

Things to expect and to check against the output, from the documented behaviour of the two systems (these are
hypotheses until measured):

- `w=majority` slower than `w=1`, `w=3` the slowest and failing when a node is down; journaling adds a disk wait.
- `secondaryPreferred` throughput on the aggregation higher than `primary` once the load is high enough to saturate
  one node; at low load the difference is small or negative (an extra hop).
- `w=1` reads from a secondary miss a fresh write some of the time; the causal session never does.
- Redis `GET` well below MongoDB `find_one`; `WAIT` adds about one round trip to a replica.
- Step-down: writes pause for the election, secondary reads do not; zero acknowledged writes lost with `majority`.
  When `mongo1` comes back the set holds a second, shorter election to give it back the primary role (priority 2).
- Redis failover: a short pause (seconds, set by Sentinel timeouts); a few acknowledged writes missing with `--wait 0`,
  fewer or none with `--wait 1`.

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

## 5. Measured results

To be pasted from `docs/perf-results.json` after the cluster run, one table per suite (the script prints them in the
format below):

```
                                  ops/s     mean      p50      p95      p99  errors   (ms)
```

| Suite | Result | Date | Cluster |
|---|---|---|---|
| mongo-writes | _not run yet_ | | |
| mongo-reads | _not run yet_ | | |
| staleness | _not run yet_ | | |
| redis | _standalone Redis 5 only: replica reads and `WAIT` not exercised_ | | |
| mongo-failover | _not run yet_ | | |
| redis-failover | _not run yet_ | | |
