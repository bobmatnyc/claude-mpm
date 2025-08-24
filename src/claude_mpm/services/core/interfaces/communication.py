"""
Communication and External Service Interfaces for Claude MPM Framework
======================================================================

WHY: This module contains interfaces for external communication including
WebSocket/SocketIO services, project analysis, and ticket management.
These are grouped together because they handle external interactions.

DESIGN DECISION: Communication interfaces are separated because they deal
with external systems and protocols, requiring different error handling
and reliability patterns than internal services.

EXTRACTED FROM: services/core/interfaces.py (lines 1195-1397)
- WebSocket/SocketIO communication
- Project analysis
- Ticket management
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


# WebSocket/SocketIO service interface
class SocketIOServiceInterface(ABC):
    """Interface for WebSocket communication.

    WHY: Real-time communication is essential for monitoring and interactive
    features. This interface abstracts WebSocket/SocketIO implementation to
    enable different transport mechanisms and fallback strategies.

    DESIGN DECISION: Provides both broadcasting and targeted messaging to
    support different communication patterns and enable efficient updates.
    """

    @abstractmethod
    def start_sync(self) -> None:
        """Start the WebSocket server synchronously."""

    @abstractmethod
    def stop_sync(self) -> None:
        """Stop the WebSocket server synchronously."""

    @abstractmethod
    def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast an event to all connected clients.

        Args:
            event_type: Type of event to broadcast
            data: Event data to send
        """

    @abstractmethod
    def send_to_client(
        self, client_id: str, event_type: str, data: Dict[str, Any]
    ) -> bool:
        """Send an event to a specific client.

        Args:
            client_id: ID of the target client
            event_type: Type of event to send
            data: Event data to send

        Returns:
            True if message sent successfully
        """

    @abstractmethod
    def get_connection_count(self) -> int:
        """Get number of connected clients.

        Returns:
            Number of connected clients
        """

    @abstractmethod
    def is_running(self) -> bool:
        """Check if server is running.

        Returns:
            True if server is active
        """

    @abstractmethod
    def session_started(
        self, session_id: str, launch_method: str, working_dir: str
    ) -> None:
        """Notify that a session has started.

        Args:
            session_id: ID of the started session
            launch_method: Method used to launch the session
            working_dir: Working directory of the session
        """

    @abstractmethod
    def session_ended(self) -> None:
        """Notify that a session has ended."""

    @abstractmethod
    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ) -> None:
        """Notify Claude status change.

        Args:
            status: New status of Claude
            pid: Process ID if applicable
            message: Optional status message
        """

    @abstractmethod
    def agent_delegated(self, agent: str, task: str, status: str = "started") -> None:
        """Notify agent delegation.

        Args:
            agent: Name of the delegated agent
            task: Task assigned to the agent
            status: Status of the delegation
        """

    @abstractmethod
    def todo_updated(self, todos: List[Dict[str, Any]]) -> None:
        """Notify todo list update.

        Args:
            todos: Updated list of todo items
        """


# Project analyzer interface
class ProjectAnalyzerInterface(ABC):
    """Interface for project analysis operations.

    WHY: Understanding project structure and characteristics is essential for
    context-aware agent behavior. This interface abstracts project analysis
    to support different project types and structures.

    DESIGN DECISION: Analysis methods return structured data to enable caching
    and incremental updates when project structure changes.
    """

    @abstractmethod
    def analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure and characteristics.

        Args:
            project_path: Path to the project root

        Returns:
            Dictionary with project analysis results
        """

    @abstractmethod
    def detect_technology_stack(self) -> List[str]:
        """Detect technologies used in the project.

        Returns:
            List of detected technologies
        """

    @abstractmethod
    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and conventions.

        Returns:
            Dictionary of pattern analysis results
        """

    @abstractmethod
    def get_project_structure(self) -> Dict[str, Any]:
        """Get project directory structure analysis.

        Returns:
            Dictionary representing project structure
        """

    @abstractmethod
    def identify_entry_points(self) -> List[Path]:
        """Identify project entry points.

        Returns:
            List of entry point paths
        """

    @abstractmethod
    def get_dependencies(self) -> Dict[str, List[str]]:
        """Get project dependencies by type.

        Returns:
            Dictionary mapping dependency types to lists of dependencies
        """

    @abstractmethod
    def analyze_test_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage if available.

        Returns:
            Dictionary with test coverage information
        """

    @abstractmethod
    def get_build_configuration(self) -> Dict[str, Any]:
        """Get build configuration information.

        Returns:
            Dictionary with build configuration details
        """


# Ticket manager interface
class TicketManagerInterface(ABC):
    """Interface for ticket management operations.

    WHY: Ticket management provides work tracking and organization. This
    interface abstracts ticket operations to support different backend
    systems (file-based, API-based, database).

    DESIGN DECISION: Ticket operations return success/failure status to enable
    proper error handling and fallback strategies when ticket systems are unavailable.
    """

    @abstractmethod
    def create_ticket(
        self, title: str, description: str, priority: str = "medium"
    ) -> str:
        """Create a new ticket.

        Args:
            title: Ticket title
            description: Ticket description
            priority: Ticket priority level

        Returns:
            Ticket ID
        """

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket by ID.

        Args:
            ticket_id: ID of ticket to retrieve

        Returns:
            Ticket data or None if not found
        """

    @abstractmethod
    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        """Update ticket information.

        Args:
            ticket_id: ID of ticket to update
            updates: Dictionary of fields to update

        Returns:
            True if update successful
        """

    @abstractmethod
    def list_tickets(
        self, status: Optional[str] = None, priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List tickets with optional filtering.

        Args:
            status: Optional status filter
            priority: Optional priority filter

        Returns:
            List of ticket data
        """

    @abstractmethod
    def assign_ticket(self, ticket_id: str, assignee: str) -> bool:
        """Assign ticket to a user.

        Args:
            ticket_id: ID of ticket to assign
            assignee: User to assign ticket to

        Returns:
            True if assignment successful
        """

    @abstractmethod
    def close_ticket(self, ticket_id: str, resolution: Optional[str] = None) -> bool:
        """Close a ticket.

        Args:
            ticket_id: ID of ticket to close
            resolution: Optional resolution description

        Returns:
            True if close successful
        """

    @abstractmethod
    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """Search tickets by query.

        Args:
            query: Search query string

        Returns:
            List of matching ticket data
        """

    @abstractmethod
    def get_ticket_statistics(self) -> Dict[str, Any]:
        """Get ticket statistics.

        Returns:
            Dictionary with ticket statistics
        """
