"""Read/write performance and failover tests on the MongoDB replica set and the Redis primary/replicas/Sentinel.

    py scripts/benchmark_cluster.py mongo-writes          # write concern: w=1, w=1+journal, majority, all nodes
    py scripts/benchmark_cluster.py mongo-reads           # primary vs secondaryPreferred vs secondary vs nearest
    py scripts/benchmark_cluster.py staleness             # how often a secondary read misses a fresh write
    py scripts/benchmark_cluster.py redis                 # plain vs WAIT writes, master vs replica reads, Redis vs Mongo
    py scripts/benchmark_cluster.py mongo-failover        # step the primary down while writing and reading
    py scripts/benchmark_cluster.py redis-failover        # Sentinel failover while writing, then count lost writes
    py scripts/benchmark_cluster.py all                   # everything except the two failover tests
    py scripts/benchmark_cluster.py all --out docs/perf-results.json

Settings come from .env (MONGO_URI, REDIS_SENTINELS / REDIS_URL). Use the replica-set URI on the cluster:
MONGO_URI=mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0. Everything is written to the scratch
database `medsignal_bench` and to Redis keys `bench:*`, both removed at the end (--keep leaves them); the real
database is never touched. The results feed docs/cap-theorem.md.
"""
import argparse
import asyncio
import itertools
import json
import random
import statistics
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import AsyncMongoClient
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import Nearest, Primary, SecondaryPreferred
from pymongo.read_preferences import Secondary as SecondaryOnly
from pymongo.write_concern import WriteConcern
from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from app.core.config import get_settings

BENCH_DB = "medsignal_bench"
PREFIX = "bench:"
RESULTS: dict = {}


# ---------------------------------------------------------------- measuring

def summarize(latencies: list[float], errors: int, seconds: float, units: int = 1) -> dict:
    """latencies in seconds -> one row of the result tables (milliseconds)."""
    ms = sorted(x * 1000 for x in latencies)

    def pct(p: float) -> float:
        return round(ms[min(len(ms) - 1, int(len(ms) * p))], 2) if ms else 0.0
    return {"ops": len(ms), "errors": errors, "per_sec": round(len(ms) * units / seconds) if seconds else 0,
            "mean_ms": round(statistics.fmean(ms), 2) if ms else 0.0, "p50_ms": pct(0.50), "p95_ms": pct(0.95),
            "p99_ms": pct(0.99)}


async def load(op, total: int, concurrency: int, units: int = 1) -> dict:
    """Runs `op(i)` `total` times with `concurrency` in flight and times each call."""
    latencies: list[float] = []
    errors = 0
    counter = iter(range(total))

    async def worker():
        nonlocal errors
        for i in counter:
            t = time.perf_counter()
            try:
                await op(i)
                latencies.append(time.perf_counter() - t)
            except Exception:
                errors += 1

    start = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    return summarize(latencies, errors, time.perf_counter() - start, units)


def table(title: str, rows: dict[str, dict]) -> None:
    print(f"\n{title}")
    head = f"{'':30s} {'ops/s':>8s} {'mean':>8s} {'p50':>8s} {'p95':>8s} {'p99':>8s} {'errors':>7s}   (ms)"
    print(head + "\n" + "-" * len(head))
    for name, r in rows.items():
        print(f"{name:30s} {r['per_sec']:>8d} {r['mean_ms']:>8.2f} {r['p50_ms']:>8.2f} {r['p95_ms']:>8.2f} "
              f"{r['p99_ms']:>8.2f} {r['errors']:>7d}")


def doc(i: int, quarter: str = "2026Q1") -> dict:
    return {"_id": f"d{i}", "quarter": quarter, "ingredient_rxcui": str(i % 200), "reaction_term": f"R{i % 50}",
            "prr": random.random() * 10, "a": i % 40, "is_signal": i % 3 == 0, "note": "x" * 200}


# ---------------------------------------------------------------- MongoDB

def mongo_client(settings, **kw) -> AsyncMongoClient:
    return AsyncMongoClient(settings.mongo_uri, serverSelectionTimeoutMS=kw.pop("select_ms", 5000), **kw)


async def topology(client: AsyncMongoClient) -> str:
    hello = await client.admin.command("hello")
    members = hello.get("hosts", [])
    return (f"primary={hello.get('primary', hello.get('me'))}, members={len(members) or 1}"
            f"{'' if members else ' (standalone: replica tests are meaningless)'}")


