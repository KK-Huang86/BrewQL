"""Import real Find Coffee cafes into an empty real-mode database (import-real-cafes D3).

    DATASET=real docker compose up          # runs as the cafe-import service before the backend

Reads the pgAdmin exports from REAL_DATA_DIR (outside the repo), keeps only public columns, and
writes everything in one transaction. Exit codes: 0 done or skipped (demo mode, cafes already
there), 1 write failed (nothing written), 2 missing or invalid exports or settings (nothing written).
"""

import asyncio
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Protocol

from app.real_cafes import RealBatch, prepare

log = logging.getLogger(__name__)

# pgAdmin names each export after its table plus the export date, e.g. cafes20261108.csv.
EXPORTS = ("cafes*.csv", "cafe_cafeattributevote*.csv", "cafe_nomad_cache*.csv")


class RealCafeStore(Protocol):
    async def has_cafes(self) -> bool: ...

    async def write(self, batch: RealBatch) -> None: ...


class ExportError(Exception):
    pass


async def main(directory: Path, *, dataset: str, store: RealCafeStore) -> int:
    if dataset == "demo":
        print("DATASET=demo: real cafe import skipped")
        return 0
    if dataset != "real":
        print(f"DATASET must be demo or real, got {dataset!r}", file=sys.stderr)
        return 2
    if await store.has_cafes():
        # Only an empty database is imported; rebuild the real volume to import a newer export.
        print("database already has cafes: real cafe import skipped")
        return 0
    try:
        batch = prepare(*(_read(_find(directory, pattern)) for pattern in EXPORTS))
    except (ExportError, ValueError, KeyError) as e:
        print(f"export error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    try:
        await store.write(batch)
    except Exception as e:
        log.error("real cafe import failed", extra={"error": type(e).__name__})
        print(f"import failed, nothing written: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(" ".join(f"{k}={v}" for k, v in batch.report.items()))
    return 0


def _find(directory: Path, pattern: str) -> Path:
    found = sorted(directory.glob(pattern))
    if len(found) != 1:
        raise ExportError(f"expected one {pattern} in {directory}, found {len(found)}")
    return found[0]


def _read(path: Path) -> list[dict[str, str]]:
    # pgAdmin may write a byte order mark; utf-8-sig drops it.
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


async def _run() -> int:
    from app.logging_setup import configure_logging
    from app.real_cafes_store import PgRealCafeStore

    configure_logging()
    dataset = os.environ.get("DATASET", "demo")
    dsn = os.environ.get("REAL_IMPORT_DATABASE_URL", "")
    if dataset == "real" and not dsn:
        print("REAL_IMPORT_DATABASE_URL is not set (database owner)", file=sys.stderr)
        return 2
    store = PgRealCafeStore(dsn)
    try:
        return await main(Path(os.environ.get("REAL_DATA_DIR", "/real-data")), dataset=dataset, store=store)
    finally:
        await store.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
