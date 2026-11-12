"""FR-13, FR-14: view, update and delete the profile; change password; alert settings."""
from app.application.dtos.auth import UserResponse
from app.application.dtos.profile import AlertSettingsDto, PasswordChange, ProfileUpdate
from app.application.ports.user_repository import UserRepository
from app.core.security import hash_password, verify_password
from app.domain.entities.user import AlertSettings
from app.domain.exceptions import (
    AlreadyExistsError,
    InvalidCredentialsError,
    NotFoundError,
)


def _dto(u) -> UserResponse:
    return UserResponse(user_id=u.user_id, username=u.username, email=u.email, role=u.role.value)


class ManageProfile:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def _get(self, user_id: str):
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def get(self, user_id: str) -> UserResponse:
        return _dto(await self._get(user_id))

    async def update(self, user_id: str, body: ProfileUpdate) -> UserResponse:
        user = await self._get(user_id)
        for field in ("username", "email"):
            value = getattr(body, field)
            if value and value != getattr(user, field):
                other = await self.users.get_by_username_or_email(value)
                if other and other.user_id != user_id:
                    raise AlreadyExistsError(f"{field} already in use")
                setattr(user, field, value.lower() if field == "email" else value)
        await self.users.update(user)
        return _dto(user)

    async def delete(self, user_id: str) -> None:
        if not await self.users.delete(user_id):
            raise NotFoundError("User not found")

    async def change_password(self, user_id: str, body: PasswordChange) -> None:
        user = await self._get(user_id)
        if not verify_password(body.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is wrong")
        user.password_hash = hash_password(body.new_password)
        await self.users.update(user)

    async def get_settings(self, user_id: str) -> AlertSettingsDto:
        return AlertSettingsDto(**(await self._get(user_id)).settings.model_dump())

    async def update_settings(self, user_id: str, body: AlertSettingsDto) -> AlertSettingsDto:
        user = await self._get(user_id)
        user.settings = AlertSettings(**body.model_dump())
        await self.users.update(user)
        return body
