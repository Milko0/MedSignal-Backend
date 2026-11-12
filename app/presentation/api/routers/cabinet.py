from fastapi import APIRouter, Depends, status

from app.application.dtos.cabinet import AlertItem, FollowedDrug, FollowRequest
from app.presentation.api.dependencies import (
    CurrentUser,
    dismiss_alert,
    follow_drug,
    get_current_user,
    list_alerts,
    list_followed,
    unfollow_drug,
)
from app.presentation.api.responses import NOT_FOUND, USER

router = APIRouter(prefix="/cabinet", tags=["My medicines"], responses=USER)


@router.get("", response_model=list[FollowedDrug], summary="Medicine cabinet (FR-16)",
            description="The drugs the user follows, each with its live shortage status (Redis).")
async def cabinet(user: CurrentUser = Depends(get_current_user), uc=Depends(list_followed)):
    return await uc.execute(user.user_id)


@router.post("/follows", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND, summary="Follow a drug (FR-15)",
             description="Following is idempotent. The user then gets alerts for new signals, label changes, "
                         "shortage changes and recalls of the drug (see Profile > alert settings).")
async def follow(body: FollowRequest, user: CurrentUser = Depends(get_current_user), uc=Depends(follow_drug)):
    await uc.execute(user.user_id, body.rxcui)


@router.delete("/follows/{rxcui}", status_code=status.HTTP_204_NO_CONTENT, summary="Unfollow a drug (FR-15)")
async def unfollow(rxcui: str, user: CurrentUser = Depends(get_current_user), uc=Depends(unfollow_drug)):
    await uc.execute(user.user_id, rxcui)


@router.get("/alerts", response_model=list[AlertItem], summary="List alerts (FR-17)",
            description="Newest first. Alerts expire after 30 days (Redis TTL), so old ones disappear by themselves.")
async def alerts(user: CurrentUser = Depends(get_current_user), uc=Depends(list_alerts)):
    return await uc.execute(user.user_id)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Dismiss an alert (FR-18)")
async def dismiss_one(alert_id: str, user: CurrentUser = Depends(get_current_user), uc=Depends(dismiss_alert)):
    await uc.execute(user.user_id, alert_id)


@router.delete("/alerts", status_code=status.HTTP_204_NO_CONTENT, summary="Dismiss all alerts (FR-18)")
async def dismiss_all(user: CurrentUser = Depends(get_current_user), uc=Depends(dismiss_alert)):
    await uc.execute(user.user_id, None)
