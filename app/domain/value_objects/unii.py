import re
from dataclasses import dataclass

_UNII = re.compile(r"^[A-Z0-9]{10}$")


@dataclass(frozen=True)
class Unii:
    value: str

    def __post_init__(self) -> None:
        if not _UNII.match(self.value):
            raise ValueError(f"Invalid UNII: {self.value!r}")
