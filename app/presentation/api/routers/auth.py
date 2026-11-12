from fastapi import APIRouter, Depends, status

from app.application.dtos.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.presentation.api.dependencies import (
    CurrentUser,
    get_current_user,
    login_uc,
    logout_uc,
    register_uc,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register (FR-11)")
async def register(body: RegisterRequest, uc=Depends(register_uc)):
    return await uc.execute(body)


@router.post("/login", response_model=TokenResponse, summary="Log in (FR-12)")
async def login(body: LoginRequest, uc=Depends(login_uc)):
    return await uc.execute(body)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out: revoke the current token",
             description="The bearer token sent with this request stops working at once (until then it would be "
                         "valid until its expiry). The client should also drop it.")
async def logout(user: CurrentUser = Depends(get_current_user), uc=Depends(logout_uc)):
    await uc.execute(user.jti, user.expires_at)
