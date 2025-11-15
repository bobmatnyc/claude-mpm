"""Comprehensive unit tests for EventBus.

This test suite provides complete coverage of the EventBus class,
testing event publishing, subscription, filtering, and singleton behavior.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All event scenarios tested
- Thread safety verified
- Wildcard patterns tested
"""

import pytest
import asyncio
import threading
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from claude_mpm.services.event_bus.event_bus import EventBus


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def event_bus():
    """Create fresh EventBus instance for each test.

    Note: EventBus is singleton, so we need to reset it between tests.
    """
    # Reset singleton instance
    EventBus._instance = None
    bus = EventBus()
    bus.clear_filters()
    bus.clear_history()
    bus.reset_stats()
    bus.remove_all_listeners()
    bus.enable()
    yield bus
    # Cleanup
    bus.remove_all_listeners()
    EventBus._instance = None


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "message": "Test event",
        "timestamp": datetime.now().isoformat(),
        "user": "test_user"
    }


# ============================================================================
# TEST SINGLETON BEHAVIOR
# ============================================================================


class TestSingletonBehavior:
    """Tests for EventBus singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Test EventBus returns same instance on multiple calls."""
        # Arrange & Act
        bus1 = EventBus()
        bus2 = EventBus()

        # Assert
        assert bus1 is bus2

    def test_get_instance_returns_singleton(self):
        """Test get_instance() returns singleton."""
        # Arrange & Act
        bus1 = EventBus.get_instance()
        bus2 = EventBus()

        # Assert
        assert bus1 is bus2

    def test_singleton_thread_safe(self):
        """Test singleton creation is thread-safe."""
        # Arrange
        instances = []

        def create_instance():
            instances.append(EventBus())

        # Act
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        # All instances should be the same object
        assert all(inst is instances[0] for inst in instances)

    def test_singleton_initializes_once(self):
        """Test singleton initializes only once."""
        # Arrange & Act
        bus1 = EventBus()
        initial_stats = bus1.get_stats()

        bus2 = EventBus()

        # Assert
        assert bus1 is bus2
        # Stats should be same (not reset)
        assert bus2.get_stats() == initial_stats


# ============================================================================
# TEST INITIALIZATION
# ============================================================================


class TestInitialization:
    """Tests for EventBus initialization."""

    def test_init_sets_defaults(self, event_bus):
        """Test initialization sets default values."""
        # Arrange & Act (event_bus from fixture)

        # Assert
        assert event_bus._enabled is True
        assert event_bus._debug is False
        assert len(event_bus._event_filters) == 0
        assert event_bus._max_history_size == 100

    def test_init_creates_stats(self, event_bus):
        """Test initialization creates stats dictionary."""
        # Arrange & Act
        stats = event_bus.get_stats()

        # Assert
        assert stats["events_published"] == 0
        assert stats["events_filtered"] == 0
        assert stats["events_failed"] == 0
        assert stats["last_event_time"] is None

    def test_init_creates_emitter(self, event_bus):
        """Test initialization creates event emitter."""
        # Arrange & Act (event_bus from fixture)

        # Assert
        assert event_bus._emitter is not None
        assert hasattr(event_bus._emitter, 'emit')


# ============================================================================
# TEST ENABLE/DISABLE
# ============================================================================


class TestEnableDisable:
    """Tests for enable() and disable() methods."""

    def test_enable_sets_flag(self, event_bus):
        """Test enable() sets enabled flag to True."""
        # Arrange
        event_bus._enabled = False

        # Act
        event_bus.enable()

        # Assert
        assert event_bus._enabled is True

    def test_disable_sets_flag(self, event_bus):
        """Test disable() sets enabled flag to False."""
        # Arrange & Act
        event_bus.disable()

        # Assert
        assert event_bus._enabled is False

    def test_publish_when_disabled_returns_false(self, event_bus, sample_event_data):
        """Test publish returns False when bus is disabled."""
        # Arrange
        event_bus.disable()

        # Act
        result = event_bus.publish("test.event", sample_event_data)

        # Assert
        assert result is False

    def test_publish_when_enabled_returns_true(self, event_bus, sample_event_data):
        """Test publish returns True when bus is enabled."""
        # Arrange
        event_bus.enable()

        # Act
        result = event_bus.publish("test.event", sample_event_data)

        # Assert
        assert result is True


# ============================================================================
# TEST EVENT PUBLISHING
# ============================================================================


