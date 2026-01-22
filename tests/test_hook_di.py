"""Unit tests for the DI (Dependency Injection) infrastructure in hook handler.

Tests cover:
- HookServiceContainer singleton pattern, thread safety, lazy initialization
- Service override mechanism for testing
- Protocol implementations and runtime_checkable behavior
- Integration with ClaudeHookHandler and EventHandlers
- Backward compatibility when container is not provided

WHY these tests matter:
- DI container is core infrastructure that all hook handlers depend on
- Thread safety is critical in async hook handling scenarios
- Override mechanism enables proper unit testing of dependent components
- Protocol compliance ensures substitutability of implementations
"""

import threading
import unittest
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from claude_mpm.hooks.claude_hooks.services.container import (
    HookServiceContainer,
    get_container,
)
from claude_mpm.hooks.claude_hooks.services.protocols import (
    IAutoPauseHandler,
    IConnectionManager,
    IDuplicateDetector,
    IEventHandlers,
    IMemoryHookManager,
    IResponseTrackingManager,
    IStateManager,
    ISubagentProcessor,
)

# =============================================================================
# Mock Implementations of Protocols
# =============================================================================


class MockStateManager:
    """Mock implementation of IStateManager for testing."""

    def __init__(self) -> None:
        self.active_delegations: dict = {}
        self.delegation_history: list = []
        self.delegation_requests: dict = {}
        self.pending_prompts: dict = {}
        self.events_processed: int = 0
        self._track_delegation_calls: list = []
        self._cleanup_calls: int = 0

    def track_delegation(
        self, session_id: str, agent_type: str, request_data: Optional[dict] = None
    ) -> None:
        self._track_delegation_calls.append(
            {
                "session_id": session_id,
                "agent_type": agent_type,
                "request_data": request_data,
            }
        )
        self.active_delegations[session_id] = agent_type

    def get_delegation_agent_type(self, session_id: str) -> str:
        return self.active_delegations.get(session_id, "unknown")

    def cleanup_old_entries(self) -> None:
        self._cleanup_calls += 1

    def get_git_branch(self, working_dir: Optional[str] = None) -> str:
        return "mock-branch"

    def find_matching_request(self, session_id: str) -> Optional[dict]:
        return self.delegation_requests.get(session_id)

    def remove_request(self, session_id: str) -> None:
        self.delegation_requests.pop(session_id, None)

    def increment_events_processed(self) -> bool:
        self.events_processed += 1
        return self.events_processed % 100 == 0


class MockConnectionManager:
    """Mock implementation of IConnectionManager for testing."""

    def __init__(self) -> None:
        self.emitted_events: list = []
        self._cleanup_called: bool = False

    def emit_event(self, namespace: str, event: str, data: dict) -> None:
        self.emitted_events.append(
            {"namespace": namespace, "event": event, "data": data}
        )

    def cleanup(self) -> None:
        self._cleanup_called = True


class MockDuplicateDetector:
    """Mock implementation of IDuplicateDetector for testing."""

    def __init__(self) -> None:
        self._duplicates: set = set()
        self._checked_events: list = []

    def is_duplicate(self, event: dict) -> bool:
        key = self.generate_event_key(event)
        self._checked_events.append(event)
        return key in self._duplicates

    def generate_event_key(self, event: dict) -> str:
        return f"{event.get('type', '')}:{event.get('session_id', '')}"

    def mark_as_duplicate(self, event: dict) -> None:
        """Test helper to mark an event as duplicate."""
        key = self.generate_event_key(event)
        self._duplicates.add(key)


class MockResponseTrackingManager:
    """Mock implementation of IResponseTrackingManager for testing."""

    def __init__(self) -> None:
        self.response_tracking_enabled: bool = True
        self.response_tracker: Optional[Any] = None
        self.track_all_interactions: bool = False
        self.auto_pause_handler: Optional[Any] = None
        self._tracked_responses: list = []

    def track_agent_response(
        self,
        session_id: str,
        agent_type: str,
        event: dict,
        delegation_requests: dict,
    ) -> None:
        self._tracked_responses.append(
            {
                "type": "agent",
                "session_id": session_id,
                "agent_type": agent_type,
                "event": event,
            }
        )

    def track_stop_response(
        self,
        event: dict,
        session_id: str,
        metadata: dict,
        pending_prompts: dict,
    ) -> None:
        self._tracked_responses.append(
            {
                "type": "stop",
                "session_id": session_id,
                "event": event,
                "metadata": metadata,
            }
        )

    def track_assistant_response(
        self,
        event: dict,
        pending_prompts: dict,
    ) -> None:
        self._tracked_responses.append({"type": "assistant", "event": event})


