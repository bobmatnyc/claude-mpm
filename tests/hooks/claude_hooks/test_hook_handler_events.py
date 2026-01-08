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


class TestEventReadingAndParsing:
    """Test event reading and JSON parsing functionality."""

    def test_read_hook_event_valid_json(self):
        """Test reading valid JSON from stdin."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        valid_event = {
            "hook_event_name": "Start",
            "session_id": "test-session-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
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


class TestDelegationScanning:
    """Test delegation pattern detection in assistant responses."""

    def test_scan_for_delegation_patterns_detects_patterns(self):
        """Test that delegation patterns are detected and autotodos are created."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        # Create handler and event handlers
        hook_handler = ClaudeHookHandler()
        event_handlers = EventHandlers(hook_handler)

        # Mock the event log to capture autotodos
        from unittest.mock import MagicMock

        mock_event_log = MagicMock()

        # Create event with delegation anti-pattern
        event = {
            "response": "Make sure to add .env.local to your .gitignore file. You'll need to run npm install after that.",
            "session_id": "test-session-123",
        }

        # Patch the modules that are imported inside the method
        with patch(
            "claude_mpm.services.event_log.get_event_log",
            return_value=mock_event_log,
        ):
            # Scan for patterns
            event_handlers._scan_for_delegation_patterns(event)

        # Verify autotodos were created
        assert mock_event_log.append_event.call_count == 2  # Two patterns detected
        calls = mock_event_log.append_event.call_args_list

        # Check first autotodo
        assert calls[0][1]["event_type"] == "autotodo.delegation"
        assert "Verify" in calls[0][1]["payload"]["content"]
        assert ".env.local" in calls[0][1]["payload"]["original_text"]

        # Check second autotodo
        assert calls[1][1]["event_type"] == "autotodo.delegation"
        assert "Task" in calls[1][1]["payload"]["content"]
        assert "npm install" in calls[1][1]["payload"]["original_text"]

    def test_scan_for_delegation_patterns_no_patterns(self):
        """Test that no autotodos are created when no patterns are detected."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        hook_handler = ClaudeHookHandler()
        event_handlers = EventHandlers(hook_handler)

        mock_event_log = MagicMock()

        # Create event without delegation patterns
        event = {
            "response": "I've completed the task successfully. The file has been updated.",
            "session_id": "test-session-123",
        }

        with patch(
            "claude_mpm.services.event_log.get_event_log",
            return_value=mock_event_log,
        ):
            event_handlers._scan_for_delegation_patterns(event)

        # Verify no autotodos were created
        mock_event_log.append_event.assert_not_called()

    def test_scan_for_delegation_patterns_empty_response(self):
        """Test handling of empty response."""
        from src.claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        hook_handler = ClaudeHookHandler()
        event_handlers = EventHandlers(hook_handler)

        mock_event_log = MagicMock()

        # Create event with empty response
        event = {"response": "", "session_id": "test-session-123"}

        with patch(
            "claude_mpm.services.event_log.get_event_log",
            return_value=mock_event_log,
        ):
            event_handlers._scan_for_delegation_patterns(event)

        # Verify no autotodos were created
        mock_event_log.append_event.assert_not_called()
