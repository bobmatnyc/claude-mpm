"""Bridge between SDK agent events and MPM's SocketIO-based monitoring UI.

Translates claude-agent-sdk message types into MPM event emissions
for the monitoring dashboard.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentEvent:
    """A normalized event from an agent execution."""

    event_type: str  # "text", "tool_start", "tool_end", "result", "error"
    agent_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# Type alias for event listener callbacks
EventListener = Callable[[AgentEvent], Any]


class SDKEventBridge:
    """Collects SDK messages and dispatches them as MPM AgentEvents.

    Usage:
        bridge = SDKEventBridge(agent_id="research-1")
        bridge.on_event(my_listener)  # Register listener

        # Use with run_streaming:
        result = await runner.run_streaming(
            prompt="...",
            on_text=bridge.handle_text,
            on_tool_call=bridge.handle_tool_call,
        )
        bridge.handle_result(result)  # Emit final result event
    """

    def __init__(self, agent_id: str | None = None) -> None:
        self.agent_id = agent_id
        self._listeners: list[EventListener] = []
        self._events: list[AgentEvent] = []

    def on_event(self, listener: EventListener) -> None:
        """Register a listener for agent events."""
        self._listeners.append(listener)

    @property
    def events(self) -> list[AgentEvent]:
        """All events captured during this bridge's lifetime."""
        return list(self._events)

    def _emit(self, event: AgentEvent) -> None:
        """Record event and notify all listeners."""
        self._events.append(event)
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                logger.warning("Event listener error", exc_info=True)

    async def handle_text(self, text: str) -> None:
        """Handle a text block from streaming output."""
        self._emit(
            AgentEvent(
                event_type="text",
                agent_id=self.agent_id,
                data={"text": text},
            )
        )

    async def handle_tool_call(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> None:
        """Handle a tool call from streaming output."""
        self._emit(
            AgentEvent(
                event_type="tool_start",
                agent_id=self.agent_id,
                data={"tool_name": tool_name, "input": tool_input},
            )
        )

    def handle_result(self, result: Any) -> None:
        """Handle the final AgentResult."""
        from claude_mpm.services.agents.agent_runtime import AgentResult

        data: dict[str, Any] = {}
        if isinstance(result, AgentResult):
            data = {
                "text": result.text[:200],  # truncate for events
                "cost_usd": result.cost_usd,
                "num_turns": result.num_turns,
                "duration_ms": result.duration_ms,
                "tool_count": len(result.tool_calls),
                "is_error": result.is_error,
            }

        event_type = "error" if data.get("is_error") else "result"
        self._emit(
            AgentEvent(
                event_type=event_type,
                agent_id=self.agent_id,
                data=data,
            )
        )

    def summary(self) -> dict[str, Any]:
        """Return a summary of all events for logging."""
        counts: dict[str, int] = {}
        for event in self._events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return {
            "agent_id": self.agent_id,
            "total_events": len(self._events),
            "event_counts": counts,
        }
