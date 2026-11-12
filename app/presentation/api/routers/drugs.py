from fastapi import APIRouter, Depends, Path, Query

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
from app.presentation.api.responses import NOT_FOUND, RXCUI_EXAMPLES, UNAUTHORIZED

router = APIRouter(prefix="/drugs", tags=["Drugs"])

RXCUI = Path(description="Ingredient RxCUI (from the search)", openapi_examples=RXCUI_EXAMPLES)


@router.get("", response_model=list[DrugSearchResult], summary="Search a drug, typo tolerant (FR-01)",
            description="Matches ingredient names, synonyms and **brand names** (`ozempic`, `lipitor`), tolerating "
                        "typos (`ibuprofin`). Returns the best matches ranked by `score` (1.0 exact, 0.9 prefix, "
                        "otherwise similarity >= 0.75), each normalised to its ingredient RxCUI. Not paginated: "
                        "this is a suggestion list, so use `limit`.")
async def search(query: str = Query(min_length=2, description="Name, brand or misspelling",
                                    openapi_examples={"brand": {"value": "ozempic"}, "typo": {"value": "ibuprofin"},
                                                      "ingredient": {"value": "atorvastatin"}}),
                 limit: int = Query(10, ge=1, le=50), uc=Depends(search_drug)):
    return await uc.execute(query, limit)


@router.get("/{rxcui}/overview", response_model=Drug360Response, responses={**NOT_FOUND, **UNAUTHORIZED},
            summary="Drug 360 page (FR-02)",
            description="Everything about one ingredient: shortage status (Redis cache-aside), recalls by class, "
                        "label summary, top reported reactions, ATC classes and `match_coverage`. Open to guests; "
                        "with a token, `is_followed` tells whether the user follows the drug. `dosage_form` and "
                        "`route` narrow the shortage section.")
async def overview(rxcui: str = RXCUI, dosage_form: str | None = Query(None, examples=["TABLET"]),
                   route: str | None = Query(None, examples=["ORAL"]),
                   user: CurrentUser | None = Depends(get_current_user_optional), uc=Depends(get_drug_360)):
    return await uc.execute(rxcui, user.user_id if user else None, dosage_form, route)


@router.get("/{rxcui}/reaction-trend", response_model=list[TrendPoint], responses=NOT_FOUND,
            summary="Monthly trend of the top reactions (FR-03)",
            description="Reports per month for the drug's top reactions (suspect role), over the last `months` "
                        "months of data, zero-filled. One row per (month, reaction): ready for a line chart.")
async def reaction_trend(rxcui: str = RXCUI, months: int = Query(12, ge=3, le=36), uc=Depends(get_reaction_trend)):
    return await uc.execute(rxcui, months)


@router.get("/{rxcui}/label-gaps", response_model=DisclaimedResponse[LabelGapsData], responses=NOT_FOUND,
            summary="Label-gap candidates (FR-07)",
            description="Reactions reported at least `min_reports` times for the drug and **not** found in its "
                        "prescription label (adverse reactions, warnings, boxed warning). `match_level` is "
                        "FULL / PARTIAL / NONE. A candidate, not a finding: see `meta.disclaimer`.")
async def label_gaps(rxcui: str = RXCUI, min_reports: int = Query(20, ge=1), uc=Depends(get_label_gaps)):
    return disclaimed(await uc.execute(rxcui, min_reports))
