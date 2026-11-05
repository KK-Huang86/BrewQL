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
