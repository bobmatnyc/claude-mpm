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