class MockMemoryHookManager:
    """Mock implementation of IMemoryHookManager for testing."""

    def __init__(self) -> None:
        self._pre_hooks: list = []
        self._post_hooks: list = []

    def trigger_pre_delegation_hook(
        self, agent_type: str, tool_input: dict, session_id: str
    ) -> None:
        self._pre_hooks.append(
            {
                "agent_type": agent_type,
                "tool_input": tool_input,
                "session_id": session_id,
            }
        )

    def trigger_post_delegation_hook(
        self, agent_type: str, event: dict, session_id: str
    ) -> None:
        self._post_hooks.append(
            {"agent_type": agent_type, "event": event, "session_id": session_id}
        )


class MockSubagentProcessor:
    """Mock implementation of ISubagentProcessor for testing."""

    def __init__(self) -> None:
        self._processed_events: list = []

    def process_subagent_stop(self, event: dict) -> None:
        self._processed_events.append(event)


class MockAutoPauseHandler:
    """Mock implementation of IAutoPauseHandler for testing."""

    def __init__(self) -> None:
        self._pause_active: bool = False
        self._user_messages: list = []
        self._tool_calls: list = []
        self._assistant_responses: list = []
        self._usage_updates: list = []

    def is_pause_active(self) -> bool:
        return self._pause_active

    def on_user_message(self, message: str) -> None:
        self._user_messages.append(message)

    def on_tool_call(self, tool_name: str, tool_input: dict) -> None:
        self._tool_calls.append({"tool_name": tool_name, "tool_input": tool_input})

    def on_assistant_response(self, response: str) -> None:
        self._assistant_responses.append(response)

    def on_usage_update(self, usage: dict) -> Optional[str]:
        self._usage_updates.append(usage)
        return None

    def emit_threshold_warning(self, threshold: str) -> str:
        return f"Warning: {threshold} threshold reached"

    def on_session_end(self) -> Optional[Any]:
        return None


class MockEventHandlers:
    """Mock implementation of IEventHandlers for testing."""

    def __init__(self) -> None:
        self._handled_events: dict = {
            "user_prompt": [],
            "pre_tool": [],
            "post_tool": [],
            "notification": [],
            "stop": [],
            "subagent_stop": [],
            "subagent_start": [],
            "session_start": [],
            "assistant_response": [],
        }

    def handle_user_prompt_fast(self, event: dict) -> None:
        self._handled_events["user_prompt"].append(event)

    def handle_pre_tool_fast(self, event: dict) -> Optional[dict]:
        self._handled_events["pre_tool"].append(event)
        return None

    def handle_post_tool_fast(self, event: dict) -> None:
        self._handled_events["post_tool"].append(event)

    def handle_notification_fast(self, event: dict) -> None:
        self._handled_events["notification"].append(event)

    def handle_stop_fast(self, event: dict) -> None:
        self._handled_events["stop"].append(event)

    def handle_subagent_stop_fast(self, event: dict) -> None:
        self._handled_events["subagent_stop"].append(event)

    def handle_subagent_start_fast(self, event: dict) -> None:
        self._handled_events["subagent_start"].append(event)

    def handle_session_start_fast(self, event: dict) -> None:
        self._handled_events["session_start"].append(event)

    def handle_assistant_response(self, event: dict) -> None:
        self._handled_events["assistant_response"].append(event)


# =============================================================================
# Container Tests
# =============================================================================


