"""Configuration for the UI Service.

Uses a dataclass with environment variable support, following the pattern
established in claude_mpm/config/socketio_config.py.
"""

import os
from dataclasses import dataclass, field


@dataclass
class UIServiceConfig:
    """Configuration for the claude-mpm UI Service.

    All fields can be overridden via environment variables with the
    CLAUDE_MPM_UI_ prefix.

    Attributes:
        host: Host address to bind to.
        port: Port number to bind to.
        reload: Enable uvicorn auto-reload (development only).
        log_level: Uvicorn log level.
        cors_origins: List of allowed CORS origins.
        anthropic_api_key: Anthropic API key (from env ANTHROPIC_API_KEY).
        max_sessions: Maximum number of concurrent managed sessions.
        session_timeout_minutes: Minutes of inactivity before session cleanup.
    """

    host: str = "127.0.0.1"
    port: int = 7777
    reload: bool = False
    log_level: str = "info"
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:*", "http://127.0.0.1:*"]
    )
    anthropic_api_key: str | None = None
    max_sessions: int = 10
    session_timeout_minutes: int = 60

    @classmethod
    def from_env(cls) -> "UIServiceConfig":
        """Create configuration from environment variables.

        Returns:
            UIServiceConfig populated from environment.
        """
        cors_env = os.getenv("CLAUDE_MPM_UI_CORS_ORIGINS")
        cors_origins = (
            cors_env.split(",")
            if cors_env
            else ["http://localhost:*", "http://127.0.0.1:*"]
        )

        return cls(
            host=os.getenv("CLAUDE_MPM_UI_HOST", "127.0.0.1"),
            port=int(os.getenv("CLAUDE_MPM_UI_PORT", "7777")),
            reload=os.getenv("CLAUDE_MPM_UI_RELOAD", "false").lower() == "true",
            log_level=os.getenv("CLAUDE_MPM_UI_LOG_LEVEL", "info"),
            cors_origins=cors_origins,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_sessions=int(os.getenv("CLAUDE_MPM_UI_MAX_SESSIONS", "10")),
            session_timeout_minutes=int(
                os.getenv("CLAUDE_MPM_UI_SESSION_TIMEOUT", "60")
            ),
        )
