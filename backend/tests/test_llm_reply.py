from types import SimpleNamespace as NS

import pytest

from app.llm import ReplyError, parse_reply


def reply(*blocks, stop_reason="end_turn"):
    """Minimal stand-in for an anthropic Message: content blocks + stop_reason."""
    return NS(content=list(blocks), stop_reason=stop_reason)


def text(t):
    return NS(type="text", text=t)


def test_valid_structured_reply_yields_sql():
    assert parse_reply(reply(text('{"sql": "SELECT COUNT(*) FROM cafes"}'))) == "SELECT COUNT(*) FROM cafes"


def test_blank_sql_is_an_error():
    with pytest.raises(ReplyError, match="空"):
        parse_reply(reply(text('{"sql": "  "}')))


def test_reply_cut_off_by_token_limit_is_an_error():
    with pytest.raises(ReplyError, match="上限"):
        parse_reply(reply(text('{"sql": "SELECT COUNT(*) FR'), stop_reason="max_tokens"))


def test_model_refusal_is_an_error():
    with pytest.raises(ReplyError, match="拒絕"):
        parse_reply(reply(stop_reason="refusal"))


@pytest.mark.parametrize(
    "blocks",
    [
        [],  # no text block at all
        [text("SELECT 1")],  # not JSON
        [text('{"query": "SELECT 1"}')],  # missing sql
        [text('{"sql": 42}')],  # sql not a string
        [text('["SELECT 1"]')],  # not an object
    ],
)
def test_reply_not_matching_schema_is_an_error(blocks):
    with pytest.raises(ReplyError, match="格式"):
        parse_reply(reply(*blocks))


def test_thinking_blocks_before_the_answer_are_skipped():
    # Haiku 5.5 thinks by default, so a thinking block may precede the JSON text.
    thinking = NS(type="thinking", thinking="", signature="sig")
    assert parse_reply(reply(thinking, text('{"sql": "SELECT 1"}'))) == "SELECT 1"
