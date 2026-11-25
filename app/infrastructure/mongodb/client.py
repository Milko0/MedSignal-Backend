"""MongoDB client (PyMongo native async API).

Writes use w=majority (NFR-03). Read-heavy analytics (statistics, signal explorer, trends) read from the secondaries
through `analytics_database`; everything else (accounts, ingestion, batch jobs) reads the primary. The reasoning is
in docs/adr/0003-read-preference-per-use-case.md.

Dates are stored as ISO strings (model_dump(mode="json")): they sort correctly as text and load back unchanged.
"""
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.read_preferences import SecondaryPreferred

from app.core.config import Settings


def create_mongo_client(settings: Settings) -> AsyncMongoClient:
    return AsyncMongoClient(settings.mongo_uri, w="majority", serverSelectionTimeoutMS=3000)


def analytics_database(db: AsyncDatabase, settings: Settings) -> AsyncDatabase:
    """The same database read with secondaryPreferred: a secondary when one is available and at most
    `mongo_max_staleness_seconds` behind (MongoDB's minimum is 90), the primary otherwise. With a single node
    (directConnection) the preference has no effect. Returns `db` itself when the setting is off."""
    if not settings.mongo_read_secondaries:
        return db
    return db.with_options(read_preference=SecondaryPreferred(max_staleness=settings.mongo_max_staleness_seconds))
