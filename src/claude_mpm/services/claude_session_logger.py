from pathlib import Path

"""
Claude Session Response Logger

Simplified response logging system that uses Claude Code session IDs.
Stores responses in docs/responses/{session-id}/ for easy access.

Now with optional async logging support for improved performance.
Configuration via .claude-mpm/configuration.yaml.
"""

# Try to import async logger for performance optimization
import importlib.util
import json
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

# Import configuration manager
from claude_mpm.core.config import Config

# Import centralized session manager
from claude_mpm.services.session_manager import get_session_manager

if importlib.util.find_spec("claude_mpm.services.async_session_logger"):
    from claude_mpm.services.async_session_logger import get_async_logger

    ASYNC_AVAILABLE = True
else:
    ASYNC_AVAILABLE = False

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class ClaudeSessionLogger:
    """Simplified response logger for Claude Code sessions."""

    _initialization_lock = Lock()
    _initialized = False

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
        # Use initialization flag to prevent duplicate setup
        with self._initialization_lock:
            if self._initialized and hasattr(self, "config"):
                logger.debug("ClaudeSessionLogger already initialized, skipping setup")
                return

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

            # Use centralized SessionManager for session ID
            session_manager = get_session_manager()
            self.session_id = session_manager.get_session_id()
            logger.debug(
                f"ClaudeSessionLogger using session ID from SessionManager: {self.session_id}"
            )

            self.response_counter = {}  # Track response count per session
            self._initialized = True

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
                # Pass our session_id to async logger to avoid duplicate generation
                self._async_logger = get_async_logger(config=config)
                # Synchronize session IDs - use the one we already generated
                if self.session_id and hasattr(self._async_logger, "set_session_id"):
                    self._async_logger.set_session_id(self.session_id)
                    logger.debug(
                        f"Using async logger with session ID: {self.session_id}"
                    )
                else:
                    logger.debug("Using async logger for improved performance")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize async logger, falling back to sync: {e}"
                )
                self.use_async = False

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
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Logged response to {filename} for session {self.session_id}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to log response: {e}")
            return None

    def set_session_id(self, session_id: str) -> None:
        """
        Manually set the session ID.

        Note: This updates both the local session ID and the SessionManager.

        Args:
            session_id: The session ID to use
        """
        self.session_id = session_id
        # Also update SessionManager to keep consistency
        session_manager = get_session_manager()
        session_manager.set_session_id(session_id)
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


# Singleton instance with thread-safe initialization
_logger_instance = None
_logger_lock = Lock()


def get_session_logger(config: Optional[Config] = None) -> ClaudeSessionLogger:
    """
    Get the singleton session logger instance with thread-safe initialization.

    Uses double-checked locking pattern to ensure thread safety.

    Args:
        config: Optional configuration instance to use

    Returns:
        The shared ClaudeSessionLogger instance
    """
    global _logger_instance

    # Fast path - check without lock
    if _logger_instance is not None:
        return _logger_instance

    # Slow path - acquire lock and double-check
    with _logger_lock:
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
