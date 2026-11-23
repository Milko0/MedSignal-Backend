"""FR-23: administrator CRUD on drug labels (one document per set id)."""
from app.application.ports.label_repository import LabelRepository
from app.domain.entities.label import DrugLabel
from app.domain.exceptions import AlreadyExistsError, NotFoundError, ValidationRuleError


class CrudLabels:
    def __init__(self, labels: LabelRepository) -> None:
        self.labels = labels

    async def list(self, skip: int, limit: int) -> list[DrugLabel]:
        return await self.labels.list(skip, limit)

    async def get(self, set_id: str) -> DrugLabel:
        label = await self.labels.get(set_id.lower())
        if label is None:
            raise NotFoundError(f"Label {set_id} not found")
        return label

    async def create(self, label: DrugLabel) -> DrugLabel:
        label = label.model_copy(update={"set_id": label.set_id.lower()})
        if await self.labels.get(label.set_id) is not None:
            raise AlreadyExistsError(f"Label {label.set_id} already exists")
        await self.labels.upsert_many([label])
        return label

    async def update(self, set_id: str, label: DrugLabel) -> DrugLabel:
        if label.set_id.lower() != set_id.lower():
            raise ValidationRuleError("The set_id in the body must match the URL")
        await self.get(set_id)
        label = label.model_copy(update={"set_id": set_id.lower()})
        await self.labels.upsert_many([label])
        return label

    async def delete(self, set_id: str) -> None:
        if not await self.labels.delete(set_id.lower()):
            raise NotFoundError(f"Label {set_id} not found")
