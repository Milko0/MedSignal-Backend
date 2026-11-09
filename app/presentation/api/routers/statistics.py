from fastapi import APIRouter

from app.application.dtos.signals import StatisticsResponse
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("", response_model=StatisticsResponse, summary="Reports by age group, sex, country, seriousness over time (FR-08)")
async def statistics(rxcui: str | None = None, drug_class: str | None = None, quarter: str | None = None):
    not_implemented("Statistics")
