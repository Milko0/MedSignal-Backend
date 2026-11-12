from pydantic import BaseModel, EmailStr, Field


class ProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=32)
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class AlertSettingsDto(BaseModel):
    new_signal: bool = True
    label_updated: bool = True
    shortage_changed: bool = True
    new_recall: bool = True
    min_reports: int = 20
