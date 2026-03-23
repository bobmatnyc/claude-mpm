"""Tests for SessionStateTracker observability module."""

import threading
import time

import pytest

from claude_mpm.services.agents.session_state_tracker import (
    ActivityEvent,
    SessionState,
    SessionStateTracker,
    get_global_tracker,
    set_global_tracker,
)


class TestSessionState:
    """Test SessionState enum values."""

    def test_state_values(self) -> None:
        assert SessionState.IDLE.value == "idle"
        assert SessionState.PROCESSING.value == "processing"
        assert SessionState.TOOL_CALL.value == "tool_call"
        assert SessionState.STARTING.value == "starting"
        assert SessionState.STOPPED.value == "stopped"

    def test_state_is_string(self) -> None:
        assert isinstance(SessionState.IDLE, str)
        assert SessionState.IDLE == "idle"


class TestActivityEvent:
    """Test ActivityEvent dataclass."""

    def test_to_dict_minimal(self) -> None:
        event = ActivityEvent(type="user_input", timestamp=1000.0, preview="hello")
        d = event.to_dict()
        assert d == {"type": "user_input", "timestamp": 1000.0, "preview": "hello"}
        assert "tool" not in d
        assert "status" not in d
        assert "metadata" not in d

    def test_to_dict_with_tool(self) -> None:
        event = ActivityEvent(
            type="tool_call",
            timestamp=1000.0,
            tool="Read",
            status="running",
        )
        d = event.to_dict()
        assert d["tool"] == "Read"
        assert d["status"] == "running"

    def test_to_dict_with_metadata(self) -> None:
        event = ActivityEvent(
            type="assistant_response",
            timestamp=1000.0,
            preview="response text",
            metadata={"tokens": 100},
        )
        d = event.to_dict()
        assert d["metadata"] == {"tokens": 100}


