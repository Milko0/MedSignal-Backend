from dataclasses import dataclass


@dataclass(frozen=True)
class Rxcui:
    """RxNorm concept id. Always a string (DailyMed returns an int elsewhere)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.isdigit():
            raise ValueError(f"Invalid RxCUI: {self.value!r}")

    @classmethod
    def of(cls, raw) -> "Rxcui":
        return cls(str(raw).strip())

    def __str__(self) -> str:
        return self.value
