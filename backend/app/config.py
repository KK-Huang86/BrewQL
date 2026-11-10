"""Runtime settings from environment variables (and .env in local development)."""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The project's .env sits at the repo root, while uv --directory backend runs from backend/.
# Later files win, so a .env in the working directory overrides the root one. In the container
# the root path does not exist and compose passes settings as environment variables instead.
ENV_FILES = (Path(__file__).resolve().parents[2] / ".env", Path(".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-haiku-5-5"
    # Empty string disables effort (models before Claude 4.6 reject it).
    bedrock_effort: str | None = "low"
    database_url: str = ""
    # Port compose publishes the db on locally; 5432 is often taken by other projects. Eval checks it.
    db_port: int = 5434
    cors_origins: list[str] = ["http://localhost:5173"]
    # Input guardrail; unset skips the check (local development only).
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str | None = None
    # Extra model calls after a failed attempt; capped so one question cannot multiply cost.
    max_sql_retries: int = Field(default=1, ge=0, le=5)
    # Questions the whole site answers per Taipei day; must be positive so a typo cannot remove the cap.
    daily_question_limit: int = Field(default=500, gt=0)
    # Audit trail (record-audit-log). Optional here because eval and smoke share Settings;
    # build_app is what refuses to start without them.
    audit_database_url: str = ""
    audit_ip_hmac_key: str = ""

    @field_validator("bedrock_effort", "bedrock_guardrail_id", "bedrock_guardrail_version", mode="before")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def _guardrail_needs_a_published_version(self) -> "Settings":
        # Never fall back to DRAFT: unpublished edits must not go live silently.
        if self.bedrock_guardrail_id and not self.bedrock_guardrail_version:
            raise ValueError("BEDROCK_GUARDRAIL_VERSION is required when BEDROCK_GUARDRAIL_ID is set")
        return self
