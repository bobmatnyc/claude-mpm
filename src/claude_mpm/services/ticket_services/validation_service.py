"""
Input validation service for tickets.

WHY: Centralizes all validation logic to ensure data integrity and
provide consistent error messages across the ticket system.

DESIGN DECISIONS:
- Returns validation results with detailed error messages
- Validates ticket IDs, types, statuses, priorities
- Handles pagination parameter validation
- Provides sanitization for user inputs
"""

from typing import Any, Dict, List, Optional, Tuple


class TicketValidationService:
    """Service for validating ticket inputs."""

    # Valid ticket types
    VALID_TYPES = ["task", "issue", "epic", "bug", "feature", "story"]

    # Valid ticket statuses
    VALID_STATUSES = [
        "open",
        "in_progress",
        "ready",
        "tested",
        "done",
        "waiting",
        "closed",
        "blocked",
        "all",
    ]

    # Valid priorities
    VALID_PRIORITIES = ["low", "medium", "high", "critical"]

    # Valid workflow states
    VALID_WORKFLOW_STATES = [
        "todo",
        "in_progress",
        "ready",
        "tested",
        "done",
        "blocked",
    ]

    def validate_ticket_id(self, ticket_id: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a ticket ID.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ticket_id:
            return False, "No ticket ID provided"

        if not isinstance(ticket_id, str):
            return False, "Ticket ID must be a string"

        if len(ticket_id) < 3:
            return False, "Invalid ticket ID format"

        return True, None

    def validate_ticket_type(self, ticket_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a ticket type.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ticket_type:
            return True, None  # Type is optional, default will be used

        if ticket_type not in self.VALID_TYPES:
            return (
                False,
                f"Invalid ticket type: {ticket_type}. Valid types: {', '.join(self.VALID_TYPES)}",
            )

        return True, None

    def validate_status(self, status: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a ticket status.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not status:
            return True, None  # Status is optional

        if status not in self.VALID_STATUSES:
            return (
                False,
                f"Invalid status: {status}. Valid statuses: {', '.join(self.VALID_STATUSES)}",
            )

        return True, None

    def validate_priority(self, priority: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a ticket priority.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not priority:
            return True, None  # Priority is optional, default will be used

        if priority not in self.VALID_PRIORITIES:
            return (
                False,
                f"Invalid priority: {priority}. Valid priorities: {', '.join(self.VALID_PRIORITIES)}",
            )

        return True, None

    def validate_workflow_state(self, state: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a workflow state.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not state:
            return False, "No workflow state provided"

        if state not in self.VALID_WORKFLOW_STATES:
            return (
                False,
                f"Invalid workflow state: {state}. Valid states: {', '.join(self.VALID_WORKFLOW_STATES)}",
            )

        return True, None

    def validate_pagination(
        self, page: int, page_size: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate pagination parameters.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if page < 1:
            return False, "Page number must be 1 or greater"

        if page_size < 1:
            return False, "Page size must be 1 or greater"

        if page_size > 100:
            return False, "Page size cannot exceed 100"

        return True, None

    def validate_create_params(
        self, params: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters for ticket creation.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Title is required
        if not params.get("title"):
            return False, "Title is required for ticket creation"

        if len(params["title"]) < 3:
            return False, "Title must be at least 3 characters long"

        if len(params["title"]) > 200:
            return False, "Title cannot exceed 200 characters"

        # Validate optional fields if provided
        if "type" in params:
            valid, error = self.validate_ticket_type(params["type"])
            if not valid:
                return False, error

        if "priority" in params:
            valid, error = self.validate_priority(params["priority"])
            if not valid:
                return False, error

        # Validate parent references
        if params.get("parent_epic"):
            valid, error = self.validate_ticket_id(params["parent_epic"])
            if not valid:
                return False, f"Invalid parent epic: {error}"

        if params.get("parent_issue"):
            valid, error = self.validate_ticket_id(params["parent_issue"])
            if not valid:
                return False, f"Invalid parent issue: {error}"

        return True, None

    def validate_update_params(
        self, params: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters for ticket update.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # At least one update field must be provided
        update_fields = ["status", "priority", "description", "tags", "assign"]
        if not any(field in params for field in update_fields):
            return False, "No update fields specified"

        # Validate status if provided
        if "status" in params:
            valid, error = self.validate_status(params["status"])
            if not valid:
                return False, error

        # Validate priority if provided
        if "priority" in params:
            valid, error = self.validate_priority(params["priority"])
            if not valid:
                return False, error

        return True, None

    def sanitize_tags(self, tags: Any) -> List[str]:
        """
        Sanitize and parse tags input.

        Returns:
            List of sanitized tags
        """
        if not tags:
            return []

        if isinstance(tags, str):
            # Split comma-separated tags
            tag_list = [tag.strip() for tag in tags.split(",")]
        elif isinstance(tags, list):
            tag_list = [str(tag).strip() for tag in tags]
        else:
            return []

        # Remove empty tags and duplicates
        return list(filter(None, dict.fromkeys(tag_list)))

    def sanitize_description(self, description: Any) -> str:
        """
        Sanitize description input.

        Returns:
            Sanitized description string
        """
        if not description:
            return ""

        if isinstance(description, list):
            # Join list elements with spaces
            return " ".join(str(item) for item in description)

        return str(description).strip()

    def validate_search_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a search query.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query:
            return False, "Search query cannot be empty"

        if len(query) < 2:
            return False, "Search query must be at least 2 characters"

        if len(query) > 100:
            return False, "Search query cannot exceed 100 characters"

        return True, None

    def validate_comment(self, comment: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a comment.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not comment:
            return False, "Comment cannot be empty"

        comment_str = self.sanitize_description(comment)

        if len(comment_str) < 1:
            return False, "Comment cannot be empty"

        if len(comment_str) > 5000:
            return False, "Comment cannot exceed 5000 characters"

        return True, None
