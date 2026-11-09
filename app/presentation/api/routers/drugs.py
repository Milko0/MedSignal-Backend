from fastapi import APIRouter, Depends, Query

from app.application.dtos.drugs import (Drug360Response, DrugSearchItem, LabelGapResponse, ReactionTrendResponse)
from app.application.use_cases.drugs.get_drug_360 import GetDrug360
from app.presentation.api.dependencies import get_drug_360_use_case, get_optional_user
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/drugs", tags=["Drugs"])


@router.get("", response_model=list[DrugSearchItem], summary="Search by generic, brand or misspelled name (FR-01)")
async def search_drugs(query: str = Query(min_length=2, examples=["ibuprofn"])):
    not_implemented("SearchDrug")


@router.get("/{rxcui}/overview", response_model=Drug360Response, summary="Drug 360 card (FR-02)")
async def drug_overview(rxcui: str, user: dict | None = Depends(get_optional_user),
                        uc: GetDrug360 = Depends(get_drug_360_use_case)):
    # return await uc.execute(rxcui, user["sub"] if user else None)   # enable once Mongo repositories exist
    not_implemented("GetDrug360")


@router.get("/{rxcui}/reaction-trend", response_model=ReactionTrendResponse, summary="Monthly trend of top reactions (FR-03)")
async def reaction_trend(rxcui: str):
    not_implemented("GetReactionTrend")


@router.get("/{rxcui}/label-gaps", response_model=LabelGapResponse, summary="Label-gap candidates (FR-07)")
async def label_gaps(rxcui: str):
    not_implemented("GetLabelGaps")
