"""
Service Management Interfaces for Claude MPM Framework
=====================================================

WHY: This module contains interfaces for various service operations including
memory management, hooks, WebSocket/SocketIO communication, project analysis,
and ticket management. These are grouped as "services" because they provide
specific business functionality.

DESIGN DECISION: Service interfaces are separated from infrastructure and agent
interfaces because they represent higher-level business services that build
upon the infrastructure layer.

EXTRACTED FROM: services/core/interfaces.py (lines 876-1397)
- Memory service and hooks
- WebSocket/SocketIO communication
- Project analysis and ticket management
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Version service interface
class VersionServiceInterface(ABC):
    """Interface for version detection and formatting.

    WHY: Version detection involves multiple fallback methods and different
    formatting requirements. This interface abstracts version logic to enable
    different version detection strategies and improve testability.

    DESIGN DECISION: Provides both raw version and formatted version methods
    to support different display contexts and enable caching of version data.
    """

    @abstractmethod
    def get_version(self) -> str:
        """Get the current version string.

        Returns:
            Version string in semantic version format
        """

    @abstractmethod
    def get_version_info(self) -> Dict[str, Any]:
        """Get detailed version information.

        Returns:
            Dictionary with version details and metadata
        """

    @abstractmethod
    def format_version_display(self, include_build: bool = False) -> str:
        """Format version for display purposes.

        Args:
            include_build: Whether to include build information

        Returns:
            Formatted version string for display
        """

    @abstractmethod
    def check_for_updates(self) -> Dict[str, Any]:
        """Check for available updates.

        Returns:
            Dictionary with update information
        """


# Command handler interface
class CommandHandlerInterface(ABC):
    """Interface for handling MPM commands.

    WHY: MPM command handling involves parsing, routing, and execution logic
    that should be separated from the main runner. This interface abstracts
    command handling to enable different command processing strategies.

    DESIGN DECISION: Commands return structured results to enable consistent
    error handling and response formatting across different command types.
    """

    @abstractmethod
    def handle_command(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Handle an MPM command.

        Args:
            command: Command name to execute
            args: Command arguments

        Returns:
            Dictionary with command execution results
        """

    @abstractmethod
    def get_available_commands(self) -> List[str]:
        """Get list of available commands.

        Returns:
            List of available command names
        """

    @abstractmethod
    def get_command_help(self, command: str) -> str:
        """Get help text for a specific command.

        Args:
            command: Command name

        Returns:
            Help text for the command
        """


# Memory hook interface
class MemoryHookInterface(ABC):
    """Interface for memory hook management.

    WHY: Memory management involves registering hooks at various points in the
    Claude interaction lifecycle. This interface abstracts memory hook logic
    to enable different memory management strategies.

    DESIGN DECISION: Provides both hook registration and status methods for
    comprehensive memory management integration.
    """

    @abstractmethod
    def register_memory_hooks(self):
        """Register memory-related hooks with the hook service."""

    @abstractmethod
    def unregister_memory_hooks(self):
        """Unregister memory-related hooks from the hook service."""

    @abstractmethod
    def get_hook_status(self) -> Dict[str, Any]:
        """Get status of registered memory hooks.

        Returns:
            Dictionary with hook status information
        """


