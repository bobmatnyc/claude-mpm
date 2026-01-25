"""Slack MPM Client - Slack integration for Claude Multi-Agent Project Manager.

Note: Imports are lazy to avoid config validation errors when importing submodules.
Use `from claude_mpm.slack_client.app import app` for direct access.
"""

__all__ = ["app", "settings", "start_socket_mode"]


def __getattr__(name: str):
    """Lazy import for module attributes."""
    if name == "app":
        from .app import app

        return app
    if name == "start_socket_mode":
        from .app import start_socket_mode

        return start_socket_mode
    if name == "settings":
        from .config import settings

        return settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
