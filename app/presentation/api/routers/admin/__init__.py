from fastapi import APIRouter, Depends

from app.presentation.api.dependencies import require_role
from app.presentation.api.routers.admin import excluded_terms, ingestion, reconciliation
from app.presentation.api.routers.admin.crud_factory import make_crud_router

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))])
for r in (ingestion.router, excluded_terms.router, reconciliation.router,
          make_crud_router("reports", "FR-22"), make_crud_router("labels", "FR-23"),
          make_crud_router("shortages", "FR-24"), make_crud_router("users", "FR-25")):
    router.include_router(r)
