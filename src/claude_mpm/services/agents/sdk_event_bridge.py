"""Bridge between SDK agent events and MPM's SocketIO-based monitoring UI.

Translates claude-agent-sdk message types into MPM event emissions
for the monitoring dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Namespace used when forwarding bridge events to the AsyncEventEmitter.
# The dashboard subscribes under this namespace.
_EMITTER_NAMESPACE = "agent"


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


def attach_bridge_to_emitter(bridge: SDKEventBridge) -> bool:
    """Wire a SDKEventBridge to the global AsyncEventEmitter.

    Registers a listener on ``bridge`` that forwards each ``AgentEvent`` to
    the monitor's :class:`AsyncEventEmitter`, which in turn emits to any
    registered SocketIO servers (the monitoring dashboard).

    This is best-effort: if the monitor service / emitter is not available
    (e.g. monitor not started, import errors, no running event loop), the
    function logs at debug level and returns ``False`` instead of raising.
    Callers should not depend on the dashboard being reachable.

    Args:
        bridge: The bridge to attach.  A new listener is appended; existing
            listeners are preserved.

    Returns:
        ``True`` if a forwarding listener was registered, ``False`` if the
        emitter was unavailable.
    """
    try:
        from claude_mpm.services.monitor.event_emitter import get_event_emitter
    except Exception:
        logger.debug(
            "AsyncEventEmitter import failed; dashboard bridge disabled", exc_info=True
        )
        return False

    def _forward(event: AgentEvent) -> None:
        # Build the payload the dashboard expects: include event type, agent id,
        # timestamp, and the event-specific data.
        payload: dict[str, Any] = {
            "event_type": event.event_type,
            "agent_id": event.agent_id,
            "timestamp": event.timestamp,
            **(event.data or {}),
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — schedule a fire-and-forget task on a new loop.
            # In SDK mode this should not happen because the bridge fires from
            # within the SDK's asyncio session, but be defensive.
            try:
                asyncio.run(_emit_once(payload, event.event_type))
            except Exception:
                logger.debug("Dashboard emit (no-loop) failed", exc_info=True)
            return

        # Schedule the emit without blocking the listener.
        loop.create_task(_emit_once(payload, event.event_type))

    async def _emit_once(payload: dict[str, Any], event_name: str) -> None:
        try:
            emitter = await get_event_emitter()
            await emitter.emit_event(
                namespace=_EMITTER_NAMESPACE,
                event=event_name,
                data=payload,
            )
        except Exception:
            # Dashboard is optional; never raise into bridge listeners.
            logger.debug("Dashboard emit failed", exc_info=True)

    bridge.on_event(_forward)
    logger.debug(
        "SDKEventBridge wired to AsyncEventEmitter (agent_id=%s)", bridge.agent_id
    )
    return True
