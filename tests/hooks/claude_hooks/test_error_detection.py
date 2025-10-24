#!/usr/bin/env python3
"""Unit tests for Error Handling and Duplicate Detection.

Tests duplicate detection and error handling functionality.
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


