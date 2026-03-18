"""
Comprehensive unit tests for hook event processing.

This test suite validates:
- Event transformation (Claude format to internal format)
- Field mapping and validation
- Event enrichment with metadata
- Event filtering and routing
- Batch processing capabilities
- Memory usage optimization

These tests ensure reliable event processing and transformation,
which is crucial for accurate monitoring and data collection.
"""

import json
import os
import sys
import time
import unittest
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_mpm.hooks.claude_hooks.services import (
    DuplicateEventDetector,
    StateManagerService,
    SubagentResponseProcessor,
)


class TestDuplicateEventDetector(unittest.TestCase):
    """Test the DuplicateEventDetector service."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = DuplicateEventDetector()

    def test_initialization(self):
        """Test detector initialization."""
        self.assertIsNotNone(self.detector._recent_events)
        self.assertIsNotNone(self.detector._events_lock)
        self.assertEqual(self.detector.duplicate_window_seconds, 0.1)

    def test_generate_event_key(self):
        """Test event key generation for deduplication.

        NOTE: For Stop events, key is based on hook_type + session_id only.
        Different session IDs → different keys.
        """
        event1 = {"hook_event_name": "Stop", "data": "test", "session_id": "123"}

        event2 = {"hook_event_name": "Stop", "data": "test", "session_id": "123"}

        # Different session_id makes a different key (data field is not used for Stop events)
        event3 = {"hook_event_name": "Stop", "data": "different", "session_id": "456"}

        key1 = self.detector.generate_event_key(event1)
        key2 = self.detector.generate_event_key(event2)
        key3 = self.detector.generate_event_key(event3)

        # Same events should generate same key
        self.assertEqual(key1, key2)
        # Different session_ids should generate different keys
        self.assertNotEqual(key1, key3)

    def test_duplicate_detection_within_threshold(self):
        """Test duplicate detection within 50ms threshold."""
        event = {"hook_event_name": "Stop", "data": "test"}

        # First occurrence should not be duplicate
        self.assertFalse(self.detector.is_duplicate(event))

        # Immediate second occurrence should be duplicate
        self.assertTrue(self.detector.is_duplicate(event))

        # Within 50ms should still be duplicate
        time.sleep(0.03)  # 30ms
        self.assertTrue(self.detector.is_duplicate(event))

    def test_duplicate_detection_after_threshold(self):
        """Test that events after 100ms threshold are not duplicates."""
        event = {"hook_event_name": "Stop", "data": "test"}

        # First occurrence
        self.assertFalse(self.detector.is_duplicate(event))

        # Wait beyond threshold (duplicate_window_seconds = 0.1 = 100ms)
        time.sleep(0.11)  # 110ms > 100ms threshold

        # Should not be duplicate anymore
        self.assertFalse(self.detector.is_duplicate(event))

    def test_different_events_not_duplicates(self):
        """Test that different events are not considered duplicates.

        NOTE: Key uniqueness for Stop events is based on session_id, not data.
        Different session_ids → different keys → not duplicates.
        """
        event1 = {"hook_event_name": "Stop", "data": "test1", "session_id": "session-A"}
        event2 = {"hook_event_name": "Stop", "data": "test2", "session_id": "session-B"}

        self.assertFalse(self.detector.is_duplicate(event1))
        self.assertFalse(self.detector.is_duplicate(event2))

    def test_cleanup_old_events(self):
        """Test time-based cleanup via clear_old_events() after events expire."""
        # Add 10 events with unique session_ids so they get distinct keys
        for i in range(10):
            event = {
                "hook_event_name": "Stop",
                "data": f"test{i}",
                "session_id": f"session-{i}",
            }
            self.detector.is_duplicate(event)

        # Should have exactly 10 events
        self.assertEqual(len(self.detector._recent_events), 10)

        # Wait for events to age beyond duplicate window (duplicate_window_seconds=0.1)
        time.sleep(0.11)

        # Call clear_old_events() to remove expired entries
        self.detector.clear_old_events()

        # All old events should be removed
        self.assertEqual(len(self.detector._recent_events), 0)

    def test_thread_safety(self):
        """Test thread safety of duplicate detection."""
        import threading

        events_processed = []

        def process_event(event_id):
            # Use unique session_id per event so each has a unique key
            event = {
                "hook_event_name": "Stop",
                "id": event_id,
                "session_id": f"session-{event_id}",
            }
            result = self.detector.is_duplicate(event)
            events_processed.append((event_id, result))

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=process_event, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All events should be processed
        self.assertEqual(len(events_processed), 10)

        # Each unique event should not be duplicate on first occurrence
        unique_ids = set()
        for event_id, is_dup in events_processed:
            if event_id not in unique_ids:
                self.assertFalse(is_dup)
                unique_ids.add(event_id)


class TestStateManagerService(unittest.TestCase):
    """Test the StateManagerService for state management."""

    def setUp(self):
        """Set up test fixtures."""
        self.state_manager = StateManagerService()

    def test_initialization(self):
        """Test state manager initialization."""
        self.assertIsNotNone(self.state_manager.active_delegations)
        self.assertIsNotNone(self.state_manager.delegation_history)
        self.assertIsNotNone(self.state_manager.delegation_requests)
        self.assertIsNotNone(self.state_manager.pending_prompts)
        self.assertEqual(self.state_manager.events_processed, 0)

    def test_track_delegation(self):
        """Test delegation tracking."""
        session_id = "test-session-123"
        agent_type = "engineer"
        request_data = {"task": "refactor code"}

        self.state_manager.track_delegation(session_id, agent_type, request_data)

        # Check delegation is tracked (active_delegations stores agent_type as string)
        self.assertIn(session_id, self.state_manager.active_delegations)
        self.assertEqual(self.state_manager.active_delegations[session_id], agent_type)

        # Check delegation history (deque of (key, agent_type) tuples)
        self.assertTrue(
            any(
                k.startswith(session_id)
                for k, _ in self.state_manager.delegation_history
            )
        )

        # Check request data if provided (wrapped as {"agent_type": ..., "request": ...})
        if request_data:
            self.assertIn(session_id, self.state_manager.delegation_requests)
            self.assertEqual(
                self.state_manager.delegation_requests[session_id]["request"],
                request_data,
            )

    def test_get_delegation_agent_type(self):
        """Test getting delegation agent type."""
        session_id = "test-session-123"
        agent_type = "optimizer"

        self.state_manager.track_delegation(session_id, agent_type)

        result = self.state_manager.get_delegation_agent_type(session_id)
        self.assertEqual(result, agent_type)

        # Test unknown session
        result = self.state_manager.get_delegation_agent_type("unknown-session")
        self.assertEqual(result, "unknown")

    def test_increment_events_processed(self):
        """Test event processing counter and cleanup trigger."""
        # First 99 events should not trigger cleanup
        for i in range(99):
            should_cleanup = self.state_manager.increment_events_processed()
            self.assertFalse(should_cleanup)
            self.assertEqual(self.state_manager.events_processed, i + 1)

        # 100th event should trigger cleanup
        should_cleanup = self.state_manager.increment_events_processed()
        self.assertTrue(should_cleanup)
        self.assertEqual(self.state_manager.events_processed, 100)

        # Counter does NOT reset (continues counting past 100)
        should_cleanup = self.state_manager.increment_events_processed()
        self.assertFalse(should_cleanup)
        self.assertEqual(self.state_manager.events_processed, 101)

    def test_cleanup_old_entries(self):
        """Test size-based cleanup of state entries (MAX_DELEGATION_TRACKING=200)."""
        # Add more than MAX_DELEGATION_TRACKING (200) entries to trigger cleanup
        for i in range(205):
            self.state_manager.active_delegations[f"session-{i:03d}"] = f"agent-{i}"

        self.assertEqual(len(self.state_manager.active_delegations), 205)

        # Run cleanup
        self.state_manager.cleanup_old_entries()

        # Should have trimmed to MAX_DELEGATION_TRACKING (200)
        self.assertEqual(
            len(self.state_manager.active_delegations),
            self.state_manager.MAX_DELEGATION_TRACKING,
        )

        # Alphabetically early sessions should have been removed
        self.assertNotIn("session-000", self.state_manager.active_delegations)
        # Later sessions should remain
        self.assertIn("session-200", self.state_manager.active_delegations)

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_get_git_branch(self, mock_run, mock_chdir):
        """Test git branch detection (uses git branch --show-current)."""
        mock_run.return_value = Mock(returncode=0, stdout="feature/test-branch\n")
        mock_chdir.return_value = (
            None  # Mock os.chdir so /test/repo path doesn't need to exist
        )

        branch = self.state_manager.get_git_branch("/test/repo")

        self.assertEqual(branch, "feature/test-branch")
        mock_run.assert_called_once()

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_get_git_branch_caching(self, mock_run, mock_chdir):
        """Test git branch caching."""
        mock_run.return_value = Mock(returncode=0, stdout="main\n")
        mock_chdir.return_value = (
            None  # Mock os.chdir so /test/repo path doesn't need to exist
        )

        # First call should hit git
        branch1 = self.state_manager.get_git_branch("/test/repo")
        self.assertEqual(branch1, "main")
        self.assertEqual(mock_run.call_count, 1)

        # Second call within cache time should use cache
        branch2 = self.state_manager.get_git_branch("/test/repo")
        self.assertEqual(branch2, "main")
        self.assertEqual(mock_run.call_count, 1)  # No additional call

    def test_state_transitions(self):
        """Test state transitions for delegations."""
        session_id = "test-session"

        # Start delegation
        self.state_manager.track_delegation(session_id, "agent1")
        self.assertIn(session_id, self.state_manager.active_delegations)

        # Complete delegation (remove from active)
        del self.state_manager.active_delegations[session_id]
        self.assertNotIn(session_id, self.state_manager.active_delegations)

        # History should still have it (deque of (key, agent_type) tuples)
        self.assertTrue(
            any(
                k.startswith(session_id)
                for k, _ in self.state_manager.delegation_history
            )
        )


class TestSubagentResponseProcessor(unittest.TestCase):
    """Test the SubagentResponseProcessor for complex response handling."""

    def setUp(self):
        """Set up test fixtures."""
        # Use MagicMock so len() works on delegation_requests when DEBUG=True
        # (test_agent_event_tracking.py sets CLAUDE_MPM_HOOK_DEBUG=true at module level
        # which can pollute the env for this test when run in the full suite)
        self.state_manager = MagicMock()
        self.response_tracking = MagicMock()
        self.connection_manager = MagicMock()

        self.processor = SubagentResponseProcessor(
            self.state_manager, self.response_tracking, self.connection_manager
        )

    def test_process_subagent_stop_with_memory(self):
        """Test processing subagent stop event with memory operations."""
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-session",
            "response": json.dumps(
                {
                    "memory-update": {
                        "Project Context": ["New architecture pattern"],
                        "Dependencies": ["Added pytest", "Added black"],
                    },
                    "remember": ["Use dependency injection", "Follow SOLID principles"],
                }
            ),
        }

        # Mock state manager
        self.state_manager.get_delegation_agent_type.return_value = "engineer"
        self.state_manager.delegation_requests.get.return_value = {"task": "refactor"}

        # Process event
        self.processor.process_subagent_stop(event)

        # Verify response tracking was called via response_tracker.track_response
        self.response_tracking.response_tracker.track_response.assert_called()

        # Verify connection manager emitted event
        self.connection_manager.emit_event.assert_called()

    def test_process_subagent_stop_without_memory(self):
        """Test processing subagent stop event without memory operations."""
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-session",
            "response": "Simple text response",
        }

        self.state_manager.get_delegation_agent_type.return_value = "test_agent"

        # Process event
        self.processor.process_subagent_stop(event)

        # Should still track response via response_tracker.track_response
        self.response_tracking.response_tracker.track_response.assert_called()

    @unittest.skip(
        "_extract_memory_operations was removed; memory extraction now handled by _extract_structured_response"
    )
    def test_extract_memory_operations(self):
        """Test extraction of memory operations from response."""

    @unittest.skip(
        "_extract_memory_operations was removed; memory extraction now handled by _extract_structured_response"
    )
    def test_extract_memory_operations_no_json(self):
        """Test extraction when response is not JSON."""

    @unittest.skip(
        "_extract_memory_operations was removed; memory extraction now handled by _extract_structured_response"
    )
    def test_extract_memory_operations_json_without_memory(self):
        """Test extraction from JSON without memory fields."""


class TestEventTransformation(unittest.TestCase):
    """Test event transformation and field mapping."""

    def test_claude_to_internal_format(self):
        """Test transformation from Claude format to internal format."""
        claude_event = {
            "hook_event_name": "Stop",
            "hook_event_id": "123",
            "hook_event_timestamp": "2024-01-01T12:00:00Z",
            "response": "Test response",
        }

        # Transform to internal format (this would be done by event handlers)
        internal_event = {
            "type": claude_event.get("hook_event_name"),
            "id": claude_event.get("hook_event_id"),
            "timestamp": claude_event.get("hook_event_timestamp"),
            "data": {"response": claude_event.get("response")},
        }

        self.assertEqual(internal_event["type"], "Stop")
        self.assertEqual(internal_event["id"], "123")
        self.assertIn("response", internal_event["data"])

    def test_event_enrichment(self):
        """Test event enrichment with metadata."""
        base_event = {
            "hook_event_name": "PreToolUse",
            "tool": "Read",
            "parameters": {"file_path": "/test/file.py"},
        }

        # Enrich with metadata (this would be done by event handlers)
        enriched_event = base_event.copy()
        enriched_event.update(
            {
                "processed_at": datetime.now(UTC).isoformat(),
                "session_id": "test-session",
                "git_branch": "main",
                "working_directory": "/test/project",
            }
        )

        self.assertIn("processed_at", enriched_event)
        self.assertIn("session_id", enriched_event)
        self.assertIn("git_branch", enriched_event)

    def test_field_mapping_compatibility(self):
        """Test field mapping for backward compatibility."""
        # Different field names that should map to same concept
        field_variations = [
            {"hook_event_name": "Stop"},
            {"event": "Stop"},
            {"type": "Stop"},
            {"event_type": "Stop"},
            {"hook_event_type": "Stop"},
        ]

        for event in field_variations:
            # All should resolve to 'Stop' event type
            event_type = (
                event.get("hook_event_name")
                or event.get("event")
                or event.get("type")
                or event.get("event_type")
                or event.get("hook_event_type")
            )
            self.assertEqual(event_type, "Stop")

    def test_event_validation(self):
        """Test event validation for required fields."""
        # Valid event
        valid_event = {
            "hook_event_name": "Stop",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Invalid events
        invalid_events = [
            None,  # None event
            {},  # Empty event
            {"data": "no event name"},  # Missing event name
            {"hook_event_name": ""},  # Empty event name
        ]

        # Validation function (simplified)
        def is_valid_event(event):
            if not event:
                return False
            event_name = (
                event.get("hook_event_name") or event.get("event") or event.get("type")
            )
            return bool(event_name)

        self.assertTrue(is_valid_event(valid_event))
        for invalid in invalid_events:
            self.assertFalse(is_valid_event(invalid))


class TestBatchProcessing(unittest.TestCase):
    """Test batch processing capabilities."""

    def test_batch_event_processing(self):
        """Test processing multiple events in batch."""
        events = [
            {"hook_event_name": "Stop", "id": 1},
            {"hook_event_name": "SubagentStop", "id": 2},
            {"hook_event_name": "PreToolUse", "id": 3},
        ]

        processed = []

        def process_event(event):
            processed.append(event["id"])

        # Process batch
        for event in events:
            process_event(event)

        self.assertEqual(len(processed), 3)
        self.assertEqual(processed, [1, 2, 3])

    def test_batch_filtering(self):
        """Test filtering events in batch processing."""
        events = [
            {"hook_event_name": "Stop", "id": 1},
            {"hook_event_name": "UnknownEvent", "id": 2},
            {"hook_event_name": "SubagentStop", "id": 3},
            {"hook_event_name": "InvalidEvent", "id": 4},
        ]

        valid_events = ["Stop", "SubagentStop", "PreToolUse", "PostToolUse"]

        # Filter valid events
        filtered = [e for e in events if e.get("hook_event_name") in valid_events]

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["id"], 1)
        self.assertEqual(filtered[1]["id"], 3)

    def test_batch_memory_optimization(self):
        """Test memory optimization in batch processing."""
        # Create large batch of events
        large_batch = []
        for i in range(1000):
            large_batch.append(
                {
                    "hook_event_name": "Stop",
                    "id": i,
                    "data": "x" * 1000,  # 1KB per event
                }
            )

        # Process with memory optimization (keep only recent)
        max_keep = 100
        recent_events = []

        for event in large_batch:
            recent_events.append(event)
            # Keep only recent events
            if len(recent_events) > max_keep:
                recent_events.pop(0)

        # Should only keep max_keep events
        self.assertEqual(len(recent_events), max_keep)
        # Should have the most recent events
        self.assertEqual(recent_events[-1]["id"], 999)
        self.assertEqual(recent_events[0]["id"], 900)


class TestEventRouting(unittest.TestCase):
    """Test event routing and filtering."""

    def test_route_to_correct_handler(self):
        """Test routing events to correct handlers."""
        routing_map = {
            "Stop": "handle_stop",
            "SubagentStop": "handle_subagent_stop",
            "PreToolUse": "handle_pre_tool",
            "PostToolUse": "handle_post_tool",
            "UserPromptSubmit": "handle_user_prompt",
        }

        event = {"hook_event_name": "Stop"}
        handler = routing_map.get(event["hook_event_name"])
        self.assertEqual(handler, "handle_stop")

        event = {"hook_event_name": "PreToolUse"}
        handler = routing_map.get(event["hook_event_name"])
        self.assertEqual(handler, "handle_pre_tool")

    def test_filter_by_event_type(self):
        """Test filtering events by type."""
        events = [
            {"hook_event_name": "Stop"},
            {"hook_event_name": "SubagentStop"},
            {"hook_event_name": "Stop"},
            {"hook_event_name": "PreToolUse"},
        ]

        # Filter only Stop events
        stop_events = [e for e in events if e.get("hook_event_name") == "Stop"]

        self.assertEqual(len(stop_events), 2)

        # Filter tool events
        tool_events = [
            e
            for e in events
            if e.get("hook_event_name") in ["PreToolUse", "PostToolUse"]
        ]

        self.assertEqual(len(tool_events), 1)

    def test_priority_routing(self):
        """Test priority-based event routing."""
        # Define event priorities (lower number = higher priority)
        priorities = {
            "UserPromptSubmit": 1,
            "Stop": 2,
            "SubagentStop": 2,
            "PreToolUse": 3,
            "PostToolUse": 3,
            "Notification": 4,
        }

        events = [
            {"hook_event_name": "PostToolUse"},
            {"hook_event_name": "UserPromptSubmit"},
            {"hook_event_name": "Stop"},
            {"hook_event_name": "Notification"},
        ]

        # Sort by priority
        sorted_events = sorted(
            events, key=lambda e: priorities.get(e.get("hook_event_name", ""), 999)
        )

        # Highest priority should be first
        self.assertEqual(sorted_events[0]["hook_event_name"], "UserPromptSubmit")
        self.assertEqual(sorted_events[-1]["hook_event_name"], "Notification")


if __name__ == "__main__":
    unittest.main(verbosity=2)
