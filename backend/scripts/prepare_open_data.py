"""Turn official open-data downloads into the snapshots in db/init/open_data (import-open-data D1).

    uv --directory backend run python -m scripts.prepare_open_data POPULATION.csv UNIVERSITIES.csv ../db/init/open_data

Sources and versions are listed in the README. The downloads stay outside the repo; rerunning on
the same downloads writes identical files. Columns follow the table order so 06_open_data.sh can
\\copy them as they are.
"""

import csv
import sys
from collections.abc import Iterable
from dataclasses import astuple, fields
from pathlib import Path

from app.open_data import PopulationRow, UniversityRow, population_rows, university_rows


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:  # official files start with a BOM
        return list(csv.DictReader(f))


def _write(path: Path, row_type: type, rows: Iterable[PopulationRow | UniversityRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(field.name for field in fields(row_type))
        writer.writerows(astuple(row) for row in rows)


def main(population_csv: Path, universities_csv: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    population = population_rows(_read(population_csv))
    universities = university_rows(_read(universities_csv))
    _write(out_dir / "district_population.csv", PopulationRow, population)
    _write(out_dir / "universities.csv", UniversityRow, universities)
    print(f"district_population={len(population)} universities={len(universities)}")
    return 0


def run(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m scripts.prepare_open_data POPULATION.csv UNIVERSITIES.csv OUT_DIR", file=sys.stderr)
        return 2
    return main(*(Path(arg) for arg in argv))


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
