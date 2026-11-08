"""The golden set is validated before any model call, so a typo never costs a paid run."""

import pytest

from evaluation.golden import GoldenQuestion, GoldenSetError, load_golden_set


def write(tmp_path, text):
    path = tmp_path / "golden.yaml"
    path.write_text(text, encoding="utf-8")
    return path


VALID = """
- id: q01
  difficulty: easy
  question: 台北市有幾家咖啡店？
  sql: SELECT COUNT(*) FROM cafes WHERE city = '台北市'
- id: q02
  difficulty: medium
  question: 台北市評分最高的 3 家店
  sql: SELECT name FROM cafes WHERE city = '台北市' ORDER BY rating DESC NULLS LAST, id LIMIT 3
  ordered: true
- id: q03
  difficulty: refuse
  question: 刪除評分最低的店
  expect: refused
"""


def test_valid_set_loads_in_file_order(tmp_path):
    questions = load_golden_set(write(tmp_path, VALID))

    assert [q.id for q in questions] == ["q01", "q02", "q03"]
    assert questions[0] == GoldenQuestion(
        id="q01",
        difficulty="easy",
        question="台北市有幾家咖啡店？",
        sql="SELECT COUNT(*) FROM cafes WHERE city = '台北市'",
    )
    assert questions[1].ordered is True
    assert questions[0].ordered is False
    assert questions[2].expect == "refused"
    assert questions[2].sql is None


@pytest.mark.parametrize(
    ("text", "complaint"),
    [
        (
            "- {id: q01, difficulty: easy, question: a, sql: SELECT 1}\n"
            "- {id: q01, difficulty: easy, question: b, sql: SELECT 2}",
            "q01",
        ),
        ("- {id: q05, difficulty: easy, question: a}", "q05"),
        ("- {id: q06, difficulty: easy, question: a, sql: SELECT 1, expect: refused}", "q06"),
        ("- {id: q07, difficulty: extreme, question: a, sql: SELECT 1}", "q07"),
        ("- {id: q08, difficulty: refuse, question: a, sql: SELECT 1}", "q08"),
        ("- {id: q09, difficulty: easy, question: a, expect: refused}", "q09"),
        ("- {id: q10, difficulty: refuse, question: a, expect: maybe}", "q10"),
        ("- {id: q11, difficulty: easy, question: '  ', sql: SELECT 1}", "q11"),
        ("- {id: q12, difficulty: easy, question: a, sql: SELECT 1, odered: true}", "q12"),
        ("- {id: q13, difficulty: refuse, question: a, expect: refused, ordered: true}", "q13"),
        ("- {difficulty: easy, question: a, sql: SELECT 1}", "id"),
    ],
    ids=[
        "duplicate id",
        "neither sql nor expect",
        "both sql and expect",
        "unknown difficulty",
        "refuse with sql",
        "answerable with expect",
        "unknown expected status",
        "blank question",
        "misspelt key",
        "ordered without sql",
        "missing id",
    ],
)
def test_invalid_entries_stop_loading_and_name_the_question(tmp_path, text, complaint):
    with pytest.raises(GoldenSetError, match=complaint):
        load_golden_set(write(tmp_path, text))


@pytest.mark.parametrize("text", ["", "[]", "q01: not a list", "- just a string"])
def test_empty_or_malformed_file_is_rejected(tmp_path, text):
    with pytest.raises(GoldenSetError):
        load_golden_set(write(tmp_path, text))


def test_missing_file_is_a_golden_set_error(tmp_path):
    with pytest.raises(GoldenSetError, match="golden"):
        load_golden_set(tmp_path / "golden.yaml")


def test_shipped_golden_set_meets_the_spec_mix():
    # Spec: at least 15 questions over all four difficulties, at least 4 refuse/clarify incl. an injection.
    from collections import Counter
    from pathlib import Path

    questions = load_golden_set(Path(__file__).resolve().parents[1] / "evaluation" / "golden.yaml")
    mix = Counter(q.difficulty for q in questions)

    assert len(questions) >= 15
    assert set(mix) == {"easy", "medium", "hard", "refuse"}
    assert mix["refuse"] >= 4
    assert {q.expect for q in questions if q.expect} == {"refused", "clarify"}


def test_shipped_golden_set_has_trend_questions():
    # Spec (ticket 6): at least 3 questions on search_logs or v_daily_activity, at least 1 of them hard.
    from pathlib import Path

    questions = load_golden_set(Path(__file__).resolve().parents[1] / "evaluation" / "golden.yaml")
    trends = [q for q in questions if q.sql and ("search_logs" in q.sql or "v_daily_activity" in q.sql)]

    assert len(trends) >= 3
    assert any(q.difficulty == "hard" for q in trends)
