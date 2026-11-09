from fastapi import APIRouter

from app.presentation.api.routers import auth, cabinet, drugs, health, profile, shortages, signals, statistics
from app.presentation.api.routers.admin import router as admin_router

api_router = APIRouter()
for r in (health.router, auth.router, drugs.router, signals.router, statistics.router, shortages.router,
          cabinet.router, profile.router, admin_router):
    api_router.include_router(r)
