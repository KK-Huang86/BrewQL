"""Shared test setup."""

import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def ignore_developer_env_files(monkeypatch):
    # Settings reads .env files for local runs; tests must see only what they set themselves,
    # or a developer's real guardrail or model settings would change their outcome.
    monkeypatch.setitem(Settings.model_config, "env_file", None)


@pytest.fixture(autouse=True)
def audit_settings(monkeypatch):
    # build_app refuses to start without audit settings (record-audit-log D4); give every test a
    # placeholder pair, and tests about missing settings remove them. Nothing connects at startup.
    monkeypatch.setenv("AUDIT_DATABASE_URL", "postgresql://genbi_audit_writer:x@127.0.0.1:1/none")
    monkeypatch.setenv("AUDIT_IP_HMAC_KEY", "test-key-0123456789abcdef0123456789ab")
