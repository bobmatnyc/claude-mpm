"""Configuration for Slack MPM client."""

from pydantic import Field
from pydantic_settings import BaseSettings


class SlackSettings(BaseSettings):
    """Slack application settings."""

    slack_bot_token: str = Field(
        ...,
        description="Slack Bot User OAuth Token (xoxb-...)",
    )
    slack_app_token: str = Field(
        ...,
        description="Slack App-Level Token for Socket Mode (xapp-...)",
    )
    slack_signing_secret: str = Field(
        ...,
        description="Slack Signing Secret for request verification",
    )

    mpm_api_url: str = Field(
        default="http://localhost:8000",
        description="MPM API base URL",
    )
    mpm_api_key: str | None = Field(
        default=None,
        description="Optional API key for MPM authentication",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = SlackSettings()
