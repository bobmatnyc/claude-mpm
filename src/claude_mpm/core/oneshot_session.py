"""Oneshot session handler for Claude MPM.

This module encapsulates the logic for running one-time Claude commands,
breaking down the monolithic run_oneshot method into focused, testable components.
"""

import contextlib
import os
import subprocess
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from claude_mpm.core.logger import get_logger


class OneshotSession:
    """Manages a single oneshot Claude execution session.

    WHY: This class extracts the complex oneshot logic from ClaudeRunner,
    reducing cyclomatic complexity and improving maintainability.

    DESIGN DECISION: Each method focuses on a single responsibility with
    complexity < 10 and lines < 80, making the code easier to test and modify.
    """

    def __init__(self, runner):
        """Initialize the oneshot session with a reference to the runner.

        Args:
            runner: The ClaudeRunner instance that owns this session
        """
        self.runner = runner
        self.logger = get_logger("oneshot_session")
        self.start_time = None
        self.session_id = None
        self.original_cwd = None

    def initialize_session(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """Initialize the oneshot session.

        Returns:
            Tuple of (success, error_message)
        """
        self.start_time = time.time()
        self.session_id = str(uuid.uuid4())

        # Check for special MPM commands
        if prompt.strip().startswith("/mpm:"):
            result = self.runner._handle_mpm_command(prompt.strip())
            return (result, None)

        # Initialize WebSocket if enabled
        if self.runner.enable_websocket:
            self._setup_websocket()

        # Log session start
        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"Starting non-interactive session with prompt: {prompt[:100]}",
                level="INFO",
                component="session",
            )

        return (True, None)

    def deploy_agents(self) -> bool:
        """Deploy system and project agents.

        Returns:
            True if successful, False otherwise
        """
        # Deploy system agents
        if not self.runner.setup_agents():
            print("Continuing without native agents...")

        # Deploy project-specific agents
        self.runner.deploy_project_agents_to_claude()

        return True

    def setup_infrastructure(self) -> Dict[str, Any]:
        """Set up the execution environment and build the command.

        Returns:
            Dictionary containing command, environment, and other setup details
        """
        infrastructure = {
            "env": self._prepare_environment(),
            "cmd": self._build_command(),
            "working_dir_changed": False,
        }

        # Change to user working directory if specified
        if "CLAUDE_MPM_USER_PWD" in infrastructure["env"]:
            user_pwd = infrastructure["env"]["CLAUDE_MPM_USER_PWD"]
            infrastructure["env"]["CLAUDE_WORKSPACE"] = user_pwd

            try:
                self.original_cwd = os.getcwd()
                os.chdir(user_pwd)
                infrastructure["working_dir_changed"] = True
                self.logger.info(f"Changed working directory to: {user_pwd}")
            except (PermissionError, FileNotFoundError, OSError) as e:
                self.logger.warning(f"Could not change to directory {user_pwd}: {e}")
                self.original_cwd = None

        return infrastructure

    def execute_command(
        self, prompt: str, context: Optional[str], infrastructure: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Execute the Claude command with the given prompt.

        Args:
            prompt: The user's prompt
            context: Optional context to prepend
            infrastructure: Setup details from setup_infrastructure

        Returns:
            Tuple of (success, response_or_error)
        """
        # Build final command
        cmd = self._build_final_command(prompt, context, infrastructure)

        # Log and notify
        self._notify_execution_start()

        # Execute with proper error handling
        return self._run_subprocess(cmd, infrastructure["env"], prompt)

    def _build_final_command(
        self, prompt: str, context: Optional[str], infrastructure: Dict[str, Any]
    ) -> list:
        """Build the final command with prompt and system instructions."""
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        cmd = infrastructure["cmd"] + ["--print", full_prompt]

        # Add system instructions if available
        system_prompt = self.runner._create_system_prompt()

        # Debug: log the system prompt to check for issues
        if system_prompt:
            self.logger.debug(f"System prompt length: {len(system_prompt)}")
            if "Path.cwd()" in system_prompt or "Path(" in system_prompt:
                self.logger.warning("System prompt contains Python code references!")

        if system_prompt and system_prompt != self._get_simple_context():
            # The problem might be with insert positioning
            # Let's add system prompt differently
            cmd.extend(["--append-system-prompt", system_prompt])

        return cmd

    def _notify_execution_start(self) -> None:
        """Log and notify about execution start."""
        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                "Executing Claude subprocess", level="INFO", component="session"
            )

        if self.runner.websocket_server:
            self.runner.websocket_server.claude_status_changed(
                status="running", message="Executing Claude oneshot command"
            )

    def _run_subprocess(
        self, cmd: list, env: dict, prompt: str
    ) -> Tuple[bool, Optional[str]]:
        """Run the subprocess and handle all exception types."""
        try:
            # Debug: log the command being run
            self.logger.debug(f"Running command: {' '.join(cmd[:5])}...")
            if len(cmd) > 5:
                self.logger.debug(f"Command has {len(cmd)} arguments total")

            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env, check=False
            )

            if result.returncode == 0:
                response = result.stdout.strip()
                self._handle_successful_response(response, prompt)
                return (True, response)
            error_msg = result.stderr or "Unknown error"
            self._handle_error_response(error_msg, result.returncode)
            return (False, error_msg)

        except subprocess.TimeoutExpired as e:
            return self._handle_timeout(e)
        except FileNotFoundError:
            return self._handle_claude_not_found()
        except PermissionError as e:
            return self._handle_permission_error(e)
        except KeyboardInterrupt:
            return self._handle_keyboard_interrupt()
        except MemoryError as e:
            return self._handle_memory_error(e)
        except Exception as e:
            return self._handle_unexpected_error(e)

    def cleanup_session(self) -> None:
        """Clean up the session and restore state."""
        # Restore original working directory
        if self.original_cwd:
            with contextlib.suppress(Exception):
                os.chdir(self.original_cwd)

        # Log session summary
        if self.runner.project_logger:
            try:
                summary = self.runner.project_logger.get_session_summary()
                self.runner.project_logger.log_system(
                    f"Session {summary['session_id']} completed",
                    level="INFO",
                    component="session",
                )
            except Exception as e:
                self.logger.debug(f"Failed to log session summary: {e}")

        # End WebSocket session
        if self.runner.websocket_server:
            self.runner.websocket_server.claude_status_changed(
                status="stopped", message="Session completed"
            )
            self.runner.websocket_server.session_ended()

    # Private helper methods

    def _setup_websocket(self) -> None:
        """Initialize WebSocket connection."""
        try:
            from claude_mpm.services.socketio_server import SocketIOClientProxy

            self.runner.websocket_server = SocketIOClientProxy(
                port=self.runner.websocket_port
            )
            self.runner.websocket_server.start()
            self.logger.info("Connected to Socket.IO monitoring server")

            # Notify session start
            self.runner.websocket_server.session_started(
                session_id=self.session_id,
                launch_method="oneshot",
                working_dir=os.getcwd(),
            )
        except (ImportError, ConnectionError, Exception) as e:
            self.logger.warning(f"Socket.IO connection failed: {e}")
            self.runner.websocket_server = None

    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare the execution environment."""
        env = os.environ.copy()

        # Disable telemetry for Claude Code
        # This ensures Claude Code doesn't send telemetry data during runtime
        env["DISABLE_TELEMETRY"] = "1"

        return env

    def _build_command(self) -> list:
        """Build the base Claude command."""
        cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]

        # Add custom arguments
        if self.runner.claude_args:
            cmd.extend(self.runner.claude_args)

        return cmd

    def _handle_successful_response(self, response: str, prompt: str) -> None:
        """Process a successful Claude response."""
        print(response)

        execution_time = time.time() - self.start_time

        # Log response if enabled
        if self.runner.response_logger and response:
            response_summary = prompt[:200] + "..." if len(prompt) > 200 else prompt
            self.runner.response_logger.log_response(
                request_summary=response_summary,
                response_content=response,
                metadata={
                    "mode": "oneshot",
                    "model": "opus",
                    "exit_code": 0,
                    "execution_time": execution_time,
                },
                agent="claude-direct",
            )

        # Broadcast to WebSocket
        if self.runner.websocket_server and response:
            self.runner.websocket_server.claude_output(response, "stdout")

            # Check for delegation
            if self.runner._contains_delegation(response):
                agent_name = self.runner._extract_agent_from_response(response)
                if agent_name:
                    self.runner.websocket_server.agent_delegated(
                        agent=agent_name, task=prompt[:100], status="detected"
                    )

        # Log completion
        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"Non-interactive session completed successfully in {execution_time:.2f}s",
                level="INFO",
                component="session",
            )

            self.runner._log_session_event(
                {
                    "event": "session_complete",
                    "success": True,
                    "execution_time": execution_time,
                    "response_length": len(response),
                }
            )

        # Extract tickets if enabled
        if self.runner.enable_tickets and self.runner.ticket_manager and response:
            self.runner._extract_tickets(response)

    def _handle_error_response(self, error_msg: str, return_code: int) -> None:
        """Handle an error response from Claude."""
        print(f"Error: {error_msg}")

        # Debug: print full traceback if available
        if "Traceback" in error_msg or "Error:" in error_msg:
            self.logger.debug(f"Full error output:\n{error_msg}")

        # Broadcast error
        if self.runner.websocket_server:
            self.runner.websocket_server.claude_output(error_msg, "stderr")
            self.runner.websocket_server.claude_status_changed(
                status="error", message=f"Command failed with code {return_code}"
            )

        # Log error
        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"Non-interactive session failed: {error_msg}",
                level="ERROR",
                component="session",
            )
            self.runner._log_session_event(
                {
                    "event": "session_failed",
                    "success": False,
                    "error": error_msg,
                    "return_code": return_code,
                }
            )

    def _handle_timeout(self, e: subprocess.TimeoutExpired) -> Tuple[bool, str]:
        """Handle command timeout."""
        error_msg = f"Command timed out after {e.timeout} seconds"
        print(f"⏱️  {error_msg}")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                error_msg, level="ERROR", component="session"
            )
            self.runner._log_session_event(
                {
                    "event": "session_timeout",
                    "success": False,
                    "timeout": e.timeout,
                    "exception_type": "TimeoutExpired",
                }
            )

        return (False, error_msg)

    def _handle_claude_not_found(self) -> Tuple[bool, str]:
        """Handle Claude CLI not found error."""
        error_msg = (
            "Claude CLI not found. Please ensure 'claude' is installed and in your PATH"
        )
        print(f"❌ {error_msg}")
        print(
            "\n💡 To fix: Install Claude CLI with 'npm install -g @anthropic-ai/claude-ai'"
        )

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"{error_msg}", level="ERROR", component="session"
            )
            self.runner._log_session_event(
                {
                    "event": "session_exception",
                    "success": False,
                    "exception": "FileNotFoundError",
                    "exception_type": "FileNotFoundError",
                }
            )

        return (False, error_msg)

    def _handle_permission_error(self, e: PermissionError) -> Tuple[bool, str]:
        """Handle permission denied error."""
        error_msg = f"Permission denied executing Claude CLI: {e}"
        print(f"❌ {error_msg}")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                error_msg, level="ERROR", component="session"
            )
            self.runner._log_session_event(
                {
                    "event": "session_exception",
                    "success": False,
                    "exception": str(e),
                    "exception_type": "PermissionError",
                }
            )

        return (False, error_msg)

    def _handle_keyboard_interrupt(self) -> Tuple[bool, str]:
        """Handle keyboard interrupt."""
        print("\n⚠️  Command interrupted by user")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                "Session interrupted by user", level="INFO", component="session"
            )
            self.runner._log_session_event(
                {
                    "event": "session_interrupted",
                    "success": False,
                    "reason": "user_interrupt",
                }
            )

        return (False, "User interrupted")

    def _handle_memory_error(self, e: MemoryError) -> Tuple[bool, str]:
        """Handle out of memory error."""
        error_msg = "Out of memory while processing command"
        print(f"❌ {error_msg}")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"{error_msg}: {e}", level="ERROR", component="session"
            )
            self.runner._log_session_event(
                {
                    "event": "session_exception",
                    "success": False,
                    "exception": str(e),
                    "exception_type": "MemoryError",
                }
            )

        return (False, error_msg)

    def _handle_unexpected_error(self, e: Exception) -> Tuple[bool, str]:
        """Handle unexpected errors."""
        error_msg = f"Unexpected error: {e}"
        print(f"❌ {error_msg}")
        print(f"   Error type: {type(e).__name__}")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"Exception during non-interactive session: {e}",
                level="ERROR",
                component="session",
            )
            self.runner._log_session_event(
                {
                    "event": "session_exception",
                    "success": False,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                }
            )

        return (False, error_msg)

    def _get_simple_context(self) -> str:
        """Get the simple context string for comparison."""
        # Import here to avoid circular dependency
        from claude_mpm.core.claude_runner import create_simple_context

        return create_simple_context()
