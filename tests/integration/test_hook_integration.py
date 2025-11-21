#!/usr/bin/env python3
"""
Integration tests for the complete hook handling flow.

This test suite validates:
- Complete hook event flow from trigger to dashboard
- Hook trigger to dashboard display integration
- Concurrent hook event handling
- Error recovery mechanisms
- Performance metrics and timing

These integration tests ensure the entire hook system works together
correctly, from Claude Code triggering hooks to the dashboard displaying events.
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from src.claude_mpm.hooks.claude_hooks.installer import HookInstaller


class TestHookEventFlow(unittest.TestCase):
    """Test complete hook event flow from receipt to processing."""

    def setUp(self):
        """Set up test environment."""
        # Disable debug output
        os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "false"

        # Create mock services
        self.mock_connection = Mock()
        self.mock_state = Mock()
        self.mock_response = Mock()

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    def test_complete_event_flow(
        self, mock_response_cls, mock_state_cls, mock_conn_cls
    ):
        """Test complete flow from event receipt to dashboard emission."""
        # Setup mocks
        mock_conn_cls.return_value = self.mock_connection
        mock_state_cls.return_value = self.mock_state
        mock_response_cls.return_value = self.mock_response

        # Configure state manager
        self.mock_state.increment_events_processed.return_value = False
        self.mock_state.get_delegation_agent_type.return_value = "test_agent"
        self.mock_state.get_git_branch.return_value = "main"

        # Create handler
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"
        ) as MockEvents:
            handler = ClaudeHookHandler()

            # Configure event handlers
            mock_events = MockEvents.return_value
            mock_events.handle_stop_fast = Mock()
            handler.event_handlers = mock_events

            # Create test event
            test_event = {
                "hook_event_name": "Stop",
                "session_id": "test-session-123",
                "response": "Task completed successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Simulate event processing
            handler._route_event(test_event)

            # Verify event was processed
            mock_events.handle_stop_fast.assert_called_once_with(test_event)

    def test_event_flow_with_timing(self):
        """Test event flow timing and performance metrics."""
        start_times = []
        end_times = []

        def track_timing(event):
            start_times.append(time.time())
            time.sleep(0.01)  # Simulate processing
            end_times.append(time.time())

        # Create handler with timing tracking
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
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"
        ) as MockEvents:
            handler = ClaudeHookHandler()
            mock_events = MockEvents.return_value
            mock_events.handle_stop_fast = track_timing
            handler.event_handlers = mock_events

            # Process multiple events
            for i in range(5):
                event = {"hook_event_name": "Stop", "id": i}
                handler._route_event(event)

            # Verify timing
            self.assertEqual(len(start_times), 5)
            self.assertEqual(len(end_times), 5)

            # Check processing times
            for i in range(5):
                processing_time = end_times[i] - start_times[i]
                # Processing should be reasonably fast
                self.assertLess(processing_time, 0.1)  # Less than 100ms


class TestHookToDashboard(unittest.TestCase):
    """Test hook event delivery to dashboard."""

    @patch(
        "src.claude_mpm.hooks.claude_hooks.services.connection_manager_http.requests.post"
    )
    def test_event_delivery_to_dashboard(self, mock_post):
        """Test that events are delivered to the dashboard."""
        from src.claude_mpm.hooks.claude_hooks.services.connection_manager_http import (
            ConnectionManagerService,
        )

        # Configure mock response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"success": True}

        # Create connection manager
        conn_manager = ConnectionManagerService()

        # Emit test event
        test_data = {
            "event_type": "Stop",
            "session_id": "test-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        conn_manager.emit_event("/hooks", "hook_event", test_data)

        # Verify HTTP request was made
        mock_post.assert_called()
        call_args = mock_post.call_args

        # Check URL
        self.assertIn("localhost:8765", call_args[0][0])

        # Check data
        posted_data = call_args[1]["json"]
        self.assertEqual(posted_data["namespace"], "/hooks")
        self.assertEqual(posted_data["event"], "hook_event")
        self.assertEqual(posted_data["data"]["event_type"], "Stop")

    @patch(
        "src.claude_mpm.hooks.claude_hooks.services.connection_manager_http.requests.post"
    )
    def test_dashboard_connection_failure(self, mock_post):
        """Test handling of dashboard connection failures."""
        from src.claude_mpm.hooks.claude_hooks.services.connection_manager_http import (
            ConnectionManagerService,
        )

        # Simulate connection failure
        mock_post.side_effect = Exception("Connection refused")

        # Create connection manager
        conn_manager = ConnectionManagerService()

        # Try to emit event
        test_data = {"event_type": "Stop"}

        # Should not raise exception
        try:
            conn_manager.emit_event("/hooks", "hook_event", test_data)
        except:
            self.fail("Connection failure should be handled gracefully")

    @patch(
        "src.claude_mpm.hooks.claude_hooks.services.connection_manager_http.requests.post"
    )
    def test_event_batching(self, mock_post):
        """Test batching of multiple events."""
        from src.claude_mpm.hooks.claude_hooks.services.connection_manager_http import (
            ConnectionManagerService,
        )

        mock_post.return_value.status_code = 200

        conn_manager = ConnectionManagerService()

        # Send multiple events rapidly
        for i in range(10):
            conn_manager.emit_event("/hooks", "hook_event", {"id": i})

        # All events should be sent
        self.assertEqual(mock_post.call_count, 10)


class TestConcurrentEvents(unittest.TestCase):
    """Test handling of concurrent hook events."""

    def test_concurrent_event_processing(self):
        """Test that multiple events can be processed concurrently."""
        processed_events = []
        lock = threading.Lock()

        def process_event(event_id):
            # Simulate processing
            time.sleep(0.01)
            with lock:
                processed_events.append(event_id)

        # Create handler
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ) as MockDup, patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"):
            # Configure duplicate detector to allow all events
            mock_dup_instance = MockDup.return_value
            mock_dup_instance.is_duplicate.return_value = False

            handler = ClaudeHookHandler()

            # Create threads for concurrent processing
            threads = []
            for i in range(10):
                event = {"hook_event_name": "Stop", "id": i}

                def run_handler(e):
                    handler._route_event(e)
                    process_event(e["id"])

                thread = threading.Thread(target=run_handler, args=(event,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All events should be processed
            self.assertEqual(len(processed_events), 10)
            self.assertEqual(set(processed_events), set(range(10)))

    def test_thread_safety(self):
        """Test thread safety of shared state."""
        from src.claude_mpm.hooks.claude_hooks.services import StateManagerService

        state_manager = StateManagerService()

        def modify_state(session_id):
            # Multiple operations on shared state
            state_manager.track_delegation(session_id, f"agent_{session_id}")
            time.sleep(0.001)
            agent_type = state_manager.get_delegation_agent_type(session_id)
            self.assertEqual(agent_type, f"agent_{session_id}")

        # Run concurrent modifications
        threads = []
        for i in range(20):
            thread = threading.Thread(target=modify_state, args=(f"session_{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check final state
        for i in range(20):
            agent_type = state_manager.get_delegation_agent_type(f"session_{i}")
            self.assertEqual(agent_type, f"agent_session_{i}")


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms."""

    def test_recovery_from_processing_error(self):
        """Test recovery from errors during event processing."""
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
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"
        ) as MockEvents:
            handler = ClaudeHookHandler()

            # Configure handler to raise exception
            mock_events = MockEvents.return_value
            mock_events.handle_stop_fast.side_effect = Exception("Processing error")
            handler.event_handlers = mock_events

            # Process event that will cause error
            event = {"hook_event_name": "Stop", "data": "test"}

            # Should not raise exception
            try:
                handler._route_event(event)
            except:
                self.fail("Error should be handled gracefully")

    def test_recovery_from_connection_error(self):
        """Test recovery from connection errors."""
        from src.claude_mpm.hooks.claude_hooks.services.connection_manager_http import (
            ConnectionManagerService,
        )

        with patch(
            "src.claude_mpm.hooks.claude_hooks.services.connection_manager_http.requests.post"
        ) as mock_post:
            # Simulate connection errors then recovery
            mock_post.side_effect = [
                Exception("Connection refused"),
                Exception("Connection refused"),
                Mock(status_code=200, json=Mock(return_value={"success": True})),
            ]

            conn_manager = ConnectionManagerService()

            # Try multiple times
            for i in range(3):
                conn_manager.emit_event("/hooks", "test", {"attempt": i})

            # Should have tried all times
            self.assertEqual(mock_post.call_count, 3)

    def test_graceful_degradation(self):
        """Test graceful degradation when services are unavailable."""
        # Test without EventBus
        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EventBus", None
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EVENTBUS_AVAILABLE", False
        ):
            # Should still create handler
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
                self.assertIsNotNone(handler)


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metrics and timing."""

    def test_event_processing_speed(self):
        """Test that events are processed within acceptable time."""
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

            # Process many events and measure time
            start_time = time.time()

            for i in range(100):
                event = {"hook_event_name": "Stop", "id": i}
                handler._route_event(event)

            elapsed = time.time() - start_time

            # Should process 100 events quickly
            self.assertLess(elapsed, 1.0)  # Less than 1 second for 100 events

            # Calculate average time per event
            avg_time = elapsed / 100
            self.assertLess(avg_time, 0.01)  # Less than 10ms per event

    def test_memory_usage_stability(self):
        """Test that memory usage remains stable over time."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

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
            for i in range(1000):
                event = {
                    "hook_event_name": "Stop",
                    "id": i,
                    "data": "x" * 1000,  # 1KB data
                }
                handler._route_event(event)

                # Periodically force garbage collection
                if i % 100 == 0:
                    gc.collect()

            # Final garbage collection
            gc.collect()

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable
            self.assertLess(memory_increase, 50)  # Less than 50MB increase

    def test_timeout_protection(self):
        """Test that timeout protection works correctly."""

        def slow_handler(event):
            time.sleep(2)  # Simulate slow processing

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
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"
        ) as MockEvents:
            handler = ClaudeHookHandler()

            # Configure slow handler
            mock_events = MockEvents.return_value
            mock_events.handle_stop_fast = slow_handler
            handler.event_handlers = mock_events

            # Mock stdin and signals
            with patch("sys.stdin") as mock_stdin, patch(
                "select.select"
            ) as mock_select, patch("signal.alarm") as mock_alarm, patch(
                "sys.stdout", new_callable=Mock
            ):
                # Setup mock event
                mock_stdin.isatty.return_value = False
                mock_stdin.read.return_value = json.dumps({"hook_event_name": "Stop"})
                mock_select.return_value = ([mock_stdin], [], [])

                # Configure handler mocks
                handler.duplicate_detector.is_duplicate = Mock(return_value=False)
                handler.state_manager.increment_events_processed = Mock(
                    return_value=False
                )

                # Process with timeout protection
                handler.handle()

                # Verify timeout was set
                mock_alarm.assert_any_call(10)  # 10-second timeout
                mock_alarm.assert_any_call(0)  # Clear alarm


