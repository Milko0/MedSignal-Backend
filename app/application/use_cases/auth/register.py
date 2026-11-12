"""FR-11: create an account (password hashed with bcrypt, never stored in clear)."""
import uuid

from app.application.dtos.auth import RegisterRequest, UserResponse
from app.application.ports.clock import Clock
from app.application.ports.user_repository import UserRepository
from app.core.security import hash_password
from app.domain.entities.user import User
from app.domain.exceptions import AlreadyExistsError


class Register:
    def __init__(self, users: UserRepository, clock: Clock) -> None:
        self.users, self.clock = users, clock

    async def execute(self, body: RegisterRequest) -> UserResponse:
        if await self.users.get_by_username_or_email(body.username) or await self.users.get_by_username_or_email(body.email):
            raise AlreadyExistsError("Username or email already registered")
        user = await self.users.create(User(
            user_id=str(uuid.uuid4()), username=body.username, email=body.email.lower(),
            password_hash=hash_password(body.password), created_at=self.clock.now()))
        return UserResponse(user_id=user.user_id, username=user.username, email=user.email, role=user.role.value)
