#!/usr/bin/env python3
"""Base event handler with shared state, DI, and helper utilities.

Extracted from the original ``event_handlers.EventHandlers`` god class as part
of the refactor for issue #509. The concrete handler classes
(``UserPromptHandler``, ``ToolHandler``, ``StopHandler``, ...) all hold a
reference to a :class:`BaseEventHandler` instance and reuse its lazy-loaded
services, git branch cache, and session-file helpers.

Behavior is intentionally preserved verbatim from the original implementation.
"""

import json
import os
import subprocess  # nosec B404 - subprocess used for safe git branch lookups only
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Import _log helper to avoid stderr writes (which cause hook errors).
# ``_log`` is not consumed inside this module; it is re-exported for the
# concrete handler modules (user_prompt, tool, stop, ...) that import it as
# ``from .base import _log``. Listing it in ``__all__`` documents the intent
# and suppresses Pyright's "imported but unused" warning.
try:
    from ..hook_handler import _log
except ImportError:
    # Fallback for direct execution
    def _log(message: str) -> None:
        """Fallback logger when hook_handler not available."""
        del message  # Intentionally unused; no-op fallback.


__all__ = ["_log"]


# Debug mode - MUST match hook_handler.py default (false) to prevent stderr writes
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "false").lower() == "true"


# Import constants for configuration; define fallback first so Pyright sees one type.
class TimeoutConfig:
    """Fallback TimeoutConfig when claude_mpm.core.constants is unavailable."""

    QUICK_TIMEOUT = 2.0


try:
    from claude_mpm.core.constants import TimeoutConfig  # type: ignore[assignment]
except ImportError:
    pass  # Keep the fallback TimeoutConfig defined above.


# ============================================================================
# Optional Dependencies - loaded once at module level for DI
# ============================================================================

# Log manager (for agent prompt logging)
_log_manager: Any | None = None
_log_manager_loaded = False


def _get_log_manager() -> Any | None:
    """Get log manager with lazy loading."""
    global _log_manager, _log_manager_loaded
    if not _log_manager_loaded:
        try:
            from claude_mpm.core.log_manager import get_log_manager

            _log_manager = get_log_manager()
        except ImportError:
            _log_manager = None
        _log_manager_loaded = True
    return _log_manager


# Config service (for autotodos configuration)
_config: Any | None = None
_config_loaded = False


def _get_config() -> Any | None:
    """Get Config with lazy loading."""
    global _config, _config_loaded
    if not _config_loaded:
        try:
            from claude_mpm.core.config import Config

            _config = Config()
        except ImportError:
            _config = None
        _config_loaded = True
    return _config


# Delegation detector (for anti-pattern detection)
_delegation_detector: Any | None = None
_delegation_detector_loaded = False


def _get_delegation_detector_service() -> Any | None:
    """Get delegation detector with lazy loading."""
    global _delegation_detector, _delegation_detector_loaded
    if not _delegation_detector_loaded:
        try:
            from claude_mpm.services.delegation_detector import get_delegation_detector

            _delegation_detector = get_delegation_detector()
        except ImportError:
            _delegation_detector = None
        _delegation_detector_loaded = True
    return _delegation_detector


# Event log (for PM violation logging)
_event_log: Any | None = None
_event_log_loaded = False


def _get_event_log_service() -> Any | None:
    """Get event log with lazy loading."""
    global _event_log, _event_log_loaded
    if not _event_log_loaded:
        try:
            from claude_mpm.services.event_log import get_event_log

            _event_log = get_event_log()
        except ImportError:
            _event_log = None
        _event_log_loaded = True
    return _event_log


