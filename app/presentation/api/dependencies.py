"""FastAPI dependency providers: DB handles, authentication, authorisation, use-case wiring."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.use_cases.drugs.get_drug_360 import GetDrug360
from app.core.security import decode_access_token
from app.infrastructure.mongodb.repositories.drug_repository import MongoDrugRepository
from app.infrastructure.mongodb.repositories.label_repository import MongoLabelRepository
from app.infrastructure.mongodb.repositories.recall_repository import MongoRecallRepository
from app.infrastructure.mongodb.repositories.shortage_repository import MongoShortageRepository
from app.infrastructure.mongodb.repositories.signal_repository import MongoSignalRepository
from app.infrastructure.redis.stores.follow_store import RedisFollowStore
from app.infrastructure.redis.stores.shortage_status_store import RedisShortageStatusStore

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    return request.app.state.mongo[request.app.state.settings.mongo_db]


def get_redis(request: Request):
    return request.app.state.redis


async def get_optional_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict | None:
    """Guest -> None; registered user -> {'sub': id, 'role': ...}."""
    if creds is None:
        return None
    try:
        return decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(user: dict | None = Depends(get_optional_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_role(role: str):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != role:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return checker


# ---- composition example: the only place that knows concrete adapters
def get_drug_360_use_case(db=Depends(get_db), r=Depends(get_redis)) -> GetDrug360:
    return GetDrug360(
        drugs=MongoDrugRepository(db), status_store=RedisShortageStatusStore(r),
        shortages=MongoShortageRepository(db), signals=MongoSignalRepository(db),
        labels=MongoLabelRepository(db), recalls=MongoRecallRepository(db), follows=RedisFollowStore(r),
    )
