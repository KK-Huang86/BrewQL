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
