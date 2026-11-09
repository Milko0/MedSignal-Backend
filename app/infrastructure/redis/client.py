"""Redis client: single node (local dev) or Sentinel (compose network / Virtual Lab). No managed service needed."""
from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from app.core.config import Settings


def create_redis_client(settings: Settings) -> Redis:
    if settings.redis_sentinels:
        nodes = [(h.split(":")[0], int(h.split(":")[1])) for h in settings.redis_sentinels.split(",")]
        sentinel = Sentinel(nodes, socket_timeout=1.0, decode_responses=True)
        return sentinel.master_for(settings.redis_master_name)
    return Redis.from_url(settings.redis_url, decode_responses=True)