# Session management interface
class SessionManagementInterface(ABC):
    """Interface for session management and orchestration.

    WHY: Session management involves complex orchestration of multiple services
    and lifecycle management. This interface abstracts session logic to enable
    different session management strategies.

    DESIGN DECISION: Provides both synchronous and asynchronous session methods
    to support different execution contexts and enable proper cleanup.
    """

    @abstractmethod
    def start_session(self, session_config: Dict[str, Any]) -> str:
        """Start a new session.

        Args:
            session_config: Configuration for the session

        Returns:
            Session ID
        """

    @abstractmethod
    def end_session(self, session_id: str) -> bool:
        """End an active session.

        Args:
            session_id: ID of session to end

        Returns:
            True if session ended successfully
        """

    @abstractmethod
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a session.

        Args:
            session_id: ID of session

        Returns:
            Dictionary with session status information
        """

    @abstractmethod
    def list_active_sessions(self) -> List[str]:
        """List all active session IDs.

        Returns:
            List of active session IDs
        """

    @abstractmethod
    async def cleanup_sessions(self) -> int:
        """Clean up inactive or expired sessions.

        Returns:
            Number of sessions cleaned up
        """


# Utility service interface
class UtilityServiceInterface(ABC):
    """Interface for utility functions and helper methods.

    WHY: Utility functions are often scattered throughout the codebase and
    can benefit from centralization. This interface provides a clean way
    to access common utility functions.

    DESIGN DECISION: Groups related utility functions into logical categories
    to maintain organization while providing a single access point.
    """

    @abstractmethod
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string (e.g., "1.5 MB")
        """

    @abstractmethod
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string (e.g., "2m 30s")
        """

    @abstractmethod
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem usage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """

    @abstractmethod
    def generate_unique_id(self, prefix: str = "") -> str:
        """Generate a unique identifier.

        Args:
            prefix: Optional prefix for the ID

        Returns:
            Unique identifier string
        """

    @abstractmethod
    def validate_path(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Validate a filesystem path.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """


# Memory service interface
class MemoryServiceInterface(ABC):
    """Interface for memory management operations.

    WHY: Memory management is crucial for agent learning and context retention.
    This interface abstracts memory storage, retrieval, and optimization to
    enable different backends (file-based, database, distributed cache).

    DESIGN DECISION: Memory operations return success/failure status to enable
    proper error handling and fallback strategies when memory is unavailable.
    """

    @abstractmethod
    def load_memory(self, agent_id: str) -> Optional[str]:
        """Load memory for a specific agent.

        Args:
            agent_id: Identifier of the agent

        Returns:
            Memory content as string or None if not found
        """

    @abstractmethod
    def save_memory(self, agent_id: str, content: str) -> bool:
        """Save memory for a specific agent.

        Args:
            agent_id: Identifier of the agent
            content: Memory content to save

        Returns:
            True if save successful
        """

    @abstractmethod
    def validate_memory_size(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate memory content size and structure.

        Args:
            content: Memory content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """

    @abstractmethod
    def optimize_memory(self, agent_id: str) -> bool:
        """Optimize memory by removing duplicates and consolidating entries.

        Args:
            agent_id: Identifier of the agent

        Returns:
            True if optimization successful
        """

    @abstractmethod
    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent.

        Args:
            agent_id: Identifier of the agent

        Returns:
            Dictionary with memory statistics
        """


# Hook service interface
class HookServiceInterface(ABC):
    """Interface for hook execution operations.

    WHY: Hooks provide extensibility points for the framework, allowing plugins
    and extensions to modify behavior. This interface ensures consistent hook
    registration, priority handling, and execution across different hook systems.

    DESIGN DECISION: Hooks support priority ordering and conditional execution
    to enable complex plugin interactions and performance optimization.
    """

    @abstractmethod
    def register_hook(
        self, hook_name: str, callback: callable, priority: int = 0
    ) -> str:
        """Register a hook callback.

        Args:
            hook_name: Name of the hook point
            callback: Function to call when hook is triggered
            priority: Execution priority (higher = earlier)

        Returns:
            Hook registration ID
        """

    @abstractmethod
    def unregister_hook(self, registration_id: str) -> bool:
        """Unregister a hook callback.

        Args:
            registration_id: ID returned from register_hook

        Returns:
            True if unregistration successful
        """

    @abstractmethod
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute all callbacks for a hook.

        Args:
            hook_name: Name of the hook point
            *args: Positional arguments for callbacks
            **kwargs: Keyword arguments for callbacks

        Returns:
            List of callback return values
        """

    @abstractmethod
    def get_hook_info(self, hook_name: str) -> Dict[str, Any]:
        """Get information about registered hooks.

        Args:
            hook_name: Name of the hook point

        Returns:
            Dictionary with hook information
        """
