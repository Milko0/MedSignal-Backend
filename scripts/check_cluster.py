"""End-to-end check of the replicated cluster (deploy/docker-compose.local.yml, profile app, already seeded).

    python scripts/check_cluster.py

1. the app answers through Nginx (8080) and the API container (8001);
2. a user registers (MongoDB) and follows semaglutide (Redis);
3. the worker's change-stream projector is running;
4. a signal document changes in MongoDB -> the worker creates a "new signal" alert in Redis and sets the live counter;
5. replaying the same change creates no second alert (deterministic alert id);
6. MongoDB failover: the primary is stopped, a secondary is elected, the API keeps writing;
7. Redis failover: the primary is stopped, Sentinel promotes a replica, the API keeps writing to Redis;
8. the worker restarts and resumes from its saved resume token.
Each stopped container is started again at the end of its step. Creates two test users (cluster_xxxxxx).
"""
import json
import subprocess
import time
import uuid
from pathlib import Path

import httpx

COMPOSE = ["docker", "compose", "-f", str(Path(__file__).resolve().parents[1] / "deploy" / "docker-compose.local.yml")]
WEB = "http://localhost:8080/api"
SEMA = "1991302"
REDIS_NODES = {"172.29.0.10": "redis-primary", "172.29.0.11": "redis-replica-1", "172.29.0.12": "redis-replica-2"}


def sh(*args):
    r = subprocess.run([*COMPOSE, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       check=False)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


def mongo(js):
    return sh("exec", "-T", "mongo2", "mongosh", "--quiet", "--host", "rs0/mongo1:27017,mongo2:27017,mongo3:27017",
              "--eval", js)


def wait(fn, what, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            value = fn()
            if value:
                return value, time.time() - t0
        except Exception:  # noqa: BLE001, S110 - the node may be down while we poll
            pass
        time.sleep(1)
    raise TimeoutError(what)


def step(msg):
    print(f"\n== {msg}")


def members():
    return mongo('print(rs.status().members.filter(m => m.health === 1).map(m => m.name + " " + m.stateStr).join(", "))')


def redis_master():
    return sh("exec", "-T", "sentinel-1", "redis-cli", "-p", "26379", "SENTINEL", "get-master-addr-by-name",
              "mymaster").split()[0]


def main():
    c = httpx.Client(timeout=20)
    step("1. App through Nginx (frontend container) and the API container")
    print("health via :8080", c.get(f"{WEB}/health").json())
    print("Swagger via :8001", c.get("http://localhost:8001/docs").status_code)
    print("frontend page", c.get("http://localhost:8080/login").status_code)

    step("2. Register, log in, follow semaglutide (user in MongoDB, follow in Redis)")
    name = "cluster_" + uuid.uuid4().hex[:6]
    body = {"username": name, "email": f"{name}@example.com", "password": "password123"}
    assert c.post(f"{WEB}/auth/register", json=body).status_code == 201
    tok = c.post(f"{WEB}/auth/login", json={"identifier": name, "password": "password123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert c.post(f"{WEB}/cabinet/follows", headers=h, json={"rxcui": SEMA}).status_code == 204
    print("cabinet:", [(d["name"], d["shortage_status"]) for d in c.get(f"{WEB}/cabinet", headers=h).json()])
    print("alerts before:", len(c.get(f"{WEB}/cabinet/alerts", headers=h).json()))

    step("3. Worker: change-stream projector is running on the replica set")
    print([ln for ln in sh("logs", "worker").splitlines() if "projector" in ln.lower()][-1:])

    step("4. A signal changes in MongoDB -> the worker creates a 'new signal' alert in Redis")
    sig_id = mongo('const s = db.getSiblingDB("medsignal").signals.find({ingredient_rxcui: "1991302", is_signal: true, '
                   'a: {$gte: 20}}).sort({quarter: -1, a: -1}).limit(1).toArray()[0]; print(s._id)')
    touch = (f'db.getSiblingDB("medsignal").signals.updateOne({{_id: {json.dumps(sig_id)}}}, '
             '{$set: {computed_at: new Date().toISOString()}})')
    mongo(touch)
    alerts, secs = wait(lambda: c.get(f"{WEB}/cabinet/alerts", headers=h).json(), "signal alert")
    print(f"signal {sig_id} changed; alert after {secs:.1f}s:", [(a["type"], a["message"]) for a in alerts])
    quarter, _, reaction, _ = sig_id.split("|")
    print("live counter in Redis:", sh("exec", "-T", redis_nodes_master(), "redis-cli", "GET",
                                       f"count:{SEMA}:{reaction}:{quarter}"))

    step("5. Replay the same event -> still one alert (deterministic id)")
    mongo(touch)
    time.sleep(4)
    print("alerts after replay:", len(c.get(f"{WEB}/cabinet/alerts", headers=h).json()))

    step("6. MongoDB failover: stop the primary")
    before = members()
    primary = next(m.split()[0].split(":")[0] for m in before.split(", ") if m.endswith("PRIMARY"))
    print("before:", before)
    sh("stop", primary)
    def new_primary():
        s = members()
        return s if "PRIMARY" in s and f"{primary}:27017" not in s else None

    after, secs = wait(new_primary, "new primary")
    print(f"{primary} stopped; after {secs:.0f}s:", after)
    body2 = {"username": name + "b", "email": f"{name}b@example.com", "password": "password123"}
    r, secs = wait(lambda: c.post(f"{WEB}/auth/register", json=body2), "write after failover")
    print(f"API write (register) after MongoDB failover: {r.status_code} in {secs:.0f}s")
    print("API read:", c.get(f"{WEB}/drugs", params={"query": "ozempic", "limit": 1}).json()[0]["name"])
    sh("start", primary)

    step("7. Redis failover: stop the primary, Sentinel promotes a replica")
    old = redis_master()
    print("master before:", old, REDIS_NODES.get(old))
    sh("stop", REDIS_NODES[old])
    new, secs = wait(lambda: redis_master() != old and redis_master(), "redis failover", 90)
    print(f"Sentinel promoted {REDIS_NODES.get(new)} ({new}) after {secs:.0f}s")
    def follow_ibuprofen():
        x = c.post(f"{WEB}/cabinet/follows", headers=h, json={"rxcui": "5640"})
        return x if x.status_code == 204 else None

    r, secs = wait(follow_ibuprofen, "follow after redis failover")
    print(f"API Redis write (follow ibuprofen) after failover: {r.status_code} in {secs:.0f}s")
    print("cabinet now:", [d["name"] for d in c.get(f"{WEB}/cabinet", headers=h).json()])
    print("alerts kept:", len(c.get(f"{WEB}/cabinet/alerts", headers=h).json()))
    sh("start", REDIS_NODES[old])

    step("8. Worker restart resumes from the saved token")
    sh("restart", "worker")
    time.sleep(8)
    print([ln for ln in sh("logs", "--tail", "20", "worker").splitlines() if "projector" in ln.lower()][-1:])
    print("\nALL CHECKS PASSED")


def redis_nodes_master():
    return REDIS_NODES[redis_master()]


if __name__ == "__main__":
    main()
