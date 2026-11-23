from fastapi import APIRouter, Depends

from app.application.dtos.admin import AdminUserCreate, AdminUserUpdate
from app.application.dtos.auth import UserResponse
from app.domain.entities.label import DrugLabel
from app.domain.entities.report import AdverseReport
from app.domain.entities.shortage import ShortageRecord
from app.presentation.api.dependencies import crud_labels, crud_reports, crud_shortages, crud_users, require_role
from app.presentation.api.responses import ADMIN
from app.presentation.api.routers.admin import excluded_terms, ingestion, reconciliation
from app.presentation.api.routers.admin.crud_factory import make_crud_router

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))], responses=ADMIN)
for r in (
    ingestion.router, excluded_terms.router, reconciliation.router,
    make_crud_router("reports", "FR-22", crud_reports, AdverseReport, id_label="report id (safetyreportid)",
                     notes="Newest received first. Signals change after the next signal run of the quarter."),
    make_crud_router("labels", "FR-23", crud_labels, DrugLabel, id_label="label set id", notes="Ordered by set id."),
    make_crud_router("shortages", "FR-24", crud_shortages, ShortageRecord, id_label="package NDC",
                     notes="Current records, ordered by package NDC. Changes refresh the cached shortage status; "
                           "the daily poll replaces the list with the FDA's again."),
    make_crud_router("users", "FR-25", crud_users, UserResponse, AdminUserCreate, AdminUserUpdate,
                     id_label="user id", notes="Passwords are never returned. Deleting a user also removes "
                                               "their follows and alerts."),
):
    router.include_router(r)
