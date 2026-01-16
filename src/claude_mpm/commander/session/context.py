"""Session context for Commander chat interface."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionContext:
    """Tracks the state of a Commander chat session.

    Attributes:
        connected_instance: Name of currently connected instance, or None.
        messages: Conversation history.
        session_id: Unique session identifier.
        created_at: When session was created.

    Example:
        >>> context = SessionContext()
        >>> context.is_connected
        False
        >>> context.connect_to("myapp")
        >>> context.is_connected
        True
        >>> context.connected_instance
        'myapp'
    """

    connected_instance: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    session_id: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_connected(self) -> bool:
        """Check if connected to an instance."""
        return self.connected_instance is not None

    def connect_to(self, instance_name: str) -> None:
        """Connect to an instance.

        Args:
            instance_name: Name of instance to connect to.
        """
        self.connected_instance = instance_name

    def disconnect(self) -> None:
        """Disconnect from current instance."""
        self.connected_instance = None

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history.

        Args:
            role: "user" or "assistant".
            content: Message content.
        """
        self.messages.append(Message(role=role, content=content))

    def get_messages_for_llm(self) -> list[dict]:
        """Get messages formatted for LLM API.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages.clear()
