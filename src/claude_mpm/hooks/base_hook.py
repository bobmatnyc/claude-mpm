"""Base hook class and types for claude-mpm hook system."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class HookType(Enum):
    """Types of hooks available in the system."""

    SUBMIT = "submit"  # Process user prompts
    PRE_DELEGATION = "pre_delegation"  # Filter context before delegation
    POST_DELEGATION = "post_delegation"  # Process results after delegation
    TICKET_EXTRACTION = "ticket_extraction"  # Extract and create tickets
    CUSTOM = "custom"  # User-defined hooks


@dataclass
class HookContext:
    """Context passed to hooks for processing."""

    hook_type: HookType
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    def __post_init__(self):
        """Ensure timestamp is set."""
        if not hasattr(self, "timestamp") or self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class HookResult:
    """Result returned from hook execution."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    modified: bool = False
    metadata: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None


class BaseHook(ABC):
    """Base class for all hooks."""

    def __init__(self, name: str, priority: int = 50):
        """Initialize hook with name and priority.

        Args:
            name: Unique name for the hook
            priority: Execution priority (0-100, lower executes first)
        """
        self.name = name
        self.priority = max(0, min(100, priority))  # Clamp to 0-100
        self.enabled = True
        self._async = False

    @abstractmethod
    def execute(self, context: HookContext) -> HookResult:
        """Execute the hook with given context.

        Args:
            context: Hook context containing data and metadata

        Returns:
            HookResult with execution results
        """

    async def async_execute(self, context: HookContext) -> HookResult:
        """Async version of execute. Override for async hooks."""
        # Default implementation calls sync execute in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, context)

    def validate(self, context: HookContext) -> bool:
        """Validate if hook should run for given context.

        Args:
            context: Hook context to validate

        Returns:
            True if hook should execute, False otherwise
        """
        return self.enabled

    def __repr__(self):
        """String representation of hook."""
        return f"{self.__class__.__name__}(name='{self.name}', priority={self.priority}, enabled={self.enabled})"

    def __lt__(self, other):
        """Compare hooks by priority for sorting."""
        if not isinstance(other, BaseHook):
            return NotImplemented
        return self.priority < other.priority


class SubmitHook(BaseHook):
    """Base class for hooks that process user prompts."""

    def __init__(self, name: str, priority: int = 50):
        super().__init__(name, priority)

    def validate(self, context: HookContext) -> bool:
        """Validate submit hook context."""
        if not super().validate(context):
            return False
        return context.hook_type == HookType.SUBMIT and "prompt" in context.data


class PreDelegationHook(BaseHook):
    """Base class for hooks that filter context before delegation."""

    def __init__(self, name: str, priority: int = 50):
        super().__init__(name, priority)

    def validate(self, context: HookContext) -> bool:
        """Validate pre-delegation hook context."""
        if not super().validate(context):
            return False
        return context.hook_type == HookType.PRE_DELEGATION and "agent" in context.data


class PostDelegationHook(BaseHook):
    """Base class for hooks that process results after delegation."""

    def __init__(self, name: str, priority: int = 50):
        super().__init__(name, priority)

    def validate(self, context: HookContext) -> bool:
        """Validate post-delegation hook context."""
        if not super().validate(context):
            return False
        return (
            context.hook_type == HookType.POST_DELEGATION and "result" in context.data
        )


class TicketExtractionHook(BaseHook):
    """Base class for hooks that extract and create tickets."""

    def __init__(self, name: str, priority: int = 50):
        super().__init__(name, priority)

    def validate(self, context: HookContext) -> bool:
        """Validate ticket extraction hook context."""
        if not super().validate(context):
            return False
        return context.hook_type == HookType.TICKET_EXTRACTION