class TestEndToEndIntegration(unittest.TestCase):
    """Test complete end-to-end integration scenarios."""

    def test_install_trigger_process_flow(self):
        """Test complete flow from installation to event processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test environment
            claude_dir = Path(temp_dir) / ".claude"
            claude_dir.mkdir()

            # Test installation
            with patch(
                "src.claude_mpm.hooks.claude_hooks.installer.Path.home",
                return_value=Path(temp_dir),
            ):
                installer = HookInstaller()

                # Mock version check
                with patch.object(
                    installer,
                    "is_version_compatible",
                    return_value=(True, "Compatible"),
                ), patch.object(
                    installer,
                    "get_hook_script_path",
                    return_value=Path("/mock/script.sh"),
                ):
                    # Install hooks
                    success = installer.install_hooks()
                    self.assertTrue(success)

                    # Verify settings created
                    settings_file = claude_dir / "settings.json"
                    self.assertTrue(settings_file.exists())

                    # Verify hooks configured
                    with settings_file.open() as f:
                        settings = json.load(f)

                    self.assertIn("hooks", settings)
                    self.assertIn("Stop", settings["hooks"])

    def test_real_world_scenario(self):
        """Test a realistic usage scenario."""
        # Simulate a sequence of real events
        events = [
            {"hook_event_name": "UserPromptSubmit", "prompt": "Create a test file"},
            {
                "hook_event_name": "PreToolUse",
                "tool": "Write",
                "parameters": {"file_path": "/test.py"},
            },
            {"hook_event_name": "PostToolUse", "tool": "Write", "result": "success"},
            {"hook_event_name": "Stop", "response": "File created successfully"},
        ]

        processed_events = []

        def capture_event(event):
            processed_events.append(event.get("hook_event_name"))

        with patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector"
        ) as MockDup, patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.SubagentResponseProcessor"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager"
        ), patch(
            "src.claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers"
        ) as MockEvents:
            # Configure mocks
            mock_dup = MockDup.return_value
            mock_dup.is_duplicate.return_value = False

            mock_events = MockEvents.return_value
            mock_events.handle_user_prompt_fast = lambda e: capture_event(e)
            mock_events.handle_pre_tool_fast = lambda e: capture_event(e)
            mock_events.handle_post_tool_fast = lambda e: capture_event(e)
            mock_events.handle_stop_fast = lambda e: capture_event(e)

            handler = ClaudeHookHandler()
            handler.event_handlers = mock_events

            # Process event sequence
            for event in events:
                handler._route_event(event)

            # Verify all events processed in order
            self.assertEqual(
                processed_events,
                ["UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
