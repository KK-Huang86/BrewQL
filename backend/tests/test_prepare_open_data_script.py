"""The snapshot command (import-open-data D1, import-transit-open-data D1): official downloads in,
\\copy-ready snapshots out."""

import csv
import json
from datetime import date

import pytest

from scripts.prepare_open_data import main, run
from tests.test_mrt_open_data import exit_
from tests.test_open_data import POPULATION_HEADER, population, university
from tests.test_youbike_open_data import taipei

AS_OF = "2026-11-11"


def write_csv(path, rows):
    # Official files start with a UTF-8 BOM.
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# The real downloads always have the stations in MRT_DISTRICT_FIXES and the districts they point
# to: a fix for a missing station or to an unknown district stops the build.
FIXED_STATIONS = ["公館", "南京復興", "台電大樓", "國父紀念館", "後山埤", "忠孝新生", "雙連"]
OTHER_DISTRICTS = ["中正區", "信義區", "南港區", "大同區", "松山區"]


def downloads(tmp_path):
    write_csv(
        tmp_path / "pop.csv",
        [POPULATION_HEADER, population("臺北市大安區", "290000", "11.3614")]
        + [population(f"臺北市{district}") for district in OTHER_DISTRICTS],
    )
    write_csv(tmp_path / "univ.csv", [university("0001", "範例大學", "臺北市", "大安區", ownership="公立")])
    # 大安區 first, so the 大安 MRT station (all at one spot) takes its district from it.
    bikes = [taipei(f"50010100{i}", sarea=d) for i, d in enumerate(["大安區", *OTHER_DISTRICTS], start=1)]
    (tmp_path / "yb_taipei.json").write_text(json.dumps(bikes), encoding="utf-8")
    (tmp_path / "yb_new_taipei.json").write_text(json.dumps([]), encoding="utf-8")
    # The Taipei Metro exit file is Big5 (cp950), without a BOM.
    with (tmp_path / "exits.csv").open("w", encoding="cp950", newline="") as f:
        exits = [exit_(f"{name}站出口1", "1", "25.026050", "121.543600") for name in ["大安", *FIXED_STATIONS]]
        writer = csv.DictWriter(f, fieldnames=list(exits[0]))
        writer.writeheader()
        writer.writerows(exits)
    names = ("pop.csv", "univ.csv", "yb_taipei.json", "yb_new_taipei.json", "exits.csv")
    return *(tmp_path / name for name in names), date.fromisoformat(AS_OF)


def test_snapshots_list_columns_in_table_order(tmp_path):
    out = tmp_path / "open_data"

    assert main(*downloads(tmp_path), out) == 0

    assert (out / "district_population.csv").read_text(encoding="utf-8").splitlines() == [
        "city,district,population,area_km2,as_of",
        "台北市,中正區,100000,10.5,2025-12-31",
        "台北市,信義區,100000,10.5,2025-12-31",
        "台北市,南港區,100000,10.5,2025-12-31",
        "台北市,大同區,100000,10.5,2025-12-31",
        "台北市,大安區,290000,11.3614,2025-12-31",
        "台北市,松山區,100000,10.5,2025-12-31",
    ]
    assert (out / "universities.csv").read_text(encoding="utf-8").splitlines() == [
        "code,name,ownership,level,city,district",
        "0001,範例大學,公立,一般大學,台北市,大安區",
    ]
    assert (out / "youbike_stations.csv").read_text(encoding="utf-8").splitlines() == [
        "station_no,name,city,district,docks,lat,lng,as_of",
        f"500101001,範例站01,台北市,大安區,28,25.026050,121.543600,{AS_OF}",
        f"500101002,範例站02,台北市,中正區,28,25.026050,121.543600,{AS_OF}",
        f"500101003,範例站03,台北市,信義區,28,25.026050,121.543600,{AS_OF}",
        f"500101004,範例站04,台北市,南港區,28,25.026050,121.543600,{AS_OF}",
        f"500101005,範例站05,台北市,大同區,28,25.026050,121.543600,{AS_OF}",
        f"500101006,範例站06,台北市,松山區,28,25.026050,121.543600,{AS_OF}",
    ]
    assert (out / "mrt_stations.csv").read_text(encoding="utf-8").splitlines() == [
        "name,city,district,exit_count,lat,lng,as_of",
        f"公館,台北市,中正區,1,25.026050,121.543600,{AS_OF}",
        f"南京復興,台北市,松山區,1,25.026050,121.543600,{AS_OF}",
        f"台電大樓,台北市,中正區,1,25.026050,121.543600,{AS_OF}",
        f"國父紀念館,台北市,信義區,1,25.026050,121.543600,{AS_OF}",
        f"大安,台北市,大安區,1,25.026050,121.543600,{AS_OF}",
        f"後山埤,台北市,南港區,1,25.026050,121.543600,{AS_OF}",
        f"忠孝新生,台北市,大安區,1,25.026050,121.543600,{AS_OF}",
        f"雙連,台北市,大同區,1,25.026050,121.543600,{AS_OF}",
    ]


def test_rerun_writes_identical_files(tmp_path):
    out = tmp_path / "open_data"
    main(*downloads(tmp_path), out)
    first = {p.name: p.read_bytes() for p in out.iterdir()}

    main(*downloads(tmp_path), out)

    assert {p.name: p.read_bytes() for p in out.iterdir()} == first


def test_youbike_districts_are_checked_against_the_population_snapshot(tmp_path):
    population_csv, *rest = downloads(tmp_path)
    write_csv(population_csv, [POPULATION_HEADER, population("臺北市中正區")])

    with pytest.raises(ValueError, match="台北市大安區"):
        main(population_csv, *rest, tmp_path / "open_data")


def test_command_line_reads_the_download_day(tmp_path):
    *files, _ = downloads(tmp_path)
    out = tmp_path / "open_data"

    assert run([*map(str, files), AS_OF, str(out)]) == 0
    assert (out / "mrt_stations.csv").read_text(encoding="utf-8").splitlines()[1].endswith(AS_OF)


def test_a_download_day_that_is_not_a_date_prints_usage(tmp_path, capsys):
    *files, _ = downloads(tmp_path)

    assert run([*map(str, files), "yesterday", str(tmp_path / "open_data")]) == 2
    assert "usage" in capsys.readouterr().err


def test_wrong_arguments_print_usage(capsys):
    assert run(["only-one.csv"]) == 2
    assert "usage" in capsys.readouterr().err
