"""The real cafe import command (import-real-cafes D3): skip, refuse, or write one batch."""

import csv

from app.real_cafes import RealBatch
from scripts.import_real_cafes import main
from tests.test_real_cafes import EXPORT_ROW, nomad, vote


class FakeStore:
    def __init__(self, *, has_cafes=False, fail=False):
        self._has_cafes, self._fail = has_cafes, fail
        self.written: list[RealBatch] = []

    async def has_cafes(self) -> bool:
        return self._has_cafes

    async def write(self, batch: RealBatch) -> None:
        if self._fail:
            raise RuntimeError("connection reset")
        self.written.append(batch)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def export_dir(tmp_path, *, skip=()):
    # pgAdmin export names carry the export date.
    files = {
        "cafes20261108.csv": [EXPORT_ROW],
        "cafe_cafeattributevote20261108.csv": [vote("google")],
        "cafe_nomad_cache20261108.csv": [nomad("n1", "測試咖啡")],
    }
    for name, rows in files.items():
        if name not in skip:
            write_csv(tmp_path / name, rows)
    return tmp_path


async def test_writes_one_batch_and_prints_the_report(tmp_path, capsys):
    store = FakeStore()

    code = await main(export_dir(tmp_path), dataset="real", store=store)

    assert code == 0
    [batch] = store.written
    assert (len(batch.cafes), len(batch.votes), len(batch.nomad)) == (1, 1, 1)
    assert "cafes=1 parsed=1 filled=0 unknown=0" in capsys.readouterr().out


async def test_demo_mode_skips_without_reading_anything(tmp_path, capsys):
    store = FakeStore()

    code = await main(tmp_path / "missing", dataset="demo", store=store)

    assert code == 0
    assert store.written == []
    assert "DATASET=demo" in capsys.readouterr().out


async def test_database_that_already_has_cafes_is_left_alone(tmp_path, capsys):
    store = FakeStore(has_cafes=True)

    code = await main(export_dir(tmp_path), dataset="real", store=store)

    assert code == 0
    assert store.written == []
    assert "already has cafes" in capsys.readouterr().out


async def test_missing_export_file_exits_2_before_writing(tmp_path, capsys):
    store = FakeStore()

    code = await main(export_dir(tmp_path, skip={"cafe_nomad_cache20261108.csv"}), dataset="real", store=store)

    assert code == 2
    assert store.written == []
    assert "cafe_nomad_cache*.csv" in capsys.readouterr().err


async def test_invalid_export_exits_2_before_writing(tmp_path, capsys):
    directory = export_dir(tmp_path)
    write_csv(directory / "cafe_cafeattributevote20261108.csv", [vote("google", cafe_id="404")])

    code = await main(directory, dataset="real", store=FakeStore())

    assert code == 2
    assert "vote for unknown cafe 404" in capsys.readouterr().err


async def test_failed_write_exits_1_and_says_nothing_was_written(tmp_path, capsys):
    code = await main(export_dir(tmp_path), dataset="real", store=FakeStore(fail=True))

    assert code == 1
    assert "nothing written" in capsys.readouterr().err
