from types import SimpleNamespace as NS

from app.llm import parse_reply


def reply(*blocks, stop_reason="end_turn"):
    """Minimal stand-in for an anthropic Message: content blocks + stop_reason."""
    return NS(content=list(blocks), stop_reason=stop_reason)


def text(t):
    return NS(type="text", text=t)


def test_valid_structured_reply_yields_sql():
    assert parse_reply(reply(text('{"sql": "SELECT COUNT(*) FROM cafes"}'))) == "SELECT COUNT(*) FROM cafes"
