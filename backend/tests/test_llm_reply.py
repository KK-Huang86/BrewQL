import json
from types import SimpleNamespace as NS

import pytest

from app.llm import REPLY_SCHEMA, Reply, ReplyError, parse_reply


def reply(*blocks, stop_reason="end_turn"):
    """Minimal stand-in for an anthropic Message: content blocks + stop_reason."""
    return NS(content=list(blocks), stop_reason=stop_reason)


def text(t):
    return NS(type="text", text=t)


def answer(kind, sql="", message=""):
    return text(json.dumps({"kind": kind, "sql": sql, "message": message}, ensure_ascii=False))


def test_sql_reply_yields_the_sql():
    assert parse_reply(reply(answer("sql", sql="SELECT COUNT(*) FROM cafes"))) == Reply(
        kind="sql", sql="SELECT COUNT(*) FROM cafes"
    )


def test_refuse_reply_yields_the_reason():
    assert parse_reply(reply(answer("refuse", message="只能查詢歷史資料"))) == Reply(
        kind="refuse", message="只能查詢歷史資料"
    )


def test_clarify_reply_yields_the_question_back():
    assert parse_reply(reply(answer("clarify", message="「最近」是指幾天內？"))) == Reply(
        kind="clarify", message="「最近」是指幾天內？"
    )


def test_refuse_never_carries_sql_even_if_the_model_wrote_some():
    # Only kind=sql may ever reach the executor.
    result = parse_reply(reply(answer("refuse", sql="DELETE FROM cafes", message="不能修改資料")))

    assert result.sql is None


@pytest.mark.parametrize(
    "block",
    [
        answer("sql", sql="  "),
        answer("refuse", message=" "),
        answer("clarify", message=""),
    ],
)
def test_kind_without_its_content_is_an_error(block):
    with pytest.raises(ReplyError, match="空"):
        parse_reply(reply(block))


def test_reply_cut_off_by_token_limit_is_an_error():
    with pytest.raises(ReplyError, match="上限"):
        parse_reply(reply(text('{"kind": "sql", "sql": "SELECT COUNT(*) FR'), stop_reason="max_tokens"))


def test_model_safety_refusal_is_a_refuse_without_reading_the_content():
    # The content of a refused reply is not trustworthy; never parse it.
    result = parse_reply(reply(answer("sql", sql="SELECT 1"), stop_reason="refusal"))

    assert result.kind == "refuse"
    assert result.sql is None
    assert result.message


@pytest.mark.parametrize(
    "blocks",
    [
        [],  # no text block at all
        [text("SELECT 1")],  # not JSON
        [text('{"sql": "SELECT 1"}')],  # missing kind
        [text('{"kind": "delete", "sql": "", "message": ""}')],  # unknown kind
        [text('{"kind": "sql", "sql": 42, "message": ""}')],  # sql not a string
        [text('{"kind": "refuse", "sql": "", "message": null}')],  # message not a string
        [text('["SELECT 1"]')],  # not an object
    ],
)
def test_reply_not_matching_schema_is_an_error(blocks):
    with pytest.raises(ReplyError, match="格式"):
        parse_reply(reply(*blocks))


def test_thinking_blocks_before_the_answer_are_skipped():
    # Haiku 5.5 thinks by default, so a thinking block may precede the JSON text.
    thinking = NS(type="thinking", thinking="", signature="sig")
    assert parse_reply(reply(thinking, answer("sql", sql="SELECT 1"))) == Reply(kind="sql", sql="SELECT 1")


def test_schema_forces_one_of_three_kinds():
    assert REPLY_SCHEMA["properties"]["kind"]["enum"] == ["sql", "refuse", "clarify"]
    assert set(REPLY_SCHEMA["required"]) == {"kind", "sql", "message"}
    assert REPLY_SCHEMA["additionalProperties"] is False
