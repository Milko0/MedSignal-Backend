"""Shortages (/drug/shortages.json), recalls (/drug/enforcement.json), labels (/drug/label.json), NDC (/drug/ndc.json), bulk manifest (/download.json). Spaces in queries are '+'. Page of 1000 events takes ~80 s: use bulk files for the load."""
import httpx

BASE_URL = "https://api.fda.gov"


class OpenFdaClient:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._http = client or httpx.AsyncClient(base_url=BASE_URL, timeout=60)

    async def aclose(self) -> None:
        await self._http.aclose()

    # TODO: implement methods (retries, rate limiting, error mapping)
