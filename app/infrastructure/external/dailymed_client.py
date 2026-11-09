"""/spls.json?drug_name=, /spls/{setid}.xml, /spls/{setid}/history.json, /spls/{setid}/ndcs.json."""
import httpx

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


class DailyMedClient:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._http = client or httpx.AsyncClient(base_url=BASE_URL, timeout=60)

    async def aclose(self) -> None:
        await self._http.aclose()

    # TODO: implement methods (retries, rate limiting, error mapping)
