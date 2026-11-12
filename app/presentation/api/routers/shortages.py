from fastapi import APIRouter, Depends, Path, Query

from app.application.dtos.shortages import AlternativesData
from app.presentation.api.dependencies import recommend_alternatives
from app.presentation.api.responses import NOT_FOUND, RXCUI_EXAMPLES

router = APIRouter(prefix="/shortages", tags=["Shortages"])


@router.get("/{rxcui}/alternatives", response_model=AlternativesData, responses=NOT_FOUND,
            summary="Alternatives for a drug in shortage (FR-10)",
            description="Products with the same route and dosage form that are **not** in shortage: first other "
                        "products of the same ingredient (SAME_INGREDIENT), then ingredients of the same ATC class "
                        "(SAME_CLASS). Each row shows its recalls and a signal profile (LOW / MEDIUM / HIGH by the "
                        "number of Evans signals in the latest quarter). Informational, not medical advice.")
async def alternatives(rxcui: str = Path(openapi_examples=RXCUI_EXAMPLES),
                       dosage_form: str | None = Query(None, examples=["TABLET"]),
                       route: str | None = Query(None, examples=["ORAL"]), uc=Depends(recommend_alternatives)):
    return await uc.execute(rxcui, dosage_form, route)
