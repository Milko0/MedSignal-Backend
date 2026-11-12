import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.constants import API_PREFIX, DISCLAIMER
from app.infrastructure.container_factory import build_container
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.router import api_router

log = logging.getLogger("medsignal")

TAGS = [
    {"name": "Auth", "description": "Register and log in"},
    {"name": "Drugs", "description": "Search, Drug 360, trend, label gaps"},
    {"name": "Signals", "description": "PRR signals, emerging signals, reports behind a signal"},
    {"name": "Statistics", "description": "Report statistics"},
    {"name": "Shortages", "description": "Alternatives for drugs in shortage"},
    {"name": "My medicines", "description": "Followed drugs and alerts"},
    {"name": "Profile", "description": "Profile and alert settings"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.container = await build_container(settings)
    log.info("Storage backend: %s", settings.storage_backend)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.2.0", description=DISCLAIMER, openapi_tags=TAGS, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    register_error_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
