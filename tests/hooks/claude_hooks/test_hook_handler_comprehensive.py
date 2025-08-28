#!/usr/bin/env python3
"""Comprehensive unit tests for hook_handler.py.

These tests ensure complete coverage before refactoring with rope.
"""

import json
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestEventReadingAndParsing:
    """Test event reading and JSON parsing functionality."""

    def test_read_hook_event_valid_json(self):
        """Test reading valid JSON from stdin."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        valid_event = {
            "hook_event_name": "Start",
            "session_id": "test-session-123",
            "timestamp": datetime.now().isoformat(),
        }

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = json.dumps(valid_event)
            with patch("select.select", return_value=([mock_stdin], [], [])):
                result = handler._read_hook_event()

        assert result == valid_event

    def test_read_hook_event_malformed_json(self):
        """Test handling of malformed JSON."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = "{ invalid json }"
            with patch("select.select", return_value=([mock_stdin], [], [])):
                result = handler._read_hook_event()

        assert result is None

    def test_read_hook_event_timeout(self):
        """Test timeout when no data available."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            # select returns empty list indicating timeout
            with patch("select.select", return_value=([], [], [])):
                result = handler._read_hook_event()

        assert result is None

    def test_read_hook_event_empty_input(self):
        """Test handling of empty input."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = "   \n  "
            with patch("select.select", return_value=([mock_stdin], [], [])):
                result = handler._read_hook_event()

        assert result is None

    def test_read_hook_event_interactive_terminal(self):
        """Test behavior when stdin is a terminal."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = handler._read_hook_event()

        assert result is None
        # Should not try to read from stdin
        mock_stdin.read.assert_not_called()


class TestEventRouting:
    """Test event routing to appropriate handlers."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    def test_route_event_user_prompt(self, mock_event_handlers_class):
        """Test routing UserPromptSubmit events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_handlers = MagicMock()
        mock_event_handlers_class.return_value = mock_handlers

        handler = ClaudeHookHandler()
        handler.event_handlers = mock_handlers

        event = {"hook_event_name": "UserPromptSubmit", "prompt": "test prompt"}
        handler._route_event(event)

        mock_handlers.handle_user_prompt_fast.assert_called_once_with(event)

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    def test_route_event_pre_tool(self, mock_event_handlers_class):
        """Test routing PreToolUse events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_handlers = MagicMock()
        mock_event_handlers_class.return_value = mock_handlers

        handler = ClaudeHookHandler()
        handler.event_handlers = mock_handlers

        event = {"hook_event_name": "PreToolUse", "tool_name": "Task"}
        handler._route_event(event)

        mock_handlers.handle_pre_tool_fast.assert_called_once_with(event)

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    def test_route_event_subagent_stop(self, mock_event_handlers_class):
        """Test routing SubagentStop events."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_handlers = MagicMock()
        mock_event_handlers_class.return_value = mock_handlers

        handler = ClaudeHookHandler()
        handler.event_handlers = mock_handlers

        event = {"hook_event_name": "SubagentStop", "agent_type": "research"}
        handler._route_event(event)

        mock_handlers.handle_subagent_stop_fast.assert_called_once_with(event)

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    def test_route_event_unknown_type(self, mock_event_handlers_class):
        """Test handling of unknown event types."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_handlers = MagicMock()
        mock_event_handlers_class.return_value = mock_handlers

        handler = ClaudeHookHandler()
        handler.event_handlers = mock_handlers

        event = {"hook_event_name": "UnknownEventType"}
        handler._route_event(event)

        # Should not call any handler
        mock_handlers.handle_user_prompt_fast.assert_not_called()
        mock_handlers.handle_pre_tool_fast.assert_not_called()
        mock_handlers.handle_subagent_stop_fast.assert_not_called()

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    def test_route_event_handler_exception(self, mock_event_handlers_class):
        """Test exception handling in event routing."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_handlers = MagicMock()
        mock_handlers.handle_stop_fast.side_effect = Exception("Handler error")
        mock_event_handlers_class.return_value = mock_handlers

        handler = ClaudeHookHandler()
        handler.event_handlers = mock_handlers

        event = {"hook_event_name": "Stop"}

        # Should not raise exception
        handler._route_event(event)
        mock_handlers.handle_stop_fast.assert_called_once_with(event)


class TestConnectionManagement:
    """Test SocketIO and EventBus connection management."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.get_connection_pool")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventBus")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EVENTBUS_AVAILABLE", True)
    def test_connection_pool_initialization(self, mock_eventbus, mock_get_pool):
        """Test SocketIO connection pool initialization."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_pool = MagicMock()
        mock_get_pool.return_value = mock_pool
        mock_bus = MagicMock()
        mock_eventbus.get_instance.return_value = mock_bus

        handler = ClaudeHookHandler()

        assert handler.connection_pool == mock_pool
        assert handler.event_bus == mock_bus
        mock_get_pool.assert_called_once()
        mock_eventbus.get_instance.assert_called_once()

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.get_connection_pool")
    def test_connection_pool_initialization_failure(self, mock_get_pool):
        """Test handling of connection pool initialization failure."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_get_pool.side_effect = Exception("Connection failed")

        handler = ClaudeHookHandler()

        assert handler.connection_pool is None

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventBus")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EVENTBUS_AVAILABLE", True)
    def test_eventbus_initialization_failure(self, mock_eventbus):
        """Test handling of EventBus initialization failure."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_eventbus.get_instance.side_effect = Exception("EventBus failed")

        handler = ClaudeHookHandler()

        assert handler.event_bus is None

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler._global_handler", None)
    @patch(
        "src.claude_mpm.hooks.claude_hooks.hook_handler._handler_lock", threading.Lock()
    )
    def test_singleton_pattern(self):
        """Test global handler singleton pattern."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import (
            main,
        )

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.exit"):
                    main()

        # Check that continue was printed
        output = mock_stdout.getvalue()
        assert '{"action": "continue"}' in output

    def test_cleanup_on_destruction(self):
        """Test cleanup when handler is destroyed."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_pool = MagicMock()
        handler = ClaudeHookHandler()
        handler.connection_pool = mock_pool

        # Trigger __del__
        handler.__del__()

        mock_pool.cleanup.assert_called_once()


class TestStateManagement:
    """Test state tracking and management."""

    def test_track_delegation(self):
        """Test tracking of agent delegations."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        session_id = "test-session-123"
        agent_type = "research"
        request_data = {"prompt": "Research something"}

        handler._track_delegation(session_id, agent_type, request_data)

        assert handler.active_delegations[session_id] == agent_type
        assert session_id in handler.delegation_requests
        assert handler.delegation_requests[session_id]["agent_type"] == agent_type
        assert handler.delegation_requests[session_id]["request"] == request_data

    def test_track_delegation_cleanup_old(self):
        """Test cleanup of old delegations."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Add an old delegation
        old_session = "old-session"
        old_timestamp = datetime.now().timestamp() - 400  # More than 5 minutes old
        handler.active_delegations[old_session] = "engineer"
        handler.delegation_history.append(
            (f"{old_session}:{old_timestamp}", "engineer")
        )

        # Add a new delegation
        new_session = "new-session"
        handler._track_delegation(new_session, "research")

        # Old delegation should be cleaned up
        assert old_session not in handler.active_delegations
        assert new_session in handler.active_delegations

    def test_get_delegation_agent_type_exact_match(self):
        """Test getting agent type with exact session match."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        session_id = "test-session-123"
        handler.active_delegations[session_id] = "qa"

        result = handler._get_delegation_agent_type(session_id)
        assert result == "qa"

    def test_get_delegation_agent_type_from_history(self):
        """Test getting agent type from delegation history."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        session_id = "test-session-456"
        timestamp = datetime.now().timestamp()
        handler.delegation_history.append((f"{session_id}:{timestamp}", "engineer"))

        result = handler._get_delegation_agent_type(session_id)
        assert result == "engineer"

    def test_get_delegation_agent_type_unknown(self):
        """Test getting agent type when session not found."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        result = handler._get_delegation_agent_type("unknown-session")
        assert result == "unknown"

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_git_branch_caching(self, mock_getcwd, mock_chdir, mock_run):
        """Test git branch caching with TTL."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Mock current directory
        mock_getcwd.return_value = "/original/path"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_run.return_value = mock_result

        # First call should execute git command
        branch1 = handler._get_git_branch("/test/path")
        assert branch1 == "main"
        assert mock_run.call_count == 1

        # Second call within TTL should use cache
        branch2 = handler._get_git_branch("/test/path")
        assert branch2 == "main"
        assert mock_run.call_count == 1  # Still 1, not called again

        # Expire the cache
        handler._git_branch_cache_time["/test/path"] = datetime.now().timestamp() - 40

        # Third call should execute git command again
        branch3 = handler._get_git_branch("/test/path")
        assert branch3 == "main"
        assert mock_run.call_count == 2

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries from various stores."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Add entries exceeding max limits
        for i in range(250):
            handler.active_delegations[f"session-{i}"] = f"agent-{i}"
            handler.delegation_requests[f"session-{i}"] = {"data": i}

        for i in range(150):
            handler.pending_prompts[f"prompt-{i}"] = {"prompt": f"test-{i}"}

        # Add old git branch cache entries
        old_time = datetime.now().timestamp() - 400
        handler._git_branch_cache["old-path"] = "old-branch"
        handler._git_branch_cache_time["old-path"] = old_time

        handler._cleanup_old_entries()

        # Check that storage was trimmed to max sizes
        assert len(handler.active_delegations) <= handler.MAX_DELEGATION_TRACKING
        assert len(handler.delegation_requests) <= handler.MAX_DELEGATION_TRACKING
        assert len(handler.pending_prompts) <= handler.MAX_PROMPT_TRACKING

        # Check that old git cache was removed
        assert "old-path" not in handler._git_branch_cache
        assert "old-path" not in handler._git_branch_cache_time


class TestEventEmission:
    """Test event emission through SocketIO and EventBus."""

    def test_emit_socketio_event_with_pool(self):
        """Test event emission with connection pool."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        mock_pool = MagicMock()
        handler.connection_pool = mock_pool

        data = {"test": "data", "sessionId": "test-123"}
        handler._emit_socketio_event("/hook", "test_event", data)

        # Should emit claude_event with normalized data
        mock_pool.emit.assert_called_once()
        call_args = mock_pool.emit.call_args
        assert call_args[0][0] == "claude_event"
        emitted_data = call_args[0][1]
        assert emitted_data["type"] == "hook"
        assert emitted_data["subtype"] == "test_event"

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EVENTBUS_AVAILABLE", True)
    def test_emit_socketio_event_with_eventbus(self):
        """Test event emission with EventBus."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        mock_bus = MagicMock()
        handler.event_bus = mock_bus
        handler.connection_pool = None

        data = {"test": "data"}
        handler._emit_socketio_event("/hook", "test_event", data)

        # Should publish to EventBus
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "hook.test_event"

    def test_emit_socketio_event_dual_emission(self):
        """Test dual emission to both SocketIO and EventBus."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        mock_pool = MagicMock()
        mock_bus = MagicMock()
        handler.connection_pool = mock_pool
        handler.event_bus = mock_bus

        data = {"test": "data"}
        handler._emit_socketio_event("/hook", "test_event", data)

        # Should emit to both
        mock_pool.emit.assert_called_once()
        mock_bus.publish.assert_called_once()

    def test_emit_socketio_event_error_handling(self):
        """Test error handling in event emission."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        mock_pool = MagicMock()
        mock_pool.emit.side_effect = Exception("Emit failed")
        handler.connection_pool = mock_pool

        # Should not raise exception
        handler._emit_socketio_event("/hook", "test_event", {})

    def test_emit_socketio_event_no_connections(self):
        """Test emission when no connections available."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        handler.connection_pool = None
        handler.event_bus = None

        # Should not raise exception
        handler._emit_socketio_event("/hook", "test_event", {})