async def mongo_writes(settings, args) -> None:
    client = mongo_client(settings)
    print("MongoDB", await topology(client))
    db = client[BENCH_DB]
    concerns = {"w=1": WriteConcern(w=1), "w=1, journal": WriteConcern(w=1, j=True),
                "w=majority": WriteConcern(w="majority"), "w=3 (all nodes)": WriteConcern(w=3)}
    single, bulk = {}, {}
    for name, wc in concerns.items():
        col = db.get_collection("writes", write_concern=wc)
        try:
            single[name] = await load(lambda i, c=col: c.insert_one({"_id": uuid.uuid4().hex, "n": i, "x": "x" * 200}),
                                      args.ops, args.concurrency)
            bulk[name] = await load(lambda i, c=col: c.insert_many(
                [{"_id": uuid.uuid4().hex, "n": j, "x": "x" * 200} for j in range(100)], ordered=False),
                args.ops // 20, max(1, args.concurrency // 4), units=100)
        except Exception as exc:                       # w=3 with a node down: report, keep going
            single[name] = bulk[name] = summarize([], args.ops, 1)
            print(f"  {name}: {type(exc).__name__}: {exc}")
    table(f"MongoDB insert_one ({args.ops} writes, {args.concurrency} in flight)", single)
    table("MongoDB insert_many of 100 documents (ops/s = documents/s)", bulk)
    RESULTS["mongo_writes"] = {"insert_one": single, "insert_many_100": bulk}
    await cleanup_mongo(client, args)


async def seed_reads(client, n: int) -> None:
    col = client[BENCH_DB].get_collection("reads", write_concern=WriteConcern(w="majority"))
    await col.drop()
    for start in range(0, n, 5000):
        await col.insert_many([doc(i) for i in range(start, min(n, start + 5000))], ordered=False)
    # commitQuorum="majority": the default waits for ALL voting members, so one node down would block the build forever
    await client[BENCH_DB].command({"createIndexes": "reads", "commitQuorum": "majority", "indexes": [
        {"key": {"quarter": 1, "is_signal": 1, "prr": -1}, "name": "explorer"},
        {"key": {"ingredient_rxcui": 1, "quarter": 1}, "name": "drug_quarter"}]})


async def mongo_reads(settings, args) -> None:
    client = mongo_client(settings)
    print("MongoDB", await topology(client))
    await seed_reads(client, args.docs)
    prefs = {"primary": Primary(), "secondaryPreferred": SecondaryPreferred(), "secondary": SecondaryOnly(),
             "nearest": Nearest()}
    out: dict[str, dict] = {}
    served: dict[str, Counter] = {}
    for name, pref in prefs.items():
        col = client[BENCH_DB].get_collection("reads", read_preference=pref)
        where: Counter = Counter()

        async def point(i, col=col, where=where):
            cur = col.find({"_id": f"d{random.randrange(args.docs)}"}).limit(1)
            await cur.to_list(1)
            where[str(cur.address)] += 1

        async def explorer(i, col=col):                  # signal explorer: top 20 by PRR in a quarter
            await col.find({"quarter": "2026Q1", "is_signal": True}).sort("prr", -1).limit(20).to_list(20)

        async def aggregate(i, col=col):                 # statistics: group a drug's documents
            await (await col.aggregate([{"$match": {"ingredient_rxcui": str(i % 200)}},
                                        {"$group": {"_id": "$reaction_term", "n": {"$sum": 1}, "prr": {"$avg": "$prr"}}},
                                        {"$sort": {"n": -1}}, {"$limit": 10}])).to_list(10)
        try:
            out[f"{name}: point lookup"] = await load(point, args.ops, args.concurrency)
            out[f"{name}: signal explorer"] = await load(explorer, args.ops, args.concurrency)
            out[f"{name}: statistics aggregation"] = await load(aggregate, args.ops // 2, args.concurrency)
        except Exception as exc:
            print(f"  {name}: {type(exc).__name__}: {exc}")
        served[name] = where
    table(f"MongoDB reads by read preference ({args.docs} documents, {args.concurrency} in flight)", out)
    print("\nNode that served the point lookups:")
    for name, where in served.items():
        print(f"  {name:20s} " + ", ".join(f"{a} x{n}" for a, n in sorted(where.items())))
    RESULTS["mongo_reads"] = {"latency": out, "served_by": {k: dict(v) for k, v in served.items()}}
    await cleanup_mongo(client, args)


async def staleness(settings, args) -> None:
    """Write one document, read it at once from a secondary: the share of reads that miss it is the eventual-consistency
    window made visible. Same read with a causally consistent session = read-your-writes guaranteed."""
    client = mongo_client(settings)
    print("MongoDB", await topology(client))
    db = client[BENCH_DB]
    trials = args.trials
    rows = {}

    async def run(label, wc, read_concern=None, session=False):
        w_col = db.get_collection("fresh", write_concern=wc)
        r_col = db.get_collection("fresh", read_preference=SecondaryOnly(), read_concern=read_concern or ReadConcern())
        misses, delays = 0, []
        for _ in range(trials):
            key = uuid.uuid4().hex
            if session:
                async with client.start_session(causal_consistency=True) as s:
                    await w_col.insert_one({"_id": key}, session=s)
                    found = await r_col.find_one({"_id": key}, session=s)
            else:
                await w_col.insert_one({"_id": key})
                found = await r_col.find_one({"_id": key})
            if found is None:
                misses += 1
                t = time.perf_counter()
                while await r_col.find_one({"_id": key}) is None and time.perf_counter() - t < 5:
                    await asyncio.sleep(0.001)
                delays.append((time.perf_counter() - t) * 1000)
        rows[label] = {"trials": trials, "stale_reads": misses, "stale_pct": round(100 * misses / trials, 1),
                       "catch_up_ms_mean": round(statistics.fmean(delays), 1) if delays else 0.0,
                       "catch_up_ms_max": round(max(delays), 1) if delays else 0.0}

    await run("write w=1, read secondary", WriteConcern(w=1))
    await run("write majority, read secondary", WriteConcern(w="majority"))
    await run("write majority, majority read", WriteConcern(w="majority"), ReadConcern("majority"))
    await run("causal session (read-your-writes)", WriteConcern(w="majority"), session=True)
    print(f"\n{'':40s} {'stale':>8s} {'stale %':>8s} {'catch-up mean ms':>17s} {'max ms':>8s}")
    for name, r in rows.items():
        print(f"{name:40s} {r['stale_reads']:>8d} {r['stale_pct']:>8.1f} {r['catch_up_ms_mean']:>17.1f} "
              f"{r['catch_up_ms_max']:>8.1f}")
    RESULTS["staleness"] = rows
    await cleanup_mongo(client, args)


async def cleanup_mongo(client, args) -> None:
    if not args.keep:
        await client.drop_database(BENCH_DB)


# ---------------------------------------------------------------- Redis

def redis_clients(settings):
    """(master, replica or None, sentinel or None). Replica reads need Sentinel. RESP2 is forced: the benchmark needs
    no RESP3 feature and it also runs against old Redis builds."""
    if settings.redis_sentinels:
        nodes = [(h.split(":")[0], int(h.split(":")[1])) for h in settings.redis_sentinels.split(",")]
        s = Sentinel(nodes, socket_timeout=1.0, decode_responses=True, protocol=2, sentinel_kwargs={"protocol": 2})
        return s.master_for(settings.redis_master_name), s.slave_for(settings.redis_master_name), s
    return Redis.from_url(settings.redis_url, decode_responses=True, protocol=2), None, None


async def wait_replicas(r: Redis, n: int, timeout_ms: int = 200) -> int:
    return await r.execute_command("WAIT", n, timeout_ms)


async def clean_redis(r: Redis) -> None:
    keys = [k async for k in r.scan_iter(match=f"{PREFIX}*", count=1000)]
    for i in range(0, len(keys), 1000):
        await r.delete(*keys[i:i + 1000])


async def redis_bench(settings, args) -> None:
    master, replica, _ = redis_clients(settings)
    info = await master.info("replication")
    print(f"Redis role={info.get('role')}, replicas={info.get('connected_slaves', 0)}"
          f"{'' if replica else ' (no Sentinel configured: replica reads skipped)'}")
    payload = json.dumps(doc(1))
    writes: dict[str, dict] = {}
    unreplicated: dict[str, int] = {}
    writes["SET (async replication)"] = await load(lambda i: master.set(f"{PREFIX}w:{i}", payload), args.ops,
                                                   args.concurrency)
    for n in (1, 2):
        lost = 0

        async def set_wait(i, n=n):
            nonlocal lost
            await master.set(f"{PREFIX}w{n}:{i}", payload)
            if await wait_replicas(master, n) < n:
                lost += 1                                      # acknowledged, but fewer replicas have it than asked
        writes[f"SET + WAIT {n} replica(s)"] = await load(set_wait, args.ops, args.concurrency)
        unreplicated[f"WAIT {n}"] = lost

    async def follow(i):                                       # what the app does on "follow": a MULTI/EXEC of 2 SADD
        async with master.pipeline(transaction=True) as p:
            p.sadd(f"{PREFIX}follows:{i % 500}", str(i))
            p.sadd(f"{PREFIX}followers:{i % 200}", str(i))
            await p.execute()
    writes["follow() MULTI/EXEC"] = await load(follow, args.ops, args.concurrency)
    table(f"Redis writes ({args.ops} writes, {args.concurrency} in flight)", writes)
    print("  WAIT calls that returned fewer acknowledgements than requested:", unreplicated)

    print("  seeding keys ...", flush=True)
    async with master.pipeline(transaction=False) as p:
        for i in range(args.docs):
            p.set(f"{PREFIX}kv:{i}", json.dumps(doc(i)))
        await p.execute()
    await wait_replicas(master, 2, 2000)
    print("  reading ...", flush=True)
    reads: dict[str, dict] = {}
    reads["Redis GET, master"] = await load(lambda i: master.get(f"{PREFIX}kv:{random.randrange(args.docs)}"), args.ops,
                                            args.concurrency)
    if replica:
        reads["Redis GET, replica"] = await load(lambda i: replica.get(f"{PREFIX}kv:{random.randrange(args.docs)}"),
                                                 args.ops, args.concurrency)
    reads["Redis SISMEMBER (is_following)"] = await load(
        lambda i: master.sismember(f"{PREFIX}follows:{i % 500}", str(i)), args.ops, args.concurrency)
    try:
        client = mongo_client(settings, select_ms=2000)
        await client.admin.command("ping")
        await seed_reads(client, args.docs)
        col = client[BENCH_DB]["reads"]
        reads["MongoDB find_one by _id, primary"] = await load(
            lambda i: col.find_one({"_id": f"d{random.randrange(args.docs)}"}), args.ops, args.concurrency)
        await cleanup_mongo(client, args)
    except Exception as exc:
        print(f"  MongoDB comparison skipped: {type(exc).__name__}")
    table(f"Redis reads vs MongoDB ({args.docs} keys / documents of ~300 bytes)", reads)
    RESULTS["redis"] = {"writes": writes, "unreplicated_after_wait": unreplicated, "reads": reads}
    if not args.keep:
        await clean_redis(master)


# ---------------------------------------------------------------- failover

def gaps(times: list[float]) -> tuple[float, float]:
    """(longest pause between two successful operations in seconds, when it ended): the unavailability window seen by
    the client and the moment service came back."""
    best = max(itertools.pairwise(times), key=lambda ab: ab[1] - ab[0], default=(0.0, 0.0))
    return round(best[1] - best[0], 2), best[1]


async def mongo_failover(settings, args) -> None:
    client = mongo_client(settings, select_ms=args.select_ms)
    print("MongoDB", await topology(client))
    col = client[BENCH_DB].get_collection("failover", write_concern=WriteConcern(w=args.w))
    reader = client[BENCH_DB].get_collection("failover", read_preference=SecondaryPreferred())
    acked: list[int] = []
    ack_times, read_times = [], []
    write_errors = read_errors = 0
    stop = asyncio.Event()
    t0 = time.perf_counter()

    async def writer():
        nonlocal write_errors
        i = 0
        while not stop.is_set():
            i += 1
            try:
                await col.insert_one({"_id": i})
                acked.append(i)
                ack_times.append(time.perf_counter() - t0)
            except Exception:
                write_errors += 1
            await asyncio.sleep(0.005)

    async def read_loop():
        nonlocal read_errors
        while not stop.is_set():
            try:
                await reader.count_documents({})
                read_times.append(time.perf_counter() - t0)
            except Exception:
                read_errors += 1
            await asyncio.sleep(0.02)

    tasks = [asyncio.create_task(writer()), asyncio.create_task(read_loop())]
    await asyncio.sleep(args.before)
    fail_at = time.perf_counter() - t0
    if args.manual:
        print(f"\n>>> t={fail_at:.1f}s: stop the primary now (docker stop mongo1). Waiting {args.after}s ...")
    else:
        print(f"\n>>> t={fail_at:.1f}s: replSetStepDown on the primary")
        try:
            await client.admin.command("replSetStepDown", 30, force=True)
        except Exception:
            pass                                                # the connection closes on step-down: expected
    await asyncio.sleep(args.after)
    stop.set()
    await asyncio.gather(*tasks)
    verify = client[BENCH_DB].get_collection("failover", read_preference=Primary(), read_concern=ReadConcern("majority"))
    present = {d["_id"] async for d in verify.find({}, {"_id": 1})}
    lost = [i for i in acked if i not in present]
    pause, back = gaps(ack_times)
    read_pause, _ = gaps(read_times)
    result = {"write_concern": str(args.w), "acked": len(acked), "write_errors": write_errors,
              "acked_writes_lost": len(lost), "unacked_but_stored": len(present - set(acked)),
              "longest_write_pause_s": pause, "writes_resumed_after_failure_s": round(back - fail_at, 2),
              "secondary_reads_ok": len(read_times), "read_errors": read_errors, "longest_read_pause_s": read_pause}
    print(json.dumps(result, indent=2))
    RESULTS[f"mongo_failover_w{args.w}"] = result
    await cleanup_mongo(client, args)


async def redis_failover(settings, args) -> None:
    master, _, sentinel = redis_clients(settings)
    if sentinel is None:
        sys.exit("redis-failover needs REDIS_SENTINELS (the Sentinel deployment).")
    await clean_redis(master)
    acked: list[int] = []
    ack_times: list[float] = []
    errors = 0
    stop = asyncio.Event()
    t0 = time.perf_counter()
    counter = iter(range(1, 10**9))

    async def writer():
        nonlocal errors
        while not stop.is_set():
            i = next(counter)
            try:
                await master.set(f"{PREFIX}fo:{i}", i)
                if args.wait:
                    await wait_replicas(master, args.wait)
                acked.append(i)
                ack_times.append(time.perf_counter() - t0)
            except Exception:
                errors += 1
                await asyncio.sleep(0.05)

    tasks = [asyncio.create_task(writer()) for _ in range(args.concurrency)]
    await asyncio.sleep(args.before)
    fail_at = time.perf_counter() - t0
    if args.manual:
        print(f"\n>>> t={fail_at:.1f}s: stop or pause the primary now (docker pause redis-primary). Waiting {args.after}s ...")
    else:
        print(f"\n>>> t={fail_at:.1f}s: SENTINEL FAILOVER {settings.redis_master_name}")
        sentinel_conn = sentinel.sentinels[0]
        await sentinel_conn.execute_command("SENTINEL", "FAILOVER", settings.redis_master_name)
    await asyncio.sleep(args.after)
    stop.set()
    await asyncio.gather(*tasks)
    new_master, _, _ = redis_clients(settings)
    lost = 0
    for i in range(0, len(acked), 1000):
        batch = acked[i:i + 1000]
        values = await new_master.mget([f"{PREFIX}fo:{n}" for n in batch])
        lost += sum(v is None for v in values)
    pause, back = gaps(sorted(ack_times))
    result = {"wait_replicas": args.wait, "acked": len(acked), "write_errors": errors, "acked_writes_lost": lost,
              "longest_write_pause_s": pause, "writes_resumed_after_failure_s": round(back - fail_at, 2),
              "new_master": str(await sentinel.discover_master(settings.redis_master_name))}
    print(json.dumps(result, indent=2))
    RESULTS[f"redis_failover_wait{args.wait}"] = result
    if not args.keep:
        await clean_redis(new_master)


# ---------------------------------------------------------------- main

SUITES = {"mongo-writes": mongo_writes, "mongo-reads": mongo_reads, "staleness": staleness, "redis": redis_bench,
          "mongo-failover": mongo_failover, "redis-failover": redis_failover}


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("suite", choices=[*SUITES, "all"])
    ap.add_argument("--ops", type=int, default=2000, help="operations per measurement")
    ap.add_argument("--concurrency", type=int, default=16, help="operations in flight")
    ap.add_argument("--docs", type=int, default=20000, help="documents / keys seeded for the read tests")
    ap.add_argument("--trials", type=int, default=300, help="writes in the staleness test")
    ap.add_argument("--before", type=float, default=5, help="failover tests: seconds of writes before the failure")
    ap.add_argument("--after", type=float, default=25, help="failover tests: seconds of writes after the failure")
    ap.add_argument("--manual", action="store_true", help="failover tests: you stop the primary yourself")
    ap.add_argument("--w", default="majority", help="mongo-failover write concern: 'majority' or a number (1)")
    ap.add_argument("--wait", type=int, default=0, help="redis-failover: WAIT for this many replicas after each write")
    ap.add_argument("--select-ms", type=int, default=20000, help="mongo-failover: how long a write waits for a primary")
    ap.add_argument("--keep", action="store_true", help="do not delete the benchmark data")
    ap.add_argument("--out", help="write the results as JSON")
    args = ap.parse_args()
    if args.w != "majority":
        args.w = int(args.w)
    settings = get_settings()
    for name in (["mongo-writes", "mongo-reads", "staleness", "redis"] if args.suite == "all" else [args.suite]):
        print(f"\n===== {name} =====")
        await SUITES[name](settings, args)
    if args.out:
        Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
        print(f"\nResults written to {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
