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
from app.presentation.api.responses import CONFLICT, UNAUTHORIZED, USER

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, responses=CONFLICT,
             summary="Register (FR-11)",
             description="Creates a **user** account (role `user`). Username 3-32 characters, password at least 8. "
                         "Username and email are unique, case-insensitive.")
async def register(body: RegisterRequest, uc=Depends(register_uc)):
    return await uc.execute(body)


@router.post("/login", response_model=TokenResponse, responses=UNAUTHORIZED, summary="Log in (FR-12)",
             description="`identifier` is the username **or** the email. Returns a JWT bearer token "
                         "(valid `JWT_EXPIRE_MINUTES`, default 60). In Swagger: copy `access_token`, press "
                         "**Authorize** and paste it.")
async def login(body: LoginRequest, uc=Depends(login_uc)):
    return await uc.execute(body)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=USER, summary="Log out: revoke the token",
             description="The bearer token sent with this request stops working at once (otherwise it would stay "
                         "valid until it expires). Its id is kept in Redis only until that expiry. The client should "
                         "also drop the token.")
async def logout(user: CurrentUser = Depends(get_current_user), uc=Depends(logout_uc)):
    await uc.execute(user.jti, user.expires_at)
