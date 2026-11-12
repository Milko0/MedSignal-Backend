from fastapi import APIRouter, Depends, Path, Query

from app.application.dtos.common import DisclaimedResponse, PageRequest, disclaimed
from app.application.dtos.signals import SignalList, SignalReports
from app.presentation.api.dependencies import (
    emerging_signals,
    list_signals,
    pagination,
    signal_reports,
)
from app.presentation.api.responses import QUARTER_EXAMPLE, RXCUI_EXAMPLES

router = APIRouter(prefix="/signals", tags=["Signals"])

QUARTER = Query(None, description="Calendar quarter of the receive date, `YYYYQn`. Default: the latest quarter.",
                openapi_examples=QUARTER_EXAMPLE)


@router.get("", response_model=DisclaimedResponse[SignalList],
            summary="Signal explorer: PRR, CI lower bound, chi-square (FR-04, FR-05)",
            description="Precomputed disproportionality per (ingredient, reaction, quarter) with the 2x2 counts "
                        "`a b c d`. **Signal** = Evans criteria (PRR >= 2, chi-square >= 4, a >= 3). Sorted by PRR. "
                        "`only_signals=false` also lists pairs below the threshold. `trend` holds the PRR of the "
                        "previous quarters. Paginated.")
async def signals(quarter: str | None = QUARTER,
                  rxcui: str | None = Query(None, description="Only this ingredient", openapi_examples=RXCUI_EXAMPLES),
                  reaction: str | None = Query(None, description="MedDRA preferred term, any case",
                                               examples=["RHABDOMYOLYSIS"]),
                  min_reports: int = Query(20, ge=1, description="Minimum `a` (reports with drug and reaction)"),
                  only_signals: bool = True, page: PageRequest = Depends(pagination), uc=Depends(list_signals)):
    return disclaimed(await uc.execute(quarter, rxcui, reaction, min_reports, only_signals, page))


@router.get("/emerging", response_model=DisclaimedResponse[SignalList], summary="Emerging signals (FR-06)",
            description="Signals of the quarter whose PRR is at least 1.5 x the average PRR of the previous quarters "
                        "for the same pair. The oldest quarter in the window has no history, so none there. Paginated.")
async def emerging(quarter: str | None = QUARTER, min_reports: int = Query(3, ge=1),
                   page: PageRequest = Depends(pagination), uc=Depends(emerging_signals)):
    return disclaimed(await uc.execute(quarter, min_reports, page))


@router.get("/{rxcui}/{reaction}/reports", response_model=SignalReports, summary="Reports behind a signal (FR-09)",
            description="The individual FAERS reports where the ingredient is suspect and the reaction was reported, "
                        "newest first. Paginated.")
async def reports(rxcui: str = Path(openapi_examples=RXCUI_EXAMPLES),
                  reaction: str = Path(description="MedDRA preferred term, any case", examples=["VOMITING"]),
                  page: PageRequest = Depends(pagination), uc=Depends(signal_reports)):
    return await uc.execute(rxcui, reaction, page)