class TestEventPublishing:
    """Tests for publish() method."""

    def test_publish_increments_stats(self, event_bus, sample_event_data):
        """Test publish increments events_published stat."""
        # Arrange
        initial_count = event_bus.get_stats()["events_published"]

        # Act
        event_bus.publish("test.event", sample_event_data)

        # Assert
        assert event_bus.get_stats()["events_published"] == initial_count + 1

    def test_publish_sets_last_event_time(self, event_bus, sample_event_data):
        """Test publish sets last_event_time."""
        # Arrange & Act
        event_bus.publish("test.event", sample_event_data)

        # Assert
        assert event_bus.get_stats()["last_event_time"] is not None

    def test_publish_records_in_history(self, event_bus, sample_event_data):
        """Test publish records event in history."""
        # Arrange & Act
        event_bus.publish("test.event", sample_event_data)

        # Assert
        history = event_bus.get_recent_events(limit=1)
        assert len(history) == 1
        assert history[0]["type"] == "test.event"
        assert history[0]["data"] == sample_event_data

    def test_publish_calls_registered_handlers(self, event_bus, sample_event_data):
        """Test publish calls registered event handlers."""
        # Arrange
        handler = Mock()
        event_bus.on("test.event", handler)

        # Act
        event_bus.publish("test.event", sample_event_data)

        # Assert
        handler.assert_called_once_with(sample_event_data)

    def test_publish_calls_multiple_handlers(self, event_bus, sample_event_data):
        """Test publish calls all registered handlers."""
        # Arrange
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        event_bus.on("test.event", handler1)
        event_bus.on("test.event", handler2)
        event_bus.on("test.event", handler3)

        # Act
        event_bus.publish("test.event", sample_event_data)

        # Assert
        handler1.assert_called_once()
        handler2.assert_called_once()
        handler3.assert_called_once()

    def test_publish_with_different_event_types(self, event_bus):
        """Test publish handles different event types."""
        # Arrange
        handler1 = Mock()
        handler2 = Mock()
        event_bus.on("event.type1", handler1)
        event_bus.on("event.type2", handler2)

        # Act
        event_bus.publish("event.type1", {"data": "test1"})
        event_bus.publish("event.type2", {"data": "test2"})

        # Assert
        handler1.assert_called_once_with({"data": "test1"})
        handler2.assert_called_once_with({"data": "test2"})


# ============================================================================
# TEST ASYNC PUBLISHING
# ============================================================================


class TestAsyncPublishing:
    """Tests for publish_async() method."""

    @pytest.mark.asyncio
    async def test_publish_async_success(self, event_bus, sample_event_data):
        """Test async publish succeeds."""
        # Arrange & Act
        result = await event_bus.publish_async("test.event", sample_event_data)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_publish_async_increments_stats(self, event_bus, sample_event_data):
        """Test async publish increments stats."""
        # Arrange
        initial_count = event_bus.get_stats()["events_published"]

        # Act
        await event_bus.publish_async("test.event", sample_event_data)

        # Assert
        assert event_bus.get_stats()["events_published"] == initial_count + 1

    @pytest.mark.asyncio
    async def test_publish_async_calls_handlers(self, event_bus, sample_event_data):
        """Test async publish calls handlers."""
        # Arrange
        handler = Mock()
        event_bus.on("async.event", handler)

        # Act
        await event_bus.publish_async("async.event", sample_event_data)

        # Assert
        handler.assert_called_once()


# ============================================================================
# TEST EVENT SUBSCRIPTION
# ============================================================================


class TestEventSubscription:
    """Tests for on() and once() methods."""

    def test_on_registers_handler(self, event_bus):
        """Test on() registers event handler."""
        # Arrange
        handler = Mock()

        # Act
        event_bus.on("test.event", handler)
        event_bus.publish("test.event", {"data": "test"})

        # Assert
        handler.assert_called_once()

    def test_once_calls_handler_only_once(self, event_bus):
        """Test once() handler is called only once."""
        # Arrange
        handler = Mock()
        event_bus.once("test.event", handler)

        # Act
        event_bus.publish("test.event", {"data": "first"})
        event_bus.publish("test.event", {"data": "second"})

        # Assert
        handler.assert_called_once_with({"data": "first"})

    def test_on_supports_wildcard_patterns(self, event_bus):
        """Test on() supports wildcard event patterns."""
        # Arrange
        handler = Mock()
        event_bus.on("hook.*", handler)

        # Act
        event_bus.publish("hook.pre_tool", {"data": "test1"})
        event_bus.publish("hook.post_tool", {"data": "test2"})

        # Assert
        assert handler.call_count == 2
        # Wildcard handlers receive event_type and data
        handler.assert_any_call("hook.pre_tool", {"data": "test1"})
        handler.assert_any_call("hook.post_tool", {"data": "test2"})

    def test_remove_listener_removes_handler(self, event_bus):
        """Test remove_listener() removes specific handler."""
        # Arrange
        handler = Mock()
        event_bus.on("test.event", handler)

        # Act
        event_bus.remove_listener("test.event", handler)
        event_bus.publish("test.event", {"data": "test"})

        # Assert
        handler.assert_not_called()

    def test_remove_all_listeners_for_event(self, event_bus):
        """Test remove_all_listeners() removes all handlers for event."""
        # Arrange
        handler1 = Mock()
        handler2 = Mock()
        event_bus.on("test.event", handler1)
        event_bus.on("test.event", handler2)

        # Act
        event_bus.remove_all_listeners("test.event")
        event_bus.publish("test.event", {"data": "test"})

        # Assert
        handler1.assert_not_called()
        handler2.assert_not_called()

    def test_remove_all_listeners_removes_all(self, event_bus):
        """Test remove_all_listeners() without args removes all handlers."""
        # Arrange
        handler1 = Mock()
        handler2 = Mock()
        event_bus.on("event1", handler1)
        event_bus.on("event2", handler2)

        # Act
        event_bus.remove_all_listeners()
        event_bus.publish("event1", {"data": "test"})
        event_bus.publish("event2", {"data": "test"})

        # Assert
        handler1.assert_not_called()
        handler2.assert_not_called()


