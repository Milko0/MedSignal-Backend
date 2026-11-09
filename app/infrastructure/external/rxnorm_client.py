"""/rxcui.json?name=, /approximateTerm.json?term=, /rxcui/{rxcui}/related.json?tty=IN+BN, /rxclass/class/byRxcui.json, /rxclass/classMembers.json. The interaction API was retired in 2024."""
import httpx

BASE_URL = "https://rxnav.nlm.nih.gov/REST"


class RxNormClient:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._http = client or httpx.AsyncClient(base_url=BASE_URL, timeout=60)

    async def aclose(self) -> None:
        await self._http.aclose()

    # TODO: implement methods (retries, rate limiting, error mapping)
