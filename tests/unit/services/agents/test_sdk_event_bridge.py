"""Unit tests for SDKEventBridge.

Tests event registration, emission, handler methods, and error resilience.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.agents.agent_runtime import AgentResult
from claude_mpm.services.agents.sdk_event_bridge import (
    AgentEvent,
    SDKEventBridge,
    attach_bridge_to_emitter,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bridge() -> SDKEventBridge:
    """Create a fresh SDKEventBridge for testing."""
    return SDKEventBridge(agent_id="test-agent-1")


@pytest.fixture
def listener() -> MagicMock:
    """Create a mock listener."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Event registration and emission
# ---------------------------------------------------------------------------


class TestEventRegistration:
    """Test listener registration and event dispatch."""

    def test_on_event_registers_listener(self, bridge: SDKEventBridge) -> None:
        listener = MagicMock()
        bridge.on_event(listener)
        assert len(bridge._listeners) == 1

    def test_multiple_listeners(self, bridge: SDKEventBridge) -> None:
        listeners = [MagicMock() for _ in range(3)]
        for l in listeners:
            bridge.on_event(l)
        assert len(bridge._listeners) == 3

    def test_emit_notifies_all_listeners(self, bridge: SDKEventBridge) -> None:
        listeners = [MagicMock() for _ in range(3)]
        for l in listeners:
            bridge.on_event(l)

        event = AgentEvent(event_type="text", agent_id="test-agent-1")
        bridge._emit(event)

        for l in listeners:
            l.assert_called_once_with(event)

    def test_emit_records_event(self, bridge: SDKEventBridge) -> None:
        event = AgentEvent(event_type="text", agent_id="test-agent-1")
        bridge._emit(event)
        assert len(bridge.events) == 1
        assert bridge.events[0] is event

    def test_events_returns_copy(self, bridge: SDKEventBridge) -> None:
        event = AgentEvent(event_type="text")
        bridge._emit(event)
        events = bridge.events
        events.clear()
        assert len(bridge.events) == 1  # internal list unaffected


# ---------------------------------------------------------------------------
# handle_text
# ---------------------------------------------------------------------------


class TestHandleText:
    """Test the handle_text callback."""

    @pytest.mark.asyncio
    async def test_creates_text_event(
        self, bridge: SDKEventBridge, listener: MagicMock
    ) -> None:
        bridge.on_event(listener)
        await bridge.handle_text("Hello world")

        assert len(bridge.events) == 1
        event = bridge.events[0]
        assert event.event_type == "text"
        assert event.agent_id == "test-agent-1"
        assert event.data == {"text": "Hello world"}
        assert event.timestamp > 0

    @pytest.mark.asyncio
    async def test_multiple_text_events(self, bridge: SDKEventBridge) -> None:
        await bridge.handle_text("one")
        await bridge.handle_text("two")
        assert len(bridge.events) == 2
        assert bridge.events[0].data["text"] == "one"
        assert bridge.events[1].data["text"] == "two"


# ---------------------------------------------------------------------------
# handle_tool_call
# ---------------------------------------------------------------------------


class TestHandleToolCall:
    """Test the handle_tool_call callback."""

    @pytest.mark.asyncio
    async def test_creates_tool_start_event(
        self, bridge: SDKEventBridge, listener: MagicMock
    ) -> None:
        bridge.on_event(listener)
        await bridge.handle_tool_call("Read", {"file_path": "/tmp/test.py"})

        assert len(bridge.events) == 1
        event = bridge.events[0]
        assert event.event_type == "tool_start"
        assert event.agent_id == "test-agent-1"
        assert event.data["tool_name"] == "Read"
        assert event.data["input"] == {"file_path": "/tmp/test.py"}

    @pytest.mark.asyncio
    async def test_empty_input(self, bridge: SDKEventBridge) -> None:
        await bridge.handle_tool_call("Bash", {})

        event = bridge.events[0]
        assert event.data["tool_name"] == "Bash"
        assert event.data["input"] == {}


# ---------------------------------------------------------------------------
# handle_result
# ---------------------------------------------------------------------------


class TestHandleResult:
    """Test the handle_result method."""

    def test_creates_result_event_from_agent_result(
        self, bridge: SDKEventBridge, listener: MagicMock
    ) -> None:
        bridge.on_event(listener)
        result = AgentResult(
            text="The answer is 4.",
            cost_usd=0.005,
            num_turns=1,
            duration_ms=1200,
            tool_calls=[{"tool_name": "Read", "input": {}}],
            is_error=False,
        )
        bridge.handle_result(result)

        assert len(bridge.events) == 1
        event = bridge.events[0]
        assert event.event_type == "result"
        assert event.data["text"] == "The answer is 4."
        assert event.data["cost_usd"] == 0.005
        assert event.data["num_turns"] == 1
        assert event.data["duration_ms"] == 1200
        assert event.data["tool_count"] == 1
        assert event.data["is_error"] is False

    def test_creates_error_event_when_is_error(self, bridge: SDKEventBridge) -> None:
        result = AgentResult(
            text="Something went wrong",
            is_error=True,
        )
        bridge.handle_result(result)

        event = bridge.events[0]
        assert event.event_type == "error"
        assert event.data["is_error"] is True

    def test_truncates_long_text(self, bridge: SDKEventBridge) -> None:
        long_text = "x" * 500
        result = AgentResult(text=long_text)
        bridge.handle_result(result)

        event = bridge.events[0]
        assert len(event.data["text"]) == 200

    def test_handles_non_agent_result(self, bridge: SDKEventBridge) -> None:
        """Passing a non-AgentResult should still produce an event."""
        bridge.handle_result({"some": "dict"})

        assert len(bridge.events) == 1
        event = bridge.events[0]
        assert event.event_type == "result"
        assert event.data == {}


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


