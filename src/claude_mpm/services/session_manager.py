"""
Session Manager Service

Centralized session ID management with thread-safe singleton pattern.
Ensures a single session ID is generated and used across all components.

This service addresses race conditions and duplicate session ID generation
by providing a single source of truth for session identifiers.

Extended with:
- Token usage tracking and monitoring
- Resume log generation on session end
- Context metrics persistence
- Automatic resume log injection on session startup
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

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

            # Token usage tracking
            self._cumulative_tokens = 0
            self._total_budget = 200000  # Default Claude Code budget
            self._last_stop_reason: Optional[str] = None

            # Context metrics storage
            self._context_metrics: Dict[str, Any] = {
                "total_budget": self._total_budget,
                "used_tokens": 0,
                "remaining_tokens": self._total_budget,
                "percentage_used": 0.0,
                "stop_reason": None,
                "model": "claude-sonnet-4.5",
            }

            # Resume log reference (loaded on startup if exists)
            self._resume_log_content: Optional[str] = None

            # Mark as initialized
            self.__class__._initialized = True

            logger.debug(
                f"SessionManager initialized with session ID: {self._session_id}"
            )

            # Check for resume log from previous session
            self._load_resume_log()

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

    def update_token_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        stop_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update cumulative token usage for the session.

        Args:
            input_tokens: Input tokens from latest API call
            output_tokens: Output tokens from latest API call
            stop_reason: Stop reason from Claude API

        Returns:
            Updated context metrics
        """
        with self.__class__._lock:
            # Update cumulative usage
            tokens_used = input_tokens + output_tokens
            self._cumulative_tokens += tokens_used

            # Update stop reason if provided
            if stop_reason:
                self._last_stop_reason = stop_reason

            # Calculate metrics
            remaining = max(0, self._total_budget - self._cumulative_tokens)
            percentage = (self._cumulative_tokens / self._total_budget) * 100

            # Update context metrics
            self._context_metrics = {
                "total_budget": self._total_budget,
                "used_tokens": self._cumulative_tokens,
                "remaining_tokens": remaining,
                "percentage_used": percentage,
                "stop_reason": self._last_stop_reason,
                "model": "claude-sonnet-4.5",
            }

            logger.debug(
                f"Token usage updated: {self._cumulative_tokens}/{self._total_budget} "
                f"({percentage:.1f}%) - Stop reason: {stop_reason}"
            )

            return self._context_metrics.copy()

    def get_context_metrics(self) -> Dict[str, Any]:
        """
        Get current context metrics.

        Returns:
            Dictionary containing token usage and context metrics
        """
        with self.__class__._lock:
            return self._context_metrics.copy()

    def get_token_usage_percentage(self) -> float:
        """
        Get current token usage as a percentage (0.0 to 1.0).

        Returns:
            Token usage percentage
        """
        with self.__class__._lock:
            return self._context_metrics["percentage_used"] / 100.0

    def should_warn_context_limit(self, threshold: float = 0.70) -> bool:
        """
        Check if context usage has reached warning threshold.

        Args:
            threshold: Warning threshold (0.0 to 1.0)

        Returns:
            True if threshold reached
        """
        return self.get_token_usage_percentage() >= threshold

    def _load_resume_log(self) -> None:
        """
        Load resume log from previous session if it exists.

        This is called during initialization to check for session continuity.
        """
        try:
            # Lazy import to avoid circular dependencies
            from claude_mpm.services.infrastructure.resume_log_generator import (
                ResumeLogGenerator,
            )

            generator = ResumeLogGenerator()

            # Check if there's a resume log for this session
            # (Could be from a previous interrupted session with same ID)
            resume_content = generator.load_resume_log(self._session_id)

            if resume_content:
                self._resume_log_content = resume_content
                logger.info(f"Loaded resume log for session {self._session_id}")
            else:
                logger.debug("No resume log found for current session")

        except Exception as e:
            logger.warning(f"Failed to load resume log: {e}")
            # Non-critical error, continue without resume log

    def get_resume_log_content(self) -> Optional[str]:
        """
        Get resume log content if loaded.

        Returns:
            Resume log markdown content or None
        """
        with self.__class__._lock:
            return self._resume_log_content

    def generate_resume_log(
        self,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Path]:
        """
        Generate and save resume log for current session.

        Args:
            session_state: Optional session state data to include

        Returns:
            Path to saved resume log or None if generation failed
        """
        try:
            # Lazy import to avoid circular dependencies
            from claude_mpm.models.resume_log import ContextMetrics, ResumeLog
            from claude_mpm.services.infrastructure.resume_log_generator import (
                ResumeLogGenerator,
            )

            generator = ResumeLogGenerator()

            # Create context metrics from current state
            context_metrics = ContextMetrics(
                total_budget=self._total_budget,
                used_tokens=self._cumulative_tokens,
                remaining_tokens=self._context_metrics["remaining_tokens"],
                percentage_used=self._context_metrics["percentage_used"],
                stop_reason=self._last_stop_reason,
                model=self._context_metrics["model"],
                session_id=self._session_id,
            )

            if session_state:
                # Generate from provided session state
                resume_log = generator.generate_from_session_state(
                    session_id=self._session_id,
                    session_state=session_state,
                    stop_reason=self._last_stop_reason,
                )
            else:
                # Create minimal resume log
                resume_log = ResumeLog(
                    session_id=self._session_id,
                    context_metrics=context_metrics,
                    mission_summary="Session ended - resume log auto-generated.",
                )

            if resume_log:
                file_path = generator.save_resume_log(resume_log)
                logger.info(f"Resume log generated and saved: {file_path}")
                return file_path
            logger.warning("Resume log generation returned None")
            return None

        except Exception as e:
            logger.error(f"Failed to generate resume log: {e}", exc_info=True)
            return None

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
