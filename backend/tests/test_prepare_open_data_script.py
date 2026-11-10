"""The snapshot command (import-open-data D1): official downloads in, \\copy-ready snapshots out."""

import csv

from scripts.prepare_open_data import main, run
from tests.test_open_data import POPULATION_HEADER, population, university


def write_csv(path, rows):
    # Official files start with a UTF-8 BOM.
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def downloads(tmp_path):
    write_csv(tmp_path / "pop.csv", [POPULATION_HEADER, population("臺北市大安區", "290000", "11.3614")])
    write_csv(tmp_path / "univ.csv", [university("0001", "範例大學", "臺北市", "大安區", ownership="公立")])
    return tmp_path / "pop.csv", tmp_path / "univ.csv"


def test_snapshots_list_columns_in_table_order(tmp_path):
    out = tmp_path / "open_data"

    assert main(*downloads(tmp_path), out) == 0

    assert (out / "district_population.csv").read_text(encoding="utf-8").splitlines() == [
        "city,district,population,area_km2,as_of",
        "台北市,大安區,290000,11.3614,2025-12-31",
    ]
    assert (out / "universities.csv").read_text(encoding="utf-8").splitlines() == [
        "code,name,ownership,level,city,district",
        "0001,範例大學,公立,一般大學,台北市,大安區",
    ]


def test_rerun_writes_identical_files(tmp_path):
    out = tmp_path / "open_data"
    main(*downloads(tmp_path), out)
    first = {p.name: p.read_bytes() for p in out.iterdir()}

    main(*downloads(tmp_path), out)

    assert {p.name: p.read_bytes() for p in out.iterdir()} == first


def test_wrong_arguments_print_usage(capsys):
    assert run(["only-one.csv"]) == 2
    assert "usage" in capsys.readouterr().err