class TestHookServiceContainerSingleton(unittest.TestCase):
    """Tests for HookServiceContainer singleton pattern."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_singleton_pattern_same_instance(self) -> None:
        """Two calls to get_container should return the same instance."""
        container1 = get_container()
        container2 = get_container()
        self.assertIs(container1, container2)

    def test_singleton_pattern_direct_instantiation(self) -> None:
        """Direct instantiation should also return singleton."""
        container1 = HookServiceContainer()
        container2 = HookServiceContainer()
        self.assertIs(container1, container2)

    def test_singleton_pattern_mixed_access(self) -> None:
        """get_container and direct instantiation should return same instance."""
        container1 = get_container()
        container2 = HookServiceContainer()
        container3 = get_container()
        self.assertIs(container1, container2)
        self.assertIs(container2, container3)

    def test_reset_singleton_creates_new_instance(self) -> None:
        """reset_singleton should allow a new instance to be created."""
        container1 = get_container()
        HookServiceContainer.reset_singleton()
        container2 = get_container()
        self.assertIsNot(container1, container2)


class TestHookServiceContainerThreadSafety(unittest.TestCase):
    """Tests for HookServiceContainer thread safety."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_concurrent_get_container_returns_same_instance(self) -> None:
        """Concurrent calls to get_container should return the same instance."""
        results: list = []
        errors: list = []

        def get_container_thread() -> None:
            try:
                container = get_container()
                results.append(container)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_container_thread) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)

        # All instances should be the same
        first = results[0]
        for container in results[1:]:
            self.assertIs(container, first)

    def test_concurrent_service_access_thread_safe(self) -> None:
        """Concurrent service access should be thread-safe."""
        container = get_container()
        results: list = []
        errors: list = []

        def access_service() -> None:
            try:
                # Access different services concurrently
                sm = container.get_state_manager()
                dd = container.get_duplicate_detector()
                results.append((sm, dd))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_service) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)

        # All should get the same service instances
        first_sm, first_dd = results[0]
        for sm, dd in results[1:]:
            self.assertIs(sm, first_sm)
            self.assertIs(dd, first_dd)


