"""openFDA feeds. Returns raw dictionaries exactly as the API sends them."""
from collections.abc import AsyncIterator

from app.application.ports.external_data_source import (
    LabelFeed,
    NdcFeed,
    RecallFeed,
    ShortageFeed,
)
from app.core.config import Settings
from app.infrastructure.external.http import HttpFetcher

PAGE_SIZE = 1000  # maximum per request; deep paging is limited, so FAERS comes from bulk files


class OpenFdaFeeds(ShortageFeed, NdcFeed, LabelFeed, RecallFeed):
    def __init__(self, settings: Settings, http: HttpFetcher) -> None:
        self.base, self.key, self.http = settings.openfda_base_url, settings.openfda_api_key, http

    def _params(self, **kw) -> dict:
        p = {k: v for k, v in kw.items() if v is not None}
        if self.key:
            p["api_key"] = self.key
        return p

    async def _pages(self, endpoint: str, limit: int | None, search: str | None = None) -> AsyncIterator[dict]:
        skip, yielded = 0, 0
        while limit is None or yielded < limit:
            size = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - yielded)
            data = await self.http.get_json(f"{self.base}{endpoint}", self._params(limit=size, skip=skip, search=search), allow_404=True)
            results = (data or {}).get("results") or []
            for item in results:
                if limit is not None and yielded >= limit:
                    return  # never yield more than asked, even if the server ignores `limit`
                yield item
                yielded += 1
            if len(results) < size:
                return
            skip += size

    async def last_updated(self) -> str | None:
        data = await self.http.get_json(f"{self.base}/drug/shortages.json", self._params(limit=1))
        return ((data or {}).get("meta") or {}).get("last_updated")

    def fetch_shortages(self) -> AsyncIterator[dict]:
        return self._pages("/drug/shortages.json", None)

    def fetch_products(self, limit: int | None = None) -> AsyncIterator[dict]:
        return self._pages("/drug/ndc.json", limit)

    def fetch_labels(self, limit: int | None = None) -> AsyncIterator[dict]:
        return self._pages("/drug/label.json", limit)

    def fetch_recalls(self, limit: int | None = None) -> AsyncIterator[dict]:
        return self._pages("/drug/enforcement.json", limit)
