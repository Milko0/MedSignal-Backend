"""Feeds that read raw exports from disk (openFDA bulk partitions, saved API pages). Same dictionaries as the API."""
import io
import json
import zipfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import IO

import ijson

from app.application.ports.external_data_source import (
    LabelFeed,
    NdcFeed,
    RecallFeed,
    ReportFeed,
    ShortageFeed,
)


def _records(path: Path) -> Iterator[dict]:
    """.json ({"results": [...]} or a list), .jsonl, or a .zip with one of those inside.

    Streams record by record (ijson), so memory stays flat even for a ~1 GB FAERS partition.
    """
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith((".json", ".jsonl")):
                    with z.open(name) as f:
                        yield from _parse(f, name)
        return
    with path.open("rb") as f:
        yield from _parse(f, path.name)


def _parse(f: IO[bytes], name: str) -> Iterator[dict]:
    if name.endswith(".jsonl"):
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            if line.strip():
                yield json.loads(line)
        return
    stream = io.BufferedReader(f) if not isinstance(f, io.BufferedReader) else f
    head = stream.peek(64).lstrip()
    prefix = "item" if head.startswith(b"[") else "results.item"
    yield from ijson.items(stream, prefix, use_float=True)


class FileFeeds(ShortageFeed, NdcFeed, LabelFeed, RecallFeed, ReportFeed):
    """Layout: raw_dir/{shortages,ndc,labels,recalls}.json(l) and any FAERS paths given explicitly."""

    def __init__(self, raw_dir: str) -> None:
        self.dir = Path(raw_dir)

    def _find(self, stem: str) -> Path | None:
        return next((p for ext in (".json", ".jsonl", ".zip") if (p := self.dir / f"{stem}{ext}").exists()), None)

    async def _stream(self, stem: str, limit: int | None = None) -> AsyncIterator[dict]:
        path = self._find(stem)
        if path is None:
            return
        for i, rec in enumerate(_records(path)):
            if limit is not None and i >= limit:
                return
            yield rec

    async def last_updated(self):
        return None

    def fetch_shortages(self):
        return self._stream("shortages")

    def fetch_products(self, limit=None):
        return self._stream("ndc", limit)

    def fetch_labels(self, limit=None):
        return self._stream("labels", limit)

    def fetch_recalls(self, limit=None):
        return self._stream("recalls", limit)

    async def read_bulk_file(self, path: str) -> AsyncIterator[dict]:
        for rec in _records(Path(path)):
            yield rec
