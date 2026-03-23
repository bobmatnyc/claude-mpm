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
            "config": {
                "poll_interval": self.config.poll_interval,
                "token_limit": self.config.token_limit,
                "warn_thresholds": self.config.warn_thresholds,
                "auto_pause_threshold": self.config.auto_pause_threshold,
                "max_session_duration": self.config.max_session_duration,
                "idle_timeout": self.config.idle_timeout,
            },
        }
