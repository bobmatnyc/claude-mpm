"""
Workflow service for ticket state transitions.

WHY: Manages ticket workflow states and transitions, ensuring valid
state changes and maintaining workflow integrity.

DESIGN DECISIONS:
- Enforces valid state transitions
- Handles workflow-specific operations (comments, notifications)
- Provides workflow history tracking
- Abstracts aitrackdown workflow commands
"""

import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ...core.logger import get_logger


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
        comment: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Transition a ticket to a new workflow state.

        Args:
            ticket_id: ID of the ticket
            new_state: Target workflow state
            comment: Optional comment for the transition
            force: Force transition even if not normally allowed

        Returns:
            Dict with success status and message
        """
        try:
            # Validate the transition if not forced
            if not force:
                valid, error = self.validate_transition(ticket_id, new_state)
                if not valid:
                    return {"success": False, "error": error}

            # Use aitrackdown CLI for the transition
            result = self._transition_via_aitrackdown(ticket_id, new_state, comment)

            if result["success"]:
                # Log successful transition
                self.logger.info(f"Transitioned {ticket_id} to {new_state}")

            return result

        except Exception as e:
            self.logger.error(f"Error transitioning ticket {ticket_id}: {e}")
            return {"success": False, "error": str(e)}

    def _transition_via_aitrackdown(
        self, ticket_id: str, state: str, comment: Optional[str]
    ) -> Dict[str, Any]:
        """Transition ticket using aitrackdown CLI."""
        try:
            cmd = ["aitrackdown", "transition", ticket_id, state]

            if comment:
                cmd.extend(["--comment", comment])

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            return {
                "success": True,
                "message": f"Updated workflow state for {ticket_id} to: {state}",
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to transition via CLI: {e}")
            return {
                "success": False,
                "error": f"Failed to update workflow state for ticket: {ticket_id}",
            }

    def validate_transition(
        self, ticket_id: str, new_state: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a workflow transition is allowed.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # For now, we assume all transitions are valid since we don't
        # have access to current state without fetching the ticket
        # In a real implementation, this would check current state

        if new_state not in self.WORKFLOW_TRANSITIONS:
            return False, f"Invalid workflow state: {new_state}"

        # TODO: Fetch current state and validate transition
        # current_state = self._get_current_state(ticket_id)
        # if new_state not in self.WORKFLOW_TRANSITIONS.get(current_state, []):
        #     return False, f"Cannot transition from {current_state} to {new_state}"

        return True, None

    def add_comment(self, ticket_id: str, comment: str) -> Dict[str, Any]:
        """
        Add a comment to a ticket.

        Args:
            ticket_id: ID of the ticket
            comment: Comment text

        Returns:
            Dict with success status and message
        """
        try:
            cmd = ["aitrackdown", "comment", ticket_id, comment]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            return {"success": True, "message": f"Added comment to ticket: {ticket_id}"}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to add comment: {e}")
            return {
                "success": False,
                "error": f"Failed to add comment to ticket: {ticket_id}",
            }

    def get_workflow_states(self) -> List[str]:
        """
        Get list of all valid workflow states.

        Returns:
            List of workflow state names
        """
        return list(self.WORKFLOW_TRANSITIONS.keys())

    def get_valid_transitions(self, current_state: str) -> List[str]:
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
        self, ticket_ids: List[str], new_state: str, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transition multiple tickets to a new state.

        Args:
            ticket_ids: List of ticket IDs
            new_state: Target workflow state
            comment: Optional comment for all transitions

        Returns:
            Dict with results for each ticket
        """
        results = {"succeeded": [], "failed": [], "total": len(ticket_ids)}

        for ticket_id in ticket_ids:
            result = self.transition_ticket(ticket_id, new_state, comment)

            if result["success"]:
                results["succeeded"].append(ticket_id)
            else:
                results["failed"].append(
                    {
                        "ticket_id": ticket_id,
                        "error": result.get("error", "Unknown error"),
                    }
                )

        return {"success": len(results["failed"]) == 0, "results": results}

    def get_workflow_summary(self, tickets: List[Dict[str, Any]]) -> Dict[str, int]:
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
