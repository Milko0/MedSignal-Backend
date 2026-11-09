"""2x2 table for one drug-reaction pair (see proposal section 6)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ContingencyTable:
    a: int  # drug and reaction
    b: int  # drug, no reaction
    c: int  # other drugs, reaction
    d: int  # other drugs, no reaction

    @property
    def n(self) -> int:
        return self.a + self.b + self.c + self.d
