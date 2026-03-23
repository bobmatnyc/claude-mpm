"""File-based message queue for sidecar agent -> PM hook injection.

Sidecar agents write messages to a JSON-lines file.
The PreToolUse hook reads and consumes them on each tool call.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MessagePriority(str, Enum):
    """Message priority levels."""

    CRITICAL = "critical"  # Always injected immediately
    HIGH = "high"  # Injected on next tool call
    NORMAL = "normal"  # Injected on next tool call
    LOW = "low"  # Batched, injected every N tool calls


@dataclass
class HookMessage:
    """A message to be injected into the PM session via hook."""

    text: str
    priority: MessagePriority = MessagePriority.NORMAL
    source: str = "unknown"  # e.g., "monitor", "ci", "reviewer"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "text": self.text,
            "priority": self.priority.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookMessage:
        """Deserialize from dictionary."""
        return cls(
            text=data["text"],
            priority=MessagePriority(data.get("priority", "normal")),
            source=data.get("source", "unknown"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class HookEventBus:
    """File-based message queue for hook injection.

    Messages are stored as JSON lines in a file.  The hook reads all pending
    messages, formats them as a systemMessage, then truncates the file.

    Uses file locking to handle concurrent writes from multiple sidecar agents.
    """

    def __init__(self, queue_path: str | Path | None = None) -> None:
        if queue_path:
            self.queue_path = Path(queue_path)
        else:
            # Default: ~/.claude-mpm/hook_messages.jsonl
            self.queue_path = Path.home() / ".claude-mpm" / "hook_messages.jsonl"

        # Ensure parent directory exists
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

        # Low-priority batch counter
        self._tool_call_count = 0
        self._low_priority_interval = 5  # Inject low-priority every 5 tool calls

    def send(self, message: HookMessage) -> None:
        """Write a message to the queue (called by sidecar agents)."""
        import fcntl

        line = json.dumps(message.to_dict()) + "\n"

        with open(self.queue_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def consume(self) -> list[HookMessage]:
        """Read and remove all pending messages (called by hook).

        Returns messages sorted by priority (critical first).
        """
        import fcntl

        if not self.queue_path.exists():
            return []

        messages: list[HookMessage] = []

        try:
            with open(self.queue_path, "r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    lines = f.readlines()
                    # Truncate the file
                    f.seek(0)
                    f.truncate()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    messages.append(HookMessage.from_dict(data))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Skipping malformed hook message: %s", e)
        except OSError as e:
            logger.warning("Failed to read hook message queue: %s", e)

        # Sort by priority
        priority_order = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3,
        }
        messages.sort(key=lambda m: priority_order.get(m.priority, 99))

        return messages

    def consume_for_hook(self) -> str | None:
        """Consume messages and format for systemMessage injection.

        Called by the PreToolUse hook.  Returns a formatted string to inject,
        or None if no messages pending.

        Low-priority messages are only included every N tool calls.
        """
        self._tool_call_count += 1

        messages = self.consume()
        if not messages:
            return None

        include_low = (self._tool_call_count % self._low_priority_interval) == 0

        to_inject: list[HookMessage] = []
        deferred: list[HookMessage] = []

        for msg in messages:
            if msg.priority == MessagePriority.LOW and not include_low:
                deferred.append(msg)
            else:
                to_inject.append(msg)

        # Re-queue deferred messages
        for msg in deferred:
            self.send(msg)

        if not to_inject:
            return None

        # Format messages for injection
        parts: list[str] = []
        for msg in to_inject:
            prefix = f"[{msg.source}]" if msg.source != "unknown" else ""
            if msg.priority == MessagePriority.CRITICAL:
                parts.append(f"CRITICAL {prefix}: {msg.text}")
            else:
                parts.append(f"{prefix} {msg.text}".strip())

        return "\n".join(parts)
