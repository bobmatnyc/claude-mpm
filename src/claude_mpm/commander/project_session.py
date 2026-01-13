"""Project session lifecycle coordinator for MPM Commander.

This module manages per-project execution state, coordinating between
runtime processes, events, and work queue.
"""

import logging
from enum import Enum
from typing import Optional

from .models import Project, ProjectState
from .runtime.executor import RuntimeExecutor
from .runtime.monitor import RuntimeMonitor
from .tmux_orchestrator import TmuxOrchestrator

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Project session execution state.

    Attributes:
        IDLE: No active work, ready to start
        STARTING: Initializing session resources
        RUNNING: Actively executing work
        PAUSED: Execution paused (e.g., waiting for event resolution)
        STOPPING: Shutting down gracefully
        STOPPED: Session terminated
    """

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ProjectSession:
    """Manages lifecycle of a single project's work execution.

    Coordinates between runtime executor, event system, and work queue
    for autonomous task execution within a project.

    Attributes:
        project: Associated project instance
        orchestrator: Tmux orchestrator for process management
        executor: RuntimeExecutor for spawning/managing processes
        monitor: RuntimeMonitor for output monitoring and event detection
        state: Current session execution state
        pause_reason: Reason for pause (e.g., event ID)
        active_pane: Tmux pane target for active runtime, if any

    Example:
        >>> session = ProjectSession(project, tmux_orchestrator, executor, monitor)
        >>> await session.start()
        >>> session.state
        <SessionState.RUNNING: 'running'>
        >>> await session.pause("Event requires user input")
        >>> await session.resume()
        >>> await session.stop()
    """

    def __init__(
        self,
        project: Project,
        orchestrator: TmuxOrchestrator,
        executor: Optional[RuntimeExecutor] = None,
        monitor: Optional[RuntimeMonitor] = None,
    ):
        """Initialize project session.

        Args:
            project: Project instance to manage
            orchestrator: TmuxOrchestrator for process control
            executor: Optional RuntimeExecutor (created if not provided)
            monitor: Optional RuntimeMonitor (not used if not provided)

        Raises:
            ValueError: If project or orchestrator is None
        """
        if project is None:
            raise ValueError("Project cannot be None")
        if orchestrator is None:
            raise ValueError("Orchestrator cannot be None")

        self.project = project
        self.orchestrator = orchestrator
        self.executor = executor or RuntimeExecutor(orchestrator)
        self.monitor = monitor
        self._state = SessionState.IDLE
        self.pause_reason: Optional[str] = None
        self.active_pane: Optional[str] = None

        logger.info(f"Created ProjectSession for project {project.id}")

    @property
    def state(self) -> SessionState:
        """Get current session state.

        Returns:
            Current SessionState
        """
        return self._state

    async def start(self) -> None:
        """Initialize and start project session.

        Transitions from IDLE → STARTING → RUNNING.
        Spawns Claude Code via RuntimeExecutor and starts output monitoring
        via RuntimeMonitor if available.

        Raises:
            RuntimeError: If session not in IDLE state
        """
        if self._state != SessionState.IDLE:
            raise RuntimeError(
                f"Cannot start session in state {self._state}. Must be IDLE."
            )

        logger.info(f"Starting session for project {self.project.id}")
        self._state = SessionState.STARTING

        try:
            # Create tmux session if needed
            if not self.orchestrator.session_exists():
                self.orchestrator.create_session()
                logger.debug("Created tmux session")

            # Spawn Claude Code process
            self.active_pane = await self.executor.spawn(self.project, command="claude")
            logger.info(f"Spawned Claude Code in pane {self.active_pane}")

            # Start monitoring if monitor available
            if self.monitor:
                await self.monitor.start_monitoring(self.active_pane, self.project.id)
                logger.debug(f"Started monitoring pane {self.active_pane}")

            # Update project state
            self.project.state = ProjectState.IDLE
            self.project.state_reason = None

            # Transition to RUNNING
            self._state = SessionState.RUNNING
            logger.info(f"Session started for project {self.project.id}")

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            self._state = SessionState.IDLE
            # Clean up pane if created
            if self.active_pane:
                try:
                    await self.executor.terminate(self.active_pane)
                except Exception as cleanup_error:
                    logger.debug(f"Error cleaning up pane: {cleanup_error}")
                self.active_pane = None
            raise

    async def pause(self, reason: str) -> None:
        """Pause execution (e.g., waiting for event resolution).

        Transitions from RUNNING → PAUSED.
        Execution will not resume until resume() is called.

        Args:
            reason: Reason for pause (typically event ID or description)

        Raises:
            RuntimeError: If session not in RUNNING state
        """
        if self._state != SessionState.RUNNING:
            raise RuntimeError(
                f"Cannot pause session in state {self._state}. Must be RUNNING."
            )

        logger.info(f"Pausing session for project {self.project.id}: {reason}")
        self._state = SessionState.PAUSED
        self.pause_reason = reason

        # Update project state
        self.project.state = ProjectState.BLOCKED
        self.project.state_reason = reason

    async def resume(self) -> None:
        """Resume execution after pause.

        Transitions from PAUSED → RUNNING.
        Clears pause reason and continues work execution.

        Raises:
            RuntimeError: If session not in PAUSED state
        """
        if self._state != SessionState.PAUSED:
            raise RuntimeError(
                f"Cannot resume session in state {self._state}. Must be PAUSED."
            )

        logger.info(f"Resuming session for project {self.project.id}")
        self._state = SessionState.RUNNING
        self.pause_reason = None

        # Update project state
        self.project.state = ProjectState.WORKING
        self.project.state_reason = None

    async def stop(self) -> None:
        """Gracefully stop project session.

        Transitions from any state → STOPPING → STOPPED.
        Stops monitoring, terminates runtime, and cleans up resources.
        """
        logger.info(f"Stopping session for project {self.project.id}")
        self._state = SessionState.STOPPING

        try:
            # Stop monitoring if active
            if self.monitor and self.active_pane:
                await self.monitor.stop_monitoring(self.active_pane)
                logger.debug(f"Stopped monitoring pane {self.active_pane}")

            # Terminate active pane
            if self.active_pane:
                await self.executor.terminate(self.active_pane)
                logger.debug(f"Terminated pane {self.active_pane}")
                self.active_pane = None

            # Clean up any remaining sessions (backward compatibility)
            for session_id in list(self.project.sessions.keys()):
                try:
                    session = self.project.sessions[session_id]
                    if session.tmux_target:
                        # Kill tmux pane
                        self.orchestrator.kill_pane(session.tmux_target)
                        logger.debug(f"Killed pane {session.tmux_target}")
                except Exception as e:
                    logger.warning(f"Error killing session {session_id}: {e}")

            # Update project state
            self.project.state = ProjectState.IDLE
            self.project.state_reason = None

            # Transition to STOPPED
            self._state = SessionState.STOPPED
            logger.info(f"Session stopped for project {self.project.id}")

        except Exception as e:
            logger.error(f"Error during session stop: {e}")
            self._state = SessionState.STOPPED
            raise

    def is_ready(self) -> bool:
        """Check if session can start new work.

        Returns:
            True if session is in RUNNING state (not blocked or paused)
        """
        return self._state == SessionState.RUNNING

    def can_accept_work(self) -> bool:
        """Check if session can accept new work items.

        Returns:
            True if session is IDLE or RUNNING with no active work
        """
        return (
            self._state in (SessionState.IDLE, SessionState.RUNNING)
            and self.project.active_work is None
        )
