"""The production app cannot start without an audit trail (record-audit-log D4)."""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.audit import PgAuditWriter

KEY = "test-key-0123456789abcdef0123456789ab"


@pytest.fixture(autouse=True)
def database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")


@pytest.mark.parametrize("name", ["AUDIT_DATABASE_URL", "AUDIT_IP_HMAC_KEY"])
def test_missing_audit_setting_refuses_to_start(monkeypatch, name):
    monkeypatch.delenv(name)

    with pytest.raises(RuntimeError, match=name):
        main.build_app()


def test_short_visitor_key_refuses_to_start(monkeypatch):
    # A short key makes the IP HMAC guessable by brute force over the IPv4 space.
    monkeypatch.setenv("AUDIT_IP_HMAC_KEY", "x" * 31)

    with pytest.raises(RuntimeError, match="AUDIT_IP_HMAC_KEY"):
        main.build_app()


def test_production_app_writes_audit_to_postgres_with_the_configured_key(monkeypatch):
    seen = {}
    real_create_app = main.create_app

    def spy(**kwargs):
        seen.update(kwargs)
        return real_create_app(**kwargs)

    monkeypatch.setattr(main, "create_app", spy)
    main.build_app()

    assert isinstance(seen["audit_writer"], PgAuditWriter)
    assert seen["visitor_key"] == KEY.encode()


class ClosingWriter:
    def __init__(self):
        self.closed = False

    async def write(self, record):
        pass

    async def close(self):
        self.closed = True


class Executor:
    async def run(self, sql):
        return [], []

    async def close(self):
        pass


class Generator:
    async def generate(self, question, feedback=()):
        raise AssertionError("not called")


def test_shutdown_closes_the_audit_writer():
    writer = ClosingWriter()
    app = main.create_app(generator=Generator(), executor=Executor(), cors_origins=[], audit_writer=writer)

    with TestClient(app):
        pass

    assert writer.closed