class TestSubagentStopProcessing:
    """Test complex SubagentStop event processing."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    def test_handle_subagent_stop_with_structured_response(self, mock_rtm_class):
        """Test SubagentStop with structured JSON response."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        # Setup mocks
        mock_rtm = MagicMock()
        mock_rtm.response_tracking_enabled = True
        mock_tracker = MagicMock()
        mock_rtm.response_tracker = mock_tracker
        mock_rtm_class.return_value = mock_rtm

        handler = ClaudeHookHandler()
        handler.response_tracking_manager = mock_rtm

        # Setup delegation request
        session_id = "test-session-123"
        handler.delegation_requests[session_id] = {
            "agent_type": "research",
            "request": {"prompt": "Research AI trends"},
            "timestamp": datetime.now().isoformat(),
        }

        # Create event with structured response
        structured_response = {
            "task_completed": True,
            "results": "Found 5 trends",
            "MEMORIES": [{"category": "Research", "content": "AI trend data"}],
        }
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": session_id,
            "agent_type": "research",
            "reason": "completed",
            "output": f"```json\n{json.dumps(structured_response)}\n```",
            "cwd": "/test/path",
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            with patch.object(handler, "_get_git_branch", return_value="main"):
                handler.handle_subagent_stop(event)

        # Check response tracking was called
        mock_tracker.track_response.assert_called_once()
        call_args = mock_tracker.track_response.call_args
        assert call_args[1]["agent_name"] == "research"
        assert "Research AI trends" in call_args[1]["request"]

        # Check event emission
        mock_emit.assert_called_once()
        emitted_data = mock_emit.call_args[0][2]
        assert (
            emitted_data["structured_response"]["MEMORIES"]
            == structured_response["MEMORIES"]
        )

        # Check delegation request was cleaned up
        assert session_id not in handler.delegation_requests

    def test_handle_subagent_stop_fuzzy_session_matching(self):
        """Test fuzzy session ID matching in SubagentStop."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Setup delegation with partial session ID
        stored_session = "abcdef123456789012345678"
        handler.delegation_requests[stored_session] = {
            "agent_type": "engineer",
            "request": {"prompt": "Fix bug"},
        }

        # Event with partial matching session ID
        event_session = "abcdef12"  # First 8 chars match
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": event_session,
            "reason": "completed",
        }

        # Setup mocks
        handler.response_tracking_manager = MagicMock()
        handler.response_tracking_manager.response_tracking_enabled = True
        mock_tracker = MagicMock()
        mock_tracker.track_response.return_value = Path("/logs/response.json")
        handler.response_tracking_manager.response_tracker = mock_tracker

        with patch.object(handler, "_emit_socketio_event"):
            handler.handle_subagent_stop(event)

        # Check that fuzzy match worked - request data was used and then cleaned up
        # After processing, the original stored_session should be removed
        assert stored_session not in handler.delegation_requests
        # The request was processed and removed, so event_session should also not be present
        assert event_session not in handler.delegation_requests

    def test_handle_subagent_stop_memory_extraction(self):
        """Test memory extraction from JSON response."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        memories = [
            {"category": "Architecture", "content": "Service-oriented design"},
            {"category": "Testing", "content": "85% coverage target"},
        ]

        event = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-123",
            "output": f'```json\n{{"MEMORIES": {json.dumps(memories)}}}\n```',
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            handler.handle_subagent_stop(event)

        emitted_data = mock_emit.call_args[0][2]
        assert "structured_response" in emitted_data
        assert emitted_data["structured_response"]["MEMORIES"] == memories

    def test_handle_subagent_stop_various_output_formats(self):
        """Test handling various output format scenarios."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Test with plain text output
        event1 = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-1",
            "output": "Task completed successfully",
            "reason": "completed",
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            handler.handle_subagent_stop(event1)
            assert mock_emit.called

        # Test with no output
        event2 = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-2",
            "reason": "timeout",
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            handler.handle_subagent_stop(event2)
            assert mock_emit.called

        # Test with malformed JSON in output
        event3 = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-3",
            "output": "```json\n{ invalid json }\n```",
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            handler.handle_subagent_stop(event3)
            assert mock_emit.called
            # Should still emit but without structured_response

    def test_handle_subagent_stop_agent_type_inference(self):
        """Test inference of agent type from various sources."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Test inference from task description
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-123",
            "task": "Research market trends and competitor analysis",
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            handler.handle_subagent_stop(event)

        emitted_data = mock_emit.call_args[0][2]
        assert emitted_data["agent_type"] == "research"

        # Test with engineering task
        event2 = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-456",
            "task": "Refactor code base",
        }

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            handler.handle_subagent_stop(event2)

        emitted_data = mock_emit.call_args[0][2]
        assert emitted_data["agent_type"] == "engineer"


