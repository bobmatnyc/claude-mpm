"""Runtime monitor for continuous output monitoring and event detection.

This module provides RuntimeMonitor which continuously polls tmux pane output
and detects events using OutputParser.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from ..events.manager import EventManager
from ..models.events import Event
from ..parsing.output_parser import OutputParser
from ..tmux_orchestrator import TmuxOrchestrator

logger = logging.getLogger(__name__)


class RuntimeMonitor:
    """Monitors tmux pane output and detects events.

    This class continuously polls tmux pane output, uses OutputParser to detect
    events, and emits them via EventManager. Supports starting/stopping monitoring
    for individual panes and tracking which panes are actively monitored.

    Attributes:
        orchestrator: TmuxOrchestrator for capturing output
        parser: OutputParser for event detection
        event_manager: EventManager for emitting events
        poll_interval: Seconds between polls (default: 2.0)
        capture_lines: Number of lines to capture from tmux (default: 1000)

    Example:
        >>> monitor = RuntimeMonitor(orchestrator, parser, event_manager)
        >>> await monitor.start_monitoring("%5", "proj_123")
        >>> events = await monitor.poll_once("%5")
        >>> await monitor.stop_monitoring("%5")
    """

    def __init__(
        self,
        orchestrator: TmuxOrchestrator,
        parser: OutputParser,
        event_manager: EventManager,
        poll_interval: float = 2.0,
        capture_lines: int = 1000,
    ):
        """Initialize runtime monitor.

        Args:
            orchestrator: TmuxOrchestrator for capturing output
            parser: OutputParser for event detection
            event_manager: EventManager for emitting events
            poll_interval: Seconds between polls (default: 2.0)
            capture_lines: Number of lines to capture (default: 1000)

        Raises:
            ValueError: If any required parameter is None
        """
        if orchestrator is None:
            raise ValueError("Orchestrator cannot be None")
        if parser is None:
            raise ValueError("Parser cannot be None")
        if event_manager is None:
            raise ValueError("EventManager cannot be None")

        self.orchestrator = orchestrator
        self.parser = parser
        self.event_manager = event_manager
        self.poll_interval = poll_interval
        self.capture_lines = capture_lines

        # Track active monitors: pane_target -> (project_id, task, last_output_hash)
        self._monitors: Dict[str, tuple[str, Optional[asyncio.Task], int]] = {}
        self._running = False

        logger.debug(
            "RuntimeMonitor initialized (interval: %.2fs, lines: %d)",
            poll_interval,
            capture_lines,
        )

    async def start_monitoring(self, pane_target: str, project_id: str) -> None:
        """Start monitoring a pane for events.

        Creates a background task that continuously polls the pane output
        and detects events. Only one monitor per pane is allowed.

        Args:
            pane_target: Tmux pane target to monitor (e.g., '%5')
            project_id: Project ID for event attribution

        Raises:
            ValueError: If pane_target or project_id is None/empty
            RuntimeError: If monitoring already active for this pane

        Example:
            >>> await monitor.start_monitoring("%5", "proj_123")
        """
        if not pane_target:
            raise ValueError("Pane target cannot be None or empty")
        if not project_id:
            raise ValueError("Project ID cannot be None or empty")

        if pane_target in self._monitors:
            raise RuntimeError(f"Monitoring already active for pane {pane_target}")

        logger.info(
            "Starting monitoring for pane %s (project: %s)", pane_target, project_id
        )

        # Create background polling task
        task = asyncio.create_task(
            self._monitor_loop(pane_target, project_id), name=f"monitor-{pane_target}"
        )

        # Track monitor with initial output hash of 0
        self._monitors[pane_target] = (project_id, task, 0)

    async def stop_monitoring(self, pane_target: str) -> None:
        """Stop monitoring a pane.

        Cancels the background polling task and removes the monitor.

        Args:
            pane_target: Tmux pane target to stop monitoring

        Raises:
            ValueError: If pane_target is None/empty

        Example:
            >>> await monitor.stop_monitoring("%5")
        """
        if not pane_target:
            raise ValueError("Pane target cannot be None or empty")

        if pane_target not in self._monitors:
            logger.debug("No monitoring active for pane %s", pane_target)
            return

        logger.info("Stopping monitoring for pane %s", pane_target)

        _project_id, task, _ = self._monitors[pane_target]

        # Cancel the monitoring task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Remove from monitors
        del self._monitors[pane_target]
        logger.debug("Stopped monitoring pane %s", pane_target)

    async def poll_once(self, pane_target: str) -> List[Event]:
        """Poll pane output once and return any detected events.

        This is a one-time poll that doesn't require starting a monitor.
        Useful for on-demand event checking.

        Args:
            pane_target: Tmux pane target to poll

        Returns:
            List of Event objects detected in the output

        Raises:
            ValueError: If pane_target is None/empty

        Example:
            >>> events = await monitor.poll_once("%5")
            >>> for event in events:
            ...     print(f"Event: {event.title}")
        """
        if not pane_target:
            raise ValueError("Pane target cannot be None or empty")

        # Determine project_id if this pane is being monitored
        project_id = "unknown"
        session_id = None
        if pane_target in self._monitors:
            project_id, _, _ = self._monitors[pane_target]

        logger.debug("Polling pane %s once", pane_target)

        try:
            # Capture output from tmux
            output = self.orchestrator.capture_output(
                pane_target, lines=self.capture_lines
            )

            # Parse for events - don't create events automatically
            parse_results = self.parser.parse(
                content=output,
                project_id=project_id,
                session_id=session_id,
                create_events=False,
            )

            # Create events manually so we can return them
            events = []
            for result in parse_results:
                event = self.event_manager.create(
                    project_id=project_id,
                    session_id=session_id,
                    event_type=result.event_type,
                    title=result.title,
                    content=result.content,
                    options=result.options,
                    context=result.context,
                )
                events.append(event)

            logger.debug(
                "Poll detected %d events from pane %s", len(events), pane_target
            )
            return events

        except Exception as e:
            logger.warning("Failed to poll pane %s: %s", pane_target, e)
            return []

    @property
    def active_monitors(self) -> Dict[str, str]:
        """Get map of pane_target -> project_id for active monitors.

        Returns:
            Dict mapping pane targets to their project IDs

        Example:
            >>> monitors = monitor.active_monitors
            >>> print(monitors)
            {'%5': 'proj_123', '%6': 'proj_456'}
        """
        return {pane: project_id for pane, (project_id, _, _) in self._monitors.items()}

    async def _monitor_loop(self, pane_target: str, project_id: str) -> None:
        """Background monitoring loop for a single pane.

        Continuously polls the pane output at the configured interval and
        detects events. Uses output hashing to avoid reprocessing identical output.

        Args:
            pane_target: Tmux pane target to monitor
            project_id: Project ID for event attribution
        """
        logger.debug("Monitor loop started for pane %s", pane_target)

        while pane_target in self._monitors:
            try:
                # Capture output from tmux
                output = self.orchestrator.capture_output(
                    pane_target, lines=self.capture_lines
                )

                # Check if output has changed since last poll
                output_hash = hash(output)
                _, task, last_hash = self._monitors.get(
                    pane_target, (project_id, None, 0)
                )

                if output_hash == last_hash:
                    # No change in output, skip parsing
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Update hash
                self._monitors[pane_target] = (project_id, task, output_hash)

                # Parse for events
                parse_results = self.parser.parse(
                    content=output,
                    project_id=project_id,
                    session_id=None,
                    create_events=True,  # Create events via EventManager
                )

                if parse_results:
                    logger.info(
                        "Detected %d events from pane %s",
                        len(parse_results),
                        pane_target,
                    )

            except Exception as e:
                logger.error(
                    "Error in monitor loop for pane %s: %s",
                    pane_target,
                    e,
                    exc_info=True,
                )

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

        logger.debug("Monitor loop stopped for pane %s", pane_target)

    async def stop_all(self) -> None:
        """Stop all active monitors.

        Cancels all background polling tasks and clears the monitor registry.

        Example:
            >>> await monitor.stop_all()
        """
        logger.info("Stopping all %d active monitors", len(self._monitors))

        # Get all pane targets before iteration (avoid dict size change during iteration)
        pane_targets = list(self._monitors.keys())

        for pane_target in pane_targets:
            await self.stop_monitoring(pane_target)

        logger.info("All monitors stopped")
