"""One HTTP fetcher for all external APIs: rate limit, retry with backoff, JSON only."""
import asyncio
import time

import httpx


class HttpFetcher:
    def __init__(self, requests_per_second: float = 2.0, max_retries: int = 4, timeout: float = 60.0,
                 client: httpx.AsyncClient | None = None, sleep=asyncio.sleep) -> None:
        self.min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self.max_retries = max_retries
        self.client = client or httpx.AsyncClient(timeout=timeout)
        self._last = 0.0
        self._sleep = sleep

    async def _throttle(self) -> None:
        """Reserves the next free time slot before awaiting, so concurrent callers never share a slot:
        with many requests in flight the rate stays at requests_per_second while network latency overlaps."""
        now = time.monotonic()
        slot = max(now, self._last + self.min_interval)
        self._last = slot
        if slot > now:
            await self._sleep(slot - now)

    async def get_json(self, url: str, params: dict | None = None, allow_404: bool = False) -> dict | list | None:
        """Returns the decoded JSON. 404 returns None when allow_404 (openFDA answers 404 for 'no matches').
        429 and 5xx are retried with exponential backoff; other errors raise."""
        for attempt in range(self.max_retries + 1):
            await self._throttle()
            try:
                resp = await self.client.get(url, params=params)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
                await self._sleep(2 ** attempt)
                continue
            if resp.status_code == 404 and allow_404:
                return None
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    resp.raise_for_status()
                retry_after = resp.headers.get("Retry-After")
                await self._sleep(float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        return None

    async def aclose(self) -> None:
        await self.client.aclose()
