from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.application.dtos.signals import Statistics
from app.presentation.api.dependencies import statistics as statistics_uc
from app.presentation.api.responses import QUARTER_EXAMPLE, RXCUI_EXAMPLES

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("", response_model=Statistics, summary="Report statistics (FR-08)",
            description="Counts of reports grouped by one dimension, for all drugs or one ingredient, for all "
                        "quarters or one. `quarter` gives the series over time (one bucket per quarter, oldest "
                        "first); `age_group` uses the order 0-17, 18-44, 45-64, 65-74, 75+, UNKNOWN; the others are "
                        "sorted by count.")
async def statistics(group_by: Literal["age_group", "sex", "country", "seriousness", "report_type", "quarter"],
                     rxcui: str | None = Query(None, openapi_examples=RXCUI_EXAMPLES),
                     quarter: str | None = Query(None, openapi_examples=QUARTER_EXAMPLE), uc=Depends(statistics_uc)):
    return await uc.execute(group_by, rxcui, quarter)
