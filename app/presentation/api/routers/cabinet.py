from fastapi import APIRouter, Depends

from app.application.dtos.cabinet import AlertListResponse, CabinetResponse, FollowRequest
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/cabinet", tags=["My medicines"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=CabinetResponse, summary="Followed drugs with status (FR-16)")
async def list_followed():
    not_implemented("ListFollowed")


@router.post("/follows", status_code=204, summary="Follow a drug (FR-15)")
async def follow(body: FollowRequest):
    not_implemented("FollowDrug")


@router.delete("/follows/{rxcui}", status_code=204, summary="Unfollow a drug (FR-15)")
async def unfollow(rxcui: str):
    not_implemented("UnfollowDrug")


@router.get("/alerts", response_model=AlertListResponse, summary="Alerts, 30-day expiry (FR-18)")
async def list_alerts():
    not_implemented("ListAlerts")


@router.delete("/alerts/{alert_id}", status_code=204, summary="Dismiss one alert (FR-18)")
async def dismiss_alert(alert_id: str):
    not_implemented("DismissAlert")


@router.delete("/alerts", status_code=204, summary="Dismiss all alerts (FR-18)")
async def dismiss_all():
    not_implemented("DismissAllAlerts")
