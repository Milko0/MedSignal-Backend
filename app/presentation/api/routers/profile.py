from fastapi import APIRouter, Depends, status

from app.application.dtos.auth import UserResponse
from app.application.dtos.profile import AlertSettingsDto, PasswordChange, ProfileUpdate
from app.presentation.api.dependencies import (
    CurrentUser,
    get_current_user,
    logout_uc,
    manage_profile,
)
from app.presentation.api.responses import CONFLICT, UNAUTHORIZED, USER

router = APIRouter(prefix="/profile", tags=["Profile"], responses=USER)


@router.get("", response_model=UserResponse, summary="View profile (FR-13)")
async def get_profile(user: CurrentUser = Depends(get_current_user), uc=Depends(manage_profile)):
    return await uc.get(user.user_id)


@router.patch("", response_model=UserResponse, responses=CONFLICT, summary="Update profile (FR-13)",
              description="Send only the fields to change.")
async def update_profile(body: ProfileUpdate, user: CurrentUser = Depends(get_current_user), uc=Depends(manage_profile)):
    return await uc.update(user.user_id, body)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Delete account (FR-13)",
               description="Deletes the account and logs out (the token is revoked).")
async def delete_profile(user: CurrentUser = Depends(get_current_user), uc=Depends(manage_profile),
                         logout=Depends(logout_uc)):
    await uc.delete(user.user_id)
    await logout.execute(user.jti, user.expires_at)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT, responses=UNAUTHORIZED, summary="Change password",
             description="401 also when `current_password` is wrong.")
async def change_password(body: PasswordChange, user: CurrentUser = Depends(get_current_user), uc=Depends(manage_profile)):
    await uc.change_password(user.user_id, body)


@router.get("/alert-settings", response_model=AlertSettingsDto, summary="Alert settings (FR-14)")
async def get_alert_settings(user: CurrentUser = Depends(get_current_user), uc=Depends(manage_profile)):
    return await uc.get_settings(user.user_id)


@router.put("/alert-settings", response_model=AlertSettingsDto, summary="Update alert settings (FR-14)",
            description="Which alert types the user receives for followed drugs, and the minimum number of "
                        "reports for a new-signal alert.")
async def put_alert_settings(body: AlertSettingsDto, user: CurrentUser = Depends(get_current_user),
                             uc=Depends(manage_profile)):
    return await uc.update_settings(user.user_id, body)
