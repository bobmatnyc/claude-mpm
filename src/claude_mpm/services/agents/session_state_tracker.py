"""Thread-safe session state tracking for SDK mode observability.

Updated by _launch_sdk_mode() as it processes messages.
Read by MessageEndpoint HTTP handlers (/session, /activity).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SessionState(str, Enum):
    """PM session states."""

    IDLE = "idle"  # Waiting for user input
    PROCESSING = "processing"  # Agent is thinking/responding
    TOOL_CALL = "tool_call"  # Currently executing a tool
    STARTING = "starting"  # Session initializing
    STOPPED = "stopped"  # Session ended


@dataclass
class ActivityEvent:
    """A single event in the activity feed."""

    type: (
        str  # "user_input", "tool_call", "tool_result", "assistant_response", "result"
    )
    timestamp: float
    preview: str = ""  # First ~200 chars
    tool: str | None = None
    status: str | None = None  # "running", "complete", "error"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON response."""
        d: dict[str, Any] = {
            "type": self.type,
            "timestamp": self.timestamp,
            "preview": self.preview,
        }
        if self.tool:
            d["tool"] = self.tool
        if self.status:
            d["status"] = self.status
        if self.metadata:
            d["metadata"] = self.metadata
        return d


class SessionStateTracker:
    """Thread-safe session state tracker.

    All writes happen from the asyncio REPL thread.
    All reads happen from the HTTP server thread.
    Uses a lock for thread safety.
    """

    def __init__(self, max_events: int = 100) -> None:
        self._lock = threading.Lock()
        self._state = SessionState.STARTING
        self._session_id: str | None = None
        self._model: str | None = None
        self._started_at: float = time.time()
        self._last_activity: float = time.time()
        self._turn_count: int = 0
        self._current_tool: str | None = None
        self._total_cost_usd: float = 0.0
        self._tokens_used: int = 0  # Cumulative input+output tokens
        self._events: deque[ActivityEvent] = deque(maxlen=max_events)

    # -- Write methods (called from REPL thread) --

    def set_state(self, state: SessionState) -> None:
        """Update the current session state."""
        with self._lock:
            self._state = state
            self._last_activity = time.time()

    def set_session_id(self, session_id: str) -> None:
        """Set the SDK session ID."""
        with self._lock:
            self._session_id = session_id

    def set_model(self, model: str) -> None:
        """Set the model name from an AssistantMessage."""
        with self._lock:
            self._model = model

    def record_user_input(self, text: str) -> None:
        """Record that the user submitted input."""
        with self._lock:
            self._state = SessionState.PROCESSING
            self._turn_count += 1
            self._last_activity = time.time()
            self._events.append(
                ActivityEvent(
                    type="user_input",
                    timestamp=time.time(),
                    preview=text[:200],
                )
            )

    def record_tool_call(self, tool_name: str) -> None:
        """Record that a tool call has started."""
        with self._lock:
            self._state = SessionState.TOOL_CALL
            self._current_tool = tool_name
            self._last_activity = time.time()
            self._events.append(
                ActivityEvent(
                    type="tool_call",
                    timestamp=time.time(),
                    tool=tool_name,
                    status="running",
                )
            )

    def record_tool_result(self, tool_name: str) -> None:
        """Record that a tool call has completed."""
        with self._lock:
            self._current_tool = None
            self._state = SessionState.PROCESSING
            self._last_activity = time.time()
            # Update last matching tool_call event status
            for event in reversed(self._events):
                if (
                    event.type == "tool_call"
                    and event.tool == tool_name
                    and event.status == "running"
                ):
                    event.status = "complete"
                    break

    def record_assistant_message(
        self, text: str, usage: dict[str, Any] | None = None
    ) -> None:
        """Record an assistant text response."""
        with self._lock:
            self._last_activity = time.time()
            self._events.append(
                ActivityEvent(
                    type="assistant_response",
                    timestamp=time.time(),
                    preview=text[:200],
                )
            )
            if usage:
                self._tokens_used += usage.get("input_tokens", 0) + usage.get(
                    "output_tokens", 0
                )

    def record_result(
        self,
        session_id: str | None,
        cost: float | None,
        num_turns: int | None,
        usage: dict[str, Any] | None,
    ) -> None:
        """Record a ResultMessage (end of a turn)."""
        with self._lock:
            self._state = SessionState.IDLE
            self._current_tool = None
            self._last_activity = time.time()
            if session_id:
                self._session_id = session_id
            if cost:
                self._total_cost_usd += cost
            if usage:
                self._tokens_used += usage.get("input_tokens", 0) + usage.get(
                    "output_tokens", 0
                )

    def record_stopped(self) -> None:
        """Record that the session has ended."""
        with self._lock:
            self._state = SessionState.STOPPED
            self._last_activity = time.time()

    # -- Read methods (called from HTTP thread) --

    def get_session_state(self) -> dict[str, Any]:
        """Return a snapshot of the current session state."""
        with self._lock:
            return {
                "session_id": self._session_id,
                "state": self._state.value,
                "model": self._model,
                "started_at": self._started_at,
                "turn_count": self._turn_count,
                "last_activity": self._last_activity,
                "current_tool": self._current_tool,
                "total_cost_usd": self._total_cost_usd,
                "uptime_seconds": time.time() - self._started_at,
                "context_usage": {
                    "tokens_used": self._tokens_used,
                },
            }

    def get_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent activity events."""
        with self._lock:
            events = list(self._events)
            return [e.to_dict() for e in events[-limit:]]


# ---------------------------------------------------------------------------
# Module-level singleton for cross-thread access
# ---------------------------------------------------------------------------

_global_tracker: SessionStateTracker | None = None
_global_lock = threading.Lock()


def get_global_tracker() -> SessionStateTracker | None:
    """Get the global session state tracker (if set)."""
    return _global_tracker


def set_global_tracker(tracker: SessionStateTracker) -> None:
    """Set the global session state tracker."""
    global _global_tracker
    with _global_lock:
        _global_tracker = tracker
