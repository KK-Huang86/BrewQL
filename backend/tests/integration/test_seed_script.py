"""db/init/02_seed.sh picks the seed by DATASET (import-real-cafes D1, D3), run as Postgres init would."""

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import asyncpg

SEED_SCRIPT = Path(__file__).resolve().parents[3] / "db" / "init" / "02_seed.sh"


def run_seed(dsn: str, dataset: str | None) -> subprocess.CompletedProcess:
    url = urlparse(dsn)
    env = {
        **os.environ,
        "POSTGRES_USER": url.username,
        "POSTGRES_DB": url.path.lstrip("/"),
        "PGHOST": url.hostname,
        "PGPORT": str(url.port),
        "PGPASSWORD": url.password,
    }
    env.pop("DATASET", None)
    if dataset is not None:
        env["DATASET"] = dataset
    return subprocess.run(["bash", str(SEED_SCRIPT)], env=env, capture_output=True, text=True, check=False)


async def cafe_count(dsn: str) -> int:
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetchval("SELECT count(*) FROM cafes")
    finally:
        await conn.close()


async def test_real_leaves_the_tables_for_cafe_import(empty_db):
    done = run_seed(empty_db, "real")

    assert done.returncode == 0, done.stderr
    assert await cafe_count(empty_db) == 0


async def test_without_dataset_the_demo_seed_runs(empty_db):
    done = run_seed(empty_db, None)

    assert done.returncode == 0, done.stderr
    assert await cafe_count(empty_db) == 200


async def test_an_unknown_dataset_stops_init(empty_db):
    # A typo would otherwise seed demo into a volume named after it.
    done = run_seed(empty_db, "reel")

    assert done.returncode != 0
    assert "DATASET must be demo or real" in done.stderr
    assert await cafe_count(empty_db) == 0
