"""
Event normalizer for Socket.IO events in claude-mpm.

WHY: The system currently has inconsistent event formats across different components.
This normalizer ensures all events follow a consistent schema before broadcasting,
providing backward compatibility while establishing a standard format.

DESIGN DECISION: Transform all events to a consistent schema:
- event: Socket.IO event name (always "mpm_event")
- type: Main category (hook, system, session, file, connection)
- subtype: Specific event type (pre_tool, heartbeat, started, etc.)
- timestamp: ISO format timestamp
- data: Raw event payload
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ...core.logging_config import get_logger


class EventSource(Enum):
    """Event sources.

    WHY: Identifying where events come from helps with debugging,
    filtering, and understanding system behavior.
    """

    HOOK = "hook"  # Events from Claude Code hooks
    DASHBOARD = "dashboard"  # Events from dashboard UI
    SYSTEM = "system"  # System/server operations
    AGENT = "agent"  # Agent operations
    CLI = "cli"  # CLI commands
    API = "api"  # API calls
    TEST = "test"  # Test scripts


class EventType(Enum):
    """Main event categories.

    WHY: Categorizing events helps with filtering, routing, and understanding
    the system's behavior at a high level.
    """

    HOOK = "hook"  # Claude Code hook events
    SYSTEM = "system"  # System health and status events
    SESSION = "session"  # Session lifecycle events
    FILE = "file"  # File system events
    CONNECTION = "connection"  # Client connection events
    MEMORY = "memory"  # Memory system events
    GIT = "git"  # Git operation events
    TODO = "todo"  # Todo list updates
    TICKET = "ticket"  # Ticket system events
    AGENT = "agent"  # Agent delegation events
    ERROR = "error"  # Error events
    PERFORMANCE = "performance"  # Performance metrics
    CLAUDE = "claude"  # Claude process events
    TEST = "test"  # Test events
    CODE = "code"  # Code analysis events
    TOOL = "tool"  # Tool events
    SUBAGENT = "subagent"  # Subagent events


@dataclass
class NormalizedEvent:
    """Represents a normalized event with consistent structure.

    WHY: Using a dataclass ensures type safety and makes the event
    structure explicit and self-documenting.
    """

    event: str = "mpm_event"  # Socket.IO event name
    source: str = ""  # WHERE the event comes from
    type: str = ""  # WHAT category of event
    subtype: str = ""  # Specific event type
    timestamp: str = ""  # ISO format timestamp
    data: Dict[str, Any] = field(default_factory=dict)  # Event payload
    correlation_id: Optional[str] = (
        None  # For correlating related events (e.g., pre_tool/post_tool)
    )
    session_id: Optional[str] = None  # Session identifier for stream grouping
    cwd: Optional[str] = None  # Working directory for project identification

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for emission."""
        result = {
            "event": self.event,
            "source": self.source,
            "type": self.type,
            "subtype": self.subtype,
            "timestamp": self.timestamp,
            "data": self.data,
        }
        # Include correlation_id if present
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        # Include session_id if present
        if self.session_id:
            result["session_id"] = self.session_id
        # Include cwd if present
        if self.cwd:
            result["cwd"] = self.cwd
        return result


