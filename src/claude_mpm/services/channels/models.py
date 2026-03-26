"""Core data models for the multi-channel connection manager."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from claude_mpm.services.github.repo_context import GitHubRepoContext


class SessionState(Enum):
    STARTING = "starting"
    IDLE = "idle"
    PROCESSING = "processing"
    STOPPED = "stopped"


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ChannelMessage:
    """A message flowing through the hub."""

    text: str
    session_name: str
    channel: str  # "terminal", "telegram", "slack"
    user_id: str  # channel-specific user identifier
    user_display: str  # human-readable name for display
    timestamp: float = field(default_factory=time.time)
    thread_id: str | None = None  # Telegram thread / Slack thread_ts
    message_id: str | None = None  # for reply routing
    reply_fn: Callable[[str], Awaitable[None]] | None = (
        None  # send reply back to channel
    )


@dataclass
class SessionEvent:
    """An event broadcast to all session subscribers."""

    session_name: str
    event_type: (
        str  # "user_message", "assistant_message", "tool_call", "error", "state_change"
    )
    data: dict  # event-specific payload
    timestamp: float = field(default_factory=time.time)
    channel: str = ""
    user_id: str = ""


@dataclass
class ChannelSession:
    """A named SDK session managed by the hub."""

    name: str  # human-readable session name, e.g. "myapp"
    cwd: str  # working directory for this session
    created_by_channel: str
    created_by_user: str
    created_at: float = field(default_factory=time.time)
    state: SessionState = SessionState.STARTING
    session_id: str | None = None  # SDK session_id (from ResultMessage)
    participants: list[str] = field(default_factory=list)  # "channel:user_id" strings
    kuzu_namespace: str = ""
    github_context: GitHubRepoContext | None = field(default=None)

    def __post_init__(self) -> None:
        if not self.kuzu_namespace:
            self.kuzu_namespace = self._compute_namespace()

    def _compute_namespace(self) -> str:
        key = f"{self.created_by_channel}:{self.created_by_user}"
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        return f"channel_{self.created_by_channel}_{h}"

    def add_participant(self, channel: str, user_id: str) -> None:
        key = f"{channel}:{user_id}"
        if key not in self.participants:
            self.participants.append(key)

    def has_participant(self, channel: str, user_id: str) -> bool:
        return f"{channel}:{user_id}" in self.participants
