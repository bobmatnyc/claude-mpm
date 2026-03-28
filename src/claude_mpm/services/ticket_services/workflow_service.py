"""
Workflow service for ticket state transitions.

WHY: Manages ticket workflow states and transitions, ensuring valid
state changes and maintaining workflow integrity.

DESIGN DECISIONS:
- Enforces valid state transitions
- Direct aitrackdown CLI calls have been removed; ticket operations
  should go through the mcp-ticketer MCP server via the ticketing_agent.
- Provides workflow history tracking
- Workflow state validation is kept for reference/documentation.
"""

import logging
from typing import Any

from ...core.logger import get_logger

_deprecation_logger = logging.getLogger(__name__)


class TicketWorkflowService:
    """Service for managing ticket workflow states."""

    # Valid workflow transitions
    WORKFLOW_TRANSITIONS = {
        "todo": ["in_progress", "blocked"],
        "in_progress": ["ready", "blocked", "todo"],
        "ready": ["tested", "in_progress", "blocked"],
        "tested": ["done", "ready", "blocked"],
        "done": ["tested", "ready"],  # Can reopen
        "blocked": ["todo", "in_progress", "ready"],
    }

    # Status to workflow state mapping
    STATUS_TO_WORKFLOW = {
        "open": "todo",
        "in_progress": "in_progress",
        "ready": "ready",
        "tested": "tested",
        "done": "done",
        "closed": "done",
        "blocked": "blocked",
        "waiting": "blocked",
    }

    def __init__(self):
        """Initialize the workflow service."""
        self.logger = get_logger("services.ticket_workflow")

    def transition_ticket(
        self,
        ticket_id: str,
        new_state: str,
        comment: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Transition a ticket to a new workflow state.

        Direct aitrackdown CLI transitions have been removed.
        Use mcp-ticketer MCP tools via the ticketing_agent instead.

        Args:
            ticket_id: ID of the ticket
            new_state: Target workflow state
            comment: Optional comment for the transition
            force: Force transition even if not normally allowed

        Returns:
            Dict with success status and message
        """
        _deprecation_logger.warning(
            "Direct ticket transitions deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent."
        )
        return {
            "success": False,
            "error": "Direct ticket transitions deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent.",
        }

    def validate_transition(
        self, ticket_id: str, new_state: str
    ) -> tuple[bool, str | None]:
        """
        Validate if a workflow transition is allowed.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if new_state not in self.WORKFLOW_TRANSITIONS:
            return False, f"Invalid workflow state: {new_state}"

        return True, None

    def add_comment(self, ticket_id: str, comment: str) -> dict[str, Any]:
        """
        Add a comment to a ticket.

        Direct aitrackdown CLI comments have been removed.
        Use mcp-ticketer MCP tools via the ticketing_agent instead.

        Args:
            ticket_id: ID of the ticket
            comment: Comment text

        Returns:
            Dict with success status and message
        """
        _deprecation_logger.warning(
            "Direct ticket comments deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent."
        )
        return {
            "success": False,
            "error": "Direct ticket comments deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent.",
        }

    def get_workflow_states(self) -> list[str]:
        """
        Get list of all valid workflow states.

        Returns:
            List of workflow state names
        """
        return list(self.WORKFLOW_TRANSITIONS.keys())

    def get_valid_transitions(self, current_state: str) -> list[str]:
        """
        Get valid transitions from a given state.

        Args:
            current_state: Current workflow state

        Returns:
            List of valid target states
        """
        return self.WORKFLOW_TRANSITIONS.get(current_state, [])

    def map_status_to_workflow(self, status: str) -> str:
        """
        Map a ticket status to a workflow state.

        Args:
            status: Ticket status

        Returns:
            Corresponding workflow state
        """
        return self.STATUS_TO_WORKFLOW.get(status, "todo")

    def bulk_transition(
        self, ticket_ids: list[str], new_state: str, comment: str | None = None
    ) -> dict[str, Any]:
        """
        Transition multiple tickets to a new state.

        Direct aitrackdown CLI transitions have been removed.
        Use mcp-ticketer MCP tools via the ticketing_agent instead.

        Args:
            ticket_ids: List of ticket IDs
            new_state: Target workflow state
            comment: Optional comment for all transitions

        Returns:
            Dict with results for each ticket
        """
        _deprecation_logger.warning(
            "Direct bulk ticket transitions deprecated. "
            "Use mcp-ticketer MCP tools via ticketing_agent."
        )
        return {
            "success": False,
            "results": {
                "succeeded": [],
                "failed": [
                    {"ticket_id": tid, "error": "Deprecated"} for tid in ticket_ids
                ],
                "total": len(ticket_ids),
            },
        }

    def get_workflow_summary(self, tickets: list[dict[str, Any]]) -> dict[str, int]:
        """
        Get summary of tickets by workflow state.

        Args:
            tickets: List of ticket dictionaries

        Returns:
            Dict mapping workflow states to counts
        """
        summary = dict.fromkeys(self.WORKFLOW_TRANSITIONS.keys(), 0)
        summary["unknown"] = 0

        for ticket in tickets:
            status = ticket.get("status", "unknown")
            workflow_state = self.map_status_to_workflow(status)

            if workflow_state in summary:
                summary[workflow_state] += 1
            else:
                summary["unknown"] += 1

        return summary
