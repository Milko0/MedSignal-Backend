from fastapi import APIRouter, Query

from app.application.dtos.signals import SignalListResponse, SignalReportsResponse
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("", response_model=SignalListResponse, summary="Signals per quarter with PRR, CI lower, chi-square (FR-04, FR-05)")
async def list_signals(quarter: str = Query("2026Q3", examples=["2026Q3"]), drug: str | None = None,
                       reaction: str | None = None, min_reports: int = 20, page: int = 1, page_size: int = 20):
    not_implemented("ListSignals")


@router.get("/emerging", response_model=SignalListResponse, summary="Emerging signals (FR-06)")
async def emerging(quarter: str = "2026Q3", limit: int = 20):
    not_implemented("EmergingSignals")


@router.get("/{rxcui}/{reaction}/reports", response_model=SignalReportsResponse, summary="Reports behind a signal (FR-09)")
async def signal_reports(rxcui: str, reaction: str, page: int = 1, page_size: int = 20):
    not_implemented("SignalReports")
