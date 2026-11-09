"""Motor client. Writes use w=majority (NFR-03); heavy reads may go to secondaries."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReadPreference

from app.core.config import Settings


def create_mongo_client(settings: Settings) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.mongo_uri, w="majority", serverSelectionTimeoutMS=3000)


def get_collection(db: AsyncIOMotorDatabase, name: str, secondary_ok: bool = False):
    if secondary_ok:
        return db.get_collection(name, read_preference=ReadPreference.SECONDARY_PREFERRED)
    return db[name]
