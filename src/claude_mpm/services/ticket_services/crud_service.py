"""
CRUD operations service for tickets.

WHY: Centralizes all Create, Read, Update, Delete operations for tickets,
separating data access from presentation logic.

DESIGN DECISIONS:
- Uses TicketManager as backend (can be replaced with actual implementation)
- Returns standardized response objects
- Direct ticket CLI operations (aitrackdown) have been removed; ticket
  operations should go through the mcp-ticketer MCP server via the
  ticketing_agent.
- Provides consistent error handling
"""

import logging
from typing import Any

from ...core.logger import get_logger

_deprecation_logger = logging.getLogger(__name__)


class TicketCRUDService:
    """Service for ticket CRUD operations."""

    def __init__(self, ticket_manager=None):
        """
        Initialize the CRUD service.

        Args:
            ticket_manager: Optional ticket manager instance for testing
        """
        self.logger = get_logger("services.ticket_crud")
        self._ticket_manager = ticket_manager

    @property
    def ticket_manager(self):
        """Lazy load ticket manager."""
        if self._ticket_manager is None:
            try:
                from ..ticket_manager import TicketManager
            except ImportError:
                from claude_mpm.services.ticket_manager import TicketManager
            self._ticket_manager = TicketManager()
        return self._ticket_manager

    def create_ticket(
        self,
        title: str,
        ticket_type: str = "task",
        priority: str = "medium",
        description: str = "",
        tags: list[str] | None = None,
        parent_epic: str | None = None,
        parent_issue: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new ticket.

        Returns:
            Dict with success status and ticket_id or error message
        """
        try:
            ticket_id = self.ticket_manager.create_ticket(
                title=title,
                ticket_type=ticket_type,
                description=description,
                priority=priority,
                tags=tags or [],
                source="claude-mpm-cli",
                parent_epic=parent_epic,
                parent_issue=parent_issue,
            )

            if ticket_id:
                return {
                    "success": True,
                    "ticket_id": ticket_id,
                    "message": f"Created ticket: {ticket_id}",
                }
            return {"success": False, "error": "Failed to create ticket"}
        except Exception as e:
            self.logger.error(f"Error creating ticket: {e}")
            return {"success": False, "error": str(e)}

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """
        Get a specific ticket by ID.

        Returns:
            Ticket data or None if not found
        """
        try:
            return self.ticket_manager.get_ticket(ticket_id)
        except Exception as e:
            self.logger.error(f"Error getting ticket {ticket_id}: {e}")
            return None

    def list_tickets(
        self,
        limit: int = 20,
        page: int = 1,
        page_size: int = 20,
        type_filter: str = "all",
        status_filter: str = "all",
    ) -> dict[str, Any]:
        """
        List tickets with pagination and filtering.

        Returns:
            Dict with tickets list and pagination info
        """
        try:
            tickets = self._list_via_manager(
                limit, page, page_size, type_filter, status_filter
            )

            return {
                "success": True,
                "tickets": tickets,
                "page": page,
                "page_size": page_size,
                "total_shown": len(tickets),
            }
        except Exception as e:
            self.logger.error(f"Error listing tickets: {e}")
            return {"success": False, "error": str(e), "tickets": []}

    def _list_via_manager(
        self,
        limit: int,
        page: int,
        page_size: int,
        type_filter: str,
        status_filter: str,
    ) -> list[dict]:
        """List tickets using TicketManager."""
        all_tickets = self.ticket_manager.list_recent_tickets(limit=limit * 2)

        # Apply filters
        filtered_tickets = []
        for ticket in all_tickets:
            if type_filter != "all":
                ticket_type = ticket.get("metadata", {}).get("ticket_type", "unknown")
                if ticket_type != type_filter:
                    continue

            if status_filter != "all":
                if ticket.get("status") != status_filter:
                    continue

            filtered_tickets.append(ticket)

        # Apply pagination
        offset = (page - 1) * page_size
        return filtered_tickets[offset : offset + page_size]

    def update_ticket(
        self,
        ticket_id: str,
        status: str | None = None,
        priority: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Update a ticket's properties.

        Returns:
            Dict with success status and message
        """
        try:
            updates = {}
            if status:
                updates["status"] = status
            if priority:
                updates["priority"] = priority
            if description:
                updates["description"] = description
            if tags:
                updates["tags"] = tags
            if assignees:
                updates["assignees"] = assignees

            if not updates:
                return {"success": False, "error": "No updates specified"}

            success = self.ticket_manager.update_task(ticket_id, **updates)

            if success:
                return {"success": True, "message": f"Updated ticket: {ticket_id}"}

            return {"success": False, "error": f"Failed to update ticket: {ticket_id}"}
        except Exception as e:
            self.logger.error(f"Error updating ticket {ticket_id}: {e}")
            return {"success": False, "error": str(e)}

    def close_ticket(
        self, ticket_id: str, resolution: str | None = None
    ) -> dict[str, Any]:
        """
        Close a ticket.

        Returns:
            Dict with success status and message
        """
        try:
            success = self.ticket_manager.close_task(ticket_id, resolution=resolution)

            if success:
                return {"success": True, "message": f"Closed ticket: {ticket_id}"}

            return {"success": False, "error": f"Failed to close ticket: {ticket_id}"}
        except Exception as e:
            self.logger.error(f"Error closing ticket {ticket_id}: {e}")
            return {"success": False, "error": str(e)}

    def delete_ticket(self, ticket_id: str, force: bool = False) -> dict[str, Any]:
        """
        Delete a ticket.

        Direct CLI deletion via aitrackdown has been removed.
        Use mcp-ticketer MCP tools via the ticketing_agent instead.

        Returns:
            Dict with success status and message
        """
        _deprecation_logger.warning(
            "Direct ticket deletion deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent."
        )
        return {
            "success": False,
            "error": "Direct ticket deletion deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent.",
        }
