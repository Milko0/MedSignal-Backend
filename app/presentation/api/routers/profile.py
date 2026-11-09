from fastapi import APIRouter, Depends

from app.application.dtos.auth import UserOut
from app.application.dtos.profile import AlertSettings, PasswordChange, ProfileUpdate
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/profile", tags=["Profile"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=UserOut, summary="View profile (FR-14)")
async def get_profile():
    not_implemented("GetProfile")


@router.patch("", response_model=UserOut, summary="Update profile (FR-14)")
async def update_profile(body: ProfileUpdate):
    not_implemented("UpdateProfile")


@router.post("/password", status_code=204, summary="Change password (FR-14)")
async def change_password(body: PasswordChange):
    not_implemented("ChangePassword")


@router.delete("", status_code=204, summary="Delete account (FR-14)")
async def delete_profile():
    not_implemented("DeleteProfile")


@router.get("/alert-settings", response_model=AlertSettings, summary="Alert preferences")
async def get_alert_settings():
    not_implemented("AlertSettings")


@router.put("/alert-settings", response_model=AlertSettings, summary="Save alert preferences")
async def save_alert_settings(body: AlertSettings):
    not_implemented("AlertSettings")
