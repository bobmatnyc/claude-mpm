"""Output polling loop for MPM Commander."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Dict, Optional

from ..models.project import ProjectState, ToolSession
from ..registry import ProjectRegistry
from ..tmux_orchestrator import TmuxOrchestrator
from .event_detector import BasicEventDetector
from .output_buffer import OutputBuffer

if TYPE_CHECKING:
    from .event_detector import DetectedEvent

logger = logging.getLogger(__name__)


class OutputPoller:
    """Polls tmux sessions for new output and detects events."""

    def __init__(
        self,
        tmux: TmuxOrchestrator,
        registry: ProjectRegistry,
        poll_interval: float = 0.5,
        capture_lines: int = 1000,
    ):
        """Initialize output poller.

        Args:
            tmux: TmuxOrchestrator instance for capturing output
            registry: ProjectRegistry for state management
            poll_interval: Seconds between polls (default: 0.5)
            capture_lines: Number of lines to capture from tmux (default: 1000)
        """
        self.tmux = tmux
        self.registry = registry
        self.poll_interval = poll_interval
        self.capture_lines = capture_lines
        self.detector = BasicEventDetector()
        self.buffers: Dict[str, OutputBuffer] = {}
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self.on_error: Optional[Callable[[str, DetectedEvent], None]] = None
        self.on_idle: Optional[Callable[[str], None]] = None

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Output poller started (interval: %.2fs)", self.poll_interval)

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Output poller stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop - runs until stopped."""
        while self._running:
            try:
                await self._poll_all_sessions()
            except Exception as e:
                logger.error("Polling error: %s", e, exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def _poll_all_sessions(self) -> None:
        """Poll all active sessions for new output."""
        for project in self.registry.list_all():
            for session_id, session in project.sessions.items():
                if session.status in ("stopped", "error"):
                    continue

                await self._poll_session(project.id, session)

    async def _poll_session(self, project_id: str, session: ToolSession) -> None:
        """Poll a single session for output changes.

        Args:
            project_id: ID of the project owning the session
            session: Session object to poll
        """
        # Skip stopped or errored sessions
        if session.status in ("stopped", "error"):
            return

        # Get or create buffer
        if session.id not in self.buffers:
            self.buffers[session.id] = OutputBuffer(session_id=session.id)

        buffer = self.buffers[session.id]

        # Capture output from tmux
        try:
            output = self.tmux.capture_output(
                session.tmux_target, lines=self.capture_lines
            )
        except Exception as e:
            logger.warning("Failed to capture output for %s: %s", session.id, e)
            return

        # Check for changes
        has_changed, new_content = buffer.update(output)
        if not has_changed:
            return

        # Update session output buffer
        session.output_buffer = output
        session.last_output_at = datetime.now(timezone.utc)

        # Detect events - errors take priority
        error_event = self.detector.detect_error(new_content)
        if error_event:
            logger.warning("Error detected in %s: %s", session.id, error_event.content)
            session.status = "error"
            self.registry.update_state(
                project_id, ProjectState.ERROR, error_event.content
            )
            if self.on_error:
                self.on_error(session.id, error_event)
            return

        # Check for idle state
        is_idle = self.detector.detect_idle(output)
        if is_idle:
            if session.status != "idle":
                logger.debug("Session %s now idle", session.id)
                session.status = "idle"
                if self.on_idle:
                    self.on_idle(session.id)
        elif session.status == "idle":
            logger.debug("Session %s now running", session.id)
            session.status = "running"
            self.registry.update_state(project_id, ProjectState.WORKING)

    def clear_buffer(self, session_id: str) -> None:
        """Clear the buffer for a session.

        Args:
            session_id: ID of session to clear buffer for
        """
        if session_id in self.buffers:
            del self.buffers[session_id]