# ============================================================================
# TEST EVENT FILTERING
# ============================================================================


class TestEventFiltering:
    """Tests for event filtering functionality."""

    def test_add_filter_allows_matching_events(self, event_bus):
        """Test add_filter() allows matching events."""
        # Arrange
        event_bus.add_filter("allowed.event")

        # Act
        result = event_bus.publish("allowed.event", {"data": "test"})

        # Assert
        assert result is True

    def test_add_filter_blocks_non_matching_events(self, event_bus):
        """Test filters block non-matching events."""
        # Arrange
        event_bus.add_filter("allowed.event")

        # Act
        result = event_bus.publish("blocked.event", {"data": "test"})

        # Assert
        assert result is False

    def test_add_filter_supports_wildcards(self, event_bus):
        """Test filters support wildcard patterns."""
        # Arrange
        event_bus.add_filter("hook.*")

        # Act
        result1 = event_bus.publish("hook.pre_tool", {"data": "test"})
        result2 = event_bus.publish("hook.post_tool", {"data": "test"})
        result3 = event_bus.publish("other.event", {"data": "test"})

        # Assert
        assert result1 is True
        assert result2 is True
        assert result3 is False

    def test_remove_filter_removes_pattern(self, event_bus):
        """Test remove_filter() removes filter pattern."""
        # Arrange
        event_bus.add_filter("test.event")

        # Act
        event_bus.remove_filter("test.event")
        result = event_bus.publish("other.event", {"data": "test"})

        # Assert
        # No filters, so all events allowed
        assert result is True

    def test_clear_filters_removes_all(self, event_bus):
        """Test clear_filters() removes all filters."""
        # Arrange
        event_bus.add_filter("filter1.*")
        event_bus.add_filter("filter2.*")

        # Act
        event_bus.clear_filters()
        result = event_bus.publish("anything.event", {"data": "test"})

        # Assert
        assert result is True

    def test_filtered_events_increment_stats(self, event_bus):
        """Test filtered events increment filtered stat."""
        # Arrange
        event_bus.add_filter("allowed.event")
        initial_filtered = event_bus.get_stats()["events_filtered"]

        # Act
        event_bus.publish("blocked.event", {"data": "test"})

        # Assert
        assert event_bus.get_stats()["events_filtered"] == initial_filtered + 1


# ============================================================================
# TEST EVENT HISTORY
# ============================================================================


class TestEventHistory:
    """Tests for event history functionality."""

    def test_get_recent_events_returns_history(self, event_bus):
        """Test get_recent_events() returns event history."""
        # Arrange
        event_bus.publish("event1", {"data": "test1"})
        event_bus.publish("event2", {"data": "test2"})

        # Act
        history = event_bus.get_recent_events(limit=10)

        # Assert
        assert len(history) == 2
        assert history[0]["type"] == "event1"
        assert history[1]["type"] == "event2"

    def test_get_recent_events_respects_limit(self, event_bus):
        """Test get_recent_events() respects limit parameter."""
        # Arrange
        for i in range(10):
            event_bus.publish(f"event{i}", {"data": i})

        # Act
        history = event_bus.get_recent_events(limit=5)

        # Assert
        assert len(history) == 5
        # Should return most recent 5
        assert history[0]["type"] == "event5"
        assert history[4]["type"] == "event9"

    def test_history_limited_to_max_size(self, event_bus):
        """Test history is limited to max size."""
        # Arrange
        max_size = event_bus._max_history_size

        # Act
        for i in range(max_size + 50):
            event_bus.publish(f"event{i}", {"data": i})

        # Assert
        history = event_bus.get_recent_events(limit=max_size + 100)
        assert len(history) == max_size

    def test_clear_history_removes_all(self, event_bus):
        """Test clear_history() removes all history."""
        # Arrange
        event_bus.publish("event1", {"data": "test1"})
        event_bus.publish("event2", {"data": "test2"})

        # Act
        event_bus.clear_history()

        # Assert
        history = event_bus.get_recent_events()
        assert len(history) == 0


