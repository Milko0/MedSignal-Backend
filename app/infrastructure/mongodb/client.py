"""MongoDB client (PyMongo native async API). Writes use w=majority (NFR-03); heavy reads may go to secondaries.

Dates are stored as ISO strings (model_dump(mode="json")): they sort correctly as text and load back unchanged.
"""
from pymongo import AsyncMongoClient, ReadPreference
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import Settings


def create_mongo_client(settings: Settings) -> AsyncMongoClient:
    return AsyncMongoClient(settings.mongo_uri, w="majority", serverSelectionTimeoutMS=3000)


def get_collection(db: AsyncDatabase, name: str, secondary_ok: bool = False):
    if secondary_ok:
        return db.get_collection(name, read_preference=ReadPreference.SECONDARY_PREFERRED)
    return db[name]
