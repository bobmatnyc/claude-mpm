from pathlib import Path

"""Session management service for orchestrating Claude sessions.

This service handles:
1. Interactive session orchestration
2. Oneshot session orchestration
3. Session lifecycle management
4. Session logging and cleanup

Extracted from ClaudeRunner to follow Single Responsibility Principle.

DEPENDENCY INJECTION:
This service uses protocol-based dependency injection to avoid circular imports.
It accepts a ClaudeRunnerProtocol instead of importing ClaudeRunner directly.
"""

import time
import uuid
from datetime import timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.enums import OperationResult, ServiceState
from claude_mpm.services.core.interfaces import SessionManagementInterface

# Protocol imports for type checking without circular dependencies
if TYPE_CHECKING:
    from claude_mpm.core.protocols import ClaudeRunnerProtocol
else:
    # At runtime, accept any object with matching interface
    ClaudeRunnerProtocol = Any


class SessionManagementService(BaseService, SessionManagementInterface):
    """Service for managing Claude session orchestration."""

    def __init__(self, runner: Optional["ClaudeRunnerProtocol"] = None):
        """Initialize the session management service.

        Args:
            runner: ClaudeRunner instance (or any object matching ClaudeRunnerProtocol)
                    for delegation
        """
        super().__init__(name="session_management_service")
        self.runner: Optional[ClaudeRunnerProtocol] = runner
        self.active_sessions = {}  # Track active sessions

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def run_interactive_session(self, initial_context: Optional[str] = None) -> bool:
        """Run Claude in interactive mode using session delegation.

        WHY: This method delegates to InteractiveSession class for better
        maintainability and reduced complexity. The session class handles all
        the details while this method provides the orchestration interface.

        Args:
            initial_context: Optional initial context to pass to Claude

        Returns:
            bool: True if session completed successfully, False otherwise
        """
        try:
            from claude_mpm.core.interactive_session import InteractiveSession

            # Create session handler
            session = InteractiveSession(self.runner)

            # Step 1: Initialize session
            success, error = session.initialize_interactive_session()
            if not success:
                self.logger.error(f"Failed to initialize interactive session: {error}")
                return False

            # Step 2: Set up environment
            success, environment = session.setup_interactive_environment()
            if not success:
                self.logger.error("Failed to setup interactive environment")
                return False

            # Step 3: Handle interactive input/output
            # This is where the actual Claude process runs
            session.handle_interactive_input(environment)

            return True

        except Exception as e:
            self.logger.error(f"Interactive session failed: {e}")
            return False
        finally:
            # Step 4: Clean up session
            if "session" in locals():
                session.cleanup_interactive_session()

    def run_oneshot_session(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt using session delegation.

        WHY: This method delegates to OneshotSession class for better
        maintainability and reduced complexity. The session class handles
        all the details while this method provides the orchestration interface.

        Args:
            prompt: The command or prompt to execute
            context: Optional context to prepend to the prompt

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from claude_mpm.core.oneshot_session import OneshotSession

            # Create session handler
            session = OneshotSession(self.runner)

            # Step 1: Initialize session
            success, error = session.initialize_session(prompt)
            if not success:
                return False

            # Special case: MPM commands return early
            if (
                error is None
                and self.runner.command_handler_service
                and self.runner.command_handler_service.is_mpm_command(prompt)
            ):
                return success

            # Step 2: Deploy agents
            if not session.deploy_agents():
                self.logger.warning("Agent deployment had issues, continuing...")

            # Step 3: Set up infrastructure
            infrastructure = session.setup_infrastructure()

            # Step 4: Execute command
            success, response = session.execute_command(prompt, context, infrastructure)

            return success

        except Exception as e:
            self.logger.error(f"Oneshot session failed: {e}")
            return False
        finally:
            # Step 5: Clean up session
            if "session" in locals():
                session.cleanup_session()

    def create_session_log_file(self) -> Optional[Path]:
        """Create a session log file for the current session.

        Returns:
            Path to the created log file, or None if creation failed
        """
        try:
            import uuid
            from datetime import datetime

            from claude_mpm.config.paths import paths

            # Create session logs directory if it doesn't exist
            session_logs_dir = paths.project_root / ".claude-mpm" / "logs" / "sessions"
            session_logs_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique session log filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            session_id = str(uuid.uuid4())[:8]
            log_filename = f"session_{timestamp}_{session_id}.jsonl"
            log_file = session_logs_dir / log_filename

            # Create empty log file
            log_file.touch()

            self.logger.debug(f"Created session log file: {log_file}")
            return log_file

        except Exception as e:
            self.logger.warning(f"Failed to create session log file: {e}")
            return None

    def log_session_event(self, log_file: Path, event_data: dict):
        """Log an event to the session log file.

        Args:
            log_file: Path to the session log file
            event_data: Event data to log
        """
        if not log_file or not log_file.exists():
            return

        try:
            import json
            from datetime import datetime

            # Add timestamp to event data
            event_data["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Append to log file as JSONL
            with log_file.open("a") as f:
                f.write(json.dumps(event_data) + "\n")

        except Exception as e:
            self.logger.warning(f"Failed to log session event: {e}")

    def get_service_status(self) -> dict:
        """Get current session management service status.

        Returns:
            dict: Session management service status information
        """
        return {
            "service_available": True,
            "runner_available": self.runner is not None,
            "interactive_session_available": True,
            "oneshot_session_available": True,
            "active_sessions": len(self.active_sessions),
        }

    # Implementation of abstract methods from SessionManagementInterface

    def start_session(self, session_config: Dict[str, Any]) -> str:
        """Start a new session.

        Args:
            session_config: Configuration for the session

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_info = {
            "id": session_id,
            "config": session_config,
            "start_time": time.time(),
            "status": ServiceState.RUNNING,
            "type": session_config.get("type", "interactive"),
        }

        self.active_sessions[session_id] = session_info
        self.logger.info(f"Started session {session_id}")

        return session_id

    def end_session(self, session_id: str) -> bool:
        """End an active session.

        Args:
            session_id: ID of session to end

        Returns:
            True if session ended successfully
        """
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id]
            session_info["status"] = "ended"
            session_info["end_time"] = time.time()

            # Remove from active sessions
            del self.active_sessions[session_id]

            self.logger.info(f"Ended session {session_id}")
            return True
        self.logger.warning(f"Session {session_id} not found")
        return False

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a session.

        Args:
            session_id: ID of session

        Returns:
            Dictionary with session status information
        """
        if session_id in self.active_sessions:
            return self.active_sessions[session_id].copy()
        return {
            "id": session_id,
            "status": OperationResult.ERROR,
            "error": "Session not found",
        }

    def list_active_sessions(self) -> List[str]:
        """List all active session IDs.

        Returns:
            List of active session IDs
        """
        return list(self.active_sessions.keys())

    async def cleanup_sessions(self) -> int:
        """Clean up inactive or expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        expired_sessions = []

        # Find sessions older than 24 hours
        for session_id, session_info in self.active_sessions.items():
            if current_time - session_info["start_time"] > 86400:  # 24 hours
                expired_sessions.append(session_id)

        # Clean up expired sessions
        for session_id in expired_sessions:
            self.end_session(session_id)

        self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)