class TestHookServiceContainerLazyInitialization(unittest.TestCase):
    """Tests for HookServiceContainer lazy initialization."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_services_not_created_until_accessed(self) -> None:
        """Services should not be instantiated until first access."""
        container = get_container()

        # Internal state should be None before access
        self.assertIsNone(container._state_manager)
        self.assertIsNone(container._duplicate_detector)
        self.assertIsNone(container._connection_manager)

    def test_state_manager_created_on_first_access(self) -> None:
        """StateManager should be created on first get_state_manager call."""
        container = get_container()
        self.assertIsNone(container._state_manager)

        sm = container.get_state_manager()

        self.assertIsNotNone(sm)
        self.assertIsNotNone(container._state_manager)
        self.assertIs(sm, container._state_manager)

    def test_same_service_returned_on_subsequent_access(self) -> None:
        """Same service instance should be returned on subsequent calls."""
        container = get_container()

        sm1 = container.get_state_manager()
        sm2 = container.get_state_manager()

        self.assertIs(sm1, sm2)

    def test_duplicate_detector_lazy_init(self) -> None:
        """DuplicateDetector should be lazily initialized."""
        container = get_container()
        self.assertIsNone(container._duplicate_detector)

        dd = container.get_duplicate_detector()

        self.assertIsNotNone(dd)
        self.assertIs(dd, container.get_duplicate_detector())

    def test_connection_manager_lazy_init(self) -> None:
        """ConnectionManager should be lazily initialized."""
        container = get_container()
        self.assertIsNone(container._connection_manager)

        cm = container.get_connection_manager()

        self.assertIsNotNone(cm)
        self.assertIs(cm, container.get_connection_manager())


class TestHookServiceContainerOverrides(unittest.TestCase):
    """Tests for HookServiceContainer service override mechanism."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_override_state_manager(self) -> None:
        """Overriding state manager should return the mock."""
        container = get_container()
        mock_sm = MockStateManager()

        container.override_state_manager(mock_sm)
        result = container.get_state_manager()

        self.assertIs(result, mock_sm)

    def test_override_connection_manager(self) -> None:
        """Overriding connection manager should return the mock."""
        container = get_container()
        mock_cm = MockConnectionManager()

        container.override_connection_manager(mock_cm)
        result = container.get_connection_manager()

        self.assertIs(result, mock_cm)

    def test_override_duplicate_detector(self) -> None:
        """Overriding duplicate detector should return the mock."""
        container = get_container()
        mock_dd = MockDuplicateDetector()

        container.override_duplicate_detector(mock_dd)
        result = container.get_duplicate_detector()

        self.assertIs(result, mock_dd)

    def test_override_response_tracking_manager(self) -> None:
        """Overriding response tracking manager should return the mock."""
        container = get_container()
        mock_rtm = MockResponseTrackingManager()

        container.override_response_tracking_manager(mock_rtm)
        result = container.get_response_tracking_manager()

        self.assertIs(result, mock_rtm)

    def test_override_memory_hook_manager(self) -> None:
        """Overriding memory hook manager should return the mock."""
        container = get_container()
        mock_mhm = MockMemoryHookManager()

        container.override_memory_hook_manager(mock_mhm)
        result = container.get_memory_hook_manager()

        self.assertIs(result, mock_mhm)

    def test_override_subagent_processor(self) -> None:
        """Overriding subagent processor should return the mock."""
        container = get_container()
        mock_sp = MockSubagentProcessor()

        container.override_subagent_processor(mock_sp)
        result = container.get_subagent_processor()

        self.assertIs(result, mock_sp)

    def test_override_auto_pause_handler(self) -> None:
        """Overriding auto-pause handler should return the mock."""
        container = get_container()
        mock_aph = MockAutoPauseHandler()

        container.override_auto_pause_handler(mock_aph)
        result = container.get_auto_pause_handler()

        self.assertIs(result, mock_aph)

    def test_override_event_handlers(self) -> None:
        """Overriding event handlers should return the mock."""
        container = get_container()
        mock_eh = MockEventHandlers()

        container.override_event_handlers(mock_eh)
        result = container.get_event_handlers(hook_handler=MagicMock())

        self.assertIs(result, mock_eh)

    def test_override_prevents_lazy_init(self) -> None:
        """Override should be returned without triggering lazy init."""
        container = get_container()
        mock_sm = MockStateManager()

        container.override_state_manager(mock_sm)

        # Internal _state_manager should still be None
        self.assertIsNone(container._state_manager)

        # But get_state_manager returns the override
        result = container.get_state_manager()
        self.assertIs(result, mock_sm)

        # And _state_manager is still None (no lazy init occurred)
        self.assertIsNone(container._state_manager)


