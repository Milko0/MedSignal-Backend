import re
from dataclasses import dataclass

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@dataclass(frozen=True)
class SetId:
    """SPL set id (a UUID, stored lower-case)."""

    value: str

    def __post_init__(self) -> None:
        if not _UUID.match(self.value):
            raise ValueError(f"Invalid SPL set id: {self.value!r}")

    @classmethod
    def of(cls, raw: str) -> "SetId":
        return cls(raw.strip().lower())
