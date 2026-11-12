"""National Drug Code. openFDA uses hyphenated 4-4, 5-3, 5-4 products and 4-4-2, 5-3-2, 5-4-1 packages;
RxNav returns 11 digits (5-4-2)."""
import re
from dataclasses import dataclass

_PRODUCT_SHAPES = {(4, 4), (5, 3), (5, 4)}
_PACKAGE_SHAPES = {(4, 4, 2), (5, 3, 2), (5, 4, 1)}


@dataclass(frozen=True)
class Ndc:
    labeler: str
    product: str
    package: str | None = None

    @classmethod
    def parse(cls, text: str) -> "Ndc":
        s = str(text).strip()
        if re.fullmatch(r"\d+-\d+-\d+", s):
            lab, prod, pack = s.split("-")
            if (len(lab), len(prod), len(pack)) not in _PACKAGE_SHAPES:
                raise ValueError(f"Unexpected NDC package shape: {text!r}")
            return cls(lab, prod, pack)
        if re.fullmatch(r"\d+-\d+", s):
            lab, prod = s.split("-")
            if (len(lab), len(prod)) not in _PRODUCT_SHAPES:
                raise ValueError(f"Unexpected NDC product shape: {text!r}")
            return cls(lab, prod, None)
        if re.fullmatch(r"\d{11}", s):
            return cls(s[:5], s[5:9], s[9:])
        if re.fullmatch(r"\d{9}", s):
            return cls(s[:5], s[5:9], None)
        raise ValueError(f"Cannot parse NDC: {text!r}")

    @property
    def product_ndc(self) -> str:
        return f"{self.labeler}-{self.product}"

    @property
    def package_ndc(self) -> str:
        if self.package is None:
            raise ValueError("Product-level NDC has no package")
        return f"{self.labeler}-{self.product}-{self.package}"

    @property
    def product11(self) -> str:
        return self.labeler.zfill(5) + self.product.zfill(4)

    def to_ndc11(self) -> str:
        """ndc11 = labeler.zfill(5) + product.zfill(4) + package.zfill(2)."""
        if self.package is None:
            raise ValueError("Product-level NDC has no package")
        return self.product11 + self.package.zfill(2)