class TestHookServiceContainerResetMethods(unittest.TestCase):
    """Tests for HookServiceContainer reset methods."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_reset_overrides_clears_overrides(self) -> None:
        """reset_overrides should clear all service overrides."""
        container = get_container()
        mock_sm = MockStateManager()
        mock_cm = MockConnectionManager()

        container.override_state_manager(mock_sm)
        container.override_connection_manager(mock_cm)

        # Verify overrides are active
        self.assertIs(container.get_state_manager(), mock_sm)

        container.reset_overrides()

        # After reset, should get real services (not mocks)
        new_sm = container.get_state_manager()
        self.assertIsNot(new_sm, mock_sm)

    def test_reset_overrides_preserves_cached_services(self) -> None:
        """reset_overrides should preserve already-initialized services."""
        container = get_container()

        # Initialize a service
        sm1 = container.get_state_manager()

        # Add an override for a different service
        mock_cm = MockConnectionManager()
        container.override_connection_manager(mock_cm)

        container.reset_overrides()

        # Original service should still be cached
        sm2 = container.get_state_manager()
        self.assertIs(sm1, sm2)

    def test_reset_all_clears_services_and_overrides(self) -> None:
        """reset_all should clear both services and overrides."""
        container = get_container()

        # Initialize services and add overrides
        container.get_state_manager()
        mock_cm = MockConnectionManager()
        container.override_connection_manager(mock_cm)

        container.reset_all()

        # All internal state should be None
        self.assertIsNone(container._state_manager)
        self.assertIsNone(container._connection_manager)
        self.assertEqual(len(container._overrides), 0)

    def test_reset_singleton_allows_new_instance(self) -> None:
        """reset_singleton should allow creating a completely new container."""
        container1 = get_container()
        container1.get_state_manager()

        HookServiceContainer.reset_singleton()

        container2 = get_container()

        self.assertIsNot(container1, container2)
        # New container should have clean state
        self.assertIsNone(container2._state_manager)


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestProtocolCompliance(unittest.TestCase):
    """Tests that mock implementations satisfy protocol interfaces."""

    def test_mock_state_manager_satisfies_protocol(self) -> None:
        """MockStateManager should be recognized as IStateManager."""
        mock = MockStateManager()
        self.assertIsInstance(mock, IStateManager)

    def test_mock_connection_manager_satisfies_protocol(self) -> None:
        """MockConnectionManager should be recognized as IConnectionManager."""
        mock = MockConnectionManager()
        self.assertIsInstance(mock, IConnectionManager)

    def test_mock_duplicate_detector_satisfies_protocol(self) -> None:
        """MockDuplicateDetector should be recognized as IDuplicateDetector."""
        mock = MockDuplicateDetector()
        self.assertIsInstance(mock, IDuplicateDetector)

    def test_mock_response_tracking_manager_satisfies_protocol(self) -> None:
        """MockResponseTrackingManager should be recognized as IResponseTrackingManager."""
        mock = MockResponseTrackingManager()
        self.assertIsInstance(mock, IResponseTrackingManager)

    def test_mock_memory_hook_manager_satisfies_protocol(self) -> None:
        """MockMemoryHookManager should be recognized as IMemoryHookManager."""
        mock = MockMemoryHookManager()
        self.assertIsInstance(mock, IMemoryHookManager)

    def test_mock_subagent_processor_satisfies_protocol(self) -> None:
        """MockSubagentProcessor should be recognized as ISubagentProcessor."""
        mock = MockSubagentProcessor()
        self.assertIsInstance(mock, ISubagentProcessor)

    def test_mock_auto_pause_handler_satisfies_protocol(self) -> None:
        """MockAutoPauseHandler should be recognized as IAutoPauseHandler."""
        mock = MockAutoPauseHandler()
        self.assertIsInstance(mock, IAutoPauseHandler)

    def test_mock_event_handlers_satisfies_protocol(self) -> None:
        """MockEventHandlers should be recognized as IEventHandlers."""
        mock = MockEventHandlers()
        self.assertIsInstance(mock, IEventHandlers)


# =============================================================================
# Integration Tests
# =============================================================================


class TestClaudeHookHandlerIntegration(unittest.TestCase):
    """Integration tests for ClaudeHookHandler with DI container."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    @patch("claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.AutoPauseHandler")
    def test_handler_accepts_container_parameter(
        self,
        mock_aph_class: MagicMock,
        mock_mhm_class: MagicMock,
        mock_rtm_class: MagicMock,
        mock_eh_class: MagicMock,
    ) -> None:
        """ClaudeHookHandler should accept a container parameter."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        container = get_container()
        handler = ClaudeHookHandler(container=container)

        self.assertIsNotNone(handler)
        self.assertIs(handler._container, container)

    @patch("claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.AutoPauseHandler")
    def test_handler_uses_container_services(
        self,
        mock_aph_class: MagicMock,
        mock_mhm_class: MagicMock,
        mock_rtm_class: MagicMock,
        mock_eh_class: MagicMock,
    ) -> None:
        """ClaudeHookHandler should get services from provided container."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        container = get_container()

        # Override with mocks
        mock_sm = MockStateManager()
        mock_dd = MockDuplicateDetector()
        mock_cm = MockConnectionManager()

        container.override_state_manager(mock_sm)
        container.override_duplicate_detector(mock_dd)
        container.override_connection_manager(mock_cm)

        handler = ClaudeHookHandler(container=container)

        # Handler should use our mocks
        self.assertIs(handler.state_manager, mock_sm)
        self.assertIs(handler.duplicate_detector, mock_dd)
        self.assertIs(handler.connection_manager, mock_cm)

    @patch("claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.AutoPauseHandler")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.StateManagerService")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ConnectionManagerService")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.DuplicateEventDetector")
    def test_handler_backward_compatible_without_container(
        self,
        mock_ded_class: MagicMock,
        mock_cms_class: MagicMock,
        mock_sms_class: MagicMock,
        mock_aph_class: MagicMock,
        mock_mhm_class: MagicMock,
        mock_rtm_class: MagicMock,
        mock_eh_class: MagicMock,
    ) -> None:
        """ClaudeHookHandler should work without container (backward compatible)."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        # Create handler without container
        handler = ClaudeHookHandler()

        self.assertIsNotNone(handler)
        # Container should be None in backward compatible mode
        self.assertIsNone(handler._container)
        # Services should be created directly
        mock_sms_class.assert_called()
        mock_cms_class.assert_called()
        mock_ded_class.assert_called()


class TestEventHandlersIntegration(unittest.TestCase):
    """Integration tests for EventHandlers with dependency injection."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_event_handlers_accepts_injected_dependencies(self) -> None:
        """EventHandlers should accept optional injected dependencies."""
        from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        mock_hook_handler = MagicMock()
        mock_hook_handler.state_manager = MockStateManager()
        mock_hook_handler.connection_manager = MockConnectionManager()
        mock_hook_handler.duplicate_detector = MockDuplicateDetector()
        mock_hook_handler.response_tracking_manager = MockResponseTrackingManager()
        mock_hook_handler.memory_hook_manager = MockMemoryHookManager()

        # Create with injected dependencies
        mock_log_manager = MagicMock()
        mock_config = MagicMock()
        mock_delegation_detector = MagicMock()
        mock_event_log = MagicMock()

        handlers = EventHandlers(
            mock_hook_handler,
            log_manager=mock_log_manager,
            config=mock_config,
            delegation_detector=mock_delegation_detector,
            event_log=mock_event_log,
        )

        # Verify injected dependencies are used
        self.assertIs(handlers._log_manager, mock_log_manager)
        self.assertIs(handlers._config, mock_config)
        self.assertIs(handlers._delegation_detector, mock_delegation_detector)
        self.assertIs(handlers._event_log, mock_event_log)

    def test_event_handlers_works_without_injected_dependencies(self) -> None:
        """EventHandlers should work without optional injected dependencies."""
        from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers

        mock_hook_handler = MagicMock()
        mock_hook_handler.state_manager = MockStateManager()
        mock_hook_handler.connection_manager = MockConnectionManager()
        mock_hook_handler.duplicate_detector = MockDuplicateDetector()
        mock_hook_handler.response_tracking_manager = MockResponseTrackingManager()
        mock_hook_handler.memory_hook_manager = MockMemoryHookManager()

        # Create without injected dependencies
        handlers = EventHandlers(mock_hook_handler)

        self.assertIsNotNone(handlers)
        # Internal references should be None (will use lazy loading)
        self.assertIsNone(handlers._log_manager)
        self.assertIsNone(handlers._config)