class EventNormalizer:
    """Normalizes events to a consistent schema.

    WHY: This class handles the transformation of various event formats
    into a single, consistent schema that clients can reliably parse.
    """

    # Mapping of event names to (type, subtype) tuples
    EVENT_MAPPINGS = {
        # Hook events
        "pre_tool": (EventType.HOOK, "pre_tool"),
        "post_tool": (EventType.HOOK, "post_tool"),
        "pre_response": (EventType.HOOK, "pre_response"),
        "post_response": (EventType.HOOK, "post_response"),
        "hook_event": (EventType.HOOK, "generic"),
        "hook_execution": (EventType.HOOK, "execution"),  # Hook execution metadata
        "UserPrompt": (EventType.HOOK, "user_prompt"),  # Legacy format
        # Test events (legacy format)
        "TestStart": (EventType.TEST, "start"),
        "TestEnd": (EventType.TEST, "end"),
        # Tool events (legacy format)
        "ToolCall": (EventType.TOOL, "call"),
        # Subagent events (legacy format)
        "SubagentStart": (EventType.SUBAGENT, "start"),
        "SubagentStop": (EventType.SUBAGENT, "stop"),
        # System events
        "heartbeat": (EventType.SYSTEM, "heartbeat"),
        "system_status": (EventType.SYSTEM, "status"),
        "system_event": (EventType.SYSTEM, "generic"),
        # Session events
        "session_started": (EventType.SESSION, "started"),
        "session_ended": (EventType.SESSION, "ended"),
        "session_event": (EventType.SESSION, "generic"),
        # File events
        "file_changed": (EventType.FILE, "changed"),
        "file_created": (EventType.FILE, "created"),
        "file_deleted": (EventType.FILE, "deleted"),
        "file_event": (EventType.FILE, "generic"),
        # Connection events
        "client_connected": (EventType.CONNECTION, "connected"),
        "client_disconnected": (EventType.CONNECTION, "disconnected"),
        "connection_event": (EventType.CONNECTION, "generic"),
        # Memory events
        "memory_loaded": (EventType.MEMORY, "loaded"),
        "memory_created": (EventType.MEMORY, "created"),
        "memory_updated": (EventType.MEMORY, "updated"),
        "memory_injected": (EventType.MEMORY, "injected"),
        "memory_event": (EventType.MEMORY, "generic"),
        # Git events
        "git_operation": (EventType.GIT, "operation"),
        "git_commit": (EventType.GIT, "commit"),
        "git_push": (EventType.GIT, "push"),
        "git_pull": (EventType.GIT, "pull"),
        # Todo events
        "todo_updated": (EventType.TODO, "updated"),
        "todo_created": (EventType.TODO, "created"),
        "todo_completed": (EventType.TODO, "completed"),
        # Ticket events
        "ticket_created": (EventType.TICKET, "created"),
        "ticket_updated": (EventType.TICKET, "updated"),
        "ticket_closed": (EventType.TICKET, "closed"),
        # Agent events
        "agent_delegated": (EventType.AGENT, "delegated"),
        "agent_completed": (EventType.AGENT, "completed"),
        # Claude events
        "claude_status": (EventType.CLAUDE, "status"),
        "claude_output": (EventType.CLAUDE, "output"),
        "claude_started": (EventType.CLAUDE, "started"),
        "claude_stopped": (EventType.CLAUDE, "stopped"),
        # Error events
        "error": (EventType.ERROR, "general"),
        "error_occurred": (EventType.ERROR, "occurred"),
        # Performance events
        "performance": (EventType.PERFORMANCE, "metric"),
        "performance_metric": (EventType.PERFORMANCE, "metric"),
    }

    # Patterns to extract event type from various formats
    TYPE_PATTERNS = [
        # Pattern 1: event_type field
        (r'"event_type"\s*:\s*"([^"]+)"', lambda m: m.group(1)),
        # Pattern 2: type field
        (r'"type"\s*:\s*"([^"]+)"', lambda m: m.group(1)),
        # Pattern 3: event field
        (r'"event"\s*:\s*"([^"]+)"', lambda m: m.group(1)),
        # Pattern 4: Hook format (hook:event_name)
        (r'"hook"\s*:\s*"([^"]+)"', lambda m: f"hook_{m.group(1)}"),
    ]

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.stats = {
            "normalized": 0,
            "already_normalized": 0,
            "unknown_format": 0,
            "errors": 0,
        }

    def normalize(
        self, event_data: Any, source: Optional[str] = None
    ) -> NormalizedEvent:
        """Normalize an event to the standard schema.

        WHY: This method handles various input formats and transforms them
        into a consistent structure that all clients can understand.

        Args:
            event_data: The event data in any supported format
            source: Optional source override (e.g., "hook", "dashboard", "test")

        Returns:
            NormalizedEvent with consistent structure
        """
        try:
            # If already normalized (has all required fields), validate and return
            if self._is_normalized(event_data):
                self.stats["already_normalized"] += 1
                return self._validate_normalized(event_data)

            # Extract event information from various formats
            event_type, subtype, data = self._extract_event_info(event_data)

            # Determine event source
            event_source = self._determine_source(event_data, event_type, source)

            # Get or generate timestamp
            timestamp = self._extract_timestamp(event_data)

            # Extract correlation_id, session_id, and cwd if present
            correlation_id = None
            session_id = None
            cwd = None
            if isinstance(event_data, dict):
                correlation_id = event_data.get("correlation_id")
                # Try both naming conventions for session_id
                session_id = event_data.get("session_id") or event_data.get("sessionId")
                # Try multiple field names for working directory
                cwd = (
                    event_data.get("cwd")
                    or event_data.get("working_directory")
                    or event_data.get("workingDirectory")
                )

            # Create normalized event
            normalized = NormalizedEvent(
                event="mpm_event",
                source=event_source,
                type=event_type,
                subtype=subtype,
                timestamp=timestamp,
                data=data,
                correlation_id=correlation_id,
                session_id=session_id,
                cwd=cwd,
            )

            self.stats["normalized"] += 1
            self.logger.debug(f"Normalized event: {event_type}/{subtype}")

            return normalized

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Failed to normalize event: {e}")

            # Return a generic event on error
            return NormalizedEvent(
                event="mpm_event",
                source="system",
                type="unknown",
                subtype="error",
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={"original": str(event_data), "error": str(e)},
            )

    def _is_normalized(self, event_data: Any) -> bool:
        """Check if event is already in normalized format.

        WHY: Avoid double-normalization and preserve already correct events.
        """
        if not isinstance(event_data, dict):
            return False

        # Check for normalized format (must have source, type, subtype, timestamp, and data)
        required_fields = {"source", "type", "subtype", "timestamp", "data"}
        return all(field in event_data for field in required_fields)

    def _validate_normalized(self, event_data: Dict[str, Any]) -> NormalizedEvent:
        """Validate and convert an already normalized event.

        WHY: Ensure even pre-normalized events are valid and properly typed.
        """
        # Map source if it's a known indicator
        source = event_data.get("source", "system")
        if source == "claude_hooks":
            source = EventSource.HOOK.value
        elif source not in [e.value for e in EventSource]:
            # If source is not a valid EventSource value, keep it as-is
            pass

        # Extract session_id and cwd, trying multiple naming conventions
        session_id = event_data.get("session_id") or event_data.get("sessionId")
        cwd = (
            event_data.get("cwd")
            or event_data.get("working_directory")
            or event_data.get("workingDirectory")
        )

        return NormalizedEvent(
            event="mpm_event",  # Always use standard event name
            source=source,
            type=event_data.get("type", "unknown"),
            subtype=event_data.get("subtype", "generic"),
            timestamp=event_data.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
            data=event_data.get("data", {}),
            correlation_id=event_data.get("correlation_id"),
            session_id=session_id,
            cwd=cwd,
        )

    def _extract_event_info(self, event_data: Any) -> Tuple[str, str, Dict[str, Any]]:
        """Extract event type, subtype, and data from various formats.

        WHY: The system has multiple event formats that need to be handled:
        - Simple strings (event names)
        - Dictionaries with type field
        - Hook events with special structure
        - Legacy formats
        """
        # Handle string events (just event name)
        if isinstance(event_data, str):
            event_type, subtype = self._map_event_name(event_data)
            return event_type, subtype, {"event_name": event_data}

        # Handle dictionary events
        if isinstance(event_data, dict):
            # Special case: type="hook" with event field (legacy hook format)
            if event_data.get("type") == "hook" and "event" in event_data:
                event_type = "hook"
                subtype = event_data["event"]
                data = self._extract_data_payload(event_data)
                return event_type, subtype, data

            # Try to extract event name/type
            event_name = self._extract_event_name(event_data)

            # Map to type and subtype
            event_type, subtype = self._map_event_name(event_name)

            # Extract data payload
            data = self._extract_data_payload(event_data)

            return event_type, subtype, data

        # Unknown format
        self.stats["unknown_format"] += 1
        return "unknown", "generic", {"original": str(event_data)}

    def _extract_event_name(self, event_dict: Dict[str, Any]) -> str:
        """Extract event name from dictionary.

        WHY: Events use different field names for the event identifier.
        """
        # Priority order for event name fields
        for field in ["event_type", "type", "event", "hook", "name"]:
            if field in event_dict:
                value = event_dict[field]
                if isinstance(value, str):
                    return value

        # Try to extract from JSON string representation
        event_str = str(event_dict)
        for pattern, extractor in self.TYPE_PATTERNS:
            match = re.search(pattern, event_str)
            if match:
                return extractor(match)

        return "unknown"

    def _map_event_name(self, event_name: str) -> Tuple[str, str]:
        """Map event name to (type, subtype) tuple.

        WHY: Consistent categorization helps clients filter and handle events.
        """
        # Direct mapping
        if event_name in self.EVENT_MAPPINGS:
            event_type, subtype = self.EVENT_MAPPINGS[event_name]
            return (
                event_type.value if isinstance(event_type, EventType) else event_type
            ), subtype

        # Handle colon-separated event names (e.g., "code:analysis:queued", "code:progress")
        # These are commonly used by the code analysis system
        if ":" in event_name:
            parts = event_name.split(":", 2)  # Split into max 3 parts
            if len(parts) >= 2:
                type_part = parts[0].lower()
                # For events like "code:analysis:queued", combine the last parts as subtype
                # Replace colons with underscores for clean subtypes
                if len(parts) == 3:
                    subtype_part = f"{parts[1]}_{parts[2]}"
                else:
                    subtype_part = parts[1].replace(":", "_")

                # Map the type part to known types
                if type_part in [
                    "code",  # Code analysis events
                    "hook",
                    "session",
                    "file",
                    "system",
                    "connection",
                    "memory",
                    "git",
                    "todo",
                    "ticket",
                    "agent",
                    "claude",
                    "error",
                    "performance",
                    "test",
                    "tool",
                    "subagent",
                ]:
                    return type_part, subtype_part

        # Handle dotted event names (e.g., "connection.status", "session.started")
        if "." in event_name:
            parts = event_name.split(".", 1)
            if len(parts) == 2:
                type_part, subtype_part = parts
                # Map the type part to known types
                type_lower = type_part.lower()
                if type_lower in [
                    "hook",
                    "session",
                    "file",
                    "system",
                    "connection",
                    "memory",
                    "git",
                    "todo",
                    "ticket",
                    "agent",
                    "claude",
                    "error",
                    "performance",
                    "test",
                    "tool",
                    "subagent",
                ]:
                    return type_lower, subtype_part

        # Try to infer from event name patterns
        event_lower = event_name.lower()

        # Check if event name matches a known EventType value directly
        for event_type_enum in EventType:
            if event_lower == event_type_enum.value:
                return event_type_enum.value, "generic"

        # Hook events (hook_* or *_hook or hook.*)
        if "hook" in event_lower:
            # Handle "hook.event_name" format
            if "hook." in event_lower:
                # Extract the part after "hook."
                parts = event_name.split(".", 1)
                if len(parts) > 1:
                    return EventType.HOOK.value, parts[1]
            # Handle pre_ and post_ prefixes
            if event_lower.startswith(("pre_", "post_")):
                return EventType.HOOK.value, event_lower
            return EventType.HOOK.value, "generic"

        # Session events
        if "session" in event_lower:
            if "start" in event_lower:
                return EventType.SESSION.value, "started"
            if "end" in event_lower:
                return EventType.SESSION.value, "ended"
            return EventType.SESSION.value, "generic"

        # File events
        if "file" in event_lower:
            if "create" in event_lower:
                return EventType.FILE.value, "created"
            if "delete" in event_lower:
                return EventType.FILE.value, "deleted"
            if "change" in event_lower or "modify" in event_lower:
                return EventType.FILE.value, "changed"
            return EventType.FILE.value, "generic"

        # System events
        if "system" in event_lower or "heartbeat" in event_lower:
            if "heartbeat" in event_lower:
                return EventType.SYSTEM.value, "heartbeat"
            return EventType.SYSTEM.value, "status"

        # Connection events
        if "connect" in event_lower or "client" in event_lower:
            if "disconnect" in event_lower:
                return EventType.CONNECTION.value, "disconnected"
            if "connect" in event_lower:
                return EventType.CONNECTION.value, "connected"
            return EventType.CONNECTION.value, "generic"

        # Memory events
        if "memory" in event_lower:
            if "load" in event_lower:
                return EventType.MEMORY.value, "loaded"
            if "create" in event_lower:
                return EventType.MEMORY.value, "created"
            if "update" in event_lower:
                return EventType.MEMORY.value, "updated"
            if "inject" in event_lower:
                return EventType.MEMORY.value, "injected"
            return EventType.MEMORY.value, "generic"

        # Code analysis events - using underscores for clean subtypes
        if "code" in event_lower:
            if "analysis" in event_lower:
                if "queue" in event_lower:
                    return EventType.CODE.value, "analysis_queued"
                if "start" in event_lower:
                    return EventType.CODE.value, "analysis_start"
                if "complete" in event_lower:
                    return EventType.CODE.value, "analysis_complete"
                if "error" in event_lower:
                    return EventType.CODE.value, "analysis_error"
                if "cancel" in event_lower:
                    return EventType.CODE.value, "analysis_cancelled"
                return EventType.CODE.value, "analysis_generic"
            if "progress" in event_lower:
                return EventType.CODE.value, "progress"
            if "file" in event_lower:
                if "discovered" in event_lower:
                    return EventType.CODE.value, "file_discovered"
                if "analyzed" in event_lower:
                    return EventType.CODE.value, "file_analyzed"
                return EventType.CODE.value, "file_complete"
            if "directory" in event_lower:
                return EventType.CODE.value, "directory_discovered"
            if "node" in event_lower:
                return EventType.CODE.value, "node_found"
            return EventType.CODE.value, "generic"

        # Default to unknown with lowercase subtype
        return "unknown", event_name.lower() if event_name else ""

    def _extract_data_payload(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the data payload from an event dictionary.

        WHY: Different event formats store the payload in different places.
        """
        # If there's a explicit data field, use it
        if "data" in event_dict:
            return (
                event_dict["data"]
                if isinstance(event_dict["data"], dict)
                else {"value": event_dict["data"]}
            )

        # Otherwise, use the entire dict minus metadata fields
        metadata_fields = {
            "event",
            "type",
            "subtype",
            "timestamp",
            "event_type",
            "hook",
        }
        data = {k: v for k, v in event_dict.items() if k not in metadata_fields}

        return data if data else event_dict

    def _extract_timestamp(self, event_data: Any) -> str:
        """Extract or generate timestamp.

        WHY: Consistent timestamp format is essential for event ordering
        and debugging.
        """
        if isinstance(event_data, dict):
            # Try various timestamp field names
            for field in ["timestamp", "time", "created_at", "date"]:
                if field in event_data:
                    timestamp = event_data[field]
                    # Validate it's a string in ISO format
                    if isinstance(timestamp, str) and "T" in timestamp:
                        return timestamp
                    # Convert other formats
                    try:
                        if isinstance(timestamp, (int, float)):
                            return datetime.fromtimestamp(
                                timestamp, tz=timezone.utc
                            ).isoformat()
                    except Exception:
                        pass

        # Generate new timestamp if not found
        return datetime.now(timezone.utc).isoformat()

    def _determine_source(
        self, event_data: Any, event_type: str, source_override: Optional[str] = None
    ) -> str:
        """Determine the source of an event.

        WHY: Knowing where events originate helps with debugging,
        filtering, and understanding system behavior.

        Args:
            event_data: The raw event data
            event_type: The determined event type
            source_override: Optional explicit source

        Returns:
            The event source as a string
        """
        # Use explicit source override if provided
        if source_override:
            return source_override

        # Check if event data contains source field
        if isinstance(event_data, dict):
            # Direct source field
            if "source" in event_data:
                source = event_data["source"]
                if isinstance(source, str):
                    # Map known source indicators to EventSource values
                    if source == "claude_hooks":
                        return EventSource.HOOK.value
                    # Return the source as-is if it's a valid EventSource value
                    valid_sources = [e.value for e in EventSource]
                    if source in valid_sources:
                        return source
                    # Otherwise, keep the original source value
                    return source

            # Check for indicators of specific sources
            # Test indicator - only if type is actually "test"
            if event_type == "test" or (
                isinstance(event_data.get("type"), str)
                and event_data.get("type") == "test"
            ):
                return EventSource.TEST.value

            # Dashboard indicator
            if "dashboard" in str(event_data).lower() or "ui_action" in event_data:
                return EventSource.DASHBOARD.value

            # CLI indicator
            if "cli" in str(event_data).lower() or "command" in event_data:
                return EventSource.CLI.value

            # API indicator
            if "api" in str(event_data).lower() or "endpoint" in event_data:
                return EventSource.API.value

        # Infer from event type
        if event_type == EventType.HOOK.value:
            return EventSource.HOOK.value
        if event_type == EventType.TEST.value:
            return EventSource.TEST.value
        if event_type in [EventType.AGENT.value, EventType.SUBAGENT.value]:
            return EventSource.AGENT.value
        if event_type in [
            EventType.SYSTEM.value,
            EventType.SESSION.value,
            EventType.CONNECTION.value,
            EventType.PERFORMANCE.value,
        ]:
            return EventSource.SYSTEM.value

        # Default to system source
        return EventSource.SYSTEM.value

    def get_stats(self) -> Dict[str, int]:
        """Get normalization statistics.

        WHY: Monitoring normalization helps identify problematic event sources.
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics counters.

        WHY: Periodic reset prevents counter overflow and enables
        rate calculations.
        """
        self.stats = {
            "normalized": 0,
            "already_normalized": 0,
            "unknown_format": 0,
            "errors": 0,
        }


# Utility functions for consistent event type checking
def is_hook_event(event_data: Dict[str, Any]) -> bool:
    """Check if an event is a hook event (handles both normalized and legacy formats).

    WHY: Hook events can come in multiple formats and we need consistent checking
    across the codebase to avoid missing events.

    Args:
        event_data: Event dictionary to check

    Returns:
        True if this is a hook event, False otherwise
    """
    if not isinstance(event_data, dict):
        return False

    event_type = event_data.get("type", "")

    # Check normalized format: type="hook"
    if event_type == "hook":
        return True

    # Check legacy format: type="hook.something"
    return bool(isinstance(event_type, str) and event_type.startswith("hook."))


def get_hook_event_name(event_data: Dict[str, Any]) -> str:
    """Extract the hook event name from either normalized or legacy format.

    WHY: Hook events store their specific name differently in normalized vs legacy
    formats, and we need a consistent way to extract it.

    Args:
        event_data: Event dictionary containing a hook event

    Returns:
        The specific hook event name (e.g., "pre_tool", "user_prompt")
        or empty string if not a hook event
    """
    if not is_hook_event(event_data):
        return ""

    event_type = event_data.get("type", "")
    event_subtype = event_data.get("subtype", "")

    # Normalized format: type="hook", subtype="pre_tool"
    if event_type == "hook" and event_subtype:
        return event_subtype

    # Legacy format: type="hook.pre_tool"
    if isinstance(event_type, str) and event_type.startswith("hook."):
        return event_type[5:]  # Remove "hook." prefix

    # Fallback: check 'event' field (another legacy format)
    return event_data.get("event", "")


def is_event_type(
    event_data: Dict[str, Any], type_name: str, subtype: Optional[str] = None
) -> bool:
    """Check if an event matches a specific type and optionally subtype.

    WHY: This provides a consistent way to check event types that works with
    both normalized and legacy formats.

    Args:
        event_data: Event dictionary to check
        type_name: The type to check for (e.g., "hook", "session", "file")
        subtype: Optional subtype to also check (e.g., "pre_tool", "started")

    Returns:
        True if the event matches the specified type (and subtype if provided)
    """
    if not isinstance(event_data, dict):
        return False

    event_type = event_data.get("type", "")
    event_subtype = event_data.get("subtype", "")

    # Check normalized format
    if event_type == type_name:
        if subtype is None:
            return True
        return event_subtype == subtype

    # Check legacy dotted format (e.g., "hook.pre_tool")
    if subtype and isinstance(event_type, str):
        legacy_type = f"{type_name}.{subtype}"
        if event_type == legacy_type:
            return True

    return False
