from fastapi import APIRouter

from app.application.dtos.auth import LoginRequest, RegisterRequest, TokenResponse
from app.presentation.api.responses import not_implemented

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201, summary="Register (FR-11)")
async def register(body: RegisterRequest):
    not_implemented("Register")


@router.post("/login", response_model=TokenResponse, summary="Log in (FR-12)")
async def login(body: LoginRequest):
    not_implemented("Login")
