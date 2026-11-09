from fastapi import APIRouter

from app.application.dtos.shortages import AlternativesResponse
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/shortages", tags=["Shortages"])


@router.get("/{rxcui}/alternatives", response_model=AlternativesResponse,
            summary="Alternatives with same route and dosage form, not in shortage (FR-10)")
async def alternatives(rxcui: str):
    not_implemented("RecommendAlternatives")
