"""FR-24: administrator CRUD on the current shortage records (one per package NDC).

Every change also refreshes the cached ShortageSummary of the ingredients involved, so the Drug 360 page, the
medicine cabinet and the signal rows show it at once. The daily poll replaces the list with the FDA's again.
"""
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.entities.shortage import ShortageRecord
from app.domain.exceptions import AlreadyExistsError, NotFoundError, ValidationRuleError


class CrudShortages:
    def __init__(self, shortages: ShortageRepository, shortage_status: ShortageStatusStore) -> None:
        self.shortages, self.shortage_status = shortages, shortage_status

    async def _invalidate(self, *records: ShortageRecord | None) -> None:
        for r in records:
            for rxcui in (r.ingredient_rxcuis if r else []):
                await self.shortage_status.delete(rxcui)     # recomputed from the documents on the next read

    async def list(self, skip: int, limit: int) -> list[ShortageRecord]:
        current = await self.shortages.current_by_package()
        return [current[k] for k in sorted(current)][skip:skip + limit]

    async def get(self, package_ndc: str) -> ShortageRecord:
        record = await self.shortages.get(package_ndc)
        if record is None:
            raise NotFoundError(f"Shortage record {package_ndc} not found")
        return record

    async def create(self, record: ShortageRecord) -> ShortageRecord:
        if await self.shortages.get(record.package_ndc) is not None:
            raise AlreadyExistsError(f"Shortage record {record.package_ndc} already exists")
        await self.shortages.upsert(record)
        await self._invalidate(record)
        return record

    async def update(self, package_ndc: str, record: ShortageRecord) -> ShortageRecord:
        if record.package_ndc != package_ndc:
            raise ValidationRuleError("The package_ndc in the body must match the URL")
        old = await self.get(package_ndc)
        await self.shortages.upsert(record)
        await self._invalidate(old, record)
        return record

    async def delete(self, package_ndc: str) -> None:
        old = await self.get(package_ndc)
        await self.shortages.delete(package_ndc)
        await self._invalidate(old)
