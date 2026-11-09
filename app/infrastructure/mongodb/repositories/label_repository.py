"""MongoDB adapter for the labels collection. TODO: implement the methods."""
from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.label_repository import LabelRepository


class MongoLabelRepository(LabelRepository):
    def __init__(self, db):
        self._col = db['labels']

    async def upsert(self, label: dict) -> None:
        raise NotImplementedError

    async def summary_for_drug(self, rxcui: str) -> dict | None:
        raise NotImplementedError

    async def adverse_text_for_drug(self, rxcui: str) -> str:
        raise NotImplementedError

    async def history(self, set_id: str) -> list[dict]:
        raise NotImplementedError

