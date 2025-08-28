#!/usr/bin/env python3
"""
Test Memory Cleanup and Event Stream Management
===============================================

Tests for preventing memory leaks in the dashboard by ensuring:
- Old events are properly cleaned up
- Event streams are paginated correctly
- Memory usage stays bounded with large event volumes
- Circular references are avoided
"""

import gc
import json
import sys
import threading
import time
import unittest
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class EventStreamManager:
    """Manages event streams with automatic cleanup and pagination."""

    def __init__(self, max_events=10000, cleanup_interval=60, event_ttl=3600):
        """
        Initialize the event stream manager.

        Args:
            max_events: Maximum number of events to keep in memory
            cleanup_interval: Seconds between cleanup runs
            event_ttl: Time-to-live for events in seconds
        """
        self.max_events = max_events
        self.cleanup_interval = cleanup_interval
        self.event_ttl = event_ttl

        # Use deque for efficient removal from both ends
        self.events = deque(maxlen=max_events)
        self.event_index = {}  # Fast lookup by event_id

        # Cleanup thread
        self.cleanup_thread = None
        self.running = False
        self.lock = threading.RLock()

        # Statistics
        self.stats = {
            "total_events": 0,
            "events_dropped": 0,
            "cleanup_runs": 0,
            "events_expired": 0,
        }

    def start(self):
        """Start the cleanup thread."""
        if not self.running:
            self.running = True
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop, daemon=True
            )
            self.cleanup_thread.start()

    def stop(self):
        """Stop the cleanup thread and clear events."""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        self.clear_all()

    def add_event(self, event):
        """
        Add an event to the stream.

        Args:
            event: Event dictionary with 'event_id' and 'timestamp'
        """
        with self.lock:
            # Add timestamp if not present
            if "timestamp" not in event:
                event["timestamp"] = datetime.utcnow().isoformat()

            # Check if we're at capacity
            if len(self.events) >= self.max_events:
                # Remove oldest event
                old_event = self.events[0]
                if "event_id" in old_event:
                    self.event_index.pop(old_event["event_id"], None)
                self.stats["events_dropped"] += 1

            # Add new event
            self.events.append(event)
            if "event_id" in event:
                self.event_index[event["event_id"]] = event

            self.stats["total_events"] += 1

    def get_events(self, start_index=0, limit=100):
        """
        Get paginated events.

        Args:
            start_index: Starting index for pagination
            limit: Maximum number of events to return

        Returns:
            Dictionary with events and pagination info
        """
        with self.lock:
            total = len(self.events)

            # Calculate actual indices
            start = max(0, min(start_index, total))
            end = min(start + limit, total)

            # Get slice of events
            events_slice = []
            for i in range(start, end):
                events_slice.append(self.events[i])

            return {
                "events": events_slice,
                "total": total,
                "start": start,
                "count": len(events_slice),
                "has_more": end < total,
            }

    def clear_old_events(self):
        """Remove events older than TTL."""
        with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.event_ttl)

            # Count events to remove
            remove_count = 0
            for event in self.events:
                try:
                    # Parse timestamp
                    if isinstance(event.get("timestamp"), str):
                        event_time = datetime.fromisoformat(
                            event["timestamp"].replace("Z", "+00:00")
                        )
                    else:
                        event_time = event.get("timestamp", now)

                    if event_time < cutoff:
                        remove_count += 1
                    else:
                        break  # Events are ordered, so we can stop
                except (ValueError, TypeError):
                    remove_count += 1  # Remove invalid events

            # Remove old events
            for _ in range(remove_count):
                old_event = self.events.popleft()
                if "event_id" in old_event:
                    self.event_index.pop(old_event["event_id"], None)
                self.stats["events_expired"] += 1

    def clear_all(self):
        """Clear all events from memory."""
        with self.lock:
            self.events.clear()
            self.event_index.clear()
            gc.collect()

    def _cleanup_loop(self):
        """Background thread for periodic cleanup."""
        while self.running:
            time.sleep(self.cleanup_interval)
            if self.running:
                self.clear_old_events()
                self.stats["cleanup_runs"] += 1

                # Force garbage collection periodically
                if self.stats["cleanup_runs"] % 10 == 0:
                    gc.collect()

    def get_memory_usage(self):
        """Get approximate memory usage of stored events."""
        with self.lock:
            # Estimate size (rough approximation)
            total_size = 0
            sample_size = min(100, len(self.events))

            if sample_size > 0:
                # Sample some events to estimate average size
                sample_sum = sum(
                    len(json.dumps(self.events[i]))
                    for i in range(
                        0, len(self.events), max(1, len(self.events) // sample_size)
                    )
                )
                avg_size = sample_sum / sample_size
                total_size = int(avg_size * len(self.events))

            return {
                "event_count": len(self.events),
                "estimated_bytes": total_size,
                "estimated_mb": round(total_size / (1024 * 1024), 2),
            }


class TestEventStreamManager(unittest.TestCase):
    """Test the EventStreamManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = EventStreamManager(
            max_events=1000, cleanup_interval=1, event_ttl=10
        )

    def tearDown(self):
        """Clean up after tests."""
        self.manager.stop()

    def test_initialization(self):
        """Test manager initialization."""
        self.assertEqual(self.manager.max_events, 1000)
        self.assertEqual(self.manager.cleanup_interval, 1)
        self.assertEqual(self.manager.event_ttl, 10)
        self.assertEqual(len(self.manager.events), 0)
        self.assertFalse(self.manager.running)

    def test_add_event(self):
        """Test adding events to the stream."""
        # Add an event
        event = {"event_id": "test-1", "data": "test data"}
        self.manager.add_event(event)

        self.assertEqual(len(self.manager.events), 1)
        self.assertIn("timestamp", self.manager.events[0])
        self.assertEqual(self.manager.stats["total_events"], 1)

    def test_event_capacity_limit(self):
        """Test that events are dropped when at capacity."""
        # Set small capacity for testing
        self.manager = EventStreamManager(max_events=10)

        # Add more events than capacity
        for i in range(15):
            self.manager.add_event({"event_id": f"test-{i}", "data": f"data-{i}"})

        # Should only keep last 10 events
        self.assertEqual(len(self.manager.events), 10)
        self.assertEqual(self.manager.stats["events_dropped"], 5)

        # Verify oldest events were dropped
        event_ids = [e["event_id"] for e in self.manager.events]
        self.assertIn("test-14", event_ids)
        self.assertNotIn("test-0", event_ids)

    def test_pagination(self):
        """Test event pagination."""
        # Add 100 events
        for i in range(100):
            self.manager.add_event({"event_id": f"test-{i}", "data": f"data-{i}"})

        # Get first page
        page1 = self.manager.get_events(start_index=0, limit=20)
        self.assertEqual(page1["count"], 20)
        self.assertEqual(page1["start"], 0)
        self.assertEqual(page1["total"], 100)
        self.assertTrue(page1["has_more"])

        # Get middle page
        page2 = self.manager.get_events(start_index=40, limit=20)
        self.assertEqual(page2["count"], 20)
        self.assertEqual(page2["start"], 40)
        self.assertTrue(page2["has_more"])

        # Get last page
        page3 = self.manager.get_events(start_index=90, limit=20)
        self.assertEqual(page3["count"], 10)
        self.assertEqual(page3["start"], 90)
        self.assertFalse(page3["has_more"])

    def test_clear_old_events(self):
        """Test clearing old events based on TTL."""
        # Set very short TTL
        self.manager = EventStreamManager(event_ttl=1)

        # Add events with different timestamps
        now = datetime.utcnow()

        # Old event
        old_event = {
            "event_id": "old-1",
            "timestamp": (now - timedelta(seconds=2)).isoformat(),
        }
        self.manager.add_event(old_event)

        # Recent event
        recent_event = {"event_id": "recent-1", "timestamp": now.isoformat()}
        self.manager.add_event(recent_event)

        # Clear old events
        time.sleep(1.1)
        self.manager.clear_old_events()

        # Only recent event should remain
        self.assertEqual(len(self.manager.events), 1)
        self.assertEqual(self.manager.events[0]["event_id"], "recent-1")
        self.assertEqual(self.manager.stats["events_expired"], 1)

    def test_cleanup_thread(self):
        """Test automatic cleanup thread."""
        # Use short intervals for testing
        self.manager = EventStreamManager(cleanup_interval=0.5, event_ttl=1)

        # Start cleanup thread
        self.manager.start()
        self.assertTrue(self.manager.running)

        # Add old event
        old_event = {
            "event_id": "old-1",
            "timestamp": (datetime.utcnow() - timedelta(seconds=2)).isoformat(),
        }
        self.manager.add_event(old_event)

        # Wait for cleanup
        time.sleep(1)

        # Event should be cleaned up
        self.assertEqual(len(self.manager.events), 0)
        self.assertGreater(self.manager.stats["cleanup_runs"], 0)

        self.manager.stop()

    def test_memory_usage_calculation(self):
        """Test memory usage estimation."""
        # Add events
        for i in range(100):
            self.manager.add_event(
                {"event_id": f"test-{i}", "data": "x" * 100}  # 100 bytes of data
            )

        usage = self.manager.get_memory_usage()

        self.assertEqual(usage["event_count"], 100)
        self.assertGreater(usage["estimated_bytes"], 10000)  # At least 100*100 bytes
        self.assertGreater(usage["estimated_mb"], 0)

    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        errors = []

        def add_events(thread_id):
            try:
                for i in range(100):
                    self.manager.add_event(
                        {"event_id": f"thread-{thread_id}-{i}", "data": f"data-{i}"}
                    )
            except Exception as e:
                errors.append(e)

        def read_events(thread_id):
            try:
                for i in range(50):
                    self.manager.get_events(start_index=i * 10, limit=10)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=add_events, args=(i,))
            t2 = threading.Thread(target=read_events, args=(i,))
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should occur
        self.assertEqual(len(errors), 0)

    def test_memory_leak_prevention(self):
        """Test that memory is properly released."""
        import gc
        import weakref

        # Create events with potential circular references
        events = []
        for i in range(100):
            event = {"event_id": f"leak-test-{i}", "data": {"index": i}}
            # Create a weak reference to track garbage collection
            events.append(weakref.ref(event))
            self.manager.add_event(event)

        # Clear all events
        self.manager.clear_all()

        # Force garbage collection
        gc.collect()

        # Check that events were garbage collected
        alive_count = sum(1 for ref in events if ref() is not None)

        # Most events should be garbage collected
        # (some might still be referenced in locals)
        self.assertLess(alive_count, 10)


class TestEventStreamPerformance(unittest.TestCase):
    """Performance tests for event stream management."""

    def test_large_event_volume(self):
        """Test handling large volumes of events."""
        manager = EventStreamManager(max_events=50000)

        start_time = time.time()

        # Add 100,000 events
        for i in range(100000):
            manager.add_event(
                {
                    "event_id": f"perf-{i}",
                    "type": "test.event",
                    "data": {"index": i, "payload": "x" * 100},
                }
            )

        elapsed = time.time() - start_time

        # Should handle 100k events in reasonable time
        self.assertLess(elapsed, 10)  # Less than 10 seconds

        # Should only keep max_events
        self.assertEqual(len(manager.events), 50000)
        self.assertEqual(manager.stats["events_dropped"], 50000)

        # Test pagination performance
        start_time = time.time()
        for i in range(100):
            manager.get_events(start_index=i * 100, limit=100)
        elapsed = time.time() - start_time

        # Pagination should be fast
        self.assertLess(elapsed, 1)  # Less than 1 second for 100 pages

        manager.stop()

    def test_memory_bounded(self):
        """Test that memory usage stays bounded."""
        manager = EventStreamManager(max_events=10000)

        # Add many events
        for i in range(50000):
            manager.add_event(
                {"event_id": f"mem-{i}", "data": "x" * 1000}  # 1KB per event
            )

        # Check memory usage
        usage = manager.get_memory_usage()

        # Should not exceed max_events
        self.assertEqual(usage["event_count"], 10000)

        # Memory should be bounded (roughly 10MB for 10k events of 1KB each)
        self.assertLess(usage["estimated_mb"], 20)

        manager.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
