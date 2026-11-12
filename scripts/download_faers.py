"""Download FAERS bulk partitions (openFDA /drug/event) for a rolling window of quarters.

    python -m scripts.download_faers --latest 4 --parts-per-quarter 2 --dry-run      # what would be downloaded
    python -m scripts.download_faers --latest 4 --parts-per-quarter 2 --prune        # download + drop old quarters
    python -m scripts.download_faers --quarters 2026q2 2026q3 --parts-per-quarter all

Sizes (manifest of Nov 2026): a quarter is ~30 partitions, ~2.5-3 GB zipped, ~350k reports; one partition is
~85 MB zipped and ~12k reports. The clean dataset keeps only the fields we use, so it is far smaller than the zips.
`--parts-per-quarter K` takes K partitions spread evenly over each quarter: the same sampling rate in every
quarter keeps the PRRs comparable across quarters (a PRR is a ratio, so it is stable under uniform sampling;
only the counts shrink, so fewer pairs reach a >= 3).

Rolling window: each run keeps the newest N quarters of the manifest. With --prune, zips of quarters that left the
window are deleted, so data/faers never grows (Q1..Q4 -> next quarter -> Q2..Q5). Files already downloaded with the
right size are skipped, so a re-run only fetches the new quarter.
"""
import argparse
import sys
from pathlib import Path

import httpx

MANIFEST = "https://api.fda.gov/download.json"


def quarter_of(part: dict) -> str:
    return part["file"].split("/")[-2]          # .../drug/event/2026q3/drug-event-0001-of-0036.json.zip


def load_partitions() -> list[dict]:
    data = httpx.get(MANIFEST, timeout=60).json()
    return [p for p in data["results"]["drug"]["event"]["partitions"] if quarter_of(p)[:4].isdigit()]


def spread(items: list, k: int | None) -> list:
    """k items evenly spread over the list (all of them when k is None or >= len)."""
    if k is None or k >= len(items):
        return items
    return [items[int((i + 0.5) * len(items) / k)] for i in range(k)]


def select(parts: list[dict], quarters: list[str] | None, latest: int | None, per_quarter: int | None) -> list[dict]:
    by_q: dict[str, list[dict]] = {}
    for p in parts:
        by_q.setdefault(quarter_of(p), []).append(p)
    chosen = [q.lower() for q in quarters] if quarters else sorted(by_q)[-(latest or 4):]
    missing = [q for q in chosen if q not in by_q]
    if missing:
        raise SystemExit(f"Not in the manifest: {missing}. Latest available: {sorted(by_q)[-4:]}")
    return [p for q in chosen for p in spread(sorted(by_q[q], key=lambda x: x["file"]), per_quarter)]


def local_path(out: Path, part: dict) -> Path:
    return out / f"{quarter_of(part)}-{part['file'].split('/')[-1]}"


def download(part: dict, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", part["file"], timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {dest.name}: {done / total:6.1%}", end="", flush=True)
    tmp.replace(dest)
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quarters", nargs="+", help="explicit quarters, e.g. 2026q2 2026q3")
    ap.add_argument("--latest", type=int, default=None, help="newest N quarters of the manifest (default 4)")
    ap.add_argument("--parts-per-quarter", default="2", help="partitions per quarter, or 'all' (default 2)")
    ap.add_argument("--out", default="data/faers")
    ap.add_argument("--prune", action="store_true", help="delete local zips of quarters outside the selection")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    per_q = None if a.parts_per_quarter == "all" else int(a.parts_per_quarter)
    sel = select(load_partitions(), a.quarters, a.latest, per_q)
    out = Path(a.out)
    quarters = sorted({quarter_of(p) for p in sel})
    zipped = sum(float(p.get("size_mb", 0)) for p in sel)
    records = sum(int(p.get("records", 0) or 0) for p in sel)
    print(f"Quarters {quarters}: {len(sel)} files, {zipped:,.0f} MB zipped, ~{records:,} reports")
    if a.dry_run:
        for p in sel:
            print(f"  {local_path(out, p).name}  {p.get('size_mb')} MB  {p.get('records')} reports")
        return

    out.mkdir(parents=True, exist_ok=True)
    if a.prune:
        for f in sorted(out.glob("*.json.zip")):
            if f.name.split("-")[0] not in quarters:
                print(f"  prune {f.name} (outside the window)")
                f.unlink()
    for p in sel:
        dest = local_path(out, p)
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  skip {dest.name} (already here)")
            continue
        try:
            download(p, dest)
        except httpx.HTTPError as exc:
            print(f"  FAILED {dest.name}: {exc}", file=sys.stderr)
    print(f"Done. Build with: python -m scripts.build_clean_dataset --faers \"{out.as_posix()}/*.json.zip\"")


if __name__ == "__main__":
    main()