class TestDuplicateDetection:
    """Test duplicate event detection."""

    def test_is_duplicate_event_detection(self):
        """Test detection of duplicate events."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler

        # Reset recent events
        hook_handler._recent_events = deque(maxlen=10)

        handler = hook_handler.ClaudeHookHandler()

        event = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "Task",
        }

        event_key = handler._get_event_key(event)
        current_time = time.time()

        # Add to recent events
        with hook_handler._events_lock:
            hook_handler._recent_events.append((event_key, current_time))

        # Check duplicate within 100ms window
        with hook_handler._events_lock:
            is_dup = False
            for recent_key, recent_time in hook_handler._recent_events:
                if recent_key == event_key and (current_time - recent_time) < 0.1:
                    is_dup = True
                    break

        assert is_dup

        # Check non-duplicate after 100ms
        time.sleep(0.11)
        current_time = time.time()
        with hook_handler._events_lock:
            is_dup = False
            for recent_key, recent_time in hook_handler._recent_events:
                if recent_key == event_key and (current_time - recent_time) < 0.1:
                    is_dup = True
                    break

        assert not is_dup

    def test_get_event_key_generation(self):
        """Test event key generation for duplicate detection."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Test PreToolUse with Task
        event1 = {
            "hook_event_name": "PreToolUse",
            "session_id": "sess-123",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "research",
                "prompt": "Find information about AI",
            },
        }
        key1 = handler._get_event_key(event1)
        assert "PreToolUse:sess-123:Task:research:Find information" in key1

        # Test UserPromptSubmit
        event2 = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "sess-456",
            "prompt": "Help me code",
        }
        key2 = handler._get_event_key(event2)
        assert "UserPromptSubmit:sess-456:Help me code" in key2

        # Test other event types
        event3 = {"hook_event_name": "Stop", "session_id": "sess-789"}
        key3 = handler._get_event_key(event3)
        assert key3 == "Stop:sess-789"

    def test_recent_events_deque_maxlen(self):
        """Test that recent events deque respects max length."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler

        # Reset and test deque
        hook_handler._recent_events = deque(maxlen=10)

        # Add more than maxlen events
        for i in range(15):
            hook_handler._recent_events.append((f"event-{i}", time.time()))

        assert len(hook_handler._recent_events) == 10
        # Oldest events should be removed
        assert hook_handler._recent_events[0][0] == "event-5"
        assert hook_handler._recent_events[-1][0] == "event-14"


class TestErrorHandling:
    """Test error handling and recovery."""

    @patch("sys.stdin")
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_with_timeout(self, mock_stdout, mock_stdin):
        """Test timeout handling with SIGALRM."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Setup stdin to block
        mock_stdin.isatty.return_value = False
        mock_stdin.read.side_effect = lambda: time.sleep(15)  # Longer than timeout

        # Mock signal alarm
        original_alarm = signal.alarm
        alarm_calls = []

        def mock_alarm(seconds):
            alarm_calls.append(seconds)
            return original_alarm(0)  # Cancel any real alarm

        with patch("signal.alarm", side_effect=mock_alarm):
            with patch("signal.signal"):
                handler.handle()

        # Check that alarm was set
        assert 10 in alarm_calls

        # Check that continue was printed
        output = mock_stdout.getvalue()
        assert '{"action": "continue"}' in output

    def test_handle_json_parse_error(self):
        """Test handling of JSON parsing errors."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch.object(handler, "_read_hook_event", return_value=None):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                handler.handle()

        output = mock_stdout.getvalue()
        assert '{"action": "continue"}' in output

    def test_handle_exception_recovery(self):
        """Test recovery from exceptions during event handling."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch.object(
            handler, "_read_hook_event", side_effect=Exception("Read error")
        ), patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            handler.handle()

        output = mock_stdout.getvalue()
        assert '{"action": "continue"}' in output

    @patch("subprocess.run")
    def test_git_branch_subprocess_errors(self, mock_run):
        """Test handling of subprocess errors in git branch detection."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Test timeout
        mock_run.side_effect = subprocess.TimeoutExpired("git", 2.0)
        result = handler._get_git_branch("/test/path")
        assert result == "Unknown"

        # Test command failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.side_effect = None
        mock_run.return_value = mock_result
        result = handler._get_git_branch("/test/path2")
        assert result == "Unknown"

        # Test git not found
        mock_run.side_effect = FileNotFoundError()
        result = handler._get_git_branch("/test/path3")
        assert result == "Unknown"

    def test_connection_failure_handling(self):
        """Test handling of connection failures."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Setup failing connections
        mock_pool = MagicMock()
        mock_pool.emit.side_effect = Exception("Connection refused")
        handler.connection_pool = mock_pool

        mock_bus = MagicMock()
        mock_bus.publish.side_effect = Exception("Bus error")
        handler.event_bus = mock_bus

        # Should not raise exception
        handler._emit_socketio_event("/hook", "test_event", {})

    def test_continue_execution_idempotency(self):
        """Test that continue is only sent once."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            handler._continue_execution()
            handler._continue_execution()  # Call twice

        output = mock_stdout.getvalue()
        # Should only have one continue
        assert output.count('{"action": "continue"}') == 2  # Each call prints


class TestMainEntryPoint:
    """Test main entry point and signal handling."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler._global_handler", None)
    def test_main_creates_singleton(self):
        """Test that main creates singleton handler."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler

        with patch.object(hook_handler.ClaudeHookHandler, "handle") as mock_handle:
            with patch("sys.stdout", new_callable=StringIO):
                with patch("sys.exit") as mock_exit:
                    hook_handler.main()

        assert hook_handler._global_handler is not None
        mock_handle.assert_called_once()
        mock_exit.assert_called_with(0)

    @patch(
        "src.claude_mpm.hooks.claude_hooks.hook_handler._global_handler", MagicMock()
    )
    def test_main_reuses_singleton(self):
        """Test that main reuses existing singleton."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler

        existing_handler = hook_handler._global_handler

        with patch.object(existing_handler, "handle") as mock_handle:
            with patch("sys.stdout", new_callable=StringIO):
                with patch("sys.exit"):
                    hook_handler.main()

        # Should reuse existing handler
        assert hook_handler._global_handler is existing_handler
        mock_handle.assert_called_once()

    def test_main_signal_handlers(self):
        """Test signal handler registration."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler

        signal_calls = []

        def mock_signal(sig, handler):
            signal_calls.append((sig, handler))

        with patch("signal.signal", side_effect=mock_signal):
            with patch.object(hook_handler.ClaudeHookHandler, "handle"):
                with patch("sys.stdout", new_callable=StringIO):
                    with patch("sys.exit"):
                        hook_handler.main()

        # Check that SIGTERM and SIGINT were registered
        registered_signals = [call[0] for call in signal_calls]
        assert signal.SIGTERM in registered_signals
        assert signal.SIGINT in registered_signals

    def test_main_exception_handling(self):
        """Test exception handling in main."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler

        with patch.object(
            hook_handler.ClaudeHookHandler,
            "__init__",
            side_effect=Exception("Init failed"),
        ), patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with patch("sys.exit") as mock_exit:
                hook_handler.main()

        # Should still print continue
        output = mock_stdout.getvalue()
        assert '{"action": "continue"}' in output
        mock_exit.assert_called_with(0)


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_delegation_workflow(self):
        """Test complete delegation tracking workflow."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Step 1: Track delegation
        session_id = "workflow-session-123"
        request_data = {
            "prompt": "Research Python async patterns",
            "description": "Find best practices",
        }

        handler._track_delegation(session_id, "research", request_data)

        # Step 2: Process SubagentStop
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": session_id,
            "reason": "completed",
            "output": '```json\n{"task_completed": true, "results": "Found 3 patterns"}\n```',
            "cwd": "/project",
        }

        # Setup mocks
        handler.response_tracking_manager = MagicMock()
        handler.response_tracking_manager.response_tracking_enabled = True
        mock_tracker = MagicMock()
        mock_tracker.track_response.return_value = Path("/logs/response.json")
        handler.response_tracking_manager.response_tracker = mock_tracker

        with patch.object(handler, "_emit_socketio_event") as mock_emit:
            with patch.object(handler, "_get_git_branch", return_value="feature/async"):
                handler.handle_subagent_stop(event)

        # Verify response was tracked
        mock_tracker.track_response.assert_called_once()
        call_kwargs = mock_tracker.track_response.call_args[1]
        assert call_kwargs["agent_name"] == "research"
        assert "Research Python async patterns" in call_kwargs["request"]
        assert "Found 3 patterns" in call_kwargs["response"]

        # Verify event was emitted
        mock_emit.assert_called_once()
        emitted_data = mock_emit.call_args[0][2]
        assert emitted_data["agent_type"] == "research"
        assert emitted_data["structured_response"]["task_completed"] is True

        # Verify cleanup
        assert session_id not in handler.delegation_requests

    def test_periodic_cleanup_trigger(self):
        """Test that periodic cleanup is triggered."""
        from src.claude_mpm.hooks.claude_hooks import hook_handler
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        # Reset recent events to avoid duplicate detection
        hook_handler._recent_events = deque(maxlen=10)

        handler = ClaudeHookHandler()
        handler.CLEANUP_INTERVAL_EVENTS = 2  # Low threshold for testing
        handler.events_processed = 0  # Reset counter

        # Create different events to avoid duplicate detection
        events = [
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": f"test-cleanup-{i}",
                "prompt": f"test prompt {i}",
            }
            for i in range(3)
        ]

        cleanup_called = False
        original_cleanup = handler._cleanup_old_entries

        def mock_cleanup_tracking():
            nonlocal cleanup_called
            cleanup_called = True
            original_cleanup()

        with patch.object(
            handler, "_cleanup_old_entries", side_effect=mock_cleanup_tracking
        ), patch.object(handler.event_handlers, "handle_user_prompt_fast"):
            with patch("sys.stdout", new_callable=StringIO):
                # Process multiple events
                for _i, event in enumerate(events):
                    with patch.object(handler, "_read_hook_event", return_value=event):
                        handler.handle()

        # Cleanup should have been called at least once
        assert cleanup_called, "Cleanup was not called"


class TestMockValidation:
    """Validate that all dependencies are properly mocked."""

    def test_all_imports_mocked(self):
        """Test that all external imports can be mocked."""
        mock_modules = {
            "socketio": MagicMock(),
            "claude_mpm.core.socketio_pool": MagicMock(),
            "claude_mpm.services.event_bus": MagicMock(),
            "claude_mpm.services.socketio.event_normalizer": MagicMock(),
            "claude_mpm.core.constants": MagicMock(),
        }

        for module_name, mock_module in mock_modules.items():
            with patch.dict("sys.modules", {module_name: mock_module}):
                # Should be able to import without errors
                import importlib

                importlib.reload(
                    sys.modules["src.claude_mpm.hooks.claude_hooks.hook_handler"]
                )

    def test_subprocess_mocking(self):
        """Test subprocess operations are properly mocked."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test-branch\n"
            mock_run.return_value = mock_result

            result = handler._get_git_branch()

        assert result == "test-branch"
        mock_run.assert_called_once()

    def test_signal_mocking(self):
        """Test signal operations are properly mocked."""
        with patch("signal.signal") as mock_signal:
            with patch("signal.alarm") as mock_alarm:
                from src.claude_mpm.hooks.claude_hooks.hook_handler import (
                    ClaudeHookHandler,
                )

                handler = ClaudeHookHandler()

                with patch.object(handler, "_read_hook_event", return_value=None):
                    with patch("sys.stdout", new_callable=StringIO):
                        handler.handle()

        # Verify signal operations were called
        mock_signal.assert_called()
        mock_alarm.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
