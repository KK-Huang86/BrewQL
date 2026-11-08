"""Shared test setup."""

import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def ignore_developer_env_files(monkeypatch):
    # Settings reads .env files for local runs; tests must see only what they set themselves,
    # or a developer's real guardrail or model settings would change their outcome.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
