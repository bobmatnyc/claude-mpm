from pathlib import Path

"""
Response Tracker Service

Wraps the ClaudeSessionLogger to provide compatibility with the hook_handler.py
response tracking integration. This service acts as a bridge between the hook
system and the session logging system.

WHY: The hook_handler expects a ResponseTracker class with specific methods,
but we already have ClaudeSessionLogger that does the actual work. This wrapper
ensures compatibility while respecting configuration settings.

DESIGN DECISIONS:
- Wraps ClaudeSessionLogger instead of duplicating code
- Properly checks configuration to respect enabled/disabled state
- Provides the expected interface for hook_handler.py
- Handles agent name normalization for consistent tracking
"""

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.shared.config_loader import ConfigLoader

logger = get_logger(__name__)


class ResponseTracker:
    """Response tracker that wraps ClaudeSessionLogger for hook compatibility.

    WHY: This class provides the interface expected by hook_handler.py while
    delegating actual logging to the proven ClaudeSessionLogger implementation.
    This avoids code duplication and maintains consistency.

    DESIGN: The tracker checks configuration settings on initialization and
    respects the enabled/disabled state. It provides the track_response method
    expected by the hook handler.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize the response tracker.

        Args:
            config: Optional configuration instance
        """
        # Load configuration if not provided
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load_main_config()
        self.config = config

        # Check if response tracking is enabled
        response_tracking_config = self.config.get("response_tracking", {})
        response_logging_config = self.config.get("response_logging", {})

        # Check both configurations - explicit False takes precedence
        if "enabled" in response_tracking_config:
            self.enabled = response_tracking_config.get("enabled", False)
        elif "enabled" in response_logging_config:
            self.enabled = response_logging_config.get("enabled", False)
        else:
            self.enabled = False  # Default to disabled if not configured

        # Initialize the session logger only if enabled
        self.session_logger = None
        if self.enabled:
            try:
                # Get base directory from configuration
                base_dir = response_tracking_config.get("base_dir")
                if not base_dir:
                    base_dir = response_logging_config.get(
                        "session_directory", ".claude-mpm/responses"
                    )

                # Use singleton session logger for proper sharing
                from claude_mpm.services.claude_session_logger import get_session_logger

                self.session_logger = get_session_logger(config)
                logger.debug(
                    f"Response tracker initialized with base directory: {base_dir}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize session logger: {e}")
                self.enabled = False
        else:
            logger.info("Response tracking is disabled in configuration")

    def track_response(
        self,
        agent_name: str,
        request: str,
        response: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Path]:
        """Track an agent response.

        WHY: This method provides the interface expected by hook_handler.py
        while delegating to ClaudeSessionLogger for actual storage.

        Args:
            agent_name: Name of the agent that generated the response
            request: The original request/prompt
            response: The agent's response
            session_id: Optional session ID (will use logger's if not provided)
            metadata: Optional additional metadata

        Returns:
            Path to the saved response file, or None if disabled/failed
        """
        # Check if tracking is enabled
        if not self.enabled or not self.session_logger:
            logger.debug(
                f"Response tracking disabled, skipping response from {agent_name}"
            )
            return None

        # Check excluded agents
        response_tracking_config = self.config.get("response_tracking", {})
        excluded_agents = response_tracking_config.get("excluded_agents", [])

        # Normalize agent name for comparison
        normalized_agent = agent_name.lower().replace("-", "_").replace(" ", "_")

        # Check if agent is excluded
        for excluded in excluded_agents:
            excluded_normalized = excluded.lower().replace("-", "_").replace(" ", "_")
            if normalized_agent == excluded_normalized:
                logger.debug(
                    f"Agent {agent_name} is in excluded list, skipping response tracking"
                )
                return None

        # Set session ID if provided
        if session_id and session_id != self.session_logger.session_id:
            self.session_logger.set_session_id(session_id)

        # Prepare enhanced metadata
        enhanced_metadata = metadata or {}
        enhanced_metadata.update(
            {
                "agent": agent_name,
                "tracked_by": "ResponseTracker",
                "tracking_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Check if metadata tracking is enabled and add additional fields
        metadata_tracking = response_tracking_config.get("metadata_tracking", {})
        if metadata_tracking.get("track_model", True):
            enhanced_metadata["model"] = enhanced_metadata.get("model", "claude-3")
        if (
            metadata_tracking.get("track_duration", True)
            and "duration_ms" in enhanced_metadata
        ):
            enhanced_metadata["duration_ms"] = enhanced_metadata.get("duration_ms")
        if (
            metadata_tracking.get("track_tools", True)
            and "tool_name" in enhanced_metadata
        ):
            enhanced_metadata["tools_used"] = [enhanced_metadata.get("tool_name")]

        # Log the response using the session logger
        try:
            file_path = self.session_logger.log_response(
                request_summary=request,
                response_content=response,
                metadata=enhanced_metadata,
                agent=agent_name,
            )

            if file_path:
                logger.debug(
                    f"Successfully tracked response from {agent_name} to {file_path}"
                )
            else:
                logger.warning(f"Failed to track response from {agent_name}")

            return file_path

        except Exception as e:
            logger.error(f"Error tracking response from {agent_name}: {e}")
            return None

    def is_enabled(self) -> bool:
        """Check if response tracking is enabled.

        Returns:
            True if tracking is enabled, False otherwise
        """
        return self.enabled and self.session_logger is not None

    def get_session_path(self) -> Optional[Path]:
        """Get the current session directory path.

        Returns:
            Path to the session directory, or None if not available
        """
        if self.session_logger:
            return self.session_logger.get_session_path()
        return None

    def set_session_id(self, session_id: str) -> None:
        """Set a specific session ID for tracking.

        Args:
            session_id: The session ID to use
        """
        if self.session_logger:
            self.session_logger.set_session_id(session_id)
            logger.info(f"Response tracker session ID set to: {session_id}")


# Singleton instance with thread-safe initialization
_tracker_instance = None
_tracker_lock = Lock()


def get_response_tracker(config: Optional[Config] = None) -> ResponseTracker:
    """Get the singleton response tracker instance with thread-safe initialization.

    Uses double-checked locking pattern to ensure thread safety.

    Args:
        config: Optional configuration instance

    Returns:
        The shared ResponseTracker instance
    """
    global _tracker_instance

    # Fast path - check without lock
    if _tracker_instance is not None:
        return _tracker_instance

    # Slow path - acquire lock and double-check
    with _tracker_lock:
        if _tracker_instance is None:
            _tracker_instance = ResponseTracker(config=config)
        return _tracker_instance


def track_response(
    agent_name: str,
    request: str,
    response: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Convenience function to track a response.

    Args:
        agent_name: Name of the agent
        request: The original request
        response: The agent's response
        session_id: Optional session ID
        metadata: Optional metadata

    Returns:
        Path to the saved response file
    """
    tracker = get_response_tracker()
    return tracker.track_response(agent_name, request, response, session_id, metadata)
