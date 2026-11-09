"""Application factory (composition root of the API process)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.infrastructure.mongodb.client import create_mongo_client
from app.infrastructure.redis.client import create_redis_client
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.router import api_router

DESCRIPTION = """
MedSignal cross-analyses FAERS adverse event reports, DailyMed labels, openFDA shortages and RxNorm names.

**Reports are voluntary and unverified; they show a statistical signal, not proof of causation.**
Every signal and label-gap response carries `meta.disclaimer` (NFR-11).
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.mongo = create_mongo_client(settings)  # lazy: connects on first use
    app.state.redis = create_redis_client(settings)
    yield
    app.state.mongo.close()
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", description=DESCRIPTION, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"])
    register_error_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
