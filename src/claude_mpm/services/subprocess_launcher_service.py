"""Subprocess launcher service for launching Claude as a subprocess with PTY.

This service handles:
1. PTY (pseudo-terminal) creation and management
2. Subprocess launching with proper I/O handling
3. Terminal state management and restoration
4. Signal handling for graceful shutdown
5. WebSocket integration for status updates

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

import contextlib
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import tty
from typing import Any, Dict, List, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.enums import OperationResult, ServiceState
from claude_mpm.services.core.interfaces import SubprocessLauncherInterface


class SubprocessLauncherService(BaseService, SubprocessLauncherInterface):
    """Service for launching Claude as a subprocess with PTY support."""

    def __init__(self, project_logger=None, websocket_server=None):
        """Initialize the subprocess launcher service.

        Args:
            project_logger: Optional logger for system events
            websocket_server: Optional WebSocket server for status updates
        """
        super().__init__(name="subprocess_launcher_service")
        self.project_logger = project_logger
        self.websocket_server = websocket_server

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    # Implementation of abstract methods from SubprocessLauncherInterface

    def launch_subprocess(self, command: List[str], **kwargs) -> Dict[str, Any]:
        """Launch a subprocess with PTY support.

        Args:
            command: Command and arguments to execute
            **kwargs: Additional subprocess options

        Returns:
            Dictionary with subprocess information and handles
        """
        # For now, delegate to the existing interactive method
        # In a full implementation, this would return process info
        try:
            env = kwargs.get("env", self.prepare_subprocess_environment())
            self.launch_subprocess_interactive(command, env)
            return {
                "status": OperationResult.SUCCESS,
                "command": command,
                "method": "interactive",
            }
        except Exception as e:
            return {
                "status": OperationResult.FAILED,
                "error": str(e),
                "command": command,
            }

    async def launch_subprocess_async(
        self, command: List[str], **kwargs
    ) -> Dict[str, Any]:
        """Launch a subprocess asynchronously with PTY support.

        Args:
            command: Command and arguments to execute
            **kwargs: Additional subprocess options

        Returns:
            Dictionary with subprocess information and handles
        """
        # For async version, we'd use asyncio subprocess
        # For now, delegate to sync version
        return self.launch_subprocess(command, **kwargs)

    def terminate_subprocess(self, process_id: str) -> bool:
        """Terminate a running subprocess.

        Args:
            process_id: ID of the process to terminate

        Returns:
            True if termination successful
        """
        # This would need process tracking to be implemented
        # For now, return False as we don't track processes
        self.logger.warning(f"Process termination not implemented for ID: {process_id}")
        return False

    def get_subprocess_status(self, process_id: str) -> Dict[str, Any]:
        """Get status of a running subprocess.

        Args:
            process_id: ID of the process

        Returns:
            Dictionary with process status information
        """
        # This would need process tracking to be implemented
        # For now, return unknown status
        return {
            "process_id": process_id,
            "status": OperationResult.UNKNOWN,
            "message": "Process tracking not implemented",
        }

    def launch_subprocess_interactive(
        self, cmd: List[str], env: Dict[str, str]
    ) -> None:
        """Launch Claude as a subprocess with PTY for interactive mode.

        This method launches Claude as a subprocess when explicitly requested
        (via --launch-method subprocess). Subprocess mode maintains the parent process,
        which can be useful for:
        1. Maintaining WebSocket connections and monitoring
        2. Providing proper cleanup and error handling
        3. Debugging and development scenarios

        Uses PTY (pseudo-terminal) to maintain full interactive capabilities.
        Response logging is handled through the hook system, not I/O interception,
        for better performance and compatibility.

        Args:
            cmd: Command list to execute
            env: Environment variables for the subprocess
        """
        # Save original terminal settings
        original_tty = None
        if sys.stdin.isatty():
            original_tty = termios.tcgetattr(sys.stdin)

        # Create PTY
        master_fd, slave_fd = pty.openpty()

        try:
            # Start Claude process
            process = subprocess.Popen(
                cmd, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, env=env
            )

            # Close slave in parent
            os.close(slave_fd)

            if self.project_logger:
                self.project_logger.log_system(
                    f"Claude subprocess started with PID {process.pid}",
                    level="INFO",
                    component="subprocess",
                )

            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status=ServiceState.RUNNING,
                    pid=process.pid,
                    message="Claude subprocess started",
                )

            # Set terminal to raw mode for proper interaction
            if sys.stdin.isatty():
                tty.setraw(sys.stdin)

            # Handle Ctrl+C gracefully
            def signal_handler(signum, frame):
                if process.poll() is None:
                    process.terminate()
                raise KeyboardInterrupt()

            signal.signal(signal.SIGINT, signal_handler)

            # I/O loop
            self._handle_subprocess_io(master_fd, process)

            # Wait for process to complete
            process.wait()

            # Note: Response logging is handled through the hook system

            if self.project_logger:
                self.project_logger.log_system(
                    f"Claude subprocess exited with code {process.returncode}",
                    level="INFO",
                    component="subprocess",
                )

            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status=ServiceState.STOPPED,
                    message=f"Claude subprocess exited with code {process.returncode}",
                )

        finally:
            # Restore terminal
            if original_tty and sys.stdin.isatty():
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_tty)

            # Close PTY
            with contextlib.suppress(Exception):
                os.close(master_fd)

            # Ensure process is terminated
            if "process" in locals() and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            # End WebSocket session if in subprocess mode
            if self.websocket_server:
                self.websocket_server.session_ended()

    def _handle_subprocess_io(self, master_fd: int, process: subprocess.Popen) -> None:
        """Handle I/O between the subprocess and the terminal.

        Args:
            master_fd: Master file descriptor for the PTY
            process: The subprocess instance
        """
        while True:
            # Check if process is still running
            if process.poll() is not None:
                break

            # Check for data from Claude or stdin
            r, _, _ = select.select([master_fd, sys.stdin], [], [], 0)

            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        os.write(sys.stdout.fileno(), data)
                        # Broadcast output to WebSocket clients
                        if self.websocket_server:
                            try:
                                # Decode and send
                                output = data.decode("utf-8", errors="replace")
                                self.websocket_server.claude_output(output, "stdout")
                            except Exception as e:
                                self.logger.debug(f"Failed to broadcast output: {e}")
                    else:
                        break  # EOF
                except OSError:
                    break

            if sys.stdin in r:
                try:
                    data = os.read(sys.stdin.fileno(), 4096)
                    if data:
                        os.write(master_fd, data)
                except OSError:
                    break

    def is_subprocess_mode_available(self) -> bool:
        """Check if subprocess mode is available on this platform.

        Returns:
            True if subprocess mode with PTY is available
        """
        import importlib.util

        # Check if we can import required modules
        required = ["pty", "select", "termios", "tty"]
        return all(importlib.util.find_spec(mod) is not None for mod in required)

    def create_subprocess_command(
        self, base_cmd: List[str], additional_args: Optional[List[str]] = None
    ) -> List[str]:
        """Create a subprocess command with proper arguments.

        Args:
            base_cmd: Base command to execute
            additional_args: Additional arguments to append

        Returns:
            Complete command list for subprocess execution
        """
        cmd = base_cmd.copy()
        if additional_args:
            cmd.extend(additional_args)
        return cmd

    def prepare_subprocess_environment(
        self, base_env: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Prepare environment variables for subprocess execution.

        Args:
            base_env: Base environment variables to extend

        Returns:
            Complete environment dictionary for subprocess
        """
        env = os.environ.copy()
        if base_env:
            env.update(base_env)

        # Disable telemetry for Claude Code subprocesses
        # This ensures Claude Code doesn't send telemetry data during runtime
        env["DISABLE_TELEMETRY"] = "1"

        return env
