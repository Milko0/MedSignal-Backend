"""The ONLY place where Redis key strings are built.

shortage:{rxcui}                      HASH   live shortage status
follows:{userId}                      SET    drugs followed by a user
followers:{rxcui}                     SET    users following a drug (reverse index)
alert:{userId}:{eventId}              HASH   one alert, TTL 30 days
alerts:{userId}                       ZSET   alert ids scored by timestamp
count:{rxcui}:{reaction}:{quarter}    STRING live counter, SET by recomputation (idempotent)
"""


def shortage(rxcui: str) -> str:
    return f"shortage:{rxcui}"


def follows(user_id: str) -> str:
    return f"follows:{user_id}"


def followers(rxcui: str) -> str:
    return f"followers:{rxcui}"


def alert(user_id: str, event_id: str) -> str:
    return f"alert:{user_id}:{event_id}"


def alert_index(user_id: str) -> str:
    return f"alerts:{user_id}"


def counter(rxcui: str, reaction: str, quarter: str) -> str:
    return f"count:{rxcui}:{reaction}:{quarter}"
