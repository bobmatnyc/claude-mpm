"""Dependency Injection container for hook handler services.

This module provides a DI container that manages service instantiation,
lazy initialization, and service overriding for testing.

WHY DI Container:
- Centralized service management
- Lazy initialization reduces startup overhead
- Easy testing through service overriding
- Clear dependency graph
- Thread-safe singleton pattern
"""

import threading
from typing import Any, Optional, TypeVar

# Import service protocols for type hints
from .protocols import (
    IAutoPauseHandler,
    IConnectionManager,
    IDuplicateDetector,
    IEventHandlers,
    IMemoryHookManager,
    IResponseTrackingManager,
    IStateManager,
    ISubagentProcessor,
)

T = TypeVar("T")


class HookServiceContainer:
    """Dependency injection container for hook handler services.

    Features:
    - Lazy initialization of services
    - Thread-safe singleton pattern
    - Service overriding for testing
    - Automatic dependency resolution

    Usage:
        # Normal usage (services created lazily)
        container = HookServiceContainer()
        state_manager = container.get_state_manager()

        # Testing usage (override services)
        container = HookServiceContainer()
        container.override_state_manager(mock_state_manager)
        state_manager = container.get_state_manager()  # Returns mock

        # Reset overrides
        container.reset_overrides()
    """

    # Thread-safe singleton
    _instance: Optional["HookServiceContainer"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "HookServiceContainer":
        """Thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize container if not already initialized."""
        if getattr(self, "_initialized", False):
            return

        # Service instances (lazily initialized)
        self._state_manager: Optional[IStateManager] = None
        self._connection_manager: Optional[IConnectionManager] = None
        self._duplicate_detector: Optional[IDuplicateDetector] = None
        self._response_tracking_manager: Optional[IResponseTrackingManager] = None
        self._memory_hook_manager: Optional[IMemoryHookManager] = None
        self._subagent_processor: Optional[ISubagentProcessor] = None
        self._auto_pause_handler: Optional[IAutoPauseHandler] = None
        self._event_handlers: Optional[IEventHandlers] = None

        # Override factories for testing
        self._overrides: dict[str, Any] = {}

        # Lock for lazy initialization
        self._init_lock = threading.Lock()

        self._initialized = True

    # =========================================================================
    # Lazy Service Getters
    # =========================================================================

    def get_state_manager(self) -> IStateManager:
        """Get or create StateManagerService instance."""
        if "state_manager" in self._overrides:
            return self._overrides["state_manager"]

        if self._state_manager is None:
            with self._init_lock:
                if self._state_manager is None:
                    from claude_mpm.hooks.claude_hooks.services.state_manager import (
                        StateManagerService,
                    )

                    self._state_manager = StateManagerService()
        return self._state_manager

    def get_connection_manager(self) -> IConnectionManager:
        """Get or create ConnectionManagerService instance."""
        if "connection_manager" in self._overrides:
            return self._overrides["connection_manager"]

        if self._connection_manager is None:
            with self._init_lock:
                if self._connection_manager is None:
                    from claude_mpm.hooks.claude_hooks.services.connection_manager_http import (
                        ConnectionManagerService,
                    )

                    self._connection_manager = ConnectionManagerService()
        return self._connection_manager

    def get_duplicate_detector(self) -> IDuplicateDetector:
        """Get or create DuplicateEventDetector instance."""
        if "duplicate_detector" in self._overrides:
            return self._overrides["duplicate_detector"]

        if self._duplicate_detector is None:
            with self._init_lock:
                if self._duplicate_detector is None:
                    from claude_mpm.hooks.claude_hooks.services.duplicate_detector import (
                        DuplicateEventDetector,
                    )

                    self._duplicate_detector = DuplicateEventDetector()
        return self._duplicate_detector

    def get_response_tracking_manager(self) -> IResponseTrackingManager:
        """Get or create ResponseTrackingManager instance."""
        if "response_tracking_manager" in self._overrides:
            return self._overrides["response_tracking_manager"]

        if self._response_tracking_manager is None:
            with self._init_lock:
                if self._response_tracking_manager is None:
                    from claude_mpm.hooks.claude_hooks.response_tracking import (
                        ResponseTrackingManager,
                    )

                    self._response_tracking_manager = ResponseTrackingManager()
        return self._response_tracking_manager

    def get_memory_hook_manager(self) -> IMemoryHookManager:
        """Get or create MemoryHookManager instance."""
        if "memory_hook_manager" in self._overrides:
            return self._overrides["memory_hook_manager"]

        if self._memory_hook_manager is None:
            with self._init_lock:
                if self._memory_hook_manager is None:
                    from claude_mpm.hooks.claude_hooks.memory_integration import (
                        MemoryHookManager,
                    )

                    self._memory_hook_manager = MemoryHookManager()
        return self._memory_hook_manager

    def get_auto_pause_handler(self) -> Optional[IAutoPauseHandler]:
        """Get or create AutoPauseHandler instance.

        Returns None if initialization fails (auto-pause is optional).
        """
        if "auto_pause_handler" in self._overrides:
            return self._overrides["auto_pause_handler"]

        if self._auto_pause_handler is None:
            with self._init_lock:
                if self._auto_pause_handler is None:
                    try:
                        from claude_mpm.hooks.claude_hooks.auto_pause_handler import (
                            AutoPauseHandler,
                        )

                        self._auto_pause_handler = AutoPauseHandler()
                    except Exception:
                        # Auto-pause is optional
                        self._auto_pause_handler = None
        return self._auto_pause_handler

    def get_subagent_processor(
        self,
        state_manager: Optional[IStateManager] = None,
        response_tracking_manager: Optional[IResponseTrackingManager] = None,
        connection_manager: Optional[IConnectionManager] = None,
    ) -> ISubagentProcessor:
        """Get or create SubagentResponseProcessor instance.

        Args:
            state_manager: Optional override for state manager
            response_tracking_manager: Optional override for response tracking
            connection_manager: Optional override for connection manager
        """
        if "subagent_processor" in self._overrides:
            return self._overrides["subagent_processor"]

        if self._subagent_processor is None:
            with self._init_lock:
                if self._subagent_processor is None:
                    from claude_mpm.hooks.claude_hooks.services.subagent_processor import (
                        SubagentResponseProcessor,
                    )

                    # Use provided dependencies or get from container
                    sm = state_manager or self.get_state_manager()
                    rtm = (
                        response_tracking_manager
                        or self.get_response_tracking_manager()
                    )
                    cm = connection_manager or self.get_connection_manager()

                    self._subagent_processor = SubagentResponseProcessor(sm, rtm, cm)
        return self._subagent_processor

    def get_event_handlers(self, hook_handler: Any = None) -> IEventHandlers:
        """Get or create EventHandlers instance.

        Args:
            hook_handler: The ClaudeHookHandler instance for backward compatibility.
                         In the future, this will be replaced with proper DI.
        """
        if "event_handlers" in self._overrides:
            return self._overrides["event_handlers"]

        if self._event_handlers is None:
            with self._init_lock:
                if self._event_handlers is None:
                    from claude_mpm.hooks.claude_hooks.event_handlers import (
                        EventHandlers,
                    )

                    if hook_handler is None:
                        raise ValueError(
                            "hook_handler is required to create EventHandlers"
                        )
                    self._event_handlers = EventHandlers(hook_handler)
        return self._event_handlers

    # =========================================================================
    # Service Override Methods (for testing)
    # =========================================================================

    def override_state_manager(self, service: IStateManager) -> None:
        """Override state manager with a mock or custom implementation."""
        self._overrides["state_manager"] = service

    def override_connection_manager(self, service: IConnectionManager) -> None:
        """Override connection manager with a mock or custom implementation."""
        self._overrides["connection_manager"] = service

    def override_duplicate_detector(self, service: IDuplicateDetector) -> None:
        """Override duplicate detector with a mock or custom implementation."""
        self._overrides["duplicate_detector"] = service

    def override_response_tracking_manager(
        self, service: IResponseTrackingManager
    ) -> None:
        """Override response tracking manager with a mock or custom implementation."""
        self._overrides["response_tracking_manager"] = service

    def override_memory_hook_manager(self, service: IMemoryHookManager) -> None:
        """Override memory hook manager with a mock or custom implementation."""
        self._overrides["memory_hook_manager"] = service

    def override_subagent_processor(self, service: ISubagentProcessor) -> None:
        """Override subagent processor with a mock or custom implementation."""
        self._overrides["subagent_processor"] = service

    def override_auto_pause_handler(self, service: Optional[IAutoPauseHandler]) -> None:
        """Override auto-pause handler with a mock or custom implementation."""
        self._overrides["auto_pause_handler"] = service

    def override_event_handlers(self, service: IEventHandlers) -> None:
        """Override event handlers with a mock or custom implementation."""
        self._overrides["event_handlers"] = service

    def reset_overrides(self) -> None:
        """Reset all service overrides."""
        self._overrides.clear()

    def reset_all(self) -> None:
        """Reset all services and overrides.

        Useful for testing to ensure clean state between tests.
        """
        self._state_manager = None
        self._connection_manager = None
        self._duplicate_detector = None
        self._response_tracking_manager = None
        self._memory_hook_manager = None
        self._subagent_processor = None
        self._auto_pause_handler = None
        self._event_handlers = None
        self._overrides.clear()

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the singleton instance.

        USE WITH CAUTION: This is primarily for testing.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.reset_all()
            cls._instance = None


def get_container() -> HookServiceContainer:
    """Get the global HookServiceContainer singleton.

    Returns:
        The singleton HookServiceContainer instance.
    """
    return HookServiceContainer()
