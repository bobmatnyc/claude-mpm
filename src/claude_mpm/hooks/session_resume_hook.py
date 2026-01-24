"""Session Resume Startup Hook.

WHY: This hook automatically checks for paused sessions on PM startup and displays
resume context to help users continue their work seamlessly.

DESIGN DECISIONS:
- Runs automatically on PM startup
- Non-blocking: doesn't prevent PM from starting if check fails
- Displays context to stdout for user visibility
- Integrates with existing session pause/resume infrastructure
- Checks for ACTIVE-PAUSE.jsonl (incremental auto-pause) before regular paused sessions
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

# Try to import _log from hook_handler, fall back to no-op
try:
    from claude_mpm.hooks.claude_hooks.hook_handler import _log
except ImportError:

    def _log(msg: str) -> None:
        pass  # Silent fallback


logger = get_logger(__name__)


class SessionResumeStartupHook:
    """Hook for automatic session resume detection on PM startup."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the session resume hook.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = project_path or Path.cwd()
        self.resume_helper = SessionResumeHelper(self.project_path)
        self._session_displayed = False
        self.sessions_dir = self.project_path / ".claude-mpm" / "sessions"

    def _format_task_list_summary(self, task_list: Dict[str, Any]) -> str:
        """Format task list state for display.

        Args:
            task_list: Task list dict from session data with keys:
                - pending_tasks: List of task dicts with 'id' and 'title'
                - in_progress_tasks: List of task dicts with 'id' and 'title'
                - completed_count: Integer count of completed tasks

        Returns:
            Formatted string showing pending and in_progress tasks.
            Returns empty string if no tasks to display.
        """
        if not task_list:
            return ""

        lines: List[str] = []
        pending_tasks = task_list.get("pending_tasks", [])
        in_progress_tasks = task_list.get("in_progress_tasks", [])

        # Format pending tasks
        if pending_tasks:
            lines.append("📋 Pending Tasks:")
            for task in pending_tasks[:5]:  # Limit to first 5
                task_id = task.get("id", "?")
                title = task.get("title", "Untitled")
                lines.append(f"  • [{task_id}] {title}")
            if len(pending_tasks) > 5:
                lines.append(f"  ... and {len(pending_tasks) - 5} more")

        # Format in-progress tasks
        if in_progress_tasks:
            lines.append("🔄 In Progress:")
            for task in in_progress_tasks[:5]:  # Limit to first 5
                task_id = task.get("id", "?")
                title = task.get("title", "Untitled")
                lines.append(f"  • [{task_id}] {title}")
            if len(in_progress_tasks) > 5:
                lines.append(f"  ... and {len(in_progress_tasks) - 5} more")

        if not lines:
            return ""

        return "\n".join(lines)

    def check_for_active_pause(self) -> Optional[Dict[str, Any]]:
        """Check for an active incremental pause session.

        Returns:
            Pause session metadata if ACTIVE-PAUSE.jsonl exists, None otherwise
        """
        active_pause_path = self.sessions_dir / "ACTIVE-PAUSE.jsonl"

        if not active_pause_path.exists():
            logger.debug("No ACTIVE-PAUSE.jsonl found")
            return None

        try:
            # Read JSONL file to get first and last actions
            with active_pause_path.open("r") as f:
                lines = f.readlines()

            if not lines:
                logger.warning("ACTIVE-PAUSE.jsonl is empty")
                return None

            # Parse first action (session start)
            first_action = json.loads(lines[0])

            # Parse last action (most recent)
            last_action = json.loads(lines[-1]) if len(lines) > 1 else first_action

            # Extract metadata
            return {
                "is_incremental": True,
                "session_id": first_action.get("session_id"),
                "started_at": first_action.get("timestamp"),
                "context_at_start": first_action.get("data", {}).get(
                    "context_percentage", 0
                ),
                "current_context": last_action.get("context_percentage", 0),
                "action_count": len(lines),
                "file_path": str(active_pause_path),
                "task_list": last_action.get("data", {}).get("task_list", {}),
            }

        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.error(f"Failed to parse ACTIVE-PAUSE.jsonl: {e}", exc_info=True)
            return None

    def display_active_pause_warning(self, pause_info: Dict[str, Any]) -> None:
        """Display warning about active incremental pause session.

        Args:
            pause_info: Pause session metadata from check_for_active_pause()
        """
        _log("=" * 60)
        _log("⚠️  ACTIVE AUTO-PAUSE SESSION DETECTED")
        _log("=" * 60)
        _log(f"Session ID: {pause_info['session_id']}")
        _log(f"Started at: {pause_info['started_at']}")
        _log(f"Context at pause: {pause_info['context_at_start']:.1%}")
        _log(f"Actions recorded: {pause_info['action_count']}")

        # Display task list summary if available
        task_list = pause_info.get("task_list", {})
        task_summary = self._format_task_list_summary(task_list)
        if task_summary:
            _log("")
            _log(task_summary)

        _log("\nThis session was auto-paused due to high context usage.")
        _log("Options:")
        _log("  1. Continue (actions will be appended)")
        _log("  2. Use /mpm-init pause --finalize to create snapshot")
        _log("  3. Use /mpm-init pause --discard to abandon")
        _log("=" * 60 + "\n")

    def on_pm_startup(self) -> Optional[Dict[str, Any]]:
        """Execute on PM startup to check for paused sessions.

        Checks in priority order:
        1. ACTIVE-PAUSE.jsonl (incremental auto-pause)
        2. Regular paused sessions (session-*.json)

        Returns:
            Session data if paused session found, None otherwise
        """
        try:
            # Check if we already displayed a session in this process
            if self._session_displayed:
                logger.debug("Session already displayed, skipping")
                return None

            # PRIORITY 1: Check for active incremental pause FIRST
            active_pause_info = self.check_for_active_pause()
            if active_pause_info:
                self.display_active_pause_warning(active_pause_info)
                self._session_displayed = True
                logger.info("Active pause session detected and displayed")
                return active_pause_info

            # PRIORITY 2: Fall back to regular paused sessions
            session_data = self.resume_helper.check_and_display_resume_prompt()

            if session_data:
                self._session_displayed = True
                logger.info("Paused session context displayed to user")

            return session_data

        except Exception as e:
            logger.error(f"Failed to check for paused sessions: {e}", exc_info=True)
            return None

    def get_session_count(self) -> int:
        """Get count of paused sessions.

        Returns:
            Number of paused sessions
        """
        try:
            return self.resume_helper.get_session_count()
        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            return 0

    def clear_displayed_session(self, session_data: Dict[str, Any]) -> bool:
        """Clear a session after it has been displayed and user has acknowledged.

        Args:
            session_data: Session data to clear

        Returns:
            True if successfully cleared, False otherwise
        """
        try:
            return self.resume_helper.clear_session(session_data)
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False


# Global hook instance
_session_resume_hook: Optional[SessionResumeStartupHook] = None


def get_session_resume_hook(
    project_path: Optional[Path] = None,
) -> SessionResumeStartupHook:
    """Get or create the global session resume hook instance.

    Args:
        project_path: Project root path (default: current directory)

    Returns:
        SessionResumeStartupHook instance
    """
    global _session_resume_hook

    if _session_resume_hook is None:
        _session_resume_hook = SessionResumeStartupHook(project_path)
        logger.debug("Created session resume hook instance")

    return _session_resume_hook


def trigger_session_resume_check() -> Optional[Dict[str, Any]]:
    """Trigger a session resume check (convenience function).

    This is the main entry point for PM startup integration.

    Returns:
        Session data if found, None otherwise
    """
    hook = get_session_resume_hook()
    return hook.on_pm_startup()
