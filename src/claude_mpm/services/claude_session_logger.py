from pathlib import Path

"""
Claude Session Response Logger

Simplified response logging system that uses Claude Code session IDs.
Stores responses in docs/responses/{session-id}/ for easy access.

Now with optional async logging support for improved performance.
Configuration via .claude-mpm/configuration.yaml.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

# Import configuration manager
from claude_mpm.core.config import Config

# Try to import async logger for performance optimization
try:
    from claude_mpm.services.async_session_logger import (
        AsyncSessionLogger,
        get_async_logger,
        log_response_async,
    )

    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

logger = logging.getLogger(__name__)


class ClaudeSessionLogger:
    """Simplified response logger for Claude Code sessions."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        use_async: Optional[bool] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize the session logger.

        Args:
            base_dir: Base directory for responses. Overrides config.
            use_async: Use async logging if available. Overrides config.
            config: Configuration instance to use (creates new if not provided)
        """
        # Load configuration
        if config is None:
            config = Config()
        self.config = config

        # Get response logging configuration
        response_config = self.config.get("response_logging", {})

        # Determine base directory
        if base_dir is None:
            # Check configuration first
            base_dir = response_config.get("session_directory")
            if not base_dir:
                # Fall back to default response directory
                base_dir = ".claude-mpm/responses"
            base_dir = Path(base_dir)

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Try to get session ID from environment
        self.session_id = self._get_claude_session_id()
        self.response_counter = {}  # Track response count per session

        # Determine if we should use async logging
        if use_async is None:
            # Check if response logging is enabled at all
            if not response_config.get("enabled", True):
                logger.info("Response logging disabled in configuration")
                use_async = False
            else:
                # Check configuration for async preference
                use_async = response_config.get("use_async", True)

                # Check environment for backward compatibility
                if os.environ.get("CLAUDE_USE_ASYNC_LOG"):
                    env_async = (
                        os.environ.get("CLAUDE_USE_ASYNC_LOG", "true").lower() == "true"
                    )
                    logger.info(
                        f"Using CLAUDE_USE_ASYNC_LOG environment variable (deprecated): {env_async}"
                    )
                    use_async = env_async

        self.use_async = use_async and ASYNC_AVAILABLE
        self._async_logger = None

        if self.use_async:
            try:
                self._async_logger = get_async_logger(config=config)
                logger.info("Using async logger for improved performance")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize async logger, falling back to sync: {e}"
                )
                self.use_async = False

    def _get_claude_session_id(self) -> Optional[str]:
        """
        Get the Claude Code session ID from environment.

        Returns:
            Session ID if available, None otherwise
        """
        # Claude Code may set various environment variables
        # Check common patterns
        session_id = None

        # Check for CLAUDE_SESSION_ID
        session_id = os.environ.get("CLAUDE_SESSION_ID")

        # Check for ANTHROPIC_SESSION_ID
        if not session_id:
            session_id = os.environ.get("ANTHROPIC_SESSION_ID")

        # Check for generic SESSION_ID
        if not session_id:
            session_id = os.environ.get("SESSION_ID")

        # Generate a default based on timestamp if nothing found
        if not session_id:
            # Use a timestamp-based session ID as fallback
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"No Claude session ID found, using generated: {session_id}")
        else:
            logger.info(f"Using Claude session ID: {session_id}")

        return session_id

    def _generate_filename(self, agent: Optional[str] = None) -> str:
        """
        Generate a flat filename with session ID, agent, and timestamp.

        Args:
            agent: Optional agent name

        Returns:
            Filename in format: [session_id]-[agent]-timestamp.json
        """
        # Get agent name, defaulting to "unknown" if not provided
        agent_name = agent or "unknown"
        # Sanitize agent name (replace spaces with underscores, lowercase)
        agent_name = agent_name.replace(" ", "_").lower()

        # Generate timestamp with microseconds for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Create filename: session_id-agent-timestamp.json
        return f"{self.session_id}-{agent_name}-{timestamp}.json"

    def log_response(
        self,
        request_summary: str,
        response_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Log a response to the session directory.

        Args:
            request_summary: Brief summary of the request
            response_content: The full response content
            metadata: Optional metadata (agent name, model, etc.)
            agent: Optional agent name (overrides metadata)

        Returns:
            Path to the saved response file, or None if disabled
        """
        # Check if logging is actually enabled
        response_config = self.config.get("response_logging", {})
        if not response_config.get("enabled", True):
            logger.debug("Response logging is disabled in configuration")
            return None

        if not self.session_id:
            return None

        # Use async logger if available for better performance
        if self.use_async and self._async_logger:
            success = self._async_logger.log_response(
                request_summary=request_summary,
                response_content=response_content,
                metadata=metadata,
                agent=agent,
            )
            if success:
                # Return expected path for compatibility
                # Async logger uses timestamp-based names, so we can't return exact path
                return self.base_dir / "async_response.json"
            return None

        # Fall back to synchronous logging
        # Ensure base directory exists (flat structure, no subdirs)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Extract agent name from parameter or metadata
        agent_name = agent or (metadata.get("agent") if metadata else None) or "unknown"

        # Generate filename with flat structure
        filename = self._generate_filename(agent_name)
        file_path = self.base_dir / filename

        # Prepare response data with standardized field names
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "request": request_summary,  # Standardized field name
            "response": response_content,  # Already correct
            "agent": agent
            or (metadata.get("agent") if metadata else None)
            or "unknown",  # Standardized field name
            "metadata": metadata or {},
        }

        # Save response
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Logged response to {filename} for session {self.session_id}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to log response: {e}")
            return None

    def set_session_id(self, session_id: str) -> None:
        """
        Manually set the session ID.

        Args:
            session_id: The session ID to use
        """
        self.session_id = session_id
        logger.info(f"Session ID set to: {session_id}")

    def get_session_path(self) -> Optional[Path]:
        """
        Get the path to the responses directory.

        Note: With flat structure, returns the base directory.

        Returns:
            Path to responses directory, or None if no session
        """
        if not self.session_id:
            return None
        return self.base_dir

    def is_enabled(self) -> bool:
        """
        Check if logging is enabled.

        Returns:
            True if logging is enabled (session ID available)
        """
        return self.session_id is not None


# Singleton instance for easy access
_logger_instance = None


def get_session_logger(config: Optional[Config] = None) -> ClaudeSessionLogger:
    """
    Get the singleton session logger instance.

    Args:
        config: Optional configuration instance to use

    Returns:
        The shared ClaudeSessionLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ClaudeSessionLogger(config=config)
    return _logger_instance


def log_response(
    request_summary: str,
    response_content: str,
    metadata: Optional[Dict[str, Any]] = None,
    agent: Optional[str] = None,
) -> Optional[Path]:
    """
    Convenience function to log a response.

    Args:
        request_summary: Brief summary of the request
        response_content: The full response content
        metadata: Optional metadata
        agent: Optional agent name

    Returns:
        Path to the saved response file
    """
    logger = get_session_logger()
    return logger.log_response(request_summary, response_content, metadata, agent)
