"""
CRUD operations service for tickets.

WHY: Centralizes all Create, Read, Update, Delete operations for tickets,
separating data access from presentation logic.

DESIGN DECISIONS:
- Uses TicketManager as backend (can be replaced with actual implementation)
- Returns standardized response objects
- Handles aitrackdown CLI fallback for operations not in TicketManager
- Provides consistent error handling
"""

import json
import subprocess
from typing import Any, Dict, List, Optional

from ...core.logger import get_logger


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
        tags: Optional[List[str]] = None,
        parent_epic: Optional[str] = None,
        parent_issue: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
        """
        List tickets with pagination and filtering.

        Returns:
            Dict with tickets list and pagination info
        """
        try:
            # Try aitrackdown CLI first for better pagination
            tickets = self._list_via_aitrackdown(
                limit, page, page_size, type_filter, status_filter
            )

            if tickets is None:
                # Fallback to TicketManager
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

    def _list_via_aitrackdown(
        self,
        limit: int,
        page: int,
        page_size: int,
        type_filter: str,
        status_filter: str,
    ) -> Optional[List[Dict]]:
        """List tickets using aitrackdown CLI."""
        try:
            cmd = ["aitrackdown", "status", "tasks"]

            # Calculate offset for pagination
            offset = (page - 1) * page_size
            total_needed = offset + page_size
            cmd.extend(["--limit", str(total_needed * 2)])

            # Add filters
            if type_filter != "all":
                cmd.extend(["--type", type_filter])
            if status_filter != "all":
                cmd.extend(["--status", status_filter])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if result.stdout.strip():
                all_tickets = json.loads(result.stdout)
                if isinstance(all_tickets, list):
                    # Apply pagination
                    return all_tickets[offset : offset + page_size]
            return []
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            json.JSONDecodeError,
        ) as e:
            self.logger.debug(f"aitrackdown not available: {e}")
            return None

    def _list_via_manager(
        self,
        limit: int,
        page: int,
        page_size: int,
        type_filter: str,
        status_filter: str,
    ) -> List[Dict]:
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
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
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

            # Try TicketManager first
            success = self.ticket_manager.update_task(ticket_id, **updates)

            if success:
                return {"success": True, "message": f"Updated ticket: {ticket_id}"}

            # Fallback to aitrackdown CLI for status transitions
            if status:
                return self._update_via_aitrackdown(ticket_id, status, updates)

            return {"success": False, "error": f"Failed to update ticket: {ticket_id}"}
        except Exception as e:
            self.logger.error(f"Error updating ticket {ticket_id}: {e}")
            return {"success": False, "error": str(e)}

    def _update_via_aitrackdown(
        self, ticket_id: str, status: str, updates: Dict
    ) -> Dict[str, Any]:
        """Update ticket using aitrackdown CLI."""
        try:
            cmd = ["aitrackdown", "transition", ticket_id, status]

            # Add comment with other updates
            comment_parts = []
            if updates.get("priority"):
                comment_parts.append(f"Priority: {updates['priority']}")
            if updates.get("assignees"):
                comment_parts.append(f"Assigned to: {', '.join(updates['assignees'])}")
            if updates.get("tags"):
                comment_parts.append(f"Tags: {', '.join(updates['tags'])}")

            if comment_parts:
                comment = " | ".join(comment_parts)
                cmd.extend(["--comment", comment])

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return {"success": True, "message": f"Updated ticket: {ticket_id}"}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update via CLI: {e}")
            return {"success": False, "error": f"Failed to update ticket: {ticket_id}"}

    def close_ticket(
        self, ticket_id: str, resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Close a ticket.

        Returns:
            Dict with success status and message
        """
        try:
            # Try TicketManager first
            success = self.ticket_manager.close_task(ticket_id, resolution=resolution)

            if success:
                return {"success": True, "message": f"Closed ticket: {ticket_id}"}

            # Fallback to aitrackdown CLI
            return self._close_via_aitrackdown(ticket_id, resolution)
        except Exception as e:
            self.logger.error(f"Error closing ticket {ticket_id}: {e}")
            return {"success": False, "error": str(e)}

    def _close_via_aitrackdown(
        self, ticket_id: str, resolution: Optional[str]
    ) -> Dict[str, Any]:
        """Close ticket using aitrackdown CLI."""
        try:
            cmd = ["aitrackdown", "close", ticket_id]
            if resolution:
                cmd.extend(["--comment", resolution])

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return {"success": True, "message": f"Closed ticket: {ticket_id}"}
        except subprocess.CalledProcessError:
            return {"success": False, "error": f"Failed to close ticket: {ticket_id}"}

    def delete_ticket(self, ticket_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a ticket.

        Returns:
            Dict with success status and message
        """
        try:
            cmd = ["aitrackdown", "delete", ticket_id]
            if force:
                cmd.append("--force")

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return {"success": True, "message": f"Deleted ticket: {ticket_id}"}
        except subprocess.CalledProcessError:
            return {"success": False, "error": f"Failed to delete ticket: {ticket_id}"}
        except Exception as e:
            self.logger.error(f"Error deleting ticket {ticket_id}: {e}")
            return {"success": False, "error": str(e)}
