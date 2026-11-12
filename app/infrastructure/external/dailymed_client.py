"""DailyMed web services (history, packaging). Label TEXT comes from openFDA; DailyMed only adds version history."""
from app.core.config import Settings
from app.infrastructure.external.http import HttpFetcher


class DailyMedClient:
    def __init__(self, settings: Settings, http: HttpFetcher) -> None:
        self.base, self.http = settings.dailymed_base_url, http

    async def history(self, set_id: str) -> dict:
        return await self.http.get_json(f"{self.base}/spls/{set_id}/history.json", allow_404=True) or {}

    async def packaging(self, set_id: str) -> dict:
        return await self.http.get_json(f"{self.base}/spls/{set_id}/packaging.json", allow_404=True) or {}
