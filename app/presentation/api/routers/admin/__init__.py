"""Admin routers (FR-19 to FR-27). No admin view in the UI: use Swagger /docs."""
from fastapi import APIRouter, Depends

from app.presentation.api.dependencies import require_role
from app.presentation.api.routers.admin.crud_factory import crud_router
from app.presentation.api.routers.admin import excluded_terms, ingestion, reconciliation

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))])
router.include_router(ingestion.router)
router.include_router(reconciliation.router)
router.include_router(excluded_terms.router)
for resource, fr in (("reports", "FR-22"), ("labels", "FR-23"), ("shortages", "FR-24"), ("users", "FR-25")):
    router.include_router(crud_router(resource, fr))
