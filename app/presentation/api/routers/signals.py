from fastapi import APIRouter, Depends, Query

from app.application.dtos.common import DisclaimedResponse, disclaimed
from app.application.dtos.signals import SignalList, SignalReports
from app.presentation.api.dependencies import (
    emerging_signals,
    list_signals,
    signal_reports,
)

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("", response_model=DisclaimedResponse[SignalList],
            summary="Signal explorer: PRR, CI lower bound, chi-square (FR-04, FR-05)")
async def signals(quarter: str | None = Query(None, examples=["2026Q3"]), rxcui: str | None = None,
                  reaction: str | None = None, min_reports: int = Query(20, ge=1), only_signals: bool = True,
                  skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), uc=Depends(list_signals)):
    return disclaimed(await uc.execute(quarter, rxcui, reaction, min_reports, only_signals, skip, limit))


@router.get("/emerging", response_model=DisclaimedResponse[SignalList], summary="Emerging signals (FR-06)")
async def emerging(quarter: str | None = Query(None, examples=["2026Q3"]), min_reports: int = Query(3, ge=1),
                   uc=Depends(emerging_signals)):
    return disclaimed(await uc.execute(quarter, min_reports))


@router.get("/{rxcui}/{reaction}/reports", response_model=SignalReports, summary="Reports behind a signal (FR-09)")
async def reports(rxcui: str, reaction: str, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                  uc=Depends(signal_reports)):
    return await uc.execute(rxcui, reaction, skip, limit)
