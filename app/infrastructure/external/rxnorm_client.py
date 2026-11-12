"""RxNav REST: thin raw client. Endpoints used here were exercised by the schema profiler run of 10 Nov 2026."""
import urllib.parse

from app.core.config import Settings
from app.infrastructure.external.http import HttpFetcher


class RxNavClient:
    def __init__(self, settings: Settings, http: HttpFetcher) -> None:
        self.base, self.http = settings.rxnorm_base_url, http

    async def properties(self, rxcui: str) -> dict:
        return await self.http.get_json(f"{self.base}/rxcui/{rxcui}/properties.json", allow_404=True) or {}

    async def related(self, rxcui: str, tty: str = "IN") -> dict:
        return await self.http.get_json(f"{self.base}/rxcui/{rxcui}/related.json", {"tty": tty}, allow_404=True) or {}

    async def rxcui_by_name(self, name: str) -> dict:
        return await self.http.get_json(f"{self.base}/rxcui.json", {"name": name}, allow_404=True) or {}

    async def approximate(self, term: str, max_entries: int = 5) -> dict:
        return await self.http.get_json(f"{self.base}/approximateTerm.json", {"term": term, "maxEntries": max_entries},
                                        allow_404=True) or {}

    async def atc(self, rxcui: str) -> dict:
        return await self.http.get_json(f"{self.base}/rxclass/class/byRxcui.json", {"rxcui": rxcui, "relaSource": "ATC"},
                                        allow_404=True) or {}

    async def ndcs(self, rxcui: str) -> dict:
        return await self.http.get_json(f"{self.base}/rxcui/{rxcui}/ndcs.json", allow_404=True) or {}

    async def rxcui_by_unii(self, unii: str) -> dict:
        """UNVERIFIED route (open question 2 of the plan): test it before relying on it."""
        return await self.http.get_json(f"{self.base}/rxcui.json", {"idtype": "UNII", "id": urllib.parse.quote(unii)},
                                        allow_404=True) or {}
