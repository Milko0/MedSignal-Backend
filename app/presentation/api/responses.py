"""Shared OpenAPI pieces: the error body and the error responses each kind of route can return."""
from fastapi import HTTPException
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Body of every error (FastAPI's own shape; validation errors (422) carry a list instead of a string)."""

    detail: str

    model_config = {"json_schema_extra": {"examples": [{"detail": "Authentication required"}]}}


def _err(description: str) -> dict:
    return {"model": ErrorResponse, "description": description}


UNAUTHORIZED = {401: _err("Missing, invalid, expired or logged-out token")}
FORBIDDEN = {403: _err("The token is valid but its role is not admin")}
NOT_FOUND = {404: _err("No ingredient (or item) with this id")}
CONFLICT = {409: _err("Username or email already registered")}
USER = UNAUTHORIZED
ADMIN = {**UNAUTHORIZED, **FORBIDDEN}

# Example ids taken from the real dataset, used across the routers
RXCUI_EXAMPLES = {"semaglutide": {"value": "1991302"}, "atorvastatin": {"value": "83367"},
                  "ibuprofen": {"value": "5640"}}
QUARTER_EXAMPLE = {"latest": {"value": "2026Q3"}, "older": {"value": "2025Q4"}}


def not_implemented(detail: str = "Not implemented yet") -> None:
    """Placeholder for endpoints that are designed (Swagger) but not built yet."""
    raise HTTPException(status_code=501, detail=detail)