class BaseEventHandler:
    """Shared state and helpers for decomposed event handlers.

    Supports dependency injection for optional services:
    - log_manager: For agent prompt logging
    - config: For autotodos configuration
    - delegation_detector: For anti-pattern detection
    - event_log: For PM violation logging

    If services are not provided, they are loaded lazily on first use.
    """

    def __init__(
        self,
        hook_handler,
        *,
        log_manager: Any | None = None,
        config: Any | None = None,
        delegation_detector: Any | None = None,
        event_log: Any | None = None,
    ):
        """Initialize with reference to the main hook handler and optional services.

        Args:
            hook_handler: The main ClaudeHookHandler instance
            log_manager: Optional LogManager for agent prompt logging
            config: Optional Config for autotodos configuration
            delegation_detector: Optional DelegationDetector for anti-pattern detection
            event_log: Optional EventLog for PM violation logging
        """
        self.hook_handler = hook_handler

        # Store injected services (None means use lazy loading)
        self._log_manager = log_manager
        self._config = config
        self._delegation_detector = delegation_detector
        self._event_log = event_log

    @property
    def log_manager(self) -> Any | None:
        """Get log manager (injected or lazy loaded)."""
        if self._log_manager is not None:
            return self._log_manager
        return _get_log_manager()

    @property
    def config(self) -> Any | None:
        """Get config (injected or lazy loaded)."""
        if self._config is not None:
            return self._config
        return _get_config()

    @property
    def delegation_detector(self) -> Any | None:
        """Get delegation detector (injected or lazy loaded)."""
        if self._delegation_detector is not None:
            return self._delegation_detector
        return _get_delegation_detector_service()

    @property
    def event_log(self) -> Any | None:
        """Get event log (injected or lazy loaded)."""
        if self._event_log is not None:
            return self._event_log
        return _get_event_log_service()

    def _get_git_branch(self, working_dir: str | None = None) -> str:
        """Get git branch for the given directory with caching."""
        # Use current working directory if not specified
        if not working_dir:
            working_dir = str(Path.cwd())

        # Check cache first (cache for 300 seconds = 5 minutes)
        # WHY 5 minutes: Git branches rarely change during development sessions,
        # reducing subprocess overhead significantly without staleness issues
        current_time = datetime.now(UTC).timestamp()
        cache_key = working_dir

        if (
            cache_key in self.hook_handler._git_branch_cache
            and cache_key in self.hook_handler._git_branch_cache_time
            and current_time - self.hook_handler._git_branch_cache_time[cache_key] < 300
        ):
            return self.hook_handler._git_branch_cache[cache_key]

        # Try to get git branch
        try:
            # Use ``git -C <dir>`` instead of os.chdir(). os.chdir() is
            # process-global and, on edge cases (NFS mount, unmounted
            # worktree), can stall the entire process.
            result = subprocess.run(  # nosec B603 B607
                ["git", "-C", str(working_dir), "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=TimeoutConfig.QUICK_TIMEOUT,
                check=False,  # Quick timeout to avoid hanging
            )

            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self.hook_handler._git_branch_cache[cache_key] = branch
                self.hook_handler._git_branch_cache_time[cache_key] = current_time
                return branch
            # Not a git repository or no branch
            self.hook_handler._git_branch_cache[cache_key] = "Unknown"
            self.hook_handler._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
        ):
            # Git not available or command failed
            self.hook_handler._git_branch_cache[cache_key] = "Unknown"
            self.hook_handler._git_branch_cache_time[cache_key] = current_time
            return "Unknown"

    def _check_paused_session_tasks(self, working_dir: str) -> dict:
        """Check for paused sessions with pending tasks.

        Looks for ACTIVE-PAUSE.jsonl or LATEST-SESSION.txt and extracts
        task list information to include in session start data.

        Returns:
            Dict with has_pending_tasks and pending_task_count
        """
        result = {"has_pending_tasks": False, "pending_task_count": 0}

        try:
            sessions_dir = Path(working_dir) / ".claude-mpm" / "sessions"
            if not sessions_dir.exists():
                return result

            # Check for active pause first
            active_pause = sessions_dir / "ACTIVE-PAUSE.jsonl"
            if active_pause.exists():
                try:
                    with open(active_pause) as f:
                        lines = f.readlines()
                        if lines:
                            last_action = json.loads(lines[-1])
                            task_list = last_action.get("data", {}).get("task_list", {})
                            pending = len(task_list.get("pending_tasks", []))
                            in_progress = len(task_list.get("in_progress_tasks", []))
                            if pending + in_progress > 0:
                                result["has_pending_tasks"] = True
                                result["pending_task_count"] = pending + in_progress
                                return result
                except (json.JSONDecodeError, KeyError):
                    pass  # nosec B110 - continue to check regular sessions

            # Check for latest session
            latest_ptr = sessions_dir / "LATEST-SESSION.txt"
            if latest_ptr.exists():
                try:
                    session_name = latest_ptr.read_text().strip()
                    session_file = sessions_dir / f"{session_name}.json"
                    if session_file.exists():
                        with open(session_file) as f:
                            session_data = json.load(f)
                            task_list = session_data.get("task_list", {})
                            pending = len(task_list.get("pending_tasks", []))
                            in_progress = len(task_list.get("in_progress_tasks", []))
                            if pending + in_progress > 0:
                                result["has_pending_tasks"] = True
                                result["pending_task_count"] = pending + in_progress
                except (json.JSONDecodeError, KeyError, FileNotFoundError):
                    pass  # nosec B110 - return default result

        except Exception:
            pass  # nosec B110 - lightweight check, don't fail session start

        return result
