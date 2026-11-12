from fastapi import APIRouter, Depends

from app.application.dtos.shortages import AlternativesData
from app.presentation.api.dependencies import recommend_alternatives

router = APIRouter(prefix="/shortages", tags=["Shortages"])


@router.get("/{rxcui}/alternatives", response_model=AlternativesData,
            summary="Alternatives for a drug in shortage: same route and form, not in shortage (FR-10)")
async def alternatives(rxcui: str, dosage_form: str | None = None, route: str | None = None,
                       uc=Depends(recommend_alternatives)):
    return await uc.execute(rxcui, dosage_form, route)
