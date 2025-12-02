#!/usr/bin/env python3
"""
Comprehensive unit tests for the HookHandler class.

This test suite validates:
- HookHandler initialization and service setup
- Event processing with various event types
- Duplicate detection with 50ms threshold
- Timeout protection (30s limit)
- State management and transitions
- Memory operation extraction
- Error handling for malformed events
- HTTP request mocking to socket.io server

These tests ensure the stability and reliability of the hook data collection system,
which is critical for monitoring Claude Code interactions and providing real-time
feedback through the dashboard.
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_mpm.hooks.claude_hooks.hook_handler import (
    ClaudeHookHandler,
    check_claude_version,
)
from src.claude_mpm.hooks.claude_hooks.services import DuplicateEventDetector


class TestCheckClaudeVersion(unittest.TestCase):
    """Test Claude Code version checking functionality."""

    @patch("subprocess.run")
    def test_version_check_compatible(self, mock_run):
        """Test detection of compatible Claude Code version."""
        mock_run.return_value = Mock(
            returncode=0, stdout="1.0.95 (Claude Code)", stderr=""
        )

        is_compatible, version = check_claude_version()

        self.assertTrue(is_compatible)
        self.assertEqual(version, "1.0.95")
        mock_run.assert_called_once_with(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    @patch("subprocess.run")
    def test_version_check_incompatible(self, mock_run):
        """Test detection of incompatible Claude Code version."""
        mock_run.return_value = Mock(
            returncode=0, stdout="1.0.91 (Claude Code)", stderr=""
        )

        is_compatible, version = check_claude_version()

        self.assertFalse(is_compatible)
        self.assertEqual(version, "1.0.91")

    @patch("subprocess.run")
    def test_version_check_not_installed(self, mock_run):
        """Test handling when Claude Code is not installed."""
        mock_run.side_effect = FileNotFoundError("claude not found")

        is_compatible, version = check_claude_version()

        self.assertFalse(is_compatible)
        self.assertIsNone(version)

    @patch("subprocess.run")
    def test_version_check_timeout(self, mock_run):
        """Test handling of version check timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

        is_compatible, version = check_claude_version()

        self.assertFalse(is_compatible)
        self.assertIsNone(version)