class TestSessionStateTracker:
    """Test SessionStateTracker state machine and data collection."""

    def test_initial_state_is_starting(self) -> None:
        tracker = SessionStateTracker()
        state = tracker.get_session_state()
        assert state["state"] == "starting"

    def test_set_state(self) -> None:
        tracker = SessionStateTracker()
        tracker.set_state(SessionState.IDLE)
        assert tracker.get_session_state()["state"] == "idle"

    def test_set_session_id(self) -> None:
        tracker = SessionStateTracker()
        tracker.set_session_id("sess-123")
        assert tracker.get_session_state()["session_id"] == "sess-123"

    def test_set_model(self) -> None:
        tracker = SessionStateTracker()
        tracker.set_model("claude-sonnet-4-20250514")
        assert tracker.get_session_state()["model"] == "claude-sonnet-4-20250514"

    def test_record_user_input_transitions_to_processing(self) -> None:
        tracker = SessionStateTracker()
        tracker.set_state(SessionState.IDLE)
        tracker.record_user_input("hello world")
        state = tracker.get_session_state()
        assert state["state"] == "processing"
        assert state["turn_count"] == 1

    def test_record_user_input_increments_turn_count(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_user_input("first")
        tracker.record_user_input("second")
        tracker.record_user_input("third")
        assert tracker.get_session_state()["turn_count"] == 3

    def test_record_tool_call_transitions_to_tool_call(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_tool_call("Read")
        state = tracker.get_session_state()
        assert state["state"] == "tool_call"
        assert state["current_tool"] == "Read"

    def test_record_tool_result_clears_current_tool(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_tool_call("Read")
        tracker.record_tool_result("Read")
        state = tracker.get_session_state()
        assert state["state"] == "processing"
        assert state["current_tool"] is None

    def test_record_tool_result_marks_event_complete(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_tool_call("Read")
        tracker.record_tool_result("Read")
        events = tracker.get_activity()
        tool_event = next(e for e in events if e["type"] == "tool_call")
        assert tool_event["status"] == "complete"

    def test_record_assistant_message_creates_event(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_assistant_message("Hello there!")
        events = tracker.get_activity()
        assert len(events) == 1
        assert events[0]["type"] == "assistant_response"
        assert events[0]["preview"] == "Hello there!"

    def test_record_assistant_message_with_usage_accumulates_tokens(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_assistant_message(
            "msg1", usage={"input_tokens": 100, "output_tokens": 50}
        )
        tracker.record_assistant_message(
            "msg2", usage={"input_tokens": 200, "output_tokens": 75}
        )
        state = tracker.get_session_state()
        assert state["context_usage"]["tokens_used"] == 425

    def test_record_result_transitions_to_idle(self) -> None:
        tracker = SessionStateTracker()
        tracker.set_state(SessionState.PROCESSING)
        tracker.record_result(
            session_id="sess-abc",
            cost=0.05,
            num_turns=3,
            usage={"input_tokens": 500, "output_tokens": 200},
        )
        state = tracker.get_session_state()
        assert state["state"] == "idle"
        assert state["session_id"] == "sess-abc"
        assert state["total_cost_usd"] == 0.05
        assert state["context_usage"]["tokens_used"] == 700

    def test_record_result_accumulates_cost(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_result(session_id=None, cost=0.10, num_turns=None, usage=None)
        tracker.record_result(session_id=None, cost=0.25, num_turns=None, usage=None)
        assert tracker.get_session_state()["total_cost_usd"] == pytest.approx(0.35)

    def test_record_stopped(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_stopped()
        assert tracker.get_session_state()["state"] == "stopped"

    def test_uptime_seconds_increases(self) -> None:
        tracker = SessionStateTracker()
        state = tracker.get_session_state()
        assert state["uptime_seconds"] >= 0

    def test_last_activity_updates(self) -> None:
        tracker = SessionStateTracker()
        before = time.time()
        tracker.set_state(SessionState.IDLE)
        state = tracker.get_session_state()
        assert state["last_activity"] >= before


class TestActivityRingBuffer:
    """Test the bounded deque behavior for events."""

    def test_activity_returns_events_in_order(self) -> None:
        tracker = SessionStateTracker()
        tracker.record_user_input("first")
        tracker.record_user_input("second")
        events = tracker.get_activity()
        assert len(events) == 2
        assert events[0]["preview"] == "first"
        assert events[1]["preview"] == "second"

    def test_activity_limit_parameter(self) -> None:
        tracker = SessionStateTracker()
        for i in range(10):
            tracker.record_user_input(f"msg-{i}")
        events = tracker.get_activity(limit=3)
        assert len(events) == 3
        # Should return the LAST 3
        assert events[0]["preview"] == "msg-7"
        assert events[2]["preview"] == "msg-9"

    def test_ring_buffer_evicts_oldest(self) -> None:
        tracker = SessionStateTracker(max_events=5)
        for i in range(8):
            tracker.record_user_input(f"msg-{i}")
        events = tracker.get_activity()
        assert len(events) == 5
        # Oldest 3 should be evicted
        assert events[0]["preview"] == "msg-3"
        assert events[4]["preview"] == "msg-7"

    def test_preview_truncated_to_200_chars(self) -> None:
        tracker = SessionStateTracker()
        long_text = "x" * 500
        tracker.record_user_input(long_text)
        events = tracker.get_activity()
        assert len(events[0]["preview"]) == 200


class TestThreadSafety:
    """Test concurrent access from multiple threads."""

    def test_concurrent_writes_and_reads(self) -> None:
        tracker = SessionStateTracker()
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(50):
                    tracker.record_user_input(f"msg-{i}")
                    tracker.record_tool_call(f"tool-{i}")
                    tracker.record_tool_result(f"tool-{i}")
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(100):
                    tracker.get_session_state()
                    tracker.get_activity()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"


class TestGlobalSingleton:
    """Test module-level singleton management."""

    def test_get_global_tracker_initially_none(self) -> None:
        # Reset global state for test isolation
        import claude_mpm.services.agents.session_state_tracker as mod

        original = mod._global_tracker
        try:
            mod._global_tracker = None
            assert get_global_tracker() is None
        finally:
            mod._global_tracker = original

    def test_set_and_get_global_tracker(self) -> None:
        import claude_mpm.services.agents.session_state_tracker as mod

        original = mod._global_tracker
        try:
            tracker = SessionStateTracker()
            set_global_tracker(tracker)
            assert get_global_tracker() is tracker
        finally:
            mod._global_tracker = original


class TestFullLifecycle:
    """Test a realistic session lifecycle."""

    def test_complete_session_flow(self) -> None:
        tracker = SessionStateTracker()
        assert tracker.get_session_state()["state"] == "starting"

        # Session initialized
        tracker.set_state(SessionState.IDLE)
        tracker.set_session_id("sess-001")
        assert tracker.get_session_state()["state"] == "idle"

        # User sends input
        tracker.record_user_input("Fix the bug in auth.py")
        assert tracker.get_session_state()["state"] == "processing"

        # Model set from first response
        tracker.set_model("claude-sonnet-4-20250514")

        # Assistant calls a tool
        tracker.record_tool_call("Read")
        assert tracker.get_session_state()["state"] == "tool_call"
        assert tracker.get_session_state()["current_tool"] == "Read"

        # Tool completes
        tracker.record_tool_result("Read")
        assert tracker.get_session_state()["state"] == "processing"
        assert tracker.get_session_state()["current_tool"] is None

        # Assistant responds
        tracker.record_assistant_message(
            "I found the issue in auth.py",
            usage={"input_tokens": 1000, "output_tokens": 200},
        )

        # Turn completes
        tracker.record_result(
            session_id="sess-001",
            cost=0.02,
            num_turns=1,
            usage={"input_tokens": 500, "output_tokens": 100},
        )
        state = tracker.get_session_state()
        assert state["state"] == "idle"
        assert state["turn_count"] == 1
        assert state["total_cost_usd"] == pytest.approx(0.02)
        assert state["context_usage"]["tokens_used"] == 1800  # 1200 + 600

        # Session ends
        tracker.record_stopped()
        assert tracker.get_session_state()["state"] == "stopped"

        # Verify activity feed (record_result does not create an event)
        events = tracker.get_activity()
        assert len(events) == 3  # user_input, tool_call, assistant_response
        assert events[0]["type"] == "user_input"
        assert events[1]["type"] == "tool_call"
        assert events[1]["status"] == "complete"
        assert events[2]["type"] == "assistant_response"
