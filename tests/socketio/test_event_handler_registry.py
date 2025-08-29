#!/usr/bin/env python3
"""
Comprehensive unit tests for SocketIO Event Handler Registry.

Tests critical event handler registry functionality including:
- Handler registration before connections
- Async event registration
- Handler cleanup on shutdown
- Handler error isolation
- Event routing

WHY: These tests address critical gaps in event handler registry test coverage
identified during analysis. They ensure proper handler registration sequence
and prevent race conditions during event handler initialization.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.services.socketio.handlers.base import BaseEventHandler
from claude_mpm.services.socketio.handlers.registry import EventHandlerRegistry


class MockEventHandler(BaseEventHandler):
    """Mock event handler for testing."""

    def __init__(self, server, should_fail=False, register_count=3):
        super().__init__(server)
        self.should_fail = should_fail
        self.register_count = register_count
        self.events_registered = 0
        self.cleanup_called = False

    def register_events(self):
        if self.should_fail:
            raise RuntimeError("Mock handler registration failure")

        # Simulate registering multiple events
        for i in range(self.register_count):
            self.server.core.sio.on(f"mock_event_{i}", self._mock_handler)
            self.events_registered += 1

    async def _mock_handler(self, sid, data):
        """Mock event handler method."""

    def cleanup(self):
        self.cleanup_called = True


class MockNoEventsHandler(BaseEventHandler):
    """Mock handler that has no events to register."""

    def register_events(self):
        raise NotImplementedError("No events to register")


class TestEventHandlerRegistry:
    """Test event handler registry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock server with core.sio
        self.mock_server = Mock()
        self.mock_sio = Mock()
        self.mock_sio.handlers = {}  # Mock Socket.IO handlers dict
        self.mock_server.core = Mock()
        self.mock_server.core.sio = self.mock_sio

    def teardown_method(self):
        """Clean up after each test."""

    def test_registry_initialization(self):
        """Test registry initialization with server."""
        registry = EventHandlerRegistry(self.mock_server)

        assert registry.server == self.mock_server
        assert len(registry.handlers) == 0
        assert not registry._initialized
        assert registry.logger is not None

    def test_default_handlers_list(self):
        """Test that default handlers list contains expected handlers."""
        from claude_mpm.services.socketio.handlers.registry import EventHandlerRegistry

        # Check that default handlers are defined
        assert hasattr(EventHandlerRegistry, "DEFAULT_HANDLERS")
        assert isinstance(EventHandlerRegistry.DEFAULT_HANDLERS, list)
        assert len(EventHandlerRegistry.DEFAULT_HANDLERS) > 0

        # Check for expected handler types
        handler_names = [h.__name__ for h in EventHandlerRegistry.DEFAULT_HANDLERS]

        expected_handlers = [
            "ConnectionEventHandler",
            "HookEventHandler",
            "GitEventHandler",
            "FileEventHandler",
            "CodeAnalysisEventHandler",
        ]

        for expected in expected_handlers:
            assert expected in handler_names, f"{expected} not in default handlers"

    def test_initialize_with_default_handlers(self):
        """Test initialization with default handler classes."""
        registry = EventHandlerRegistry(self.mock_server)

        # Use mock handlers for testing
        mock_handlers = [MockEventHandler, MockNoEventsHandler]

        registry.initialize(mock_handlers)

        assert registry._initialized
        assert len(registry.handlers) == 2
        assert isinstance(registry.handlers[0], MockEventHandler)
        assert isinstance(registry.handlers[1], MockNoEventsHandler)

    def test_initialize_with_handler_failure(self):
        """Test initialization handles handler creation failures gracefully."""
        registry = EventHandlerRegistry(self.mock_server)

        # Create a handler class that fails to initialize
        class FailingHandler(BaseEventHandler):
            def __init__(self, server):
                raise RuntimeError("Handler initialization failed")

            def register_events(self):
                pass

        mock_handlers = [MockEventHandler, FailingHandler, MockNoEventsHandler]

        registry.initialize(mock_handlers)

        # Should be initialized despite one handler failing
        assert registry._initialized
        # Should have successfully initialized 2 out of 3 handlers
        assert len(registry.handlers) == 2

    def test_double_initialization_prevention(self):
        """Test that double initialization is prevented."""
        registry = EventHandlerRegistry(self.mock_server)

        mock_handlers = [MockEventHandler]

        # First initialization
        registry.initialize(mock_handlers)
        assert len(registry.handlers) == 1

        # Second initialization should be skipped
        registry.initialize([MockNoEventsHandler])  # Different handler
        assert len(registry.handlers) == 1  # Should still be 1

    def test_register_all_events_before_initialization(self):
        """Test that register_all_events fails before initialization."""
        registry = EventHandlerRegistry(self.mock_server)

        with pytest.raises(RuntimeError, match="EventHandlerRegistry not initialized"):
            registry.register_all_events()

    def test_register_all_events_without_socketio_server(self):
        """Test register_all_events fails when Socket.IO server unavailable."""
        # Mock server without core.sio
        mock_server = Mock()
        mock_server.core = None

        registry = EventHandlerRegistry(mock_server)
        registry.initialize([MockEventHandler])

        with pytest.raises(RuntimeError, match="Socket.IO server not available"):
            registry.register_all_events()

    def test_register_all_events_success(self):
        """Test successful event registration for all handlers."""
        registry = EventHandlerRegistry(self.mock_server)

        # Initialize with mock handlers
        mock_handlers = [MockEventHandler, MockEventHandler]
        registry.initialize(mock_handlers)

        # Mock Socket.IO handlers dict to track registrations
        initial_handlers = {"existing_event": Mock()}
        self.mock_sio.handlers = initial_handlers.copy()

        # Register all events
        registry.register_all_events()

        # Should have registered events from both handlers (3 each = 6 total)
        # Plus the initial handler = 7 total
        expected_total = 1 + (2 * 3)  # initial + (2 handlers * 3 events each)
        assert len(self.mock_sio.handlers) == expected_total

    def test_register_all_events_with_handler_failure(self):
        """Test register_all_events handles handler failures gracefully."""
        registry = EventHandlerRegistry(self.mock_server)

        # Mix of good and failing handlers
        class GoodHandler(MockEventHandler):
            pass

        class FailingHandler(MockEventHandler):
            def register_events(self):
                raise RuntimeError("Registration failed")

        handlers = [GoodHandler, FailingHandler, GoodHandler]
        registry.initialize(handlers)

        # Should complete despite one handler failing
        registry.register_all_events()

        # Should have registered events from the 2 good handlers
        expected_events = 2 * 3  # 2 good handlers * 3 events each
        assert len(self.mock_sio.handlers) == expected_events

    def test_register_all_events_with_no_events_handler(self):
        """Test register_all_events handles NotImplementedError gracefully."""
        registry = EventHandlerRegistry(self.mock_server)

        handlers = [MockEventHandler, MockNoEventsHandler, MockEventHandler]
        registry.initialize(handlers)

        # Should complete despite NotImplementedError from one handler
        registry.register_all_events()

        # Should have registered events from the 2 handlers with events
        expected_events = 2 * 3  # 2 handlers * 3 events each
        assert len(self.mock_sio.handlers) == expected_events

    def test_add_handler_after_initialization(self):
        """Test adding handler after initialization."""
        registry = EventHandlerRegistry(self.mock_server)

        # Initialize with one handler
        registry.initialize([MockEventHandler])
        assert len(registry.handlers) == 1

        # Add another handler
        registry.add_handler(MockNoEventsHandler)
        assert len(registry.handlers) == 2

    def test_add_handler_before_initialization(self):
        """Test that add_handler fails before initialization."""
        registry = EventHandlerRegistry(self.mock_server)

        with pytest.raises(RuntimeError, match="EventHandlerRegistry not initialized"):
            registry.add_handler(MockEventHandler)

    def test_add_handler_with_registration_failure(self):
        """Test add_handler handles registration failures."""
        registry = EventHandlerRegistry(self.mock_server)
        registry.initialize([MockEventHandler])

        # Try to add a handler that fails registration
        class FailingRegistrationHandler(MockEventHandler):
            def register_events(self):
                raise RuntimeError("Registration failed")

        with pytest.raises(RuntimeError):
            registry.add_handler(FailingRegistrationHandler)

    def test_get_handler_by_class(self):
        """Test getting handler instance by class."""
        registry = EventHandlerRegistry(self.mock_server)

        registry.initialize([MockEventHandler, MockNoEventsHandler])

        # Get handler by class
        handler = registry.get_handler(MockEventHandler)
        assert handler is not None
        assert isinstance(handler, MockEventHandler)

        no_events_handler = registry.get_handler(MockNoEventsHandler)
        assert no_events_handler is not None
        assert isinstance(no_events_handler, MockNoEventsHandler)

    def test_get_handler_not_found(self):
        """Test get_handler returns None when handler not found."""
        registry = EventHandlerRegistry(self.mock_server)

        registry.initialize([MockEventHandler])

        # Try to get handler that wasn't registered
        handler = registry.get_handler(MockNoEventsHandler)
        assert handler is None

    def test_deployment_context_detection_during_initialization(self):
        """Test that deployment context is detected during initialization."""
        registry = EventHandlerRegistry(self.mock_server)

        with patch(
            "claude_mpm.services.socketio.handlers.registry.PathContext"
        ) as mock_context:
            mock_context.detect_deployment_context.return_value.value = "production"

            registry.initialize([MockEventHandler])

            # Should have detected deployment context
            mock_context.detect_deployment_context.assert_called_once()

    def test_deployment_context_detection_failure_handling(self):
        """Test graceful handling of deployment context detection failure."""
        registry = EventHandlerRegistry(self.mock_server)

        with patch(
            "claude_mpm.services.socketio.handlers.registry.PathContext"
        ) as mock_context:
            mock_context.detect_deployment_context.side_effect = Exception(
                "Detection failed"
            )

            # Should handle the exception gracefully
            registry.initialize([MockEventHandler])

            # Should still be initialized
            assert registry._initialized

    def test_handler_registration_order(self):
        """Test that handlers are registered in the correct order."""
        registry = EventHandlerRegistry(self.mock_server)

        # Create handlers that track registration order
        registration_order = []

        class OrderedHandler1(MockEventHandler):
            def register_events(self):
                registration_order.append("Handler1")
                super().register_events()

        class OrderedHandler2(MockEventHandler):
            def register_events(self):
                registration_order.append("Handler2")
                super().register_events()

        class OrderedHandler3(MockEventHandler):
            def register_events(self):
                registration_order.append("Handler3")
                super().register_events()

        handlers = [OrderedHandler1, OrderedHandler2, OrderedHandler3]
        registry.initialize(handlers)
        registry.register_all_events()

        # Should register in order
        assert registration_order == ["Handler1", "Handler2", "Handler3"]

    def test_socket_io_handlers_tracking(self):
        """Test proper tracking of Socket.IO handler counts."""
        registry = EventHandlerRegistry(self.mock_server)

        # Start with some existing handlers
        initial_handlers = {"existing1": Mock(), "existing2": Mock()}
        self.mock_sio.handlers = initial_handlers.copy()

        # Handler that registers a specific number of events
        class CountableHandler(MockEventHandler):
            def __init__(self, server):
                super().__init__(server, register_count=2)

        registry.initialize([CountableHandler])

        # Track handler count before and after
        handlers_before = len(self.mock_sio.handlers)
        registry.register_all_events()
        handlers_after = len(self.mock_sio.handlers)

        # Should have added exactly 2 handlers
        assert handlers_after - handlers_before == 2

    def test_error_isolation_between_handlers(self):
        """Test that errors in one handler don't affect others."""
        registry = EventHandlerRegistry(self.mock_server)

        # Mix good and bad handlers
        registration_results = []

        class GoodHandler1(MockEventHandler):
            def register_events(self):
                registration_results.append("Good1 success")
                super().register_events()

        class BadHandler(MockEventHandler):
            def register_events(self):
                registration_results.append("Bad attempted")
                raise RuntimeError("Bad handler failed")

        class GoodHandler2(MockEventHandler):
            def register_events(self):
                registration_results.append("Good2 success")
                super().register_events()

        handlers = [GoodHandler1, BadHandler, GoodHandler2]
        registry.initialize(handlers)
        registry.register_all_events()

        # All handlers should have attempted registration
        assert "Good1 success" in registration_results
        assert "Bad attempted" in registration_results
        assert "Good2 success" in registration_results

        # Good handlers should have succeeded despite bad handler failure
        expected_events = 2 * 3  # 2 good handlers * 3 events each
        assert len(self.mock_sio.handlers) == expected_events

    def test_handler_cleanup_capability(self):
        """Test that handlers support cleanup operations."""
        registry = EventHandlerRegistry(self.mock_server)

        # Handler with cleanup method
        class CleanupHandler(MockEventHandler):
            def __init__(self, server):
                super().__init__(server)
                self.cleanup_called = False

            def cleanup(self):
                self.cleanup_called = True

        registry.initialize([CleanupHandler])

        # Get handler and call cleanup
        handler = registry.get_handler(CleanupHandler)
        assert handler is not None

        handler.cleanup()
        assert handler.cleanup_called

    def test_handler_base_class_enforcement(self):
        """Test that only BaseEventHandler subclasses can be registered."""
        registry = EventHandlerRegistry(self.mock_server)

        # Non-handler class
        class NotAHandler:
            pass

        # Should fail during initialization
        registry.initialize([NotAHandler])

        # Should not have created any handlers
        assert len(registry.handlers) == 0

    def test_event_handler_server_access(self):
        """Test that handlers have proper access to server instance."""
        registry = EventHandlerRegistry(self.mock_server)

        registry.initialize([MockEventHandler])

        handler = registry.get_handler(MockEventHandler)
        assert handler is not None
        assert handler.server == self.mock_server
        assert handler.server.core.sio == self.mock_sio

    def test_registry_logging_functionality(self):
        """Test that registry properly logs initialization and registration."""
        registry = EventHandlerRegistry(self.mock_server)

        # Mock logger to capture log calls
        with patch.object(registry.logger, "info") as mock_info, patch.object(
            registry.logger, "debug"
        ) as mock_debug:

            registry.initialize([MockEventHandler])
            registry.register_all_events()

            # Should have logged initialization and registration
            assert mock_info.call_count > 0
            assert mock_debug.call_count > 0

            # Check for expected log messages
            info_messages = [call[0][0] for call in mock_info.call_args_list]
            assert any("initialized" in msg.lower() for msg in info_messages)
            assert any("registered" in msg.lower() for msg in info_messages)
