"""Turn official open-data downloads into the snapshots in db/init/open_data (import-open-data D1,
import-transit-open-data D1).

    uv --directory backend run python -m scripts.prepare_open_data \\
        POPULATION.csv UNIVERSITIES.csv YOUBIKE_TAIPEI.json YOUBIKE_NEW_TAIPEI.json MRT_EXITS.csv \\
        AS_OF ../db/init/open_data

AS_OF is the day the YouBike and MRT files were downloaded (YYYY-MM-DD): those feeds carry no
version, so the download day is their data date. Sources and versions are listed in the README.
The downloads stay outside the repo; rerunning on the same downloads and day writes identical
files. Columns follow the table order so 06_open_data.sh can \\copy them as they are.
"""

import csv
import json
import sys
from collections.abc import Iterable
from dataclasses import astuple, fields
from datetime import date
from pathlib import Path

from app.open_data import (
    MrtRow,
    PopulationRow,
    UniversityRow,
    YoubikeRow,
    mrt_rows,
    population_rows,
    university_rows,
    youbike_rows,
)

USAGE = (
    "usage: python -m scripts.prepare_open_data POPULATION.csv UNIVERSITIES.csv "
    "YOUBIKE_TAIPEI.json YOUBIKE_NEW_TAIPEI.json MRT_EXITS.csv AS_OF OUT_DIR"
)


def _read(path: Path, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    # Ministry files start with a BOM; the Taipei Metro exit file is Big5 (cp950).
    with path.open(encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, row_type: type, rows: Iterable[PopulationRow | UniversityRow | YoubikeRow | MrtRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(field.name for field in fields(row_type))
        writer.writerows(astuple(row) for row in rows)


def main(
    population_csv: Path,
    universities_csv: Path,
    youbike_taipei_json: Path,
    youbike_new_taipei_json: Path,
    mrt_exits_csv: Path,
    as_of: date,
    out_dir: Path,
) -> int:
    population = population_rows(_read(population_csv))
    universities = university_rows(_read(universities_csv))
    districts = {(row.city, row.district) for row in population}
    youbike = youbike_rows(_read_json(youbike_taipei_json), _read_json(youbike_new_taipei_json), districts, as_of)
    mrt = mrt_rows(_read(mrt_exits_csv, encoding="cp950"), youbike, as_of)
    # Every snapshot is built before any is written, so a bad download leaves the old files alone.
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "district_population.csv", PopulationRow, population)
    _write(out_dir / "universities.csv", UniversityRow, universities)
    _write(out_dir / "youbike_stations.csv", YoubikeRow, youbike)
    _write(out_dir / "mrt_stations.csv", MrtRow, mrt)
    print(
        f"district_population={len(population)} universities={len(universities)} "
        f"youbike_stations={len(youbike)} mrt_stations={len(mrt)}"
    )
    return 0


def run(argv: list[str]) -> int:
    if len(argv) != 7:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        as_of = date.fromisoformat(argv[5])
    except ValueError:
        print(f"AS_OF must be YYYY-MM-DD, got {argv[5]!r}\n{USAGE}", file=sys.stderr)
        return 2
    paths = [Path(arg) for arg in argv]
    return main(*paths[:5], as_of, paths[6])


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