class TestSummary:
    """Test the summary() method."""

    @pytest.mark.asyncio
    async def test_summary_counts(self, bridge: SDKEventBridge) -> None:
        await bridge.handle_text("hello")
        await bridge.handle_text("world")
        await bridge.handle_tool_call("Read", {"path": "/tmp"})
        bridge.handle_result(AgentResult(text="done"))

        summary = bridge.summary()
        assert summary["agent_id"] == "test-agent-1"
        assert summary["total_events"] == 4
        assert summary["event_counts"] == {
            "text": 2,
            "tool_start": 1,
            "result": 1,
        }

    def test_empty_summary(self, bridge: SDKEventBridge) -> None:
        summary = bridge.summary()
        assert summary["total_events"] == 0
        assert summary["event_counts"] == {}


# ---------------------------------------------------------------------------
# Listener error resilience
# ---------------------------------------------------------------------------


class TestListenerErrorResilience:
    """Test that listener errors are caught and do not propagate."""

    @pytest.mark.asyncio
    async def test_listener_exception_caught(self, bridge: SDKEventBridge) -> None:
        bad_listener = MagicMock(side_effect=RuntimeError("boom"))
        good_listener = MagicMock()

        bridge.on_event(bad_listener)
        bridge.on_event(good_listener)

        await bridge.handle_text("test")

        # Bad listener was called (and failed)
        bad_listener.assert_called_once()
        # Good listener was still called despite the error
        good_listener.assert_called_once()
        # Event was still recorded
        assert len(bridge.events) == 1


# ---------------------------------------------------------------------------
# Agent ID
# ---------------------------------------------------------------------------


class TestAgentId:
    """Test agent_id propagation."""

    @pytest.mark.asyncio
    async def test_none_agent_id(self) -> None:
        bridge = SDKEventBridge(agent_id=None)
        await bridge.handle_text("hello")
        assert bridge.events[0].agent_id is None

    @pytest.mark.asyncio
    async def test_custom_agent_id(self) -> None:
        bridge = SDKEventBridge(agent_id="custom-42")
        await bridge.handle_text("hello")
        assert bridge.events[0].agent_id == "custom-42"


# ---------------------------------------------------------------------------
# attach_bridge_to_emitter — wiring to the dashboard
# ---------------------------------------------------------------------------


class TestAttachBridgeToEmitter:
    """Verify the bridge -> AsyncEventEmitter -> dashboard wiring.

    These tests prove that registering the forwarding listener actually
    causes events fired on the bridge to be delivered to the emitter
    (which in turn emits to SocketIO). The emitter is mocked.
    """

    @pytest.mark.asyncio
    async def test_listener_forwards_events_to_emitter(self) -> None:
        """A bridge attached via attach_bridge_to_emitter forwards events."""
        fake_emitter = MagicMock()
        fake_emitter.emit_event = AsyncMock(return_value=True)

        async def _fake_get_emitter() -> Any:
            return fake_emitter

        with patch(
            "claude_mpm.services.monitor.event_emitter.get_event_emitter",
            new=_fake_get_emitter,
        ):
            bridge = SDKEventBridge(agent_id="pm-1")
            attached = attach_bridge_to_emitter(bridge)
            assert attached is True

            # Fire an event on the bridge and let the scheduled task run.
            await bridge.handle_text("hello dashboard")
            # Yield control so the create_task in _forward gets to run.
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        # Emitter should have received the forwarded event.
        assert fake_emitter.emit_event.await_count >= 1
        call = fake_emitter.emit_event.await_args
        assert call.kwargs["event"] == "text"
        assert call.kwargs["data"]["agent_id"] == "pm-1"
        assert call.kwargs["data"]["text"] == "hello dashboard"
        assert call.kwargs["data"]["event_type"] == "text"

    @pytest.mark.asyncio
    async def test_emitter_unavailable_is_graceful_noop(self) -> None:
        """If the emitter import fails, attach returns False and bridge still works."""
        # Force the import inside attach_bridge_to_emitter to fail.
        import builtins

        real_import = builtins.__import__

        def _failing_import(name: str, globals=None, locals=None, fromlist=(), level=0):
            if name == "claude_mpm.services.monitor.event_emitter":
                raise ImportError("simulated missing monitor")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=_failing_import):
            bridge = SDKEventBridge(agent_id="pm-1")
            attached = attach_bridge_to_emitter(bridge)

        assert attached is False
        # Bridge must still operate normally without the dashboard.
        await bridge.handle_text("offline")
        assert len(bridge.events) == 1
        assert bridge.events[0].data["text"] == "offline"

    @pytest.mark.asyncio
    async def test_emit_failure_does_not_break_bridge(self) -> None:
        """If the emitter raises, the bridge listener still records the event."""
        fake_emitter = MagicMock()
        fake_emitter.emit_event = AsyncMock(side_effect=RuntimeError("boom"))

        async def _fake_get_emitter() -> Any:
            return fake_emitter

        with patch(
            "claude_mpm.services.monitor.event_emitter.get_event_emitter",
            new=_fake_get_emitter,
        ):
            bridge = SDKEventBridge(agent_id="pm-1")
            attach_bridge_to_emitter(bridge)

            await bridge.handle_text("still works")
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        # Bridge recorded its own event regardless of emitter failure.
        assert len(bridge.events) == 1
        assert bridge.events[0].event_type == "text"
