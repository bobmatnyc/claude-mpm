"""Runtime executor for spawning and managing Claude Code instances in tmux.

This module provides RuntimeExecutor which spawns Claude Code processes in tmux
panes and manages their lifecycle, including sending messages and terminating.
"""

import logging

from ..models.project import Project
from ..tmux_orchestrator import TmuxOrchestrator

logger = logging.getLogger(__name__)


class RuntimeExecutor:
    """Spawns and manages Claude Code processes in tmux panes.

    This class handles the lifecycle of Claude Code instances running in tmux panes,
    providing capabilities to spawn new instances, send messages, check status,
    and terminate processes.

    Attributes:
        orchestrator: TmuxOrchestrator instance for tmux operations

    Example:
        >>> orchestrator = TmuxOrchestrator()
        >>> executor = RuntimeExecutor(orchestrator)
        >>> pane_target = await executor.spawn(project, "claude")
        >>> await executor.send_message(pane_target, "Implement user authentication")
        >>> if executor.is_running(pane_target):
        ...     await executor.terminate(pane_target)
    """

    def __init__(self, orchestrator: TmuxOrchestrator):
        """Initialize runtime executor.

        Args:
            orchestrator: TmuxOrchestrator for tmux operations

        Raises:
            ValueError: If orchestrator is None
        """
        if orchestrator is None:
            raise ValueError("Orchestrator cannot be None")

        self.orchestrator = orchestrator
        logger.debug("RuntimeExecutor initialized")

    async def spawn(self, project: Project, command: str = "claude") -> str:
        """Spawn Claude Code in a new tmux pane for the project.

        Creates a new tmux pane in the project's working directory and spawns
        the specified command (typically "claude" for Claude Code).

        Args:
            project: Project instance with working directory
            command: Command to run (default: "claude")

        Returns:
            The pane target (e.g., '%5') that can be used for subsequent operations

        Raises:
            RuntimeError: If pane creation fails
            ValueError: If project or project.path is None

        Example:
            >>> project = Project(id="proj1", path="/path/to/project")
            >>> pane_target = await executor.spawn(project)
            >>> print(f"Spawned in pane: {pane_target}")
            Spawned in pane: %5
        """
        if project is None:
            raise ValueError("Project cannot be None")
        if not project.path:
            raise ValueError("Project path cannot be None or empty")

        logger.info(
            "Spawning %s for project %s in %s", command, project.id, project.path
        )

        try:
            # Create tmux session if it doesn't exist
            if not self.orchestrator.session_exists():
                self.orchestrator.create_session()
                logger.debug("Created tmux session")

            # Create pane with project working directory
            pane_target = self.orchestrator.create_pane(project.id, project.path)
            logger.debug("Created pane: %s", pane_target)

            # Send command to pane
            self.orchestrator.send_keys(pane_target, command, enter=True)
            logger.info("Spawned %s in pane %s", command, pane_target)

            return pane_target

        except Exception as e:
            logger.error(
                "Failed to spawn %s for project %s: %s", command, project.id, e
            )
            raise RuntimeError(f"Failed to spawn {command}: {e}") from e

    async def send_message(self, pane_target: str, message: str) -> None:
        """Send a message/command to a running Claude instance.

        Sends the message to the specified tmux pane, followed by Enter.

        Args:
            pane_target: Pane target from spawn()
            message: Message to send to Claude Code

        Raises:
            ValueError: If pane_target or message is None/empty
            RuntimeError: If sending message fails

        Example:
            >>> await executor.send_message("%5", "Fix the authentication bug")
        """
        if not pane_target:
            raise ValueError("Pane target cannot be None or empty")
        if not message:
            raise ValueError("Message cannot be None or empty")

        logger.debug("Sending message to pane %s: %s", pane_target, message[:50])

        try:
            self.orchestrator.send_keys(pane_target, message, enter=True)
            logger.info("Sent message to pane %s", pane_target)

        except Exception as e:
            logger.error("Failed to send message to pane %s: %s", pane_target, e)
            raise RuntimeError(
                f"Failed to send message to pane {pane_target}: {e}"
            ) from e

    async def terminate(self, pane_target: str) -> None:
        """Terminate a Claude Code instance.

        Kills the specified tmux pane, terminating the Claude Code process.

        Args:
            pane_target: Pane target from spawn()

        Raises:
            ValueError: If pane_target is None/empty
            RuntimeError: If termination fails

        Example:
            >>> await executor.terminate("%5")
        """
        if not pane_target:
            raise ValueError("Pane target cannot be None or empty")

        logger.info("Terminating pane %s", pane_target)

        try:
            self.orchestrator.kill_pane(pane_target)
            logger.info("Terminated pane %s", pane_target)

        except Exception as e:
            logger.error("Failed to terminate pane %s: %s", pane_target, e)
            raise RuntimeError(f"Failed to terminate pane {pane_target}: {e}") from e

    def is_running(self, pane_target: str) -> bool:
        """Check if a pane is still active.

        Args:
            pane_target: Pane target from spawn()

        Returns:
            True if pane exists and is running, False otherwise

        Example:
            >>> if executor.is_running("%5"):
            ...     print("Pane is still running")
        """
        if not pane_target:
            return False

        try:
            # List all panes and check if target exists
            panes = self.orchestrator.list_panes()
            pane_ids = [pane["id"] for pane in panes]
            is_active = pane_target in pane_ids

            logger.debug("Pane %s running: %s", pane_target, is_active)
            return is_active

        except Exception as e:
            logger.warning("Error checking if pane %s is running: %s", pane_target, e)
            return False
