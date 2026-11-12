from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8)

    model_config = {"json_schema_extra": {"examples": [{"username": "ana", "email": "ana@example.com", "password": "password123"}]}}


class LoginRequest(BaseModel):
    identifier: str  # username or email
    password: str

    model_config = {"json_schema_extra": {"examples": [{"identifier": "ana", "password": "password123"}]}}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
