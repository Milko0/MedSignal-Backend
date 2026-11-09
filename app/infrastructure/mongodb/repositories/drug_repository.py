"""MongoDB adapter for the drugs collection. TODO: implement the methods."""
from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.drug_repository import DrugRepository


class MongoDrugRepository(DrugRepository):
    def __init__(self, db):
        self._col = db['drugs']

    async def get(self, rxcui: str) -> dict | None:
        raise NotImplementedError

    async def search(self, text: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError

    async def class_members(self, class_id: str, route: str | None, dosage_form: str | None) -> list[dict]:
        raise NotImplementedError

