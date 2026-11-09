from fastapi import APIRouter

from app.application.dtos.admin import FaersLoadRequest, IngestionRunOut
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/ingestion", tags=["Admin - ingestion"])


@router.post("/faers", status_code=202, summary="Full load from FAERS bulk files (FR-19)")
async def load_faers(body: FaersLoadRequest):
    not_implemented("LoadFaersBulk")


@router.post("/incremental", status_code=202, summary="Incremental update of shortages, recalls, labels (FR-20)")
async def incremental():
    not_implemented("UpdateLabelsRecalls")


@router.get("/runs", response_model=list[IngestionRunOut], summary="Ingestion logs (FR-21)")
async def runs(limit: int = 50):
    not_implemented("ListIngestionRuns")
