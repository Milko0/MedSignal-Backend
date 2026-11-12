from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, order=True)
class Quarter:
    """Calendar quarter of the report receive date (open question 4: receivedate, not the FDA file quarter)."""

    year: int
    q: int

    @classmethod
    def from_date(cls, d: date) -> "Quarter":
        return cls(d.year, (d.month - 1) // 3 + 1)

    @classmethod
    def parse(cls, text: str) -> "Quarter":
        year, q = text.upper().split("Q")
        return cls(int(year), int(q))

    def previous(self) -> "Quarter":
        return Quarter(self.year, self.q - 1) if self.q > 1 else Quarter(self.year - 1, 4)

    def __str__(self) -> str:
        return f"{self.year}Q{self.q}"
