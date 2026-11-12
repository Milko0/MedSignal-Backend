from fastapi import APIRouter, Depends

from app.application.container import Container
from app.presentation.api.dependencies import container

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(c: Container = Depends(container)) -> dict:
    return {"status": "ok", "ingredients": await c.ingredients.count(), "reports": await c.reports.count()}
