"""Error handling for MPM Commander API.

This module defines custom exception classes that map to HTTP error responses
with structured error codes and messages.
"""

from fastapi import HTTPException


class CommanderAPIError(HTTPException):
    """Base exception for all Commander API errors.

    Provides consistent error response format with code and message.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
    """

    def __init__(self, code: str, message: str, status_code: int = 400):
        """Initialize API error.

        Args:
            code: Error code (e.g., "PROJECT_NOT_FOUND")
            message: Descriptive error message
            status_code: HTTP status code (default: 400)
        """
        super().__init__(
            status_code=status_code,
            detail={"error": {"code": code, "message": message}},
        )


class ProjectNotFoundError(CommanderAPIError):
    """Project with given ID does not exist."""

    def __init__(self, project_id: str):
        """Initialize project not found error.

        Args:
            project_id: The project ID that was not found
        """
        super().__init__(
            "PROJECT_NOT_FOUND",
            f"Project not found: {project_id}",
            404,
        )


class ProjectAlreadyExistsError(CommanderAPIError):
    """Project already registered at given path."""

    def __init__(self, path: str):
        """Initialize project already exists error.

        Args:
            path: The path that is already registered
        """
        super().__init__(
            "PROJECT_ALREADY_EXISTS",
            f"Project already registered: {path}",
            409,
        )


class InvalidPathError(CommanderAPIError):
    """Path does not exist or is not a directory."""

    def __init__(self, path: str):
        """Initialize invalid path error.

        Args:
            path: The invalid path
        """
        super().__init__(
            "INVALID_PATH",
            f"Path does not exist or is not a directory: {path}",
            400,
        )


class SessionNotFoundError(CommanderAPIError):
    """Session with given ID does not exist."""

    def __init__(self, session_id: str):
        """Initialize session not found error.

        Args:
            session_id: The session ID that was not found
        """
        super().__init__(
            "SESSION_NOT_FOUND",
            f"Session not found: {session_id}",
            404,
        )


class InvalidRuntimeError(CommanderAPIError):
    """Invalid runtime adapter specified."""

    def __init__(self, runtime: str):
        """Initialize invalid runtime error.

        Args:
            runtime: The invalid runtime name
        """
        super().__init__(
            "INVALID_RUNTIME",
            f"Invalid runtime: {runtime}",
            400,
        )


class TmuxNoSpaceError(CommanderAPIError):
    """Raised when tmux has no space for a new pane."""

    def __init__(self, message: str | None = None):
        """Initialize tmux no space error.

        Args:
            message: Custom error message (optional)
        """
        default_msg = (
            "Unable to create session: tmux has no space for new pane. "
            "Try closing some sessions or resize your terminal window. "
            "You can also create a new tmux window with `tmux new-window`."
        )
        super().__init__(
            "TMUX_NO_SPACE",
            message or default_msg,
            409,
        )
