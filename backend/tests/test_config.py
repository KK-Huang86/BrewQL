from app.config import Settings


def test_model_id_defaults_to_haiku(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    assert "haiku" in Settings(_env_file=None).bedrock_model_id


def test_model_id_can_be_switched_without_code_changes(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-5-5")
    assert Settings(_env_file=None).bedrock_model_id == "anthropic.claude-sonnet-5-5"


def test_effort_can_be_disabled_for_models_without_it(monkeypatch):
    monkeypatch.setenv("BEDROCK_EFFORT", "")
    assert Settings(_env_file=None).bedrock_effort is None


def test_every_setting_is_documented_in_env_example():
    # A new Settings field must also land in .env.example (commented out is fine).
    import re
    from pathlib import Path

    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text()
    documented = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", example, flags=re.M))

    missing = {name.upper() for name in Settings.model_fields} - documented
    assert not missing, f"add to .env.example: {sorted(missing)}"


def test_guardrail_is_off_by_default(monkeypatch):
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    assert Settings(_env_file=None).bedrock_guardrail_id is None


def test_guardrail_id_without_a_version_is_rejected_at_startup(monkeypatch):
    # Never fall back to DRAFT: an unpublished edit must not go live silently.
    import pytest
    from pydantic import ValidationError

    monkeypatch.setenv("BEDROCK_GUARDRAIL_ID", "gr-123")
    monkeypatch.delenv("BEDROCK_GUARDRAIL_VERSION", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_sql_retries_default_to_one(monkeypatch):
    # One retry fixes most small mistakes; a question costs at most two model calls.
    monkeypatch.delenv("MAX_SQL_RETRIES", raising=False)
    assert Settings(_env_file=None).max_sql_retries == 1


def test_sql_retries_accept_the_bounds(monkeypatch):
    for value in ("0", "5"):
        monkeypatch.setenv("MAX_SQL_RETRIES", value)
        assert Settings(_env_file=None).max_sql_retries == int(value)


def test_sql_retries_outside_zero_to_five_are_rejected_at_startup(monkeypatch):
    # Negative makes no sense; above 5 lets one question multiply model cost.
    import pytest
    from pydantic import ValidationError

    for value in ("-1", "6"):
        monkeypatch.setenv("MAX_SQL_RETRIES", value)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)


def test_repo_root_env_is_read_when_running_from_backend():
    # `uv --directory backend run ...` starts in backend/, but the project's .env lives at the repo root.
    from pathlib import Path

    from app.config import ENV_FILES

    repo_root = Path(__file__).resolve().parents[2]
    assert ENV_FILES[0] == repo_root / ".env"
    # A local backend/.env (or the working directory's) still wins when both exist.
    assert ENV_FILES[-1] == Path(".env")


def test_test_runs_ignore_env_files():
    from app.config import Settings

    assert Settings.model_config["env_file"] is None
