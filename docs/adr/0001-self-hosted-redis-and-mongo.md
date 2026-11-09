# ADR 0001: self-hosted MongoDB and Redis instead of managed services

Status: accepted.

The project brief requires deployment on a local cluster and on the UNIPI Virtual Lab with 3 Document DB replicas and 3 KV replicas.
A managed Redis (Upstash) or Atlas cluster cannot be deployed there. Decision: MongoDB and Redis run in Docker locally
and on the lab VMs. The ports (`application/ports`) keep the adapters swappable.

Consequences: Redis uses AOF persistence and Sentinel; the team owns failover tests (useful for the CAP section).
