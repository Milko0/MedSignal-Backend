import json

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.external.file_feeds import FileFeeds
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.openfda_client import OpenFdaFeeds
from app.infrastructure.external.rxnorm_client import RxNavClient
from app.infrastructure.external.rxnorm_normalizer import RxNormNormalizer


async def _nosleep(_):
    return None


def fetcher(handler):
    return HttpFetcher(requests_per_second=0, max_retries=3, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
                       sleep=_nosleep)


async def test_retries_on_429_and_5xx_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        if calls["n"] == 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    assert await fetcher(handler).get_json("https://x/y") == {"ok": True} and calls["n"] == 3


async def test_404_is_none_only_when_allowed_and_errors_raise():
    f = fetcher(lambda r: httpx.Response(404, json={"error": {"code": "NOT_FOUND"}}))
    assert await f.get_json("https://x", allow_404=True) is None
    with pytest.raises(httpx.HTTPStatusError):
        await f.get_json("https://x")
    with pytest.raises(httpx.HTTPStatusError):
        await fetcher(lambda r: httpx.Response(400)).get_json("https://x")


async def test_openfda_paging_stops_at_short_page_and_sends_key():
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        skip = int(request.url.params["skip"])
        n = 1000 if skip == 0 else 7
        return httpx.Response(200, json={"results": [{"i": skip + k} for k in range(n)]})

    s = Settings(openfda_api_key="KEY")
    feeds = OpenFdaFeeds(s, fetcher(handler))
    got = [r async for r in feeds.fetch_shortages()]
    assert len(got) == 1007 and seen[0]["api_key"] == "KEY" and seen[1]["skip"] == "1000"
    limited = [r async for r in feeds.fetch_products(limit=5)]
    assert len(limited) == 5 and seen[-1]["limit"] == "5"


async def test_rxnorm_normalizer_reads_real_shapes_and_caches(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        path = request.url.path
        if path.endswith("/properties.json"):
            rx = path.split("/")[-2]
            return httpx.Response(200, json={"properties": {"rxcui": rx, "name": "x", "tty": "IN" if rx == "5640" else "SCD"}})
        if path.endswith("/related.json"):
            return httpx.Response(200, json={"relatedGroup": {"rxcui": None, "conceptGroup": [
                {"tty": "IN", "conceptProperties": [{"rxcui": "5640", "name": "ibuprofen"}]}]}})
        if path.endswith("/rxcui.json"):
            return httpx.Response(200, json={"idGroup": {}})
        if path.endswith("/approximateTerm.json"):
            return httpx.Response(200, json={"approximateGroup": {"inputTerm": None, "candidate": [
                {"rxcui": "9", "score": "11.5", "source": "RXNORM", "name": "y"}]}})
        return httpx.Response(200, json={})

    n = RxNormNormalizer(RxNavClient(Settings(), fetcher(handler)), str(tmp_path))
    assert (await n.concept("5640")).ingredient_rxcuis == ["5640"]                  # an ingredient maps to itself
    assert (await n.concept("197805")).ingredient_rxcuis == ["5640"]
    assert await n.exact("nothing") == [] and (await n.approximate("whatever"))[0].score == 11.5
    first = calls["n"]
    await n.concept("197805")
    await n.exact("nothing")
    assert calls["n"] == first                                                       # served from the disk cache


async def test_file_feeds_formats(tmp_path):
    (tmp_path / "shortages.json").write_text(json.dumps({"meta": {}, "results": [{"a": 1}, {"a": 2}]}))
    (tmp_path / "ndc.jsonl").write_text('{"b": 1}\n{"b": 2}\n{"b": 3}\n')
    feeds = FileFeeds(str(tmp_path))
    assert [r async for r in feeds.fetch_shortages()] == [{"a": 1}, {"a": 2}]
    assert len([r async for r in feeds.fetch_products(limit=2)]) == 2
    assert [r async for r in feeds.fetch_labels()] == []                              # missing file: empty, not an error
    import zipfile
    with zipfile.ZipFile(tmp_path / "part.zip", "w") as z:
        z.writestr("event-0001.json", json.dumps({"results": [{"safetyreportid": "1"}]}))
    assert [r async for r in feeds.read_bulk_file(str(tmp_path / "part.zip"))] == [{"safetyreportid": "1"}]
    (tmp_path / "list.json").write_text('  [{"x": 1.5}, {"x": 2}]')                 # top-level array, streamed
    assert [r async for r in feeds.read_bulk_file(str(tmp_path / "list.json"))] == [{"x": 1.5}, {"x": 2}]
