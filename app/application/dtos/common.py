from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.constants import DISCLAIMER

T = TypeVar("T")


class Meta(BaseModel):
    disclaimer: str | None = None


class DisclaimedResponse(BaseModel, Generic[T]):
    """Envelope for every response that shows signals or label gaps (NFR-11)."""

    data: T
    meta: Meta


def disclaimed(data):
    return {"data": data, "meta": Meta(disclaimer=DISCLAIMER)}


class MessageResponse(BaseModel):
    message: str


DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


class PageRequest(BaseModel):
    """1-based page of a list endpoint. Adapters receive it as skip/limit (Mongo: .skip().limit() on an index)."""

    model_config = {"frozen": True}

    page: int = Field(1, ge=1)
    page_size: int = Field(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PageMeta(BaseModel):
    """Fields shared by every paginated list response (each subclass declares its own items field)."""

    total: int
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    total_pages: int = 0


def page_meta(total: int, req: PageRequest) -> dict:
    return {"total": total, "page": req.page, "page_size": req.page_size, "total_pages": ceil(total / req.page_size)}
