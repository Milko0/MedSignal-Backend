"""JSON Lines import/export of the clean dataset (data/clean/*.jsonl). Mongo can load the same files with mongoimport."""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from app.application.container import Container
from app.domain.entities.drug import Drug
from app.domain.entities.excluded_term import ExcludedTerm
from app.domain.entities.label import DrugLabel
from app.domain.entities.name_mapping import NameMapping
from app.domain.entities.product import Product
from app.domain.entities.recall import Recall
from app.domain.entities.report import AdverseReport
from app.domain.entities.rx_concept import RxConcept
from app.domain.entities.shortage import ShortageEvent, ShortageRecord
from app.domain.entities.signal import SafetySignal

# file name -> (model, container attribute)
FILES = {
    "ingredients.jsonl": (Drug, "ingredients"),
    "rx_concepts.jsonl": (RxConcept, "rx_concepts"),
    "products.jsonl": (Product, "products"),
    "labels.jsonl": (DrugLabel, "labels"),
    "shortages.jsonl": (ShortageRecord, "shortages"),
    "recalls.jsonl": (Recall, "recalls"),
    "name_map.jsonl": (NameMapping, "name_map"),
    "reports.jsonl": (AdverseReport, "reports"),
    "signals.jsonl": (SafetySignal, "signals"),
    "excluded_terms.jsonl": (ExcludedTerm, "excluded_terms"),
}
EVENTS_FILE = "shortage_events.jsonl"


def _line(model) -> str:
    """Compact JSON line: None and default values are left out (every default is a constant, so loading restores
    them). Saves about 30% on reports, whose embedded drugs carry many empty fields."""
    return model.model_dump_json(exclude_none=True, exclude_defaults=True) + "\n"


def export_dataset(c: Container, directory: str) -> dict:
    """Writes every collection and a size report (the 50-100 MB rule of the brief)."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"created_at": datetime.now(UTC).isoformat(), "files": {}}
    for name, (_, attr) in FILES.items():
        items = getattr(c, attr).all_items()
        with open(out / name, "w", encoding="utf-8") as f:
            f.writelines(_line(it) for it in items)
        report["files"][name] = {"records": len(items), "bytes": os.path.getsize(out / name)}
    events = c.shortages.all_events()
    with open(out / EVENTS_FILE, "w", encoding="utf-8") as f:
        f.writelines(_line(e) for e in events)
    report["files"][EVENTS_FILE] = {"records": len(events), "bytes": os.path.getsize(out / EVENTS_FILE)}
    report["total_bytes"] = sum(v["bytes"] for v in report["files"].values())
    report["total_megabytes"] = round(report["total_bytes"] / 1_000_000, 2)
    (out / "meta.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def _read_batches(path: Path, model, size: int):
    if not path.exists():
        return
    batch = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                batch.append(model.model_validate_json(line))
                if len(batch) >= size:
                    yield batch
                    batch = []
    if batch:
        yield batch


def _read(path: Path, model):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [model.model_validate_json(line) for line in f if line.strip()]


async def load_dataset(c: Container, directory: str, batch_size: int = 5000) -> dict[str, int]:
    """Fills a container from data/clean through the ports, so the same code loads the memory adapters or
    MongoDB + Redis. Writes in batches of `batch_size`. Missing files are skipped, so a partial dataset still starts."""
    base = Path(directory)
    counts: dict[str, int] = {}
    for name, (model, attr) in FILES.items():
        repo = getattr(c, attr)
        if attr in ("excluded_terms", "shortages"):            # small; shortages must be replaced as one snapshot
            items = _read(base / name, model)
            if attr == "excluded_terms":
                for it in items:
                    await repo.add(it)
            else:
                await repo.replace_current(items)
            counts[name] = len(items)
            continue
        counts[name] = 0
        for batch in _read_batches(base / name, model, batch_size):   # bounded memory (Virtual Lab VMs)
            await repo.upsert_many(batch)
            counts[name] += len(batch)
    events = _read(base / EVENTS_FILE, ShortageEvent)
    if events:
        await c.shortages.add_events(events)
    counts[EVENTS_FILE] = len(events)
    return counts
