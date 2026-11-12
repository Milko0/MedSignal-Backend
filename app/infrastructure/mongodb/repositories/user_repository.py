from pymongo.errors import DuplicateKeyError

from app.application.ports.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import AlreadyExistsError
from app.infrastructure.mongodb.documents import from_doc, to_doc


def _doc(user: User) -> dict:
    # lower-case copies carry the unique indexes, so "Ana" and "ana" are the same account
    return to_doc(user, "user_id", username_lower=user.username.lower(), email_lower=user.email.lower())


class MongoUserRepository(UserRepository):
    """`users`, `_id` = user_id, unique indexes on username_lower and email_lower (mongodb/indexes.py)."""

    def __init__(self, db) -> None:
        self.col = db["users"]

    def _load(self, doc):
        return from_doc(User, doc, "user_id")

    async def create(self, user):
        try:
            await self.col.insert_one(_doc(user))
        except DuplicateKeyError as exc:
            raise AlreadyExistsError("Username or email already registered") from exc
        return user

    async def get_by_id(self, user_id):
        return self._load(await self.col.find_one({"_id": user_id}))

    async def get_by_username_or_email(self, value):
        v = value.lower()
        return self._load(await self.col.find_one({"$or": [{"username_lower": v}, {"email_lower": v}]}))

    async def update(self, user):
        try:
            await self.col.replace_one({"_id": user.user_id}, _doc(user), upsert=True)
        except DuplicateKeyError as exc:
            raise AlreadyExistsError("Username or email already registered") from exc

    async def delete(self, user_id):
        return (await self.col.delete_one({"_id": user_id})).deleted_count == 1

    async def list(self, skip, limit):
        return [self._load(d) async for d in self.col.find({}, sort=[("created_at", 1), ("_id", 1)], skip=skip,
                                                            limit=limit)]
