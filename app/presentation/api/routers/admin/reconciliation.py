from fastapi import APIRouter

from app.application.dtos.admin import ReconcileResult
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/reconciliation", tags=["Admin - reconciliation"])


@router.post("", response_model=ReconcileResult, summary="Rebuild Redis counters/statuses from MongoDB (FR-27)")
async def reconcile():
    not_implemented("Reconcile")
