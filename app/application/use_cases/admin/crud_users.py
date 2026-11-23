"""FR-25: administrator CRUD on user accounts. Passwords are only ever written as bcrypt hashes and never returned."""
import uuid

from app.application.dtos.admin import AdminUserCreate, AdminUserUpdate
from app.application.dtos.auth import UserResponse
from app.application.ports.user_repository import UserRepository
from app.application.use_cases.profile.manage_profile import ManageProfile
from app.core.security import hash_password
from app.domain.entities.user import User
from app.domain.exceptions import AlreadyExistsError, NotFoundError


def _dto(u: User) -> UserResponse:
    return UserResponse(user_id=u.user_id, username=u.username, email=u.email, role=u.role.value)


class CrudUsers:
    def __init__(self, users: UserRepository, profile: ManageProfile, clock) -> None:
        self.users, self.profile, self.clock = users, profile, clock

    async def _get(self, user_id: str) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def _check_free(self, value: str, user_id: str | None = None) -> None:
        other = await self.users.get_by_username_or_email(value)
        if other is not None and other.user_id != user_id:
            raise AlreadyExistsError(f"{value} is already in use")

    async def list(self, skip: int, limit: int) -> list[UserResponse]:
        return [_dto(u) for u in await self.users.list(skip, limit)]

    async def get(self, user_id: str) -> UserResponse:
        return _dto(await self._get(user_id))

    async def create(self, body: AdminUserCreate) -> UserResponse:
        await self._check_free(body.username)
        await self._check_free(body.email)
        user = await self.users.create(User(
            user_id=str(uuid.uuid4()), username=body.username, email=body.email.lower(), role=body.role,
            password_hash=hash_password(body.password), created_at=self.clock.now()))
        return _dto(user)

    async def update(self, user_id: str, body: AdminUserUpdate) -> UserResponse:
        user = await self._get(user_id)
        if body.username and body.username != user.username:
            await self._check_free(body.username, user_id)
            user.username = body.username
        if body.email and body.email.lower() != user.email:
            await self._check_free(body.email, user_id)
            user.email = body.email.lower()
        if body.role is not None:
            user.role = body.role
        if body.password:
            user.password_hash = hash_password(body.password)
        await self.users.update(user)
        return _dto(user)

    async def delete(self, user_id: str) -> None:
        await self.profile.delete(user_id)       # also removes the user's follows and alerts
