from pathlib import Path

from evaluation.__main__ import DEFAULT_GOLDEN, parse_args


def test_defaults_run_every_question_for_real():
    args = parse_args([])

    assert args.dry_run is False
    assert args.only is None
    assert args.golden == DEFAULT_GOLDEN
    assert DEFAULT_GOLDEN.name == "golden.yaml"


def test_only_takes_a_comma_separated_id_list():
    assert parse_args(["--only", "q01, q12,q15"]).only == {"q01", "q12", "q15"}


def test_dry_run_and_custom_golden_file():
    args = parse_args(["--dry-run", "--golden", "/tmp/g.yaml"])

    assert args.dry_run is True
    assert args.golden == Path("/tmp/g.yaml")
