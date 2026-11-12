from fastapi import APIRouter, Depends

from app.application.dtos.admin import IngestionRunDto
from app.presentation.api.dependencies import ingestion_runs
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/ingestion", tags=["Admin: ingestion"])


@router.post("/faers", summary="Full FAERS load (FR-19)")
async def full_load():
    not_implemented("Run scripts/build_clean_dataset.py (or the worker) for now")


@router.post("/incremental", summary="Incremental update of shortages, labels and recalls (FR-20)")
async def incremental():
    not_implemented("Run the worker for now")


@router.get("/runs", response_model=list[IngestionRunDto], summary="Ingestion logs (FR-21)")
async def runs(skip: int = 0, limit: int = 50, uc=Depends(ingestion_runs)):
    return await uc.execute(skip, limit)
