"""
Migration utilities for Socket.IO event schema migration.

WHY: This module provides utilities to help migrate from the old event
formats to the new normalized schema, ensuring backward compatibility
during the transition period.

DESIGN DECISION: Provide both transformation and validation utilities
to help identify and fix inconsistent event formats across the codebase.
"""

from typing import Any, Dict, List, Tuple

from ...core.logging_config import get_logger


class EventMigrationHelper:
    """Helper class for migrating events to the new schema.

    WHY: Provides utilities to identify old format events and
    transform them to the new normalized schema.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.migration_stats = {
            "old_format_detected": 0,
            "transformed": 0,
            "validation_failed": 0,
            "already_normalized": 0,
        }

    def is_old_format(self, event_data: Any) -> bool:
        """Check if an event is in the old format.

        WHY: Need to identify which events need migration.
        """
        if not isinstance(event_data, dict):
            return True  # Non-dict events are definitely old format

        # Check for new format fields
        required_new_fields = {"event", "type", "subtype", "timestamp", "data"}
        has_all_new_fields = all(field in event_data for field in required_new_fields)

        if has_all_new_fields:
            self.migration_stats["already_normalized"] += 1
            return False

        # Old format indicators
        old_format_indicators = [
            # Hook format with "hook." prefix in type
            "type" in event_data
            and isinstance(event_data.get("type"), str)
            and event_data["type"].startswith("hook."),
            # Missing subtype field
            "type" in event_data and "subtype" not in event_data,
            # Event field used differently
            "event" in event_data and event_data.get("event") != "claude_event",
        ]

        if any(old_format_indicators):
            self.migration_stats["old_format_detected"] += 1
            return True

        return False

    def transform_to_new_format(self, event_data: Any) -> Dict[str, Any]:
        """Transform an old format event to the new schema.

        WHY: Provides a migration path from old to new format.
        """
        # Import here to avoid circular dependency
        from .event_normalizer import EventNormalizer

        normalizer = EventNormalizer()
        normalized = normalizer.normalize(event_data)

        self.migration_stats["transformed"] += 1
        return normalized.to_dict()

    def validate_event_schema(
        self, event_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate an event against the new schema.

        WHY: Ensures events conform to the expected structure
        before being sent to clients.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required_fields = {"event", "type", "subtype", "timestamp", "data"}
        missing_fields = required_fields - set(event_data.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")

        # Validate field types
        if "event" in event_data and event_data["event"] != "claude_event":
            errors.append(
                f"Invalid event name: {event_data['event']} (should be 'claude_event')"
            )

        if "type" in event_data and not isinstance(event_data["type"], str):
            errors.append(
                f"Invalid type field: should be string, got {type(event_data['type'])}"
            )

        if "subtype" in event_data and not isinstance(event_data["subtype"], str):
            errors.append(
                f"Invalid subtype field: should be string, got {type(event_data['subtype'])}"
            )

        if "timestamp" in event_data:
            timestamp = event_data["timestamp"]
            if not isinstance(timestamp, str) or "T" not in timestamp:
                errors.append(
                    f"Invalid timestamp format: {timestamp} (should be ISO format)"
                )

        if "data" in event_data and not isinstance(event_data["data"], dict):
            errors.append(
                f"Invalid data field: should be dict, got {type(event_data['data'])}"
            )

        if errors:
            self.migration_stats["validation_failed"] += 1
            return False, errors

        return True, []

    def get_migration_report(self) -> str:
        """Generate a report of migration statistics.

        WHY: Helps track migration progress and identify issues.
        """
        report = "Event Migration Report\n"
        report += "=" * 50 + "\n"
        report += (
            f"Old format detected: {self.migration_stats['old_format_detected']}\n"
        )
        report += f"Events transformed: {self.migration_stats['transformed']}\n"
        report += f"Validation failures: {self.migration_stats['validation_failed']}\n"
        report += f"Already normalized: {self.migration_stats['already_normalized']}\n"
        return report

    def reset_stats(self):
        """Reset migration statistics."""
        self.migration_stats = {
            "old_format_detected": 0,
            "transformed": 0,
            "validation_failed": 0,
            "already_normalized": 0,
        }


class EventTypeMapper:
    """Maps old event types to new type/subtype categories.

    WHY: Provides a consistent mapping from legacy event names
    to the new categorized structure.
    """

    # Comprehensive mapping of old event formats to new categories
    TYPE_MAPPINGS = {
        # Hook events with "hook." prefix
        "hook.pre_tool": ("hook", "pre_tool"),
        "hook.post_tool": ("hook", "post_tool"),
        "hook.pre_response": ("hook", "pre_response"),
        "hook.post_response": ("hook", "post_response"),
        "hook.start": ("hook", "start"),
        "hook.stop": ("hook", "stop"),
        "hook.subagent_start": ("hook", "subagent_start"),
        "hook.subagent_stop": ("hook", "subagent_stop"),
        # Hook events without prefix
        "pre_tool": ("hook", "pre_tool"),
        "post_tool": ("hook", "post_tool"),
        "pre_response": ("hook", "pre_response"),
        "post_response": ("hook", "post_response"),
        # System events
        "system_heartbeat": ("system", "heartbeat"),
        "heartbeat": ("system", "heartbeat"),
        "system_status": ("system", "status"),
        # Session events
        "session_started": ("session", "started"),
        "session_ended": ("session", "ended"),
        # File events
        "file_changed": ("file", "changed"),
        "file_created": ("file", "created"),
        "file_deleted": ("file", "deleted"),
        # Connection events
        "client_connected": ("connection", "connected"),
        "client_disconnected": ("connection", "disconnected"),
        # Memory events
        "memory_loaded": ("memory", "loaded"),
        "memory_created": ("memory", "created"),
        "memory_updated": ("memory", "updated"),
        "memory_injected": ("memory", "injected"),
        # Git events
        "git_operation": ("git", "operation"),
        "git_commit": ("git", "commit"),
        "git_push": ("git", "push"),
        # Todo events
        "todo_updated": ("todo", "updated"),
        "todo_created": ("todo", "created"),
        # Ticket events
        "ticket_created": ("ticket", "created"),
        "ticket_updated": ("ticket", "updated"),
        # Agent events
        "agent_delegated": ("agent", "delegated"),
        "agent_completed": ("agent", "completed"),
        # Claude events
        "claude_status": ("claude", "status"),
        "claude_output": ("claude", "output"),
        # Error events
        "error": ("error", "general"),
        "error_occurred": ("error", "occurred"),
        # Performance events
        "performance": ("performance", "metric"),
        "performance_metric": ("performance", "metric"),
    }

    @classmethod
    def map_event_type(cls, old_type: str) -> Tuple[str, str]:
        """Map an old event type to new type/subtype.

        WHY: Provides consistent categorization for all events.

        Args:
            old_type: The old event type string

        Returns:
            Tuple of (type, subtype)
        """
        # Direct mapping
        if old_type in cls.TYPE_MAPPINGS:
            return cls.TYPE_MAPPINGS[old_type]

        # Try to infer from patterns
        old_lower = old_type.lower()

        # Hook events
        if "hook" in old_lower or old_lower.startswith(("pre_", "post_")):
            # Remove "hook." prefix if present
            clean_type = old_type.replace("hook.", "")
            return "hook", clean_type

        # System events
        if "system" in old_lower or "heartbeat" in old_lower:
            return "system", old_type.replace("system_", "")

        # Session events
        if "session" in old_lower:
            if "start" in old_lower:
                return "session", "started"
            if "end" in old_lower:
                return "session", "ended"
            return "session", "generic"

        # File events
        if "file" in old_lower:
            if "create" in old_lower:
                return "file", "created"
            if "delete" in old_lower:
                return "file", "deleted"
            if "change" in old_lower or "modify" in old_lower:
                return "file", "changed"
            return "file", "generic"

        # Default mapping
        return "unknown", old_type

    @classmethod
    def get_event_category(cls, event_type: str, event_subtype: str) -> str:
        """Get a human-readable category for an event.

        WHY: Helps with filtering and display in UIs.
        """
        categories = {
            "hook": "Claude Hooks",
            "system": "System Status",
            "session": "Session Management",
            "file": "File Operations",
            "connection": "Client Connections",
            "memory": "Memory System",
            "git": "Git Operations",
            "todo": "Todo Management",
            "ticket": "Ticket System",
            "agent": "Agent Delegation",
            "claude": "Claude Process",
            "error": "Errors",
            "performance": "Performance Metrics",
            "unknown": "Uncategorized",
        }
        return categories.get(event_type, "Other")


def create_backward_compatible_event(
    normalized_event: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a backward-compatible version of a normalized event.

    WHY: During migration, some clients may still expect the old format.
    This creates an event that works with both old and new clients.

    Args:
        normalized_event: Event in the new normalized format

    Returns:
        Event that includes both old and new format fields
    """
    # Start with the normalized event
    compat_event = normalized_event.copy()

    # Add old format fields based on type/subtype
    event_type = normalized_event.get("type", "")
    event_subtype = normalized_event.get("subtype", "")

    # For hook events, add the old "hook." prefix format
    if event_type == "hook":
        compat_event["type_legacy"] = f"hook.{event_subtype}"

    # For other events, use the old naming convention
    elif event_type in [
        "session",
        "file",
        "memory",
        "git",
        "todo",
        "ticket",
        "agent",
        "claude",
    ]:
        compat_event["type_legacy"] = f"{event_type}_{event_subtype}"

    # Add event_type field for really old clients
    compat_event["event_type"] = compat_event.get(
        "type_legacy", f"{event_type}_{event_subtype}"
    )

    return compat_event
