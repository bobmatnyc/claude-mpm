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
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestEventEmission:
    """Test event emission through SocketIO and EventBus."""

    def test_emit_socketio_event_with_pool(self):
        """Test event emission with connection pool."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

        handler = ClaudeHookHandler()
        mock_pool = MagicMock()
        mock_pool.emit.side_effect = Exception("Emit failed")
        handler.connection_pool = mock_pool

        # Should not raise exception
        handler._emit_socketio_event("/hook", "test_event", {})

    def test_emit_socketio_event_no_connections(self):
        """Test emission when no connections available."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
        from src.claude_mpm.hooks.claude_hooks.hook_handler import \
            ClaudeHookHandler

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
