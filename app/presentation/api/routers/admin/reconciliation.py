from fastapi import APIRouter, Depends

from app.presentation.api.dependencies import reconcile

router = APIRouter(prefix="/reconciliation", tags=["Admin: reconciliation"])


@router.post("", summary="Rebuild the live layer from the documents (FR-27)")
async def run_reconciliation(uc=Depends(reconcile)) -> dict:
    return await uc.execute()
