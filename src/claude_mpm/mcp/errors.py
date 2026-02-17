"""Exception classes for MCP session errors."""

from typing import Any


class SessionError(Exception):
    """Base exception for session errors."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.session_id = session_id
        self.retry_after = retry_after


class RateLimitError(SessionError):
    """Rate limit exceeded."""


class ContextWindowError(SessionError):
    """Context window exceeded."""


class APIError(SessionError):
    """API error from Claude."""


def parse_error(result_message: dict[str, Any]) -> SessionError:
    """Parse error from result message and return appropriate exception."""
    error = result_message.get("error", "Unknown error")
    session_id = result_message.get("session_id")
    retry_after = result_message.get("retry_after")

    if "rate limit" in error.lower():
        return RateLimitError(error, session_id, retry_after or 60)
    if "context" in error.lower() and "window" in error.lower():
        return ContextWindowError(error, session_id)
    if "api" in error.lower():
        return APIError(error, session_id)
    return SessionError(error, session_id)