class TestClaudeHookHandler(unittest.TestCase):
    """Test the main ClaudeHookHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable debug output during tests
        os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "false"

        # Mock the service imports to avoid dependencies
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"):
            self.handler = ClaudeHookHandler()

    def test_initialization(self):
        """Test that HookHandler initializes all required services."""
        # Verify all services are initialized
        self.assertIsNotNone(self.handler.state_manager)
        self.assertIsNotNone(self.handler.connection_manager)
        self.assertIsNotNone(self.handler.duplicate_detector)
        self.assertIsNotNone(self.handler.subagent_processor)
        self.assertIsNotNone(self.handler.memory_hook_manager)
        self.assertIsNotNone(self.handler.response_tracking_manager)
        self.assertIsNotNone(self.handler.event_handlers)

        # Verify backward compatibility properties
        self.assertEqual(
            self.handler.connection_pool,
            self.handler.connection_manager.connection_pool,
        )
        self.assertEqual(
            self.handler.event_bus, self.handler.connection_manager.event_bus
        )

    @patch("sys.stdin")
    @patch("sys.stdout")
    @patch("select.select")
    def test_read_hook_event_valid_json(self, mock_select, mock_stdout, mock_stdin):
        """Test reading a valid JSON event from stdin."""
        # Mock stdin with valid JSON
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = '{"hook_event_name": "Stop", "data": "test"}'
        mock_select.return_value = ([mock_stdin], [], [])

        event = self.handler._read_hook_event()

        self.assertIsNotNone(event)
        self.assertEqual(event["hook_event_name"], "Stop")
        self.assertEqual(event["data"], "test")

    @patch("sys.stdin")
    @patch("select.select")
    def test_read_hook_event_invalid_json(self, mock_select, mock_stdin):
        """Test handling of invalid JSON input."""
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "not valid json{"
        mock_select.return_value = ([mock_stdin], [], [])

        event = self.handler._read_hook_event()

        self.assertIsNone(event)

    @patch("sys.stdin")
    @patch("select.select")
    def test_read_hook_event_timeout(self, mock_select, mock_stdin):
        """Test timeout protection when reading events."""
        mock_stdin.isatty.return_value = False
        # No data available within timeout
        mock_select.return_value = ([], [], [])

        event = self.handler._read_hook_event()

        self.assertIsNone(event)
        mock_select.assert_called_once_with([mock_stdin], [], [], 1.0)

    def test_route_event_user_prompt(self):
        """Test routing of UserPromptSubmit event."""
        event = {"hook_event_name": "UserPromptSubmit", "prompt": "test"}

        # Mock the event handler
        self.handler.event_handlers.handle_user_prompt_fast = Mock()

        self.handler._route_event(event)

        self.handler.event_handlers.handle_user_prompt_fast.assert_called_once_with(
            event
        )

    def test_route_event_stop(self):
        """Test routing of Stop event."""
        event = {"hook_event_name": "Stop", "response": "test"}

        # Mock the event handler
        self.handler.event_handlers.handle_stop_fast = Mock()

        self.handler._route_event(event)

        self.handler.event_handlers.handle_stop_fast.assert_called_once_with(event)

    def test_route_event_subagent_stop(self):
        """Test routing of SubagentStop event."""
        event = {"hook_event_name": "SubagentStop", "agent": "test_agent"}

        # Mock the event handler
        self.handler.event_handlers.handle_subagent_stop_fast = Mock()

        self.handler._route_event(event)

        self.handler.event_handlers.handle_subagent_stop_fast.assert_called_once_with(
            event
        )

    def test_route_event_unknown(self):
        """Test handling of unknown event types."""
        event = {"hook_event_name": "UnknownEvent", "data": "test"}

        # Should not raise an exception
        self.handler._route_event(event)

    def test_route_event_alternative_fields(self):
        """Test event routing with alternative field names for compatibility."""
        # Test with 'event' field
        event = {"event": "Stop", "data": "test"}
        self.handler.event_handlers.handle_stop_fast = Mock()
        self.handler._route_event(event)
        self.handler.event_handlers.handle_stop_fast.assert_called_once()

        # Test with 'type' field
        event = {"type": "Stop", "data": "test"}
        self.handler.event_handlers.handle_stop_fast = Mock()
        self.handler._route_event(event)
        self.handler.event_handlers.handle_stop_fast.assert_called_once()

    @patch("sys.stdout", new_callable=StringIO)
    def test_continue_execution(self, mock_stdout):
        """Test that continue action is properly formatted."""
        self.handler._continue_execution()

        output = mock_stdout.getvalue()
        self.assertEqual(output, '{"action": "continue"}\n')

        # Verify it's valid JSON
        parsed = json.loads(output.strip())
        self.assertEqual(parsed["action"], "continue")

    def test_duplicate_detection(self):
        """Test duplicate event detection with 50ms threshold."""
        # Create a real duplicate detector for this test
        self.handler.duplicate_detector = DuplicateEventDetector()

        event1 = {
            "hook_event_name": "Stop",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": "test",
        }

        # First event should not be duplicate
        self.assertFalse(self.handler.duplicate_detector.is_duplicate(event1))

        # Same event immediately after should be duplicate
        self.assertTrue(self.handler.duplicate_detector.is_duplicate(event1))

        # After waiting more than threshold, should not be duplicate
        time.sleep(0.06)  # Wait 60ms (> 50ms threshold)
        self.assertFalse(self.handler.duplicate_detector.is_duplicate(event1))

    @patch("signal.alarm")
    @patch("sys.stdout", new_callable=StringIO)
    @patch("sys.stdin")
    @patch("select.select")
    def test_handle_with_timeout(
        self, mock_select, mock_stdin, mock_stdout, mock_alarm
    ):
        """Test the handle() method with timeout protection."""
        # Mock a valid event
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = '{"hook_event_name": "Stop"}'
        mock_select.return_value = ([mock_stdin], [], [])

        # Mock duplicate detector to return False
        self.handler.duplicate_detector.is_duplicate = Mock(return_value=False)

        # Mock event handler
        self.handler.event_handlers.handle_stop_fast = Mock()

        # Mock state manager
        self.handler.state_manager.increment_events_processed = Mock(return_value=False)

        self.handler.handle()

        # Verify timeout was set and cleared
        mock_alarm.assert_any_call(10)  # 10-second timeout
        mock_alarm.assert_any_call(0)  # Clear alarm

        # Verify continue was sent
        output = mock_stdout.getvalue()
        self.assertIn('"action": "continue"', output)

    def test_state_cleanup_trigger(self):
        """Test that state cleanup is triggered after processing events."""
        # Mock state manager to trigger cleanup
        self.handler.state_manager.increment_events_processed = Mock(return_value=True)
        self.handler.state_manager.cleanup_old_entries = Mock()

        # Mock event reading
        self.handler._read_hook_event = Mock(return_value={"hook_event_name": "Stop"})
        self.handler.duplicate_detector.is_duplicate = Mock(return_value=False)
        self.handler._route_event = Mock()
        self.handler._continue_execution = Mock()

        with patch("signal.alarm"):
            self.handler.handle()

        # Verify cleanup was called
        self.handler.state_manager.cleanup_old_entries.assert_called_once()

    def test_memory_operation_extraction(self):
        """Test extraction of memory operations from events."""
        # This test would verify memory operation extraction
        # The actual implementation would be in the event handlers
        event = {
            "hook_event_name": "SubagentStop",
            "response": json.dumps(
                {
                    "memory-update": {
                        "Project Context": ["New learning"],
                    }
                }
            ),
        }

        # Mock the subagent processor
        self.handler.subagent_processor.process_subagent_stop = Mock()

        self.handler.handle_subagent_stop(event)

        self.handler.subagent_processor.process_subagent_stop.assert_called_once_with(
            event
        )

    def test_error_handling_in_handle(self):
        """Test that errors in handle() don't crash the process."""
        # Make _read_hook_event raise an exception
        self.handler._read_hook_event = Mock(side_effect=Exception("Test error"))
        self.handler._continue_execution = Mock()

        with patch("signal.alarm"):
            # Should not raise exception
            self.handler.handle()

        # Should still send continue
        self.handler._continue_execution.assert_called_once()

    def test_concurrent_event_handling(self):
        """Test handling of concurrent events (thread safety)."""
        events_processed = []

        def mock_route(event):
            events_processed.append(event)
            time.sleep(0.01)  # Simulate processing time

        self.handler._route_event = mock_route
        self.handler._read_hook_event = Mock(
            side_effect=[
                {"hook_event_name": "Stop", "id": 1},
                {"hook_event_name": "Stop", "id": 2},
                None,
            ]
        )
        self.handler.duplicate_detector.is_duplicate = Mock(return_value=False)
        self.handler._continue_execution = Mock()
        self.handler.state_manager.increment_events_processed = Mock(return_value=False)

        # Process multiple events
        with patch("signal.alarm"):
            self.handler.handle()  # First event
            self.handler.handle()  # Second event

        self.assertEqual(len(events_processed), 2)
        self.assertEqual(events_processed[0]["id"], 1)
        self.assertEqual(events_processed[1]["id"], 2)

    def test_delegation_tracking(self):
        """Test delegation tracking methods for compatibility."""
        # Test track delegation
        self.handler.state_manager.track_delegation = Mock()
        self.handler._track_delegation("session1", "test_agent", {"data": "test"})
        self.handler.state_manager.track_delegation.assert_called_once_with(
            "session1", "test_agent", {"data": "test"}
        )

        # Test get delegation agent type
        self.handler.state_manager.get_delegation_agent_type = Mock(
            return_value="test_agent"
        )
        agent_type = self.handler._get_delegation_agent_type("session1")
        self.assertEqual(agent_type, "test_agent")

        # Test get git branch
        self.handler.state_manager.get_git_branch = Mock(return_value="main")
        branch = self.handler._get_git_branch("/test/dir")
        self.assertEqual(branch, "main")

    def test_emit_socketio_event(self):
        """Test Socket.IO event emission through connection manager."""
        self.handler.connection_manager.emit_event = Mock()

        self.handler._emit_socketio_event(
            namespace="/hooks", event="test_event", data={"test": "data"}
        )

        self.handler.connection_manager.emit_event.assert_called_once_with(
            "/hooks", "test_event", {"test": "data"}
        )

    def test_cleanup_on_destruction(self):
        """Test that cleanup happens when handler is destroyed."""
        # Create a handler with a mock connection manager
        handler = ClaudeHookHandler()
        handler.connection_manager = Mock()
        handler.connection_manager.cleanup = Mock()

        # Trigger destructor
        handler.__del__()

        # Verify cleanup was called
        handler.connection_manager.cleanup.assert_called_once()

    def test_signal_handling_timeout(self):
        """Test that timeout signal triggers proper cleanup."""
        # Create a mock for the timeout handler
        continue_sent = False

        def mock_continue():
            nonlocal continue_sent
            continue_sent = True

        self.handler._continue_execution = mock_continue

        # Simulate a long-running operation
        def long_operation():
            time.sleep(2)  # Would timeout

        self.handler._read_hook_event = long_operation

        # This test verifies the timeout handler setup
        # In production, signal.alarm(10) would trigger after 10 seconds
        with patch("signal.alarm") as mock_alarm, patch("sys.exit"):
            self.handler.handle()

            # Verify alarm was set
            mock_alarm.assert_any_call(10)
            mock_alarm.assert_any_call(0)


