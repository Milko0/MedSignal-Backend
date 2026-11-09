"""Shared response pieces."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import DISCLAIMER


class Meta(BaseModel):
    disclaimer: str = Field(default=DISCLAIMER, description="NFR-11: must accompany every signal / label-gap response")
    generated_at: datetime | None = None


class Page(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
