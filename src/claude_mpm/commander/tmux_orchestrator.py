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
        """Create new pane for a project.

        Creates a new split pane in the commander session with the specified
        working directory.

        Args:
            pane_id: Identifier for this pane (used in logging)
            working_dir: Working directory for the pane

        Returns:
            Tmux target string (pane ID like "%0", "%1", etc.)

        Raises:
            subprocess.CalledProcessError: If pane creation fails

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> target = orchestrator.create_pane("my-project", "/Users/user/projects/my-project")
            >>> print(target)
            %1
        """
        logger.info(f"Creating pane '{pane_id}' in {working_dir}")

        # Split window to create new pane
        self._run_tmux(
            [
                "split-window",
                "-t",
                self.session_name,
                "-c",
                working_dir,  # Working directory
                "-P",  # Print target of new pane
                "-F",
                "#{pane_id}",  # Format: just pane ID
            ]
        )

        # Get the newly created pane's target
        # List panes and get the last one (most recently created)
        result = self._run_tmux(
            [
                "list-panes",
                "-t",
                self.session_name,
                "-F",
                "#{pane_id}",
            ]
        )

        panes = [p for p in result.stdout.strip().split("\n") if p]
        if not panes:
            raise RuntimeError(f"Failed to create pane '{pane_id}'")

        # Get last pane ID (most recently created)
        # Pane ID already includes % prefix and can be used directly as target
        new_pane_id = panes[-1]
        target = new_pane_id  # Use pane ID directly as target

        logger.debug(f"Created pane with target: {target}")
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
        """List all panes with their status.

        Returns:
            List of dicts with pane info (id, path, pid, active)

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> panes = orchestrator.list_panes()
            >>> for pane in panes:
            ...     print(f"{pane['id']}: {pane['path']}")
            %0: /Users/user/projects/proj1
            %1: /Users/user/projects/proj2
        """
        if not self.session_exists():
            logger.warning(f"Session '{self.session_name}' does not exist")
            return []

        logger.debug(f"Listing panes for session '{self.session_name}'")

        result = self._run_tmux(
            [
                "list-panes",
                "-t",
                self.session_name,
                "-F",
                "#{pane_id}|#{pane_current_path}|#{pane_pid}|#{pane_active}",
            ]
        )

        panes = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) >= 4:
                panes.append(
                    {
                        "id": parts[0],
                        "path": parts[1],
                        "pid": parts[2],
                        "active": parts[3] == "1",
                    }
                )

        logger.debug(f"Found {len(panes)} panes")
        return panes

    def kill_pane(self, target: str) -> bool:
        """Kill a specific pane.

        Args:
            target: Tmux target (from create_pane or list_panes)

        Returns:
            True if successful

        Raises:
            subprocess.CalledProcessError: If target pane doesn't exist

        Example:
            >>> orchestrator = TmuxOrchestrator()
            >>> orchestrator.create_session()
            >>> target = orchestrator.create_pane("proj", "/tmp")
            >>> orchestrator.kill_pane(target)
            True
        """
        logger.info(f"Killing pane {target}")

        self._run_tmux(["kill-pane", "-t", target])
        return True

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
