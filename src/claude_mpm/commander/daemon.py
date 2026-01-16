"""Commander daemon for autonomous multi-project orchestration.

This module implements the main daemon process that coordinates multiple
projects, manages their lifecycles, and handles graceful shutdown.
"""

import asyncio
import logging
import signal
from typing import Dict, Optional

import uvicorn

from .api.app import (
    app,
)
from .config import DaemonConfig
from .events.manager import EventManager
from .inbox import Inbox
from .persistence import EventStore, StateStore
from .project_session import ProjectSession, SessionState
from .registry import ProjectRegistry
from .tmux_orchestrator import TmuxOrchestrator

logger = logging.getLogger(__name__)


class CommanderDaemon:
    """Main daemon process for MPM Commander.

    Orchestrates multiple projects, manages their sessions, handles events,
    and provides REST API for external control.

    Attributes:
        config: Daemon configuration
        registry: Project registry
        orchestrator: Tmux orchestrator
        event_manager: Event manager
        inbox: Event inbox
        sessions: Active project sessions by project_id
        state_store: StateStore for project/session persistence
        event_store: EventStore for event queue persistence
        running: Whether daemon is currently running

    Example:
        >>> config = DaemonConfig(port=8765)
        >>> daemon = CommanderDaemon(config)
        >>> await daemon.start()
        >>> # Daemon runs until stopped
        >>> await daemon.stop()
    """

    def __init__(self, config: DaemonConfig):
        """Initialize Commander daemon.

        Args:
            config: Daemon configuration

        Raises:
            ValueError: If config is invalid
        """
        if config is None:
            raise ValueError("Config cannot be None")

        self.config = config
        self.registry = ProjectRegistry()
        self.orchestrator = TmuxOrchestrator()
        self.event_manager = EventManager()
        self.inbox = Inbox(self.event_manager, self.registry)
        self.sessions: Dict[str, ProjectSession] = {}
        self._running = False
        self._server_task: Optional[asyncio.Task] = None
        self._main_loop_task: Optional[asyncio.Task] = None

        # Initialize persistence stores
        self.state_store = StateStore(config.state_dir)
        self.event_store = EventStore(config.state_dir)

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper()),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        logger.info(
            f"Initialized CommanderDaemon (host={config.host}, "
            f"port={config.port}, state_dir={config.state_dir})"
        )

    @property
    def is_running(self) -> bool:
        """Check if daemon is running.

        Returns:
            True if daemon main loop is active
        """
        return self._running

    async def start(self) -> None:
        """Start daemon and all subsystems.

        Initializes:
        - Load state from disk (projects, sessions, events)
        - Signal handlers for graceful shutdown
        - REST API server
        - Main daemon loop
        - Tmux session for project management

        Raises:
            RuntimeError: If daemon already running
        """
        if self._running:
            raise RuntimeError("Daemon already running")

        logger.info("Starting Commander daemon...")
        self._running = True

        # Load state from disk
        await self._load_state()

        # Set up signal handlers
        self._setup_signal_handlers()

        # Inject global instances into API app
        global api_registry, api_tmux, api_event_manager, api_inbox
        api_registry = self.registry
        api_tmux = self.orchestrator
        api_event_manager = self.event_manager
        api_inbox = self.inbox

        # Start API server in background
        logger.info(f"Starting API server on {self.config.host}:{self.config.port}")
        config_uvicorn = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level.lower(),
        )
        server = uvicorn.Server(config_uvicorn)
        self._server_task = asyncio.create_task(server.serve())

        # Create tmux session for projects
        if not self.orchestrator.session_exists():
            self.orchestrator.create_session()
            logger.info("Created tmux session for project management")

        # Start main daemon loop
        logger.info("Starting main daemon loop")
        self._main_loop_task = asyncio.create_task(self.run())

        logger.info("Commander daemon started successfully")

    async def stop(self) -> None:
        """Graceful shutdown with cleanup.

        Stops all active sessions, persists state, and shuts down API server.
        """
        if not self._running:
            logger.warning("Daemon not running, nothing to stop")
            return

        logger.info("Stopping Commander daemon...")
        self._running = False

        # Stop all project sessions
        for project_id, session in list(self.sessions.items()):
            try:
                logger.info(f"Stopping session for project {project_id}")
                await session.stop()
            except Exception as e:
                logger.error(f"Error stopping session {project_id}: {e}")

        # Cancel main loop task
        if self._main_loop_task and not self._main_loop_task.done():
            self._main_loop_task.cancel()
            try:
                await self._main_loop_task
            except asyncio.CancelledError:
                pass

        # Persist state to disk
        await self._save_state()

        # Stop API server
        if self._server_task and not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass

        logger.info("Commander daemon stopped")

    async def run(self) -> None:
        """Main daemon loop.

        Continuously polls for:
        - Resolved events to resume paused sessions
        - New work items to execute
        - Project state changes
        - Periodic state persistence

        Runs until _running flag is set to False.
        """
        logger.info("Main daemon loop starting")

        # Track last save time for periodic persistence
        last_save_time = asyncio.get_event_loop().time()

        while self._running:
            try:
                # TODO: Check for resolved events and resume sessions (Phase 2 Sprint 3)
                # TODO: Check each ProjectSession for runnable work (Phase 2 Sprint 2)
                # TODO: Spawn RuntimeExecutors for new work items (Phase 2 Sprint 1)

                # Periodic state persistence
                current_time = asyncio.get_event_loop().time()
                if current_time - last_save_time >= self.config.save_interval:
                    try:
                        await self._save_state()
                        last_save_time = current_time
                    except Exception as e:
                        logger.error(f"Error during periodic save: {e}", exc_info=True)

                # Sleep to prevent tight loop
                await asyncio.sleep(self.config.poll_interval)

            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(self.config.poll_interval)

        logger.info("Main daemon loop stopped")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown.

        Registers handlers for SIGINT and SIGTERM that trigger
        daemon shutdown via asyncio event loop.
        """

        def handle_signal(signum: int, frame) -> None:
            """Handle shutdown signal.

            Args:
                signum: Signal number
                frame: Current stack frame
            """
            sig_name = signal.Signals(signum).name
            logger.info(f"Received {sig_name}, initiating graceful shutdown...")

            # Schedule shutdown in event loop
            if self._running:
                asyncio.create_task(self.stop())

        # Register signal handlers
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        logger.debug("Signal handlers configured (SIGINT, SIGTERM)")

    def get_or_create_session(self, project_id: str) -> ProjectSession:
        """Get existing session or create new one for project.

        Args:
            project_id: Project identifier

        Returns:
            ProjectSession for the project

        Raises:
            ValueError: If project not found in registry
        """
        if project_id in self.sessions:
            return self.sessions[project_id]

        project = self.registry.get(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        session = ProjectSession(project, self.orchestrator)
        self.sessions[project_id] = session

        logger.info(f"Created new session for project {project_id}")
        return session

    async def _load_state(self) -> None:
        """Load state from disk (projects, sessions, events).

        Called on daemon startup to restore previous state.
        Handles missing or corrupt files gracefully.
        """
        logger.info("Loading state from disk...")

        # Load projects
        try:
            projects = await self.state_store.load_projects()
            for project in projects:
                # Re-register projects (bypassing validation for already-registered paths)
                self.registry._projects[project.id] = project
                self.registry._path_index[project.path] = project.id
            logger.info(f"Restored {len(projects)} projects")
        except Exception as e:
            logger.error(f"Failed to load projects: {e}", exc_info=True)

        # Load sessions
        try:
            session_states = await self.state_store.load_sessions()
            for project_id, state_dict in session_states.items():
                # Only restore sessions for projects we have
                if project_id in self.registry._projects:
                    project = self.registry.get(project_id)
                    session = ProjectSession(project, self.orchestrator)

                    # Restore session state (but don't restart runtime - manual resume)
                    try:
                        session._state = SessionState(state_dict.get("state", "idle"))
                        session.active_pane = state_dict.get("pane_target")
                        session.pause_reason = state_dict.get("paused_event_id")
                        self.sessions[project_id] = session
                    except Exception as e:
                        logger.warning(
                            f"Failed to restore session for {project_id}: {e}"
                        )
            logger.info(f"Restored {len(self.sessions)} sessions")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}", exc_info=True)

        # Load events
        try:
            events = await self.event_store.load_events()
            for event in events:
                self.event_manager.add_event(event)
            logger.info(f"Restored {len(events)} events")
        except Exception as e:
            logger.error(f"Failed to load events: {e}", exc_info=True)

        logger.info("State loading complete")

    async def _save_state(self) -> None:
        """Save state to disk (projects, sessions, events).

        Called on daemon shutdown and periodically during runtime.
        Uses atomic writes to prevent corruption.
        """
        logger.debug("Saving state to disk...")

        try:
            # Save projects
            await self.state_store.save_projects(self.registry)

            # Save sessions
            await self.state_store.save_sessions(self.sessions)

            # Save events
            await self.event_store.save_events(self.inbox)

            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Failed to save state: {e}", exc_info=True)


async def main(config: Optional[DaemonConfig] = None) -> None:
    """Main entry point for running the daemon.

    Args:
        config: Optional daemon configuration (uses defaults if None)

    Example:
        >>> import asyncio
        >>> asyncio.run(main())
    """
    if config is None:
        config = DaemonConfig()

    daemon = CommanderDaemon(config)

    try:
        await daemon.start()

        # Keep daemon running until stopped
        while daemon.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Daemon error: {e}", exc_info=True)
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())
