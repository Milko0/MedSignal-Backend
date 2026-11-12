from fastapi import APIRouter, Depends

from app.application.container import Container
from app.presentation.api.dependencies import container

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness and dataset size",
            description="`ok` plus how many ingredients and reports the storage holds (0 means no dataset loaded).",
            responses={200: {"content": {"application/json": {"example": {
                "status": "ok", "ingredients": 2852, "reports": 132804}}}}})
async def health(c: Container = Depends(container)) -> dict:
    return {"status": "ok", "ingredients": await c.ingredients.count(), "reports": await c.reports.count()}
