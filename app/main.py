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

DESCRIPTION = f"""
Drug safety and shortage intelligence on real open data: FDA adverse event reports (FAERS), drug labels, NDC
products, shortages and recalls, normalised to RxNorm ingredients.

> **Disclaimer.** {DISCLAIMER} Every signal and label-gap response repeats this in `meta.disclaimer`.

**Try it.** Guests can use Drugs, Signals, Statistics and Shortages without a token. For the rest:
1. `POST /api/auth/register`, then `POST /api/auth/login` and copy `access_token`.
2. Press **Authorize** (top right), paste the token, *Authorize*. Swagger keeps it until you log out or reload.
3. `POST /api/auth/logout` revokes the token at once.

Admin routes (`/api/admin`) need a token whose role is `admin`; there is no admin screen, they are used from here.

**Conventions.** Ids are RxNorm ingredient RxCUIs (search first: `GET /api/drugs?query=ozempic`). Quarters are
`YYYYQn` by receive date. Lists that grow with the data take `page` (from 1) and `page_size` (default 10, max 100)
and return `items`, `total`, `page`, `page_size`, `total_pages`. Errors return `{{"detail": "..."}}`: 401 no or bad
token, 403 wrong role, 404 unknown id, 409 duplicate, 422 invalid input.

**Data.** A rolling window of the latest FAERS quarters (default 6, about 130k reports), so every chart covers
consecutive months. Example ids: semaglutide `1991302`, atorvastatin `83367`, ibuprofen `5640`.
"""

TAGS = [
    {"name": "Health", "description": "Liveness and dataset size."},
    {"name": "Auth", "description": "Register, log in (JWT), log out (FR-11, FR-12)."},
    {"name": "Drugs", "description": "Typo-tolerant search, Drug 360 page, reaction trend, label gaps "
                                     "(FR-01, FR-02, FR-03, FR-07). Open to guests."},
    {"name": "Signals", "description": "PRR disproportionality per quarter, emerging signals and the reports "
                                       "behind a signal (FR-04, FR-05, FR-06, FR-09). Open to guests."},
    {"name": "Statistics", "description": "Report counts by age group, sex, country, seriousness, type or "
                                          "quarter (FR-08). Open to guests."},
    {"name": "Shortages", "description": "Alternatives for a drug in shortage (FR-10). Open to guests."},
    {"name": "My medicines", "description": "Followed drugs and their alerts (FR-15 to FR-18). **User token.**"},
    {"name": "Profile", "description": "Account, password and alert settings (FR-13, FR-14). **User token.**"},
    {"name": "Admin: ingestion", "description": "Ingestion logs and triggers (FR-19 to FR-21). **Admin token.**"},
    {"name": "Admin: excluded terms", "description": "Non-specific reaction terms left out of the counts (FR-26). "
                                                     "**Admin token.**"},
    {"name": "Admin: reconciliation", "description": "Rebuild the Redis live values from the documents (FR-27). "
                                                     "**Admin token.**"},
    *({"name": f"Admin: {n}", "description": f"CRUD of {n} ({fr}). **Admin token.** Not implemented yet (501)."}
      for n, fr in (("reports", "FR-22"), ("labels", "FR-23"), ("shortages", "FR-24"), ("users", "FR-25"))),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.container = await build_container(settings)
    log.info("Storage backend: %s", settings.storage_backend)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name, version="0.3.0", description=DESCRIPTION, openapi_tags=TAGS, lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True, "docExpansion": "none",
                               "filter": True, "tryItOutEnabled": True, "defaultModelsExpandDepth": 0})
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    register_error_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
