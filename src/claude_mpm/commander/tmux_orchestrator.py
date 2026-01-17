"""Tmux orchestration layer for MPM Commander.

This module wraps tmux commands to manage sessions, panes, and I/O for
coordinating multiple project-level MPM instances.
"""

import logging
import shutil
import subprocess  # nosec B404 - Required for tmux interaction
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


class TmuxNotFoundError(Exception):
    """Raised when tmux is not installed or not found in PATH."""

    def __init__(
        self,
        message: str = "tmux not found. Please install tmux to use commander mode.",
    ):
        super().__init__(message)
        self.message = message


@dataclass
class TmuxOrchestrator:
    """Orchestrate multiple MPM sessions via tmux.

    This class provides a high-level API for managing tmux sessions and panes,
    enabling the MPM Commander to coordinate multiple project-level MPM instances.

    Attributes:
        session_name: Name of the tmux session (default: "mpm-commander")

    Example:
        >>> orchestrator = TmuxOrchestrator()
        >>> orchestrator.create_session()
        >>> target = orchestrator.create_pane("proj1", "/path/to/project")
        >>> orchestrator.send_keys(target, "echo 'Hello from pane'")
        >>> output = orchestrator.capture_output(target)
        >>> print(output)
        >>> orchestrator.kill_session()
    """

    session_name: str = "mpm-commander"

    def __post_init__(self):
        """Verify tmux is available on initialization."""
        if not shutil.which("tmux"):
            raise TmuxNotFoundError()

    def _run_tmux(
        self, args: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute tmux command and return result.

        Args:
            args: List of tmux command arguments
            check: Whether to raise exception on non-zero exit code

        Returns:
            CompletedProcess with stdout/stderr captured

        Raises:
            TmuxNotFoundError: If tmux binary not found
            subprocess.CalledProcessError: If check=True and command fails
        """
        cmd = ["tmux"] + args
        logger.debug(f"Running tmux command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)  # nosec B603

            if result.stdout:
                logger.debug(f"tmux stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"tmux stderr: {result.stderr.strip()}")

            return result

        except FileNotFoundError as err:
            raise TmuxNotFoundError() from err

    def session_exists(self) -> bool:
        """Check if commander session exists.

        Returns:
            True if session exists, False otherwise

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> if not orchestrator.session_exists():
            ...     orchestrator.create_session()
        """
        result = self._run_tmux(["has-session", "-t", self.session_name], check=False)
        exists = result.returncode == 0
        logger.debug(f"Session '{self.session_name}' exists: {exists}")
        return exists

    def create_session(self) -> bool:
        """Create main commander tmux session if not exists.

        Creates a detached tmux session for the commander. If the session
        already exists, this is a no-op.

        Returns:
            True if session was created, False if it already existed

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            True
            >>> orchestrator.create_session()  # Already exists
            False
        """
        if self.session_exists():
            logger.info(f"Session '{self.session_name}' already exists")
            return False

        logger.info(f"Creating tmux session '{self.session_name}'")
        self._run_tmux(
            [
                "new-session",
                "-d",  # Detached
                "-s",
                self.session_name,
                "-n",
                "commander",  # Window name
            ]
        )

        return True

    def create_pane(self, pane_id: str, working_dir: str) -> str:
        """Create new pane for a project (DEPRECATED - use create_window).

        This method is kept for backward compatibility but now creates a window instead.
        """
        return self.create_window(pane_id, working_dir)

    def create_window(self, window_name: str, working_dir: str) -> str:
        """Create new window for a project session.

        Creates a new window in the commander session with the specified
        working directory. Each session gets its own window to avoid
        pane size issues.

        Args:
            window_name: Name for the window (e.g., project name)
            working_dir: Working directory for the window

        Returns:
            Tmux target string (window:pane format like "mpm-commander:proj-name")

        Raises:
            subprocess.CalledProcessError: If window creation fails

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> target = orchestrator.create_window("my-project", "/path/to/project")
            >>> print(target)
            mpm-commander:my-project
        """
        logger.info(f"Creating window '{window_name}' in {working_dir}")

        # Create new window (not pane)
        self._run_tmux(
            [
                "new-window",
                "-t",
                self.session_name,
                "-n",
                window_name,  # Window name
                "-c",
                working_dir,  # Working directory
            ]
        )

        # Target is session:window_name
        target = f"{self.session_name}:{window_name}"
        logger.debug(f"Created window with target: {target}")
        return target

    def send_keys(self, target: str, keys: str, enter: bool = True) -> bool:
        """Send keystrokes to a pane.

        Args:
            target: Tmux target (from create_pane)
            keys: Keys to send to the pane
            enter: Whether to send Enter key after keys

        Returns:
            True if successful

        Raises:
            subprocess.CalledProcessError: If target pane doesn't exist

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> target = orchestrator.create_pane("proj", "/tmp")
            >>> orchestrator.send_keys(target, "echo 'Hello'")
            >>> orchestrator.send_keys(target, "ls -la", enter=False)
        """
        logger.debug(f"Sending keys to {target}: {keys}")

        args = ["send-keys", "-t", target, keys]
        if enter:
            args.append("Enter")

        self._run_tmux(args)
        return True

    def capture_output(self, target: str, lines: int = 100) -> str:
        """Capture recent output from pane.

        Args:
            target: Tmux target (from create_pane)
            lines: Number of lines to capture from history

        Returns:
            Captured output as string

        Raises:
            subprocess.CalledProcessError: If target pane doesn't exist

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> target = orchestrator.create_pane("proj", "/tmp")
            >>> orchestrator.send_keys(target, "echo 'Test output'")
            >>> output = orchestrator.capture_output(target, lines=10)
            >>> print(output)
            Test output
        """
        logger.debug(f"Capturing {lines} lines from {target}")

        result = self._run_tmux(
            [
                "capture-pane",
                "-t",
                target,
                "-p",  # Print to stdout
                "-S",
                f"-{lines}",  # Start from N lines back
            ]
        )

        return result.stdout

    def list_panes(self) -> List[Dict[str, str]]:
        """List all panes with their status (DEPRECATED - use list_windows).

        Kept for backward compatibility.
        """
        return self.list_windows()

    def list_windows(self) -> List[Dict[str, str]]:
        """List all windows in the commander session.

        Returns:
            List of dicts with window info (name, path, target, active)

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> windows = orchestrator.list_windows()
            >>> for win in windows:
            ...     print(f"{win['name']}: {win['path']}")
            commander: /Users/user
            my-project: /Users/user/projects/my-project
        """
        if not self.session_exists():
            logger.warning(f"Session '{self.session_name}' does not exist")
            return []

        logger.debug(f"Listing windows for session '{self.session_name}'")

        result = self._run_tmux(
            [
                "list-windows",
                "-t",
                self.session_name,
                "-F",
                "#{window_name}|#{pane_current_path}|#{window_active}|#{pane_pid}",
            ]
        )

        windows = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) >= 4:
                window_name = parts[0]
                windows.append(
                    {
                        "name": window_name,
                        "path": parts[1],
                        "target": f"{self.session_name}:{window_name}",
                        "active": parts[2] == "1",
                        "pid": parts[3],
                    }
                )

        logger.debug(f"Found {len(windows)} windows")
        return windows

    def kill_pane(self, target: str) -> bool:
        """Kill a specific pane/window (DEPRECATED - use kill_window).

        Kept for backward compatibility.
        """
        return self.kill_window(target)

    def kill_window(self, target: str) -> bool:
        """Kill a specific window.

        Args:
            target: Tmux target (from create_window or list_windows)

        Returns:
            True if successful

        Raises:
            subprocess.CalledProcessError: If target window doesn't exist

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> target = orchestrator.create_window("proj", "/tmp")
            >>> orchestrator.kill_window(target)
            True
        """
        logger.info(f"Killing window {target}")

        self._run_tmux(["kill-window", "-t", target])
        return True

    def sync_windows_with_registry(self, registry) -> Dict[str, str]:
        """Synchronize tmux windows with project registry.

        Checks which windows exist in tmux and updates session status
        in the registry accordingly.

        Args:
            registry: ProjectRegistry instance

        Returns:
            Dict mapping window names to their status (found/missing)

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> sync_result = orchestrator.sync_windows_with_registry(registry)
            >>> print(sync_result)
            {'my-project-claude-code': 'found', 'old-project': 'missing'}
        """
        logger.info("Synchronizing tmux windows with registry")

        # Get current tmux windows
        tmux_windows = {w["name"]: w for w in self.list_windows()}
        sync_result = {}

        # Check each project's sessions
        for project in registry.list_all():
            for session_id, session in project.sessions.items():
                # Extract window name from tmux_target (format: session:window_name)
                if session.tmux_target and ":" in session.tmux_target:
                    window_name = session.tmux_target.split(":")[-1]
                else:
                    window_name = f"{project.name}-{session.runtime}"

                if window_name in tmux_windows:
                    # Window exists - update status to running
                    if session.status != "running":
                        session.status = "running"
                        logger.debug(f"Session {session_id} marked as running")
                    sync_result[window_name] = "found"
                else:
                    # Window missing - update status to stopped
                    if session.status == "running":
                        session.status = "stopped"
                        logger.debug(f"Session {session_id} marked as stopped")
                    sync_result[window_name] = "missing"

        logger.info(f"Sync complete: {len(sync_result)} sessions checked")
        return sync_result

    def kill_session(self) -> bool:
        """Kill the entire commander session.

        Returns:
            True if session was killed, False if it didn't exist

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> orchestrator.kill_session()
            True
            >>> orchestrator.kill_session()  # Already killed
            False
        """
        if not self.session_exists():
            logger.info(f"Session '{self.session_name}' does not exist")
            return False

        logger.info(f"Killing session '{self.session_name}'")
        self._run_tmux(["kill-session", "-t", self.session_name])

        return True
