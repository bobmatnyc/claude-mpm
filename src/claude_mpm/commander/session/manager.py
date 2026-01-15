"""Session manager for Commander chat interface."""

from .context import SessionContext


class SessionManager:
    """Manages Commander chat session state.

    Coordinates session context, connection state, and conversation history.

    Example:
        >>> manager = SessionManager()
        >>> manager.connect_to("myapp")
        >>> manager.context.is_connected
        True
        >>> manager.add_user_message("Fix the bug")
        >>> len(manager.context.messages)
        1
    """

    def __init__(self):
        """Initialize session manager with fresh context."""
        self.context = SessionContext()

    def connect_to(self, instance_name: str) -> None:
        """Connect to an instance.

        Args:
            instance_name: Name of instance to connect to.
        """
        self.context.connect_to(instance_name)

    def disconnect(self) -> None:
        """Disconnect from current instance."""
        self.context.disconnect()

    def add_user_message(self, content: str) -> None:
        """Add a user message to conversation history.

        Args:
            content: User message content.
        """
        self.context.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to conversation history.

        Args:
            content: Assistant message content.
        """
        self.context.add_message("assistant", content)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.context.clear_history()

    def reset(self) -> None:
        """Reset session to initial state."""
        self.context = SessionContext()
