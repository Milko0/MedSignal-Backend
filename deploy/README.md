# deploy

Reproducible deployment (NFR-14).

## Tools used

- Docker Compose
- mongo:7, redis:7
- Nginx (frontend image)

## Rules

- `docker-compose.local.yml`: local cluster (3 Mongo, Redis primary + 2 replicas + 3 Sentinels).
- `virtual-lab/`: UNTESTED template for the 3 VMs of the UNIPI Virtual Lab; check ports and networking with the instructors.
- Host-run API against the local compose: use `MONGO_URI=...?directConnection=true` (members advertise docker hostnames).

## Contents

| Item | Role |
|---|---|
| `docker-compose.local.yml` | Databases; add `--profile app` for api, worker and frontend |
| `mongo/init-replica.sh` | rs.initiate |
| `redis/sentinel.conf` | Sentinel config |
| `virtual-lab/` | Per-VM compose and replica-set init |
