"""List / download FAERS bulk partitions for chosen quarters from the openFDA manifest.

Usage:  python scripts/download_faers.py 2026q2 2026q3 [--download]
"""
import sys

import httpx

MANIFEST = "https://api.fda.gov/download.json"


def partitions(quarters: list[str]) -> list[dict]:
    data = httpx.get(MANIFEST, timeout=60).json()
    parts = data["results"]["drug"]["event"]["partitions"]
    return [p for p in parts if p["file"].split("/")[-2] in quarters]


if __name__ == "__main__":
    qs = [a for a in sys.argv[1:] if not a.startswith("--")]
    sel = partitions(qs)
    print(f"{len(sel)} files, {sum(float(p.get('size_mb', 0)) for p in sel):,.0f} MB zipped")
    for p in sel:
        print(p["display_name"], p["file"])
        if "--download" in sys.argv:
            raise SystemExit("TODO: stream each file to ./data/faers/ and unzip")
