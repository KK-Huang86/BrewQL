"""Runtime settings from environment variables (and .env in local development)."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-haiku-5-5"
    # Empty string disables effort (models before Claude 4.6 reject it).
    bedrock_effort: str | None = "low"
    database_url: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("bedrock_effort", mode="before")
    @classmethod
    def _blank_effort_is_none(cls, value: str | None) -> str | None:
        return value or None