# ============================================================================
# TEST STATISTICS
# ============================================================================


class TestStatistics:
    """Tests for statistics tracking."""

    def test_get_stats_returns_all_metrics(self, event_bus):
        """Test get_stats() returns all metrics."""
        # Arrange & Act
        stats = event_bus.get_stats()

        # Assert
        assert "events_published" in stats
        assert "events_filtered" in stats
        assert "events_failed" in stats
        assert "last_event_time" in stats
        assert "enabled" in stats
        assert "filters_active" in stats
        assert "filter_count" in stats
        assert "history_size" in stats

    def test_reset_stats_clears_counters(self, event_bus):
        """Test reset_stats() clears all counters."""
        # Arrange
        event_bus.publish("event1", {"data": "test"})
        event_bus.publish("event2", {"data": "test"})

        # Act
        event_bus.reset_stats()

        # Assert
        stats = event_bus.get_stats()
        assert stats["events_published"] == 0
        assert stats["events_filtered"] == 0
        assert stats["events_failed"] == 0
        assert stats["last_event_time"] is None

    def test_stats_track_published_count(self, event_bus):
        """Test stats correctly track published event count."""
        # Arrange & Act
        for i in range(5):
            event_bus.publish(f"event{i}", {"data": i})

        # Assert
        assert event_bus.get_stats()["events_published"] == 5


# ============================================================================
# TEST DEBUG MODE
# ============================================================================


class TestDebugMode:
    """Tests for debug mode functionality."""

    def test_set_debug_enables_debug_logging(self, event_bus):
        """Test set_debug() enables debug logging."""
        # Arrange & Act
        event_bus.set_debug(True)

        # Assert
        assert event_bus._debug is True

    def test_set_debug_disables_debug_logging(self, event_bus):
        """Test set_debug(False) disables debug logging."""
        # Arrange
        event_bus.set_debug(True)

        # Act
        event_bus.set_debug(False)

        # Assert
        assert event_bus._debug is False


# ============================================================================
# TEST EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_publish_with_none_data(self, event_bus):
        """Test publish accepts None as event data."""
        # Arrange & Act
        result = event_bus.publish("test.event", None)

        # Assert
        assert result is True

    def test_publish_with_complex_data_types(self, event_bus):
        """Test publish handles complex data types."""
        # Arrange
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, 2),
            "set": {1, 2, 3},
        }

        # Act
        result = event_bus.publish("complex.event", complex_data)

        # Assert
        assert result is True

    def test_wildcard_handler_with_no_matching_events(self, event_bus):
        """Test wildcard handler with no matching events."""
        # Arrange
        handler = Mock()
        event_bus.on("hook.*", handler)

        # Act
        event_bus.publish("other.event", {"data": "test"})

        # Assert
        handler.assert_not_called()

    def test_concurrent_publishing(self, event_bus):
        """Test concurrent event publishing from multiple threads."""
        # Arrange
        published_count = [0]
        lock = threading.Lock()

        def publish_events():
            for i in range(10):
                if event_bus.publish(f"thread.event{i}", {"data": i}):
                    with lock:
                        published_count[0] += 1

        # Act
        threads = [threading.Thread(target=publish_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert published_count[0] == 50  # 5 threads * 10 events each


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_handler_exception_does_not_stop_other_handlers(self, event_bus):
        """Test exception in one handler doesn't stop others."""
        # Arrange
        def failing_handler(data):
            raise Exception("Handler error")

        handler1 = Mock()
        handler2 = Mock()

        event_bus.on("test.event", handler1)
        event_bus.on("test.event", failing_handler)
        event_bus.on("test.event", handler2)

        # Act
        event_bus.publish("test.event", {"data": "test"})

        # Assert
        # Both other handlers should still be called
        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_publish_with_empty_event_type(self, event_bus):
        """Test publish with empty event type."""
        # Arrange & Act
        result = event_bus.publish("", {"data": "test"})

        # Assert
        # Should still publish (no validation on event type)
        assert result is True