# =============================================================================
# Mock Usage Tests
# =============================================================================


class TestMockServiceUsage(unittest.TestCase):
    """Tests that mocked services are actually used by the handler."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    @patch("claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.AutoPauseHandler")
    def test_mocked_state_manager_tracks_delegation(
        self,
        mock_aph_class: MagicMock,
        mock_mhm_class: MagicMock,
        mock_rtm_class: MagicMock,
        mock_eh_class: MagicMock,
    ) -> None:
        """Mocked StateManager should receive track_delegation calls."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        container = get_container()
        mock_sm = MockStateManager()
        container.override_state_manager(mock_sm)

        handler = ClaudeHookHandler(container=container)

        # Simulate delegation tracking
        handler.state_manager.track_delegation("session-123", "engineer")

        self.assertEqual(len(mock_sm._track_delegation_calls), 1)
        self.assertEqual(
            mock_sm._track_delegation_calls[0]["session_id"], "session-123"
        )
        self.assertEqual(mock_sm._track_delegation_calls[0]["agent_type"], "engineer")

    @patch("claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.AutoPauseHandler")
    def test_mocked_connection_manager_emits_events(
        self,
        mock_aph_class: MagicMock,
        mock_mhm_class: MagicMock,
        mock_rtm_class: MagicMock,
        mock_eh_class: MagicMock,
    ) -> None:
        """Mocked ConnectionManager should receive emit_event calls."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        container = get_container()
        mock_cm = MockConnectionManager()
        container.override_connection_manager(mock_cm)

        handler = ClaudeHookHandler(container=container)

        # Simulate event emission
        handler.connection_manager.emit_event("/mpm", "test_event", {"key": "value"})

        self.assertEqual(len(mock_cm.emitted_events), 1)
        self.assertEqual(mock_cm.emitted_events[0]["namespace"], "/mpm")
        self.assertEqual(mock_cm.emitted_events[0]["event"], "test_event")

    @patch("claude_mpm.hooks.claude_hooks.hook_handler.EventHandlers")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.ResponseTrackingManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.MemoryHookManager")
    @patch("claude_mpm.hooks.claude_hooks.hook_handler.AutoPauseHandler")
    def test_mocked_duplicate_detector_checks_events(
        self,
        mock_aph_class: MagicMock,
        mock_mhm_class: MagicMock,
        mock_rtm_class: MagicMock,
        mock_eh_class: MagicMock,
    ) -> None:
        """Mocked DuplicateDetector should receive is_duplicate calls."""
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        container = get_container()
        mock_dd = MockDuplicateDetector()
        container.override_duplicate_detector(mock_dd)

        handler = ClaudeHookHandler(container=container)

        # Simulate duplicate check
        event = {"type": "test", "session_id": "123"}
        is_dup = handler.duplicate_detector.is_duplicate(event)

        self.assertFalse(is_dup)
        self.assertEqual(len(mock_dd._checked_events), 1)

        # Mark as duplicate and check again
        mock_dd.mark_as_duplicate(event)
        is_dup = handler.duplicate_detector.is_duplicate(event)

        self.assertTrue(is_dup)


class TestNoRuntimeImportsWithMocks(unittest.TestCase):
    """Tests that no runtime imports occur when using mocked services."""

    def setUp(self) -> None:
        """Reset singleton before each test."""
        HookServiceContainer.reset_singleton()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        HookServiceContainer.reset_singleton()

    def test_overridden_services_prevent_imports(self) -> None:
        """When services are overridden, their implementation modules should not be imported."""
        container = get_container()

        # Override all services with mocks
        container.override_state_manager(MockStateManager())
        container.override_connection_manager(MockConnectionManager())
        container.override_duplicate_detector(MockDuplicateDetector())
        container.override_response_tracking_manager(MockResponseTrackingManager())
        container.override_memory_hook_manager(MockMemoryHookManager())
        container.override_subagent_processor(MockSubagentProcessor())
        container.override_auto_pause_handler(MockAutoPauseHandler())
        container.override_event_handlers(MockEventHandlers())

        # Access all services
        sm = container.get_state_manager()
        cm = container.get_connection_manager()
        dd = container.get_duplicate_detector()
        rtm = container.get_response_tracking_manager()
        mhm = container.get_memory_hook_manager()
        sp = container.get_subagent_processor()
        aph = container.get_auto_pause_handler()
        eh = container.get_event_handlers(hook_handler=MagicMock())

        # Verify we got our mocks
        self.assertIsInstance(sm, MockStateManager)
        self.assertIsInstance(cm, MockConnectionManager)
        self.assertIsInstance(dd, MockDuplicateDetector)
        self.assertIsInstance(rtm, MockResponseTrackingManager)
        self.assertIsInstance(mhm, MockMemoryHookManager)
        self.assertIsInstance(sp, MockSubagentProcessor)
        self.assertIsInstance(aph, MockAutoPauseHandler)
        self.assertIsInstance(eh, MockEventHandlers)

        # Verify internal state is still None (no lazy init occurred)
        self.assertIsNone(container._state_manager)
        self.assertIsNone(container._connection_manager)
        self.assertIsNone(container._duplicate_detector)
        self.assertIsNone(container._response_tracking_manager)
        self.assertIsNone(container._memory_hook_manager)
        self.assertIsNone(container._subagent_processor)
        self.assertIsNone(container._auto_pause_handler)
        self.assertIsNone(container._event_handlers)


if __name__ == "__main__":
    unittest.main()
