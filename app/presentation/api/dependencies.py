"""The ONLY place (with worker.py) that knows how use cases are built from the container."""
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.container import Container
from app.application.dtos.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageRequest
from app.application.use_cases.admin.manage_excluded_terms import ManageExcludedTerms
from app.application.use_cases.auth.login import Login
from app.application.use_cases.auth.logout import Logout
from app.application.use_cases.auth.register import Register
from app.application.use_cases.cabinet.dismiss_alert import DismissAlert
from app.application.use_cases.cabinet.follow_drug import FollowDrug
from app.application.use_cases.cabinet.list_alerts import ListAlerts
from app.application.use_cases.cabinet.list_followed import ListFollowed
from app.application.use_cases.cabinet.unfollow_drug import UnfollowDrug
from app.application.use_cases.drugs.get_drug_360 import GetDrug360
from app.application.use_cases.drugs.get_label_gaps import GetLabelGaps
from app.application.use_cases.drugs.get_reaction_trend import GetReactionTrend
from app.application.use_cases.drugs.search_drug import SearchDrug
from app.application.use_cases.ingestion.list_ingestion_runs import ListIngestionRuns
from app.application.use_cases.profile.manage_profile import ManageProfile
from app.application.use_cases.shortages.recommend_alternatives import (
    RecommendAlternatives,
)
from app.application.use_cases.signals.emerging_signals import EmergingSignals
from app.application.use_cases.signals.list_signals import ListSignals
from app.application.use_cases.signals.signal_reports import SignalReportsUseCase
from app.application.use_cases.signals.statistics import GetStatistics
from app.application.use_cases.sync.reconcile import Reconcile
from app.core.config import Settings, get_settings
from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False, description="JWT from POST /api/auth/login")


@dataclass
class CurrentUser:
    user_id: str
    role: str
    jti: str
    expires_at: datetime


def settings_dep() -> Settings:
    return get_settings()


def container(request: Request) -> Container:
    return request.app.state.container


# ---- authentication ----
async def get_current_user_optional(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                                    settings: Settings = Depends(settings_dep),
                                    c: Container = Depends(container)) -> CurrentUser | None:
    """Guests have no token and get None. A bad, expired or logged-out token is a 401, never a silent guest."""
    if creds is None:
        return None
    try:
        payload = decode_access_token(settings, creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc
    if await c.revoked_tokens.is_revoked(payload["jti"]):
        raise HTTPException(status_code=401, detail="Token has been revoked (logged out)",
                            headers={"WWW-Authenticate": "Bearer"})
    return CurrentUser(user_id=payload["sub"], role=payload.get("role", "user"), jti=payload["jti"],
                       expires_at=datetime.fromtimestamp(payload["exp"], UTC))


def get_current_user(user: CurrentUser | None = Depends(get_current_user_optional)) -> CurrentUser:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_role(*roles: str):
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


# ---- pagination (every list endpoint that grows with the data) ----
def pagination(page: int = Query(1, ge=1, description="1-based page number"),
               page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE,
                                      description=f"Items per page (max {MAX_PAGE_SIZE})")) -> PageRequest:
    return PageRequest(page=page, page_size=page_size)


# ---- use case providers ----
def search_drug(c: Container = Depends(container)): return SearchDrug(c.ingredients)
def get_drug_360(c: Container = Depends(container)):
    return GetDrug360(c.ingredients, c.shortages, c.shortage_status, c.recalls, c.labels, c.reports, c.follows,
                      c.excluded_terms, c.clock)
def get_reaction_trend(c: Container = Depends(container)): return GetReactionTrend(c.reports, c.excluded_terms)
def get_label_gaps(c: Container = Depends(container)): return GetLabelGaps(c.reports, c.labels, c.excluded_terms)
def list_signals(c: Container = Depends(container)): return ListSignals(c.signals, c.ingredients, c.reports)
def emerging_signals(c: Container = Depends(container)): return EmergingSignals(c.signals, c.ingredients, c.reports)
def signal_reports(c: Container = Depends(container)): return SignalReportsUseCase(c.reports, c.ingredients)
def statistics(c: Container = Depends(container)): return GetStatistics(c.reports)
def recommend_alternatives(c: Container = Depends(container)):
    return RecommendAlternatives(c.ingredients, c.products, c.shortages, c.recalls, c.signals)
def register_uc(c: Container = Depends(container)): return Register(c.users, c.clock)
def login_uc(c: Container = Depends(container), s: Settings = Depends(settings_dep)): return Login(c.users, s)
def logout_uc(c: Container = Depends(container)): return Logout(c.revoked_tokens, c.clock)
def follow_drug(c: Container = Depends(container)): return FollowDrug(c.follows, c.ingredients)
def unfollow_drug(c: Container = Depends(container)): return UnfollowDrug(c.follows)
def list_followed(c: Container = Depends(container)):
    return ListFollowed(c.follows, c.ingredients, c.shortage_status, c.shortages, c.clock)
def list_alerts(c: Container = Depends(container)): return ListAlerts(c.alerts)
def dismiss_alert(c: Container = Depends(container)): return DismissAlert(c.alerts)
def manage_profile(c: Container = Depends(container)): return ManageProfile(c.users)
def excluded_terms_uc(c: Container = Depends(container)): return ManageExcludedTerms(c.excluded_terms, c.clock)
def ingestion_runs(c: Container = Depends(container)): return ListIngestionRuns(c.ingestion_runs)
def reconcile(c: Container = Depends(container)): return Reconcile(c.ingredients, c.shortages, c.shortage_status, c.clock)
