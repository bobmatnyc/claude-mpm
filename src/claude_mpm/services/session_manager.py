"""
Session Manager Service

Centralized session ID management with thread-safe singleton pattern.
Ensures a single session ID is generated and used across all components.

This service addresses race conditions and duplicate session ID generation
by providing a single source of truth for session identifiers.
"""

import os
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Thread-safe singleton session manager.

    Provides centralized session ID generation and management to prevent
    duplicate session IDs across different components.

    Uses double-checked locking pattern for thread-safe singleton initialization.
    """

    _instance: Optional["SessionManager"] = None
    _lock = Lock()
    _initialized = False

    def __new__(cls) -> "SessionManager":
        """
        Create or return the singleton instance using double-checked locking.

        Returns:
            The singleton SessionManager instance
        """
        # First check without lock (fast path)
        if cls._instance is None:
            # Acquire lock for thread safety
            with cls._lock:
                # Double-check inside lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize the session manager (only once).

        This method uses an initialization flag to ensure it only
        runs once, even if __init__ is called multiple times.
        """
        # Use class-level lock to ensure thread-safe initialization
        with self.__class__._lock:
            if self.__class__._initialized:
                return

            # Generate session ID once during initialization
            self._session_id = self._generate_session_id()
            self._session_start_time = datetime.now(timezone.utc)

            # Mark as initialized
            self.__class__._initialized = True

            logger.debug(
                f"SessionManager initialized with session ID: {self._session_id}"
            )

    def _generate_session_id(self) -> str:
        """
        Generate or retrieve a session ID.

        Checks environment variables first, then generates a timestamp-based ID.

        Returns:
            A unique session identifier
        """
        # Check environment variables in order of preference
        env_vars = ["CLAUDE_SESSION_ID", "ANTHROPIC_SESSION_ID", "SESSION_ID"]

        for env_var in env_vars:
            session_id = os.environ.get(env_var)
            if session_id:
                logger.debug(f"Using session ID from {env_var}: {session_id}")
                return session_id

        # Generate timestamp-based session ID
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        logger.debug(f"Generated new session ID: {session_id}")
        return session_id

    def get_session_id(self) -> str:
        """
        Get the current session ID.

        Thread-safe method to retrieve the session ID.

        Returns:
            The current session ID
        """
        return self._session_id

    def get_session_start_time(self) -> datetime:
        """
        Get the session start time.

        Returns:
            The datetime when the session was initialized
        """
        return self._session_start_time

    def set_session_id(self, session_id: str) -> None:
        """
        Override the session ID.

        This should only be used in special circumstances, as it can
        break the single session ID guarantee.

        Args:
            session_id: The new session ID to use
        """
        with self.__class__._lock:
            old_id = self._session_id
            if old_id != session_id:
                self._session_id = session_id
                logger.warning(f"Session ID changed from {old_id} to {session_id}")
            else:
                logger.debug(
                    f"Session ID already set to {session_id}, no change needed"
                )

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance (mainly for testing).

        This method should not be used in production code.
        """
        with cls._lock:
            cls._instance = None
            cls._initialized = False
            logger.debug("SessionManager singleton reset")


# Global accessor function
_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global SessionManager instance.

    Thread-safe accessor that ensures a single SessionManager exists.

    Returns:
        The singleton SessionManager instance
    """
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


def get_session_id() -> str:
    """
    Convenience function to get the current session ID.

    Returns:
        The current session ID
    """
    return get_session_manager().get_session_id()
