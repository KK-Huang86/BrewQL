"""Load and validate the golden set; any problem stops the run before a paid model call."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

import yaml

Difficulty = Literal["easy", "medium", "hard", "refuse"]
ExpectedStatus = Literal["refused", "clarify"]
DIFFICULTIES = get_args(Difficulty)
EXPECTED_STATUSES = get_args(ExpectedStatus)
_KEYS = {"id", "difficulty", "question", "sql", "expect", "ordered"}


class GoldenSetError(ValueError):
    """The golden set file is unusable; the message names the question at fault."""


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    difficulty: Difficulty
    question: str
    # Exactly one of: a reference SQL whose result is the answer, or the status to expect.
    sql: str | None = None
    expect: ExpectedStatus | None = None
    # Compare rows in order (for "top N" style questions); otherwise order is ignored.
    ordered: bool = False


def load_golden_set(path: Path) -> list[GoldenQuestion]:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise GoldenSetError(f"cannot read golden set {path}: {e}") from e
    except yaml.YAMLError as e:
        raise GoldenSetError(f"golden set {path} is not valid YAML: {e}") from e
    if not isinstance(data, list) or not data:
        raise GoldenSetError(f"golden set {path} must be a non-empty list of questions")

    questions: list[GoldenQuestion] = []
    seen: set[str] = set()
    for index, entry in enumerate(data, start=1):
        question = _parse(entry, index)
        if question.id in seen:
            raise GoldenSetError(f"{question.id}: duplicate id")
        seen.add(question.id)
        questions.append(question)
    return questions


def _parse(entry: object, index: int) -> GoldenQuestion:
    if not isinstance(entry, dict):
        raise GoldenSetError(f"entry {index}: must be a mapping")
    qid = entry.get("id")
    if not isinstance(qid, str) or not qid.strip():
        raise GoldenSetError(f"entry {index}: missing id")

    def fail(reason: str) -> GoldenSetError:
        return GoldenSetError(f"{qid}: {reason}")

    unknown = set(entry) - _KEYS
    if unknown:
        raise fail(f"unknown keys {sorted(unknown)}")
    difficulty = entry.get("difficulty")
    if difficulty not in DIFFICULTIES:
        raise fail(f"difficulty must be one of {DIFFICULTIES}")
    text = entry.get("question")
    if not isinstance(text, str) or not text.strip():
        raise fail("question is blank")
    sql, expect, ordered = entry.get("sql"), entry.get("expect"), entry.get("ordered", False)
    if (sql is None) == (expect is None):
        raise fail("needs exactly one of sql or expect")
    if difficulty == "refuse" and expect is None:
        raise fail("refuse questions use expect, not sql")
    if difficulty != "refuse" and sql is None:
        raise fail("answerable questions need a reference sql")
    if expect is not None and expect not in EXPECTED_STATUSES:
        raise fail(f"expect must be one of {EXPECTED_STATUSES}")
    if sql is not None and (not isinstance(sql, str) or not sql.strip()):
        raise fail("sql is blank")
    if not isinstance(ordered, bool):
        raise fail("ordered must be true or false")
    if ordered and sql is None:
        raise fail("ordered only applies to questions with sql")
    return GoldenQuestion(
        id=qid,
        difficulty=difficulty,
        question=text.strip(),
        sql=sql.strip() if sql else None,
        expect=expect,
        ordered=ordered,
    )
