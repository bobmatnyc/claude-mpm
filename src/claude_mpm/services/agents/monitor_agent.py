"""Monitor agent: session watchdog for SDK mode.

Runs as a background thread alongside the PM. Monitors session health
and injects warnings via the hook event bus when thresholds are crossed.

Responsibilities:
- Context pressure warnings at configurable thresholds
- Session duration warnings
- Idle/stuck detection when in processing state
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MonitorConfig:
    """Configuration for the monitor agent."""

    # Context pressure thresholds (percentage of token limit)
    token_limit: int = 200_000  # Default context window size
    warn_thresholds: list[int] = field(default_factory=lambda: [70, 80, 90, 95])

    # Polling interval in seconds
    poll_interval: float = 10.0

    # Session duration warning (seconds)
    max_session_duration: int = 3600  # 1 hour
    duration_warn_at: float = 0.8  # Warn at 80% of max

    # Idle detection: warn if processing > N seconds with no activity
    idle_timeout: int = 300  # 5 minutes

    # Auto-pause threshold (percentage) -- suggest pause at this level
    auto_pause_threshold: int = 95

    # Consecutive tool call detection thresholds
    consecutive_bash_threshold: int = 5  # Warn after 5+ consecutive Bash calls
    consecutive_read_threshold: int = 3  # Warn after 3+ consecutive Read calls


class MonitorAgent:
    """Background watchdog that monitors PM session health.

    Uses SessionStateTracker (read) and HookEventBus (write) to observe
    and communicate with the PM without direct coupling.

    The monitor is created and owned by ``_launch_sdk_mode()`` -- it is
    not a global singleton.
    """

    def __init__(self, config: MonitorConfig | None = None) -> None:
        self.config = config or MonitorConfig()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._warnings_sent: set[str] = set()  # Track which warnings already sent
        self._event_bus: Any = None  # Lazily initialised HookEventBus
        self._bridged_message_ids: set[str] = set()  # Track bridged /mpm-message IDs
        self._task_injector: Any = None  # Lazily initialised TaskInjector

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the monitor in a background daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Monitor agent already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="mpm-monitor-agent",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Monitor agent started (poll_interval=%.1fs)", self.config.poll_interval
        )

    def stop(self) -> None:
        """Stop the monitor gracefully."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Monitor agent stopped")

    @property
    def is_running(self) -> bool:
        """Return whether the monitor thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Main polling loop executed in a background thread."""
        logger.debug("Monitor loop starting")

        while not self._stop_event.is_set():
            try:
                self._check_session_health()
            except Exception:
                logger.exception("Monitor check failed")

            self._stop_event.wait(self.config.poll_interval)

        logger.debug("Monitor loop exiting")

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    def _check_session_health(self) -> None:
        """Run all health checks against current session state."""
        from .session_state_tracker import get_global_tracker

        tracker = get_global_tracker()
        if tracker is None:
            return

        state = tracker.get_session_state()

        # Skip checks if session is stopped or not started
        if state["state"] in ("stopped", "starting"):
            return

        self._check_context_pressure(state)
        self._check_session_duration(state)
        self._check_idle_too_long(state)
        self._check_tool_call_patterns()
        self._check_incoming_messages()

    def _check_context_pressure(self, state: dict[str, Any]) -> None:
        """Check token usage against thresholds."""
        tokens_used = state.get("context_usage", {}).get("tokens_used", 0)
        if tokens_used == 0:
            return

        token_limit = self.config.token_limit
        percentage = (tokens_used / token_limit) * 100

        for threshold in sorted(self.config.warn_thresholds):
            warn_key = f"context_{threshold}"
            if percentage >= threshold and warn_key not in self._warnings_sent:
                self._warnings_sent.add(warn_key)

                if threshold >= self.config.auto_pause_threshold:
                    self._inject_message(
                        f"CRITICAL: Context usage at {percentage:.0f}% "
                        f"({tokens_used:,}/{token_limit:,} tokens). "
                        "You should wrap up the current task and save session "
                        "state immediately. "
                        "Use /mpm-session-pause to save progress.",
                        priority="critical",
                    )
                else:
                    self._inject_message(
                        f"Context usage at {percentage:.0f}% "
                        f"({tokens_used:,}/{token_limit:,} tokens). "
                        f"{'Consider wrapping up soon.' if threshold >= 80 else 'Monitoring.'}",
                        priority="high" if threshold >= 80 else "normal",
                    )

    def _check_session_duration(self, state: dict[str, Any]) -> None:
        """Warn if session is running too long."""
        uptime = state.get("uptime_seconds", 0)
        warn_at = self.config.max_session_duration * self.config.duration_warn_at

        warn_key = "duration_warning"
        if uptime >= warn_at and warn_key not in self._warnings_sent:
            self._warnings_sent.add(warn_key)
            minutes = int(uptime / 60)
            max_minutes = int(self.config.max_session_duration / 60)
            self._inject_message(
                f"Session running for {minutes} minutes "
                f"(limit: {max_minutes} min). Consider saving progress.",
                priority="normal",
            )

    def _check_idle_too_long(self, state: dict[str, Any]) -> None:
        """Detect if session appears stuck while processing."""
        if state["state"] != "processing":
            return

        last_activity = state.get("last_activity", 0)
        if last_activity == 0:
            return

        idle_seconds = time.time() - last_activity

        warn_key = "idle_warning"
        if (
            idle_seconds > self.config.idle_timeout
            and warn_key not in self._warnings_sent
        ):
            self._warnings_sent.add(warn_key)
            self._inject_message(
                f"Session appears stuck -- no activity for {int(idle_seconds)}s "
                "while in 'processing' state.",
                priority="high",
            )

    def _check_tool_call_patterns(self) -> None:
        """Detect when PM makes too many consecutive direct tool calls.

        Walks recent activity in reverse chronological order, counting
        consecutive Bash or Read calls. Resets when a delegation tool
        (Agent, Task, TaskCreate, TaskUpdate) is encountered, or when
        hitting a non-tool event or a different tool type.
        """
        from .session_state_tracker import get_global_tracker

        tracker = get_global_tracker()
        if tracker is None:
            return

        events = tracker.get_activity(limit=30)

        delegation_tools = {"Agent", "Task", "TaskCreate", "TaskUpdate"}

        consecutive_bash = 0
        consecutive_read = 0

        for event in reversed(events):
            if event.get("type") != "tool_call":
                break

            tool = event.get("tool", "")

            if tool in delegation_tools:
                break

            if tool == "Bash":
                consecutive_bash += 1
                # Different tool type resets the Read counter
                consecutive_read = 0
            elif tool == "Read":
                consecutive_read += 1
                # Different tool type resets the Bash counter
                consecutive_bash = 0
            else:
                # Any other tool resets both counters
                break

        # Check Bash threshold
        warn_key_bash = "consecutive_bash"
        if (
            consecutive_bash >= self.config.consecutive_bash_threshold
            and warn_key_bash not in self._warnings_sent
        ):
            self._warnings_sent.add(warn_key_bash)
            self._inject_message(
                f"PM has made {consecutive_bash} consecutive Bash calls "
                "without delegating. Consider using Agent/Task tools to "
                "delegate this work to specialist agents.",
                priority="high",
            )

        # Check Read threshold
        warn_key_read = "consecutive_read"
        if (
            consecutive_read >= self.config.consecutive_read_threshold
            and warn_key_read not in self._warnings_sent
        ):
            self._warnings_sent.add(warn_key_read)
            self._inject_message(
                f"PM has made {consecutive_read} consecutive Read calls "
                "(deep investigation pattern). Consider delegating to a "
                "Research agent via Task tool.",
                priority="normal",
            )

    # ------------------------------------------------------------------
    # Incoming message bridge (/mpm-message -> hook injection)
    # ------------------------------------------------------------------

    def _check_incoming_messages(self) -> None:
        """Bridge incoming /mpm-message tasks to SDK session via hook injection."""
        try:
            if self._task_injector is None:
                from claude_mpm.services.communication.task_injector import TaskInjector

                self._task_injector = TaskInjector()
        except ImportError:
            return

        try:
            tasks = self._task_injector.list_message_tasks()
        except Exception:
            logger.debug("Failed to list message tasks", exc_info=True)
            return

        for task in tasks:
            task_id = task.get("id", "")
            if task_id in self._bridged_message_ids:
                continue

            # Skip already-completed tasks
            status = task.get("status", "").lower()
            if status in ("completed", "done"):
                continue

            self._bridged_message_ids.add(task_id)

            # Extract message info
            title = task.get("title", "Unknown message")
            metadata = task.get("metadata", {})
            from_project = metadata.get("from_project", "unknown")
            priority = metadata.get("priority", "normal")
            message_type = metadata.get("message_type", "notification")

            # Map priority
            if priority == "urgent":
                inject_priority = "critical"
            elif priority == "high":
                inject_priority = "high"
            else:
                inject_priority = "normal"

            # Format injection message
            project_name = (
                from_project.rsplit("/", 1)[-1] if "/" in from_project else from_project
            )
            description = task.get("description", "")

            # Build concise message for PM
            msg = f"Cross-project {message_type} from '{project_name}': {title}"
            if description:
                # Include first 300 chars of description
                msg += f"\n{description[:300]}"

            self._inject_message(msg, priority=inject_priority)

    # ------------------------------------------------------------------
    # Message injection
    # ------------------------------------------------------------------

    def _get_event_bus(self) -> Any:
        """Lazily create and cache a HookEventBus instance."""
        if self._event_bus is None:
            from .hook_event_bus import HookEventBus

            self._event_bus = HookEventBus()
        return self._event_bus

    def _inject_message(self, text: str, priority: str = "normal") -> None:
        """Send a message to the PM via hook event bus."""
        from .hook_event_bus import HookMessage, MessagePriority

        priority_map = {
            "critical": MessagePriority.CRITICAL,
            "high": MessagePriority.HIGH,
            "normal": MessagePriority.NORMAL,
            "low": MessagePriority.LOW,
        }

        bus = self._get_event_bus()
        bus.send(
            HookMessage(
                text=text,
                priority=priority_map.get(priority, MessagePriority.NORMAL),
                source="monitor",
            )
        )
        logger.info("Monitor injected: %s", text[:100])

    # ------------------------------------------------------------------
    # Status / introspection
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Get monitor status for /monitor endpoint."""
        return {
            "running": self.is_running,
            "warnings_sent": sorted(self._warnings_sent),
            "bridged_messages": len(self._bridged_message_ids),
            "config": {
                "poll_interval": self.config.poll_interval,
                "token_limit": self.config.token_limit,
                "warn_thresholds": self.config.warn_thresholds,
                "auto_pause_threshold": self.config.auto_pause_threshold,
                "max_session_duration": self.config.max_session_duration,
                "idle_timeout": self.config.idle_timeout,
            },
        }
