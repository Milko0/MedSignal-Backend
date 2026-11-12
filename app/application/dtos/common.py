from typing import Generic, TypeVar

from pydantic import BaseModel

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
