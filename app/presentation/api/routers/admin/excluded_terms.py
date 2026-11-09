from fastapi import APIRouter

from app.application.dtos.admin import ExcludedTerm
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/excluded-terms", tags=["Admin - excluded terms"])


@router.get("", response_model=list[ExcludedTerm], summary="List non-specific reaction terms (FR-26)")
async def list_terms():
    not_implemented("ManageExcludedTerms")


@router.post("", response_model=ExcludedTerm, status_code=201, summary="Add term (FR-26)")
async def add_term(body: ExcludedTerm):
    not_implemented("ManageExcludedTerms")


@router.delete("/{term}", status_code=204, summary="Remove term (FR-26)")
async def remove_term(term: str):
    not_implemented("ManageExcludedTerms")
