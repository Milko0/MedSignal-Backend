"""FR-12: verify credentials and return a JWT."""
from app.application.dtos.auth import LoginRequest, TokenResponse
from app.application.ports.user_repository import UserRepository
from app.core.config import Settings
from app.core.security import create_access_token, verify_password
from app.domain.exceptions import InvalidCredentialsError


class Login:
    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self.users, self.settings = users, settings

    async def execute(self, body: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_username_or_email(body.identifier.lower()) or \
            await self.users.get_by_username_or_email(body.identifier)
        if user is None or not verify_password(body.password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")
        return TokenResponse(access_token=create_access_token(self.settings, user.user_id, user.role.value))
