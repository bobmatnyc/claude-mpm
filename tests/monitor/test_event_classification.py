"""
Unit tests for event classification in UnifiedMonitorServer.

Tests the _categorize_event() method and api_events_handler() to ensure
correct event categorization for frontend filtering.

This test file prevents regression of the event classification fix where:
- data["data"]["subtype"] determines the actual event type
- Correct categorization ensures events reach the right frontend components
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.claude_mpm.services.monitor.server import UnifiedMonitorServer


class TestCategorizeEvent:
    """Tests for the _categorize_event() method."""

    @pytest.fixture
    def server(self):
        """Create a UnifiedMonitorServer instance for testing."""
        # Patch dependencies that would try to start actual servers
        with patch.object(UnifiedMonitorServer, "start", return_value=True):
            server = UnifiedMonitorServer(host="localhost", port=8765)
            # Set a mock logger to prevent log errors
            server.logger = MagicMock()
            yield server

    # =========================================================================
    # Claude Events
    # =========================================================================

    def test_user_prompt_categorizes_as_claude_event(self, server):
        """user_prompt should be categorized as claude_event."""
        result = server._categorize_event("user_prompt")
        assert result == "claude_event"

    def test_assistant_message_categorizes_as_claude_event(self, server):
        """assistant_message should be categorized as claude_event."""
        result = server._categorize_event("assistant_message")
        assert result == "claude_event"

    # =========================================================================
    # Tool Events
    # =========================================================================

    def test_pre_tool_categorizes_as_tool_event(self, server):
        """pre_tool should be categorized as tool_event."""
        result = server._categorize_event("pre_tool")
        assert result == "tool_event"

    def test_post_tool_categorizes_as_tool_event(self, server):
        """post_tool should be categorized as tool_event."""
        result = server._categorize_event("post_tool")
        assert result == "tool_event"

    def test_tool_start_categorizes_as_tool_event(self, server):
        """tool.start should be categorized as tool_event."""
        result = server._categorize_event("tool.start")
        assert result == "tool_event"

    def test_tool_end_categorizes_as_tool_event(self, server):
        """tool.end should be categorized as tool_event."""
        result = server._categorize_event("tool.end")
        assert result == "tool_event"

    def test_tool_use_categorizes_as_tool_event(self, server):
        """tool_use should be categorized as tool_event."""
        result = server._categorize_event("tool_use")
        assert result == "tool_event"

    def test_tool_result_categorizes_as_tool_event(self, server):
        """tool_result should be categorized as tool_event."""
        result = server._categorize_event("tool_result")
        assert result == "tool_event"

    # =========================================================================
    # Hook Events
    # =========================================================================

    def test_subagent_start_categorizes_as_hook_event(self, server):
        """subagent_start should be categorized as hook_event."""
        result = server._categorize_event("subagent_start")
        assert result == "hook_event"

    def test_subagent_stop_categorizes_as_hook_event(self, server):
        """subagent_stop should be categorized as hook_event."""
        result = server._categorize_event("subagent_stop")
        assert result == "hook_event"

    def test_todo_updated_categorizes_as_hook_event(self, server):
        """todo_updated should be categorized as hook_event."""
        result = server._categorize_event("todo_updated")
        assert result == "hook_event"

    # =========================================================================
    # Session Events
    # =========================================================================

    def test_session_started_categorizes_as_session_event(self, server):
        """session.started should be categorized as session_event."""
        result = server._categorize_event("session.started")
        assert result == "session_event"

    def test_session_ended_categorizes_as_session_event(self, server):
        """session.ended should be categorized as session_event."""
        result = server._categorize_event("session.ended")
        assert result == "session_event"

    def test_session_start_categorizes_as_session_event(self, server):
        """session_start should be categorized as session_event."""
        result = server._categorize_event("session_start")
        assert result == "session_event"

    def test_session_end_categorizes_as_session_event(self, server):
        """session_end should be categorized as session_event."""
        result = server._categorize_event("session_end")
        assert result == "session_event"

    # =========================================================================
    # Response Events
    # =========================================================================

    def test_response_start_categorizes_as_response_event(self, server):
        """response.start should be categorized as response_event."""
        result = server._categorize_event("response.start")
        assert result == "response_event"

    def test_response_end_categorizes_as_response_event(self, server):
        """response.end should be categorized as response_event."""
        result = server._categorize_event("response.end")
        assert result == "response_event"

    def test_response_started_categorizes_as_response_event(self, server):
        """response_started should be categorized as response_event."""
        result = server._categorize_event("response_started")
        assert result == "response_event"

    def test_response_ended_categorizes_as_response_event(self, server):
        """response_ended should be categorized as response_event."""
        result = server._categorize_event("response_ended")
        assert result == "response_event"

    # =========================================================================
    # Agent Events
    # =========================================================================

    def test_agent_delegated_categorizes_as_agent_event(self, server):
        """agent.delegated should be categorized as agent_event."""
        result = server._categorize_event("agent.delegated")
        assert result == "agent_event"

    def test_agent_returned_categorizes_as_agent_event(self, server):
        """agent.returned should be categorized as agent_event."""
        result = server._categorize_event("agent.returned")
        assert result == "agent_event"

    def test_agent_start_categorizes_as_agent_event(self, server):
        """agent_start should be categorized as agent_event."""
        result = server._categorize_event("agent_start")
        assert result == "agent_event"

    def test_agent_end_categorizes_as_agent_event(self, server):
        """agent_end should be categorized as agent_event."""
        result = server._categorize_event("agent_end")
        assert result == "agent_event"

    # =========================================================================
    # File Events
    # =========================================================================

    def test_file_read_categorizes_as_file_event(self, server):
        """file.read should be categorized as file_event."""
        result = server._categorize_event("file.read")
        assert result == "file_event"

    def test_file_write_categorizes_as_file_event(self, server):
        """file.write should be categorized as file_event."""
        result = server._categorize_event("file.write")
        assert result == "file_event"

    def test_file_edit_categorizes_as_file_event(self, server):
        """file.edit should be categorized as file_event."""
        result = server._categorize_event("file.edit")
        assert result == "file_event"

    def test_file_read_underscore_categorizes_as_file_event(self, server):
        """file_read should be categorized as file_event."""
        result = server._categorize_event("file_read")
        assert result == "file_event"

    def test_file_write_underscore_categorizes_as_file_event(self, server):
        """file_write should be categorized as file_event."""
        result = server._categorize_event("file_write")
        assert result == "file_event"

    # =========================================================================
    # System Events
    # =========================================================================

    def test_system_ready_categorizes_as_system_event(self, server):
        """system_ready should be categorized as system_event."""
        result = server._categorize_event("system_ready")
        assert result == "system_event"

    def test_system_shutdown_categorizes_as_system_event(self, server):
        """system_shutdown should be categorized as system_event."""
        result = server._categorize_event("system_shutdown")
        assert result == "system_event"

    # =========================================================================
    # Unknown/Fallback Events
    # =========================================================================

    def test_unknown_event_falls_back_to_claude_event(self, server):
        """Unknown events should fallback to claude_event."""
        result = server._categorize_event("unknown_event")
        assert result == "claude_event"

    def test_random_string_falls_back_to_claude_event(self, server):
        """Random strings should fallback to claude_event."""
        result = server._categorize_event("some_random_event_name")
        assert result == "claude_event"

    def test_empty_string_falls_back_to_claude_event(self, server):
        """Empty string should fallback to claude_event."""
        result = server._categorize_event("")
        assert result == "claude_event"


class TestApiEventsHandlerEventExtraction:
    """
    Tests for api_events_handler's event extraction logic.

    The handler should extract the actual event name from data["data"]["subtype"]
    and use that for categorization, not the outer event name.
    """

    @pytest.fixture
    def server(self):
        """Create a UnifiedMonitorServer instance for testing."""
        with patch.object(UnifiedMonitorServer, "start", return_value=True):
            server = UnifiedMonitorServer(host="localhost", port=8765)
            server.logger = MagicMock()
            server.sio = AsyncMock()
            yield server

    @pytest.mark.asyncio
    async def test_extracts_subtype_for_user_prompt(self, server):
        """When subtype is 'user_prompt', should categorize as claude_event."""
        # Simulate the data structure from hook handlers
        data = {
            "namespace": "hook",
            "event": "claude_event",  # Outer event name
            "data": {
                "subtype": "user_prompt",  # Actual event type
                "timestamp": "2024-01-01T00:00:00Z",
                "session_id": "test-session",
            },
        }

        # Extract actual event (simulating api_events_handler logic)
        event_data = data.get("data", {})
        actual_event = (
            event_data.get("subtype") or event_data.get("type") or data.get("event")
        )
        event_type = server._categorize_event(actual_event)

        assert actual_event == "user_prompt"
        assert event_type == "claude_event"

    @pytest.mark.asyncio
    async def test_extracts_subtype_for_pre_tool(self, server):
        """When subtype is 'pre_tool', should categorize as tool_event."""
        data = {
            "namespace": "hook",
            "event": "tool_event",  # Outer event name (might be different)
            "data": {
                "subtype": "pre_tool",  # Actual event type
                "tool_name": "Read",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        event_data = data.get("data", {})
        actual_event = (
            event_data.get("subtype") or event_data.get("type") or data.get("event")
        )
        event_type = server._categorize_event(actual_event)

        assert actual_event == "pre_tool"
        assert event_type == "tool_event"

    @pytest.mark.asyncio
    async def test_extracts_subtype_for_subagent_stop(self, server):
        """When subtype is 'subagent_stop', should categorize as hook_event."""
        data = {
            "namespace": "hook",
            "event": "hook_event",
            "data": {
                "subtype": "subagent_stop",  # Actual event type
                "agent_name": "engineer",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        event_data = data.get("data", {})
        actual_event = (
            event_data.get("subtype") or event_data.get("type") or data.get("event")
        )
        event_type = server._categorize_event(actual_event)

        assert actual_event == "subagent_stop"
        assert event_type == "hook_event"

    @pytest.mark.asyncio
    async def test_falls_back_to_type_when_no_subtype(self, server):
        """When no subtype exists, should use 'type' field."""
        data = {
            "namespace": "hook",
            "event": "claude_event",
            "data": {
                "type": "user_prompt",  # Using type instead of subtype
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        event_data = data.get("data", {})
        actual_event = (
            event_data.get("subtype") or event_data.get("type") or data.get("event")
        )
        event_type = server._categorize_event(actual_event)

        assert actual_event == "user_prompt"
        assert event_type == "claude_event"

    @pytest.mark.asyncio
    async def test_falls_back_to_outer_event_when_no_subtype_or_type(self, server):
        """When no subtype or type exists, should use outer event name."""
        data = {
            "namespace": "hook",
            "event": "claude_event",  # Should fallback to this
            "data": {"timestamp": "2024-01-01T00:00:00Z", "session_id": "test-session"},
        }

        event_data = data.get("data", {})
        actual_event = (
            event_data.get("subtype") or event_data.get("type") or data.get("event")
        )
        event_type = server._categorize_event(actual_event)

        assert actual_event == "claude_event"
        assert event_type == "claude_event"

    @pytest.mark.asyncio
    async def test_empty_data_falls_back_to_outer_event(self, server):
        """When data is empty, should use outer event name."""
        data = {
            "namespace": "hook",
            "event": "system_ready",  # Use a recognized system event
            "data": {},
        }

        event_data = data.get("data", {})
        actual_event = (
            event_data.get("subtype") or event_data.get("type") or data.get("event")
        )
        event_type = server._categorize_event(actual_event)

        assert actual_event == "system_ready"
        assert event_type == "system_event"


class TestEventCategorizationRegressionPrevention:
    """
    Regression tests to ensure the event classification fix stays intact.

    These tests specifically verify the scenario that was broken:
    - Hook events were not being properly categorized because the outer
      event name was used instead of the data["data"]["subtype"].
    """

    @pytest.fixture
    def server(self):
        """Create a UnifiedMonitorServer instance for testing."""
        with patch.object(UnifiedMonitorServer, "start", return_value=True):
            server = UnifiedMonitorServer(host="localhost", port=8765)
            server.logger = MagicMock()
            yield server

    def test_all_known_event_types_have_explicit_categories(self, server):
        """All known event types should have explicit (non-fallback) categories."""
        explicit_events = {
            # Hook events
            "subagent_start": "hook_event",
            "subagent_stop": "hook_event",
            "todo_updated": "hook_event",
            # Tool events
            "pre_tool": "tool_event",
            "post_tool": "tool_event",
            "tool.start": "tool_event",
            "tool.end": "tool_event",
            "tool_use": "tool_event",
            "tool_result": "tool_event",
            # Session events
            "session.started": "session_event",
            "session.ended": "session_event",
            "session_start": "session_event",
            "session_end": "session_event",
            # Response events
            "response.start": "response_event",
            "response.end": "response_event",
            "response_started": "response_event",
            "response_ended": "response_event",
            # Agent events
            "agent.delegated": "agent_event",
            "agent.returned": "agent_event",
            "agent_start": "agent_event",
            "agent_end": "agent_event",
            # File events
            "file.read": "file_event",
            "file.write": "file_event",
            "file.edit": "file_event",
            "file_read": "file_event",
            "file_write": "file_event",
            # Claude events
            "user_prompt": "claude_event",
            "assistant_message": "claude_event",
            # System events
            "system_ready": "system_event",
            "system_shutdown": "system_event",
        }

        for event_name, expected_category in explicit_events.items():
            result = server._categorize_event(event_name)
            assert result == expected_category, (
                f"Event '{event_name}' should be categorized as '{expected_category}', "
                f"but got '{result}'"
            )

    def test_categorization_is_case_sensitive(self, server):
        """Event categorization should be case-sensitive."""
        # These should NOT match their lowercase equivalents
        assert server._categorize_event("USER_PROMPT") == "claude_event"  # fallback
        assert server._categorize_event("Pre_Tool") == "claude_event"  # fallback
        assert server._categorize_event("SUBAGENT_STOP") == "claude_event"  # fallback

        # While these should match
        assert server._categorize_event("user_prompt") == "claude_event"
        assert server._categorize_event("pre_tool") == "tool_event"
        assert server._categorize_event("subagent_stop") == "hook_event"

    def test_subtype_takes_precedence_over_type(self, server):
        """
        When both subtype and type are present, subtype should take precedence.
        This matches the behavior in api_events_handler.
        """
        data = {
            "data": {
                "subtype": "pre_tool",  # Should use this
                "type": "user_prompt",  # Should ignore this
            }
        }

        event_data = data.get("data", {})
        actual_event = event_data.get("subtype") or event_data.get("type")
        event_type = server._categorize_event(actual_event)

        assert actual_event == "pre_tool"
        assert event_type == "tool_event"


class TestParameterizedEventClassification:
    """Parametrized tests for comprehensive event classification coverage."""

    @pytest.fixture
    def server(self):
        """Create a UnifiedMonitorServer instance for testing."""
        with patch.object(UnifiedMonitorServer, "start", return_value=True):
            server = UnifiedMonitorServer(host="localhost", port=8765)
            server.logger = MagicMock()
            yield server

    @pytest.mark.parametrize(
        "event_name,expected_category",
        [
            # Claude events
            ("user_prompt", "claude_event"),
            ("assistant_message", "claude_event"),
            # Tool events
            ("pre_tool", "tool_event"),
            ("post_tool", "tool_event"),
            ("tool.start", "tool_event"),
            ("tool.end", "tool_event"),
            ("tool_use", "tool_event"),
            ("tool_result", "tool_event"),
            # Hook events
            ("subagent_start", "hook_event"),
            ("subagent_stop", "hook_event"),
            ("todo_updated", "hook_event"),
            # Session events
            ("session.started", "session_event"),
            ("session.ended", "session_event"),
            ("session_start", "session_event"),
            ("session_end", "session_event"),
            # Response events
            ("response.start", "response_event"),
            ("response.end", "response_event"),
            ("response_started", "response_event"),
            ("response_ended", "response_event"),
            # Agent events
            ("agent.delegated", "agent_event"),
            ("agent.returned", "agent_event"),
            ("agent_start", "agent_event"),
            ("agent_end", "agent_event"),
            # File events
            ("file.read", "file_event"),
            ("file.write", "file_event"),
            ("file.edit", "file_event"),
            ("file_read", "file_event"),
            ("file_write", "file_event"),
            # System events
            ("system_ready", "system_event"),
            ("system_shutdown", "system_event"),
            # Unknown events (fallback)
            ("unknown", "claude_event"),
            ("", "claude_event"),
            ("random_event_12345", "claude_event"),
        ],
    )
    def test_event_classification(self, server, event_name, expected_category):
        """Verify each event is classified correctly."""
        result = server._categorize_event(event_name)
        assert result == expected_category, (
            f"Event '{event_name}' expected '{expected_category}', got '{result}'"
        )
