"""Protocol definitions for hook handler services.

This module defines Protocol classes for all hook handler services,
enabling type-safe dependency injection and easy testing through
protocol-based duck typing.

WHY Protocol-based DI:
- Enables loose coupling between components
- Allows easy mocking in tests without monkey-patching
- Provides clear interface contracts
- Supports static type checking with mypy
"""

from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class IStateManager(Protocol):
    """Protocol for state management service.

    Manages:
    - Agent delegation tracking
    - Git branch caching
    - Session state management
    - Cleanup of old entries
    """

    active_delegations: dict
    delegation_history: Any  # deque
    delegation_requests: dict
    pending_prompts: dict
    events_processed: int

    def track_delegation(
        self, session_id: str, agent_type: str, request_data: Optional[dict] = None
    ) -> None:
        """Track a new agent delegation with optional request data."""
        ...

    def get_delegation_agent_type(self, session_id: str) -> str:
        """Get the agent type for a session's active delegation."""
        ...

    def cleanup_old_entries(self) -> None:
        """Clean up old entries to prevent memory growth."""
        ...

    def get_git_branch(self, working_dir: Optional[str] = None) -> str:
        """Get git branch for the given directory with caching."""
        ...

    def find_matching_request(self, session_id: str) -> Optional[dict]:
        """Find matching request data for a session, with fuzzy matching fallback."""
        ...

    def remove_request(self, session_id: str) -> None:
        """Remove request data for a session."""
        ...

    def increment_events_processed(self) -> bool:
        """Increment events processed counter and return True if cleanup is needed."""
        ...


@runtime_checkable
class IConnectionManager(Protocol):
    """Protocol for connection management service.

    Handles:
    - HTTP-based event emission to dashboard
    - Event queuing and batching
    - Connection state management
    """

    def emit_event(self, namespace: str, event: str, data: dict) -> None:
        """Emit an event through HTTP to the dashboard."""
        ...

    def cleanup(self) -> None:
        """Clean up any resources."""
        ...


@runtime_checkable
class IDuplicateDetector(Protocol):
    """Protocol for duplicate event detection service.

    Detects:
    - Duplicate events within a time window
    - Rapid-fire events that should be deduplicated
    """

    def is_duplicate(self, event: dict) -> bool:
        """Check if an event is a duplicate of a recent event."""
        ...

    def generate_event_key(self, event: dict) -> str:
        """Generate a unique key for an event for deduplication."""
        ...


@runtime_checkable
class IResponseTrackingManager(Protocol):
    """Protocol for response tracking management.

    Manages:
    - Response tracking enablement
    - Comprehensive response logging
    - Agent response correlation
    """

    response_tracking_enabled: bool
    response_tracker: Optional[Any]
    track_all_interactions: bool
    auto_pause_handler: Optional[Any]

    def track_agent_response(
        self,
        session_id: str,
        agent_type: str,
        event: dict,
        delegation_requests: dict,
    ) -> None:
        """Track an agent response for logging."""
        ...

    def track_stop_response(
        self,
        event: dict,
        session_id: str,
        metadata: dict,
        pending_prompts: dict,
    ) -> None:
        """Track a stop event response."""
        ...

    def track_assistant_response(
        self,
        event: dict,
        pending_prompts: dict,
    ) -> None:
        """Track an assistant response."""
        ...


@runtime_checkable
class IMemoryHookManager(Protocol):
    """Protocol for memory hook management.

    Manages:
    - Pre/post delegation memory hooks
    - Memory field processing
    """

    def trigger_pre_delegation_hook(
        self, agent_type: str, tool_input: dict, session_id: str
    ) -> None:
        """Trigger memory hooks before delegation."""
        ...

    def trigger_post_delegation_hook(
        self, agent_type: str, event: dict, session_id: str
    ) -> None:
        """Trigger memory hooks after delegation."""
        ...


@runtime_checkable
class ISubagentProcessor(Protocol):
    """Protocol for subagent response processing.

    Handles:
    - SubagentStop event processing
    - Structured response extraction
    - Response tracking and correlation
    """

    def process_subagent_stop(self, event: dict) -> None:
        """Handle subagent stop events."""
        ...


@runtime_checkable
class IAutoPauseHandler(Protocol):
    """Protocol for auto-pause functionality.

    Manages:
    - Session pause tracking
    - Usage threshold monitoring
    - Session state capture
    """

    def is_pause_active(self) -> bool:
        """Check if auto-pause is currently active."""
        ...

    def on_user_message(self, message: str) -> None:
        """Record a user message for auto-pause tracking."""
        ...

    def on_tool_call(self, tool_name: str, tool_input: dict) -> None:
        """Record a tool call for auto-pause tracking."""
        ...

    def on_assistant_response(self, response: str) -> None:
        """Record an assistant response for auto-pause tracking."""
        ...

    def on_usage_update(self, usage: dict) -> Optional[str]:
        """Update usage metrics and return threshold crossed if any."""
        ...

    def emit_threshold_warning(self, threshold: str) -> str:
        """Emit a warning for a crossed threshold."""
        ...

    def on_session_end(self) -> Optional[Any]:
        """Finalize the current auto-pause session."""
        ...


@runtime_checkable
class IEventHandlers(Protocol):
    """Protocol for event handler collection.

    Provides handlers for:
    - UserPromptSubmit
    - PreToolUse
    - PostToolUse
    - Notification
    - Stop
    - SubagentStop
    - SubagentStart
    - SessionStart
    - AssistantResponse
    """

    def handle_user_prompt_fast(self, event: dict) -> None:
        """Handle user prompt with comprehensive data capture."""
        ...

    def handle_pre_tool_fast(self, event: dict) -> Optional[dict]:
        """Handle pre-tool use with comprehensive data capture."""
        ...

    def handle_post_tool_fast(self, event: dict) -> None:
        """Handle post-tool use with comprehensive data capture."""
        ...

    def handle_notification_fast(self, event: dict) -> None:
        """Handle notification events from Claude."""
        ...

    def handle_stop_fast(self, event: dict) -> None:
        """Handle stop events when Claude processing stops."""
        ...

    def handle_subagent_stop_fast(self, event: dict) -> None:
        """Handle subagent stop events."""
        ...

    def handle_subagent_start_fast(self, event: dict) -> None:
        """Handle SubagentStart events."""
        ...

    def handle_session_start_fast(self, event: dict) -> None:
        """Handle session start events."""
        ...

    def handle_assistant_response(self, event: dict) -> None:
        """Handle assistant response events."""
        ...


# Type alias for log function
LogFunction = Callable[[str], None]


@runtime_checkable
class ILogManager(Protocol):
    """Protocol for log manager service (optional dependency).

    Used for logging agent prompts and responses.
    """

    async def log_prompt(
        self, source: str, content: str, metadata: dict
    ) -> Optional[Any]:
        """Log a prompt to the log manager."""
        ...


@runtime_checkable
class IDelegationDetector(Protocol):
    """Protocol for delegation pattern detector (optional dependency).

    Used for detecting delegation anti-patterns in responses.
    """

    def detect_user_delegation(self, text: str) -> list[dict]:
        """Detect delegation patterns in text."""
        ...


@runtime_checkable
class IEventLog(Protocol):
    """Protocol for event log service (optional dependency).

    Used for logging PM violations and other events.
    """

    def append_event(
        self,
        event_type: str,
        payload: dict,
        status: str = "pending",
    ) -> None:
        """Append an event to the log."""
        ...


@runtime_checkable
class IConfig(Protocol):
    """Protocol for configuration service (optional dependency)."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        ...
