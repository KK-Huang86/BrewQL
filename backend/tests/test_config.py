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
