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
from .core.block_manager import BlockManager
from .env_loader import load_env
from .events.manager import EventManager
from .inbox import Inbox
from .models.events import EventStatus
from .parsing.output_parser import OutputParser
from .persistence import EventStore, StateStore
from .port_manager import CommanderPortManager
from .project_session import ProjectSession, SessionState
from .registry import ProjectRegistry
from .runtime.monitor import RuntimeMonitor
from .tmux_orchestrator import TmuxOrchestrator
from .work.executor import WorkExecutor
from .work.queue import WorkQueue
from .workflow.event_handler import EventHandler

# Load environment variables at module import
load_env()

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
        work_queues: Work queues by project_id
        work_executors: Work executors by project_id
        block_manager: Block manager for automatic work blocking
        runtime_monitor: Runtime monitor for output monitoring
        event_handler: Event handler for blocking event workflow
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
        self.work_queues: Dict[str, WorkQueue] = {}
        self.work_executors: Dict[str, WorkExecutor] = {}
        self._running = False
        self._server_task: Optional[asyncio.Task] = None
        self._main_loop_task: Optional[asyncio.Task] = None

        # Initialize port manager for PID file management
        self._port_manager = CommanderPortManager(port=config.port, host=config.host)

        # Initialize persistence stores
        self.state_store = StateStore(config.state_dir)
        self.event_store = EventStore(config.state_dir)

        # Initialize BlockManager with work queues and executors
        self.block_manager = BlockManager(
            event_manager=self.event_manager,
            work_queues=self.work_queues,
            work_executors=self.work_executors,
        )

        # Initialize RuntimeMonitor with BlockManager
        parser = OutputParser(self.event_manager)
        self.runtime_monitor = RuntimeMonitor(
            orchestrator=self.orchestrator,
            parser=parser,
            event_manager=self.event_manager,
            poll_interval=config.poll_interval,
            block_manager=self.block_manager,
        )

        # Initialize EventHandler with BlockManager
        self.event_handler = EventHandler(
            inbox=self.inbox,
            session_manager=self.sessions,
            block_manager=self.block_manager,
        )

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

        # Inject daemon instances into API app.state (BEFORE lifespan runs)
        app.state.registry = self.registry
        app.state.tmux = self.orchestrator
        app.state.event_manager = self.event_manager
        app.state.inbox = self.inbox
        app.state.work_queues = self.work_queues
        app.state.daemon_instance = self
        app.state.session_manager = self.sessions
        app.state.event_handler = self.event_handler
        logger.info(f"Injected work_queues dict id: {id(self.work_queues)}")

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

        # Write PID file for daemon tracking
        import os

        self._port_manager.write_pid_file(os.getpid())
        logger.debug(f"Wrote PID file: {self._port_manager.pid_file}")

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

        # Clear BlockManager project mappings
        for project_id in list(self.work_queues.keys()):
            try:
                removed = self.block_manager.clear_project_mappings(project_id)
                logger.debug(
                    f"Cleared {removed} work mappings for project {project_id}"
                )
            except Exception as e:
                logger.error(f"Error clearing mappings for {project_id}: {e}")

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

        # Cleanup PID file
        self._port_manager.cleanup_pid_file()
        logger.debug(f"Cleaned up PID file: {self._port_manager.pid_file}")

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
                logger.info(f"🔄 Main loop iteration (running={self._running})")
                logger.info(
                    f"work_queues dict id: {id(self.work_queues)}, keys: {list(self.work_queues.keys())}"
                )

                # Check for resolved events and resume sessions
                await self._check_and_resume_sessions()

                # Check each ProjectSession for runnable work
                logger.info(
                    f"Checking for pending work across {len(self.work_queues)} queues"
                )
                await self._execute_pending_work()

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

        Note: Signal handlers can only be registered from the main thread.
        If called from a background thread, registration is skipped.
        """
        import threading

        # Signal handlers can only be registered from the main thread
        if threading.current_thread() is not threading.main_thread():
            logger.info("Running in background thread - signal handlers skipped")
            return

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

        # Create work queue for project if not exists
        if project_id not in self.work_queues:
            self.work_queues[project_id] = WorkQueue(project_id)
            logger.debug(f"Created work queue for project {project_id}")

        # Create work executor for project if not exists
        if project_id not in self.work_executors:
            from .runtime.executor import RuntimeExecutor

            runtime_executor = RuntimeExecutor(self.orchestrator)
            self.work_executors[project_id] = WorkExecutor(
                runtime=runtime_executor, queue=self.work_queues[project_id]
            )
            logger.debug(f"Created work executor for project {project_id}")

        session = ProjectSession(
            project=project,
            orchestrator=self.orchestrator,
            monitor=self.runtime_monitor,
        )
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

    async def _check_and_resume_sessions(self) -> None:
        """Check for resolved events and resume paused sessions.

        Iterates through all paused sessions, checks if their blocking events
        have been resolved, and resumes execution if ready.
        """
        for project_id, session in list(self.sessions.items()):
            # Skip non-paused sessions
            if session.state != SessionState.PAUSED:
                continue

            # Check if pause reason (event ID) is resolved
            if not session.pause_reason:
                logger.warning(f"Session {project_id} paused with no reason, resuming")
                await session.resume()
                continue

            # Check if event is resolved
            event = self.event_manager.get(session.pause_reason)
            if event and event.status == EventStatus.RESOLVED:
                logger.info(
                    f"Event {event.id} resolved, resuming session for {project_id}"
                )
                await session.resume()

                # Unblock any work items that were blocked by this event
                if project_id in self.work_executors:
                    executor = self.work_executors[project_id]
                    queue = self.work_queues[project_id]

                    # Find work items blocked by this event
                    blocked_items = [
                        item
                        for item in queue.list()
                        if item.state.value == "blocked"
                        and item.metadata.get("block_reason") == event.id
                    ]

                    for item in blocked_items:
                        await executor.handle_unblock(item.id)
                        logger.info(f"Unblocked work item {item.id}")

    async def _execute_pending_work(self) -> None:
        """Execute pending work for all ready sessions.

        Scans all work queues for pending work. For projects with work but no session,
        auto-creates a session. Then executes the next available work item via WorkExecutor.
        """
        # First pass: Auto-create and start sessions for projects with pending work
        for project_id, queue in list(self.work_queues.items()):
            logger.info(
                f"Checking queue for {project_id}: pending={queue.pending_count}"
            )
            # Skip if no pending work
            if queue.pending_count == 0:
                continue

            # Auto-create session if needed
            if project_id not in self.sessions:
                try:
                    logger.info(
                        f"Auto-creating session for project {project_id} with pending work"
                    )
                    session = self.get_or_create_session(project_id)

                    # Start the session so it's ready for work
                    if session.state.value == "idle":
                        logger.info(f"Auto-starting session for {project_id}")
                        await session.start()
                except Exception as e:
                    logger.error(
                        f"Failed to auto-create/start session for {project_id}: {e}",
                        exc_info=True,
                    )
                    continue

        # Second pass: Execute work for ready sessions
        for project_id, session in list(self.sessions.items()):
            # Skip sessions that aren't ready for work
            if not session.is_ready():
                continue

            # Skip if no work queue exists
            if project_id not in self.work_queues:
                continue

            # Get work executor for project
            executor = self.work_executors.get(project_id)
            if not executor:
                logger.warning(
                    f"No work executor found for project {project_id}, skipping"
                )
                continue

            # Check if there's work available
            queue = self.work_queues[project_id]
            if queue.pending_count == 0:
                continue

            # Try to execute next work item
            try:
                # Pass the session's active pane for execution
                executed = await executor.execute_next(pane_target=session.active_pane)
                if executed:
                    logger.info(f"Started work execution for project {project_id}")
            except Exception as e:
                logger.error(
                    f"Error executing work for project {project_id}: {e}",
                    exc_info=True,
                )


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
