"""Session Resume Startup Hook.

WHY: This hook automatically checks for paused sessions on PM startup and displays
resume context to help users continue their work seamlessly.

DESIGN DECISIONS:
- Runs automatically on PM startup
- Non-blocking: doesn't prevent PM from starting if check fails
- Displays context to stdout for user visibility
- Integrates with existing session pause/resume infrastructure
"""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

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

    def on_pm_startup(self) -> Optional[Dict[str, Any]]:
        """Execute on PM startup to check for paused sessions.

        Returns:
            Session data if paused session found, None otherwise
        """
        try:
            # Check if we already displayed a session in this process
            if self._session_displayed:
                logger.debug("Session already displayed, skipping")
                return None

            # Check for paused sessions
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
