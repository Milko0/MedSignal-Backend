from fastapi import APIRouter, Depends, Query

from app.application.dtos.common import DisclaimedResponse, disclaimed
from app.application.dtos.drugs import (
    Drug360Response,
    DrugSearchResult,
    LabelGapsData,
    TrendPoint,
)
from app.presentation.api.dependencies import (
    CurrentUser,
    get_current_user_optional,
    get_drug_360,
    get_label_gaps,
    get_reaction_trend,
    search_drug,
)

router = APIRouter(prefix="/drugs", tags=["Drugs"])


@router.get("", response_model=list[DrugSearchResult], summary="Search a drug, typo tolerant (FR-01)")
async def search(query: str = Query(min_length=2), limit: int = Query(10, ge=1, le=50), uc=Depends(search_drug)):
    return await uc.execute(query, limit)


@router.get("/{rxcui}/overview", response_model=Drug360Response, summary="Drug 360 page (FR-02)")
async def overview(rxcui: str, dosage_form: str | None = None, route: str | None = None,
                   user: CurrentUser | None = Depends(get_current_user_optional), uc=Depends(get_drug_360)):
    return await uc.execute(rxcui, user.user_id if user else None, dosage_form, route)


@router.get("/{rxcui}/reaction-trend", response_model=list[TrendPoint], summary="Monthly trend of top reactions (FR-03)")
async def reaction_trend(rxcui: str, months: int = Query(12, ge=3, le=36), uc=Depends(get_reaction_trend)):
    return await uc.execute(rxcui, months)


@router.get("/{rxcui}/label-gaps", response_model=DisclaimedResponse[LabelGapsData], summary="Label-gap candidates (FR-07)")
async def label_gaps(rxcui: str, min_reports: int = Query(20, ge=1), uc=Depends(get_label_gaps)):
    return disclaimed(await uc.execute(rxcui, min_reports))
