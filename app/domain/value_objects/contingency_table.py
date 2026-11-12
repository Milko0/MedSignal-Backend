from dataclasses import dataclass


@dataclass(frozen=True)
class ContingencyTable:
    """2x2 table for one (drug D, reaction R) pair.

    a: reports with D and R        b: reports with D, without R
    c: reports with other drugs and R   d: reports with other drugs, without R
    """

    a: int
    b: int
    c: int
    d: int

    @property
    def total(self) -> int:
        return self.a + self.b + self.c + self.d
