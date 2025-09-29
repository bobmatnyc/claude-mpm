from pathlib import Path

"""
Session Logging Utilities

Convenience functions for session-based response logging.
"""

import os
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.claude_session_logger import get_session_logger

logger = get_logger(__name__)


def is_session_logging_enabled() -> bool:
    """
    Check if session logging is enabled.

    Returns:
        True if session logging is enabled and configured
    """
    # Check environment variable to disable
    if os.environ.get("CLAUDE_MPM_NO_SESSION_LOGGING", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        return False

    # Check if session logger has a valid session ID
    session_logger = get_session_logger()
    return session_logger.is_enabled()


def log_agent_response(
    agent_name: str,
    request: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """
    Log an agent response to the current session.

    Args:
        agent_name: Name of the agent
        request: The request/prompt sent to the agent
        response: The agent's response
        metadata: Optional additional metadata

    Returns:
        Path to the logged file, or None if logging is disabled
    """
    if not is_session_logging_enabled():
        return None

    # Create request summary
    request_summary = (
        f"[{agent_name}] {request[:100]}..."
        if len(request) > 100
        else f"[{agent_name}] {request}"
    )

    # Add agent name to metadata
    if metadata is None:
        metadata = {}
    metadata["agent"] = agent_name

    # Log the response
    session_logger = get_session_logger()
    return session_logger.log_response(
        request_summary=request_summary, response_content=response, metadata=metadata
    )


def get_current_session_id() -> Optional[str]:
    """
    Get the current session ID.

    Returns:
        Current session ID, or None if not available
    """
    session_logger = get_session_logger()
    return session_logger.session_id


def get_session_directory() -> Optional[Path]:
    """
    Get the directory for the current session.

    Returns:
        Path to session directory, or None if not available
    """
    session_logger = get_session_logger()
    return session_logger.get_session_path()


def set_session_id(session_id: str) -> None:
    """
    Manually set the session ID.

    Args:
        session_id: The session ID to use
    """
    session_logger = get_session_logger()
    session_logger.set_session_id(session_id)
    logger.info(f"Session ID set to: {session_id}")


# Environment variable helpers
def enable_session_logging() -> None:
    """Enable session logging by removing disable flag."""
    if "CLAUDE_MPM_NO_SESSION_LOGGING" in os.environ:
        del os.environ["CLAUDE_MPM_NO_SESSION_LOGGING"]


def disable_session_logging() -> None:
    """Disable session logging via environment variable."""
    os.environ["CLAUDE_MPM_NO_SESSION_LOGGING"] = "1"