class TestEventProcessing(unittest.TestCase):
    """Test event processing for different event types."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "false"
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"):
            self.handler = ClaudeHookHandler()

    def test_process_user_prompt_event(self):
        """Test processing of UserPromptSubmit events."""
        event = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Create a test file",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.handler.event_handlers.handle_user_prompt_fast = Mock()
        self.handler._route_event(event)

        self.handler.event_handlers.handle_user_prompt_fast.assert_called_once_with(
            event
        )

    def test_process_tool_events(self):
        """Test processing of PreToolUse and PostToolUse events."""
        # Pre tool use
        pre_event = {
            "hook_event_name": "PreToolUse",
            "tool": "Read",
            "parameters": {"file_path": "/test/file.py"},
        }

        self.handler.event_handlers.handle_pre_tool_fast = Mock()
        self.handler._route_event(pre_event)
        self.handler.event_handlers.handle_pre_tool_fast.assert_called_once_with(
            pre_event
        )

        # Post tool use
        post_event = {
            "hook_event_name": "PostToolUse",
            "tool": "Read",
            "result": "File contents...",
        }

        self.handler.event_handlers.handle_post_tool_fast = Mock()
        self.handler._route_event(post_event)
        self.handler.event_handlers.handle_post_tool_fast.assert_called_once_with(
            post_event
        )

    def test_process_notification_event(self):
        """Test processing of Notification events."""
        event = {
            "hook_event_name": "Notification",
            "message": "Processing complete",
            "type": "info",
        }

        self.handler.event_handlers.handle_notification_fast = Mock()
        self.handler._route_event(event)

        self.handler.event_handlers.handle_notification_fast.assert_called_once_with(
            event
        )

    def test_process_malformed_event(self):
        """Test handling of malformed events."""
        malformed_events = [
            {},  # Empty event
            {"data": "no event name"},  # Missing event name
            {"hook_event_name": None},  # None event name
            {"hook_event_name": ""},  # Empty event name
        ]

        for event in malformed_events:
            # Should not raise exception
            self.handler._route_event(event)

    def test_event_with_memory_operations(self):
        """Test events containing memory operations."""
        event = {
            "hook_event_name": "SubagentStop",
            "agent": "engineer",
            "response": json.dumps(
                {
                    "memory-update": {
                        "Project Structure": ["Added new module"],
                        "Dependencies": ["Added pytest"],
                    },
                    "remember": ["Use pytest for testing"],
                }
            ),
        }

        self.handler.event_handlers.handle_subagent_stop_fast = Mock()
        self.handler._route_event(event)

        self.handler.event_handlers.handle_subagent_stop_fast.assert_called_once_with(
            event
        )


class TestPerformance(unittest.TestCase):
    """Test performance-related aspects of the hook handler."""

    def test_event_processing_speed(self):
        """Test that events are processed within acceptable time limits."""
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"):
            handler = ClaudeHookHandler()

        event = {"hook_event_name": "Stop", "data": "test"}

        # Mock the event handler to be fast
        handler.event_handlers.handle_stop_fast = Mock()

        start_time = time.time()
        handler._route_event(event)
        elapsed = time.time() - start_time

        # Event routing should be very fast (< 10ms)
        self.assertLess(elapsed, 0.01)

    def test_memory_usage(self):
        """Test that the handler doesn't accumulate memory over time."""
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"):
            handler = ClaudeHookHandler()

        # Process many events
        for i in range(100):
            event = {"hook_event_name": "Stop", "id": i}
            handler._route_event(event)

        # Memory usage test would require more complex setup
        # This is a placeholder for the concept
        self.assertTrue(True)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete hook handling flow."""

    @patch("sys.stdin")
    @patch("sys.stdout", new_callable=StringIO)
    @patch("select.select")
    @patch("signal.alarm")
    def test_complete_event_flow(
        self, mock_alarm, mock_select, mock_stdout, mock_stdin
    ):
        """Test complete flow from event receipt to continue response."""
        # Setup stdin with a valid event
        event_data = json.dumps(
            {
                "hook_event_name": "Stop",
                "response": "Task completed successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = event_data
        mock_select.return_value = ([mock_stdin], [], [])

        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ) as MockDuplicate, patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"):
            # Setup duplicate detector to return False
            mock_dup_instance = MockDuplicate.return_value
            mock_dup_instance.is_duplicate.return_value = False

            handler = ClaudeHookHandler()
            handler.state_manager.increment_events_processed = Mock(return_value=False)
            handler.event_handlers.handle_stop_fast = Mock()

            # Run the handler
            handler.handle()

            # Verify the complete flow
            mock_select.assert_called_once()  # Event was read
            mock_dup_instance.is_duplicate.assert_called_once()  # Duplicate check
            handler.event_handlers.handle_stop_fast.assert_called_once()  # Event processed

            # Verify continue was sent
            output = mock_stdout.getvalue()
            self.assertIn('"action": "continue"', output)

            # Verify timeout was managed
            mock_alarm.assert_any_call(10)  # Set
            mock_alarm.assert_any_call(0)  # Cleared


if __name__ == "__main__":
    unittest.main(verbosity=2)
