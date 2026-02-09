"""Base classes for claude-mpm tools framework.

WHY: Provides consistent interface for bulk operations across MCP services.
Tools bypass MCP protocol overhead for batch operations.

DESIGN:
- BaseToolModule: Abstract base for service-specific tools
- Standard JSON output format for agent parsing
- Integrates with existing TokenStorage/OAuthManager
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from claude_mpm.auth import OAuthManager, TokenStorage


class ToolResult:
    """Standardized result format for tool operations."""

    def __init__(
        self,
        success: bool,
        action: str,
        data: Any = None,
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.success = success
        self.action = action
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "action": self.action,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseToolModule(ABC):
    """Abstract base class for service-specific tool modules.

    Each service (google, slack, notion) implements this interface to provide
    consistent CLI access to bulk operations.

    Example:
        class GoogleTools(BaseToolModule):
            def get_actions(self) -> list[str]:
                return ["gmail-export", "calendar-bulk-create"]

            def execute(self, action: str, **kwargs) -> ToolResult:
                if action == "gmail-export":
                    return self._gmail_export(**kwargs)
                ...
    """

    def __init__(
        self,
        storage: Optional[TokenStorage] = None,
        manager: Optional[OAuthManager] = None,
    ):
        """Initialize tool module with auth components.

        Args:
            storage: TokenStorage for credential management
            manager: OAuthManager for token refresh
        """
        self.storage = storage or TokenStorage()
        self.manager = manager or OAuthManager(storage=self.storage)

    @abstractmethod
    def get_service_name(self) -> str:
        """Return the service name (e.g., 'google', 'slack')."""

    @abstractmethod
    def get_actions(self) -> list[str]:
        """Return list of available actions for this service."""

    @abstractmethod
    def get_action_help(self, action: str) -> str:
        """Return help text for a specific action."""

    @abstractmethod
    def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute the specified action with given arguments.

        Args:
            action: Action name (e.g., 'gmail-export')
            **kwargs: Action-specific arguments

        Returns:
            ToolResult with success/data/error information

        Raises:
            ValueError: If action is not supported
        """

    def validate_action(self, action: str) -> None:
        """Validate that action is supported.

        Args:
            action: Action name to validate

        Raises:
            ValueError: If action is not in get_actions()
        """
        available = self.get_actions()
        if action not in available:
            raise ValueError(
                f"Unknown action '{action}' for {self.get_service_name()} service. "
                f"Available: {', '.join(available)}"
            )


__all__ = ["BaseToolModule", "ToolResult"]
