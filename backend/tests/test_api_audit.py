"""/api/ask leaves an audit trail (record-audit-log D3, D5, D6): a log line, then a stored record."""

import asyncio
import logging
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from app.audit import visitor_id
from app.daily_limit import DailyQuestionLimit
from app.input_guard import GuardrailUsage, GuardVerdict
from app.llm import ModelUsage, Reply
from app.main import create_app

MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
# Distinctive, so a log line that carries it is easy to spot.
QUESTION = "稽核測試：台北市大安區有幾家咖啡店？"
KEY = b"test-key-0123456789abcdef0123456789ab"
GOOD = Reply(kind="sql", sql="SELECT count(*) AS n FROM cafes", usage=ModelUsage(MODEL, 3000, 120))
BAD = Reply(kind="sql", sql="DELETE FROM cafes", usage=ModelUsage(MODEL, 3000, 40))


class Generator:
    """Plays back one outcome per call: a Reply, or an exception to raise."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes or [GOOD]), 0

    async def generate(self, question, feedback=()):
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class Executor:
    async def run(self, sql):
        return ["n"], [[40]]

    async def close(self):
        pass


class Guard:
    async def check(self, question):
        return GuardVerdict(blocked=False, usage=GuardrailUsage(1, 1))


class Events(logging.Handler):
    """Records the order of ask_audit log lines and audit writes."""

    def __init__(self):
        super().__init__()
        self.order = []

    def emit(self, record):
        if getattr(record, "event", None) == "ask_audit":
            self.order.append(("log", record.request_id))


class Writer:
    def __init__(self, events):
        self.events, self.records = events, []

    async def write(self, record):
        self.events.order.append(("write", str(record.request_id)))
        self.records.append(record)


@pytest.fixture
def events():
    handler = Events()
    logger = logging.getLogger("app.audit")
    # Production logs at INFO (configure_logging); without it the INFO audit line never reaches handlers.
    previous = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)
    logger.setLevel(previous)


def make_client(events, generator=None, daily_limit=None, max_sql_retries=0, writer=None, audit_timeout=None):
    writer = writer or Writer(events)
    timeout = {} if audit_timeout is None else {"audit_timeout_seconds": audit_timeout}
    app = create_app(
        generator=generator or Generator(),
        executor=Executor(),
        cors_origins=[],
        input_guard=Guard(),
        max_sql_retries=max_sql_retries,
        daily_limit=daily_limit,
        audit_writer=writer,
        visitor_key=KEY,
        **timeout,
    )
    return TestClient(app, raise_server_exceptions=False), writer


def test_answered_question_is_logged_then_stored(events):
    c, writer = make_client(events)

    assert c.post("/api/ask", json={"question": QUESTION}).status_code == 200

    [record] = writer.records
    assert (record.status, record.question, record.row_count) == ("ok", QUESTION, 1)
    # The log line comes first, so a failed write still leaves the second copy behind.
    assert events.order == [("log", str(record.request_id)), ("write", str(record.request_id))]


def test_audit_log_line_carries_the_record(events, caplog):
    c, writer = make_client(events)

    with caplog.at_level(logging.INFO, logger="app.audit"):
        c.post("/api/ask", json={"question": QUESTION})

    [line] = [r for r in caplog.records if getattr(r, "event", None) == "ask_audit"]
    [record] = writer.records
    assert line.request_id == str(record.request_id)
    # The executed SQL, as the guard rewrote it (LIMIT added).
    assert (line.question, line.sql, line.status) == (QUESTION, "SELECT COUNT(*) AS n FROM cafes LIMIT 1000", "ok")


def test_each_question_gets_its_own_request_id(events):
    c, writer = make_client(events)

    c.post("/api/ask", json={"question": QUESTION})
    c.post("/api/ask", json={"question": QUESTION})

    assert len({r.request_id for r in writer.records}) == 2


def test_unavailable_model_is_audited_as_an_outage(events):
    c, writer = make_client(events, generator=Generator(ConnectionError("bedrock down")))

    assert c.post("/api/ask", json={"question": QUESTION}).status_code == 502

    [record] = writer.records
    assert (record.status, record.error_kind) == ("error", "unavailable_model")


def test_question_over_the_daily_limit_is_not_audited(events):
    clock = lambda: datetime(2026, 11, 9, 4, 0, tzinfo=UTC)  # noqa: E731
    c, writer = make_client(events, daily_limit=DailyQuestionLimit(1, now=clock))

    c.post("/api/ask", json={"question": QUESTION})
    assert c.post("/api/ask", json={"question": QUESTION}).status_code == 429

    assert len(writer.records) == 1
    assert [kind for kind, _ in events.order] == ["log", "write"]


def test_visitor_comes_from_the_ip_nginx_forwards(events):
    c, writer = make_client(events)

    c.post("/api/ask", json={"question": QUESTION}, headers={"X-Real-IP": "198.51.100.7"})

    assert writer.records[0].visitor == visitor_id("198.51.100.7", KEY)


def test_visitor_falls_back_to_the_connecting_address(events):
    # An admin calling the backend directly through an SSH tunnel has no X-Real-IP.
    c, writer = make_client(events)

    c.post("/api/ask", json={"question": QUESTION})

    assert writer.records[0].visitor == visitor_id("testclient", KEY)


def test_only_the_audit_line_carries_the_question(events, caplog):
    # observability: question text is allowed in the ask_audit line and nowhere else, retries included.
    c, _ = make_client(events, generator=Generator(BAD, GOOD), max_sql_retries=1)

    with caplog.at_level(logging.DEBUG):
        c.post("/api/ask", json={"question": QUESTION})

    carrying = [r for r in caplog.records if QUESTION in r.getMessage() or QUESTION in str(r.__dict__)]
    assert [getattr(r, "event", None) for r in carrying] == ["ask_audit"]


class FailingWriter:
    def __init__(self, exc=None, delay=0.0):
        self.exc, self.delay, self.calls = exc, delay, 0

    async def write(self, record):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc


def failures(c):
    families = text_string_to_metric_families(c.get("/metrics").text)
    [value] = [s.value for f in families for s in f.samples if s.name == "brewql_audit_write_failures_total"]
    return value


def test_audit_failures_start_at_zero(events):
    c, _ = make_client(events)

    assert failures(c) == 0


def test_failed_write_still_answers_and_is_reported_once(events, caplog):
    writer = FailingWriter(exc=OSError("connection refused"))
    c, _ = make_client(events, writer=writer)

    with caplog.at_level(logging.ERROR, logger="app.audit"):
        response = c.post("/api/ask", json={"question": QUESTION})

    assert response.status_code == 200
    assert response.json()["rows"] == [[40]]
    assert writer.calls == 1  # never retried
    assert failures(c) == 1
    [error] = [r for r in caplog.records if r.levelno == logging.ERROR]
    audit_line = next(r for r in caplog.records if getattr(r, "event", None) == "ask_audit")
    assert error.request_id == audit_line.request_id  # traceable back to the logged copy
    assert QUESTION not in error.getMessage() and QUESTION not in str(error.__dict__)


def test_slow_write_times_out_instead_of_holding_the_answer(events, caplog):
    writer = FailingWriter(delay=5.0)
    c, _ = make_client(events, writer=writer, audit_timeout=0.05)

    with caplog.at_level(logging.ERROR, logger="app.audit"):
        response = c.post("/api/ask", json={"question": QUESTION})

    assert response.status_code == 200
    assert failures(c) == 1
    assert any(r.levelno == logging.ERROR and r.error == "TimeoutError" for r in caplog.records)


def test_outage_answer_survives_a_failed_audit_write(events):
    writer = FailingWriter(exc=OSError("connection refused"))
    c, _ = make_client(events, generator=Generator(ConnectionError("bedrock down")), writer=writer)

    assert c.post("/api/ask", json={"question": QUESTION}).status_code == 502
    assert failures(c) == 1
