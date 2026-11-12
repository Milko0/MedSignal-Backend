from fastapi import APIRouter, Depends, status

from app.application.dtos.admin import ExcludedTermDto
from app.presentation.api.dependencies import excluded_terms_uc

router = APIRouter(prefix="/excluded-terms", tags=["Admin: excluded terms"])


@router.get("", response_model=list[ExcludedTermDto], summary="List excluded reaction terms (FR-26)")
async def list_terms(uc=Depends(excluded_terms_uc)):
    return await uc.list()


@router.post("", response_model=ExcludedTermDto, status_code=status.HTTP_201_CREATED, summary="Add a term (FR-26)")
async def add_term(body: ExcludedTermDto, uc=Depends(excluded_terms_uc)):
    return await uc.add(body.term)


@router.delete("/{term}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a term (FR-26)")
async def remove_term(term: str, uc=Depends(excluded_terms_uc)):
    await uc.remove(term)
