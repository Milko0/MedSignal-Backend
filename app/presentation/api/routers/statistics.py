from typing import Literal

from fastapi import APIRouter, Depends

from app.application.dtos.signals import Statistics
from app.presentation.api.dependencies import statistics as statistics_uc

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("", response_model=Statistics, summary="Report statistics (FR-08)")
async def statistics(group_by: Literal["age_group", "sex", "country", "seriousness", "report_type", "quarter"],
                     rxcui: str | None = None, quarter: str | None = None, uc=Depends(statistics_uc)):
    return await uc.execute(group_by, rxcui, quarter)
