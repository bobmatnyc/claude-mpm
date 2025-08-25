"""
Output formatting service for tickets.

WHY: Separates presentation logic from business logic, allowing for
consistent formatting across different output modes and contexts.

DESIGN DECISIONS:
- Supports multiple output formats (text, json, yaml, table)
- Uses emoji for visual status indicators
- Handles pagination display
- Provides consistent formatting patterns
"""

from typing import Any, Dict, List, Optional


class TicketFormatterService:
    """Service for formatting ticket output."""

    # Status emoji mapping for visual indicators
    STATUS_EMOJI = {
        "open": "🔵",
        "in_progress": "🟡",
        "done": "🟢",
        "closed": "⚫",
        "blocked": "🔴",
        "ready": "🟣",
        "tested": "🟢",
        "waiting": "🟠",
    }

    DEFAULT_EMOJI = "⚪"

    def format_ticket_created(
        self, ticket_id: str, verbose: bool = False, **metadata
    ) -> List[str]:
        """
        Format output for created ticket.

        Returns:
            List of formatted output lines
        """
        lines = [f"✅ Created ticket: {ticket_id}"]

        if verbose:
            if metadata.get("type"):
                lines.append(f"   Type: {metadata['type']}")
            if metadata.get("priority"):
                lines.append(f"   Priority: {metadata['priority']}")
            if metadata.get("tags"):
                lines.append(f"   Tags: {', '.join(metadata['tags'])}")
            if metadata.get("parent_epic"):
                lines.append(f"   Parent Epic: {metadata['parent_epic']}")
            if metadata.get("parent_issue"):
                lines.append(f"   Parent Issue: {metadata['parent_issue']}")

        return lines

    def format_ticket_list(
        self,
        tickets: List[Dict[str, Any]],
        page: int = 1,
        page_size: int = 20,
        verbose: bool = False,
    ) -> List[str]:
        """
        Format a list of tickets for display.

        Returns:
            List of formatted output lines
        """
        if not tickets:
            return ["No tickets found matching criteria"]

        total_shown = len(tickets)
        lines = [f"Tickets (page {page}, showing {total_shown} tickets):", "-" * 80]

        for ticket in tickets:
            # Get status emoji
            status = ticket.get("status", "unknown")
            emoji = self.STATUS_EMOJI.get(status, self.DEFAULT_EMOJI)

            lines.append(f"{emoji} [{ticket['id']}] {ticket['title']}")

            if verbose:
                ticket_type = ticket.get("metadata", {}).get("ticket_type", "task")
                priority = ticket.get("priority", "medium")
                lines.append(
                    f"   Type: {ticket_type} | Status: {status} | Priority: {priority}"
                )

                if ticket.get("tags"):
                    lines.append(f"   Tags: {', '.join(ticket['tags'])}")

                lines.append(f"   Created: {ticket.get('created_at', 'Unknown')}")
                lines.append("")

        # Add pagination hints
        if total_shown == page_size:
            lines.extend(
                [
                    "-" * 80,
                    f"📄 Page {page} | Showing {total_shown} tickets",
                    f"💡 Next page: claude-mpm tickets list --page {page + 1} --page-size {page_size}",
                ]
            )
            if page > 1:
                lines.append(
                    f"💡 Previous page: claude-mpm tickets list --page {page - 1} --page-size {page_size}"
                )

        return lines

    def format_ticket_detail(
        self, ticket: Dict[str, Any], verbose: bool = False
    ) -> List[str]:
        """
        Format a single ticket's details for display.

        Returns:
            List of formatted output lines
        """
        if not ticket:
            return ["❌ Ticket not found"]

        lines = [
            f"Ticket: {ticket['id']}",
            "=" * 80,
            f"Title: {ticket['title']}",
            f"Type: {ticket.get('metadata', {}).get('ticket_type', 'unknown')}",
            f"Status: {ticket['status']}",
            f"Priority: {ticket['priority']}",
        ]

        if ticket.get("tags"):
            lines.append(f"Tags: {', '.join(ticket['tags'])}")

        if ticket.get("assignees"):
            lines.append(f"Assignees: {', '.join(ticket['assignees'])}")

        # Show parent references
        metadata = ticket.get("metadata", {})
        if metadata.get("parent_epic"):
            lines.append(f"Parent Epic: {metadata['parent_epic']}")
        if metadata.get("parent_issue"):
            lines.append(f"Parent Issue: {metadata['parent_issue']}")

        lines.extend(
            [
                "",
                "Description:",
                "-" * 40,
                ticket.get("description", "No description"),
                "",
                f"Created: {ticket['created_at']}",
                f"Updated: {ticket['updated_at']}",
            ]
        )

        if verbose and metadata:
            lines.extend(["", "Metadata:", "-" * 40])
            for key, value in metadata.items():
                if key not in ["parent_epic", "parent_issue", "ticket_type"]:
                    lines.append(f"  {key}: {value}")

        return lines

    def format_search_results(
        self, tickets: List[Dict[str, Any]], query: str, show_snippets: bool = True
    ) -> List[str]:
        """
        Format search results with optional context snippets.

        Returns:
            List of formatted output lines
        """
        if not tickets:
            return [f"No tickets found matching '{query}'"]

        lines = [f"Search results for '{query}' (showing {len(tickets)}):", "-" * 80]

        for ticket in tickets:
            status = ticket.get("status", "unknown")
            emoji = self.STATUS_EMOJI.get(status, self.DEFAULT_EMOJI)

            lines.append(f"{emoji} [{ticket['id']}] {ticket['title']}")

            if show_snippets:
                # Show snippet if query appears in description
                desc = ticket.get("description", "")
                if query.lower() in desc.lower():
                    snippet = self._get_search_snippet(desc, query)
                    lines.append(f"   {snippet}")

        return lines

    def _get_search_snippet(
        self, text: str, query: str, context_chars: int = 30
    ) -> str:
        """
        Extract a snippet of text around the search query.

        Returns:
            Formatted snippet with ellipsis if truncated
        """
        lower_text = text.lower()
        query_lower = query.lower()

        if query_lower not in lower_text:
            return ""

        idx = lower_text.index(query_lower)
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(query) + context_chars)

        snippet = text[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def format_operation_result(
        self,
        operation: str,
        ticket_id: str,
        success: bool,
        message: Optional[str] = None,
    ) -> str:
        """
        Format the result of a ticket operation.

        Returns:
            Formatted result message
        """
        if success:
            emoji = "✅"
            default_messages = {
                "update": f"Updated ticket: {ticket_id}",
                "close": f"Closed ticket: {ticket_id}",
                "delete": f"Deleted ticket: {ticket_id}",
                "comment": f"Added comment to ticket: {ticket_id}",
                "workflow": f"Updated workflow state for {ticket_id}",
            }
            msg = message or default_messages.get(
                operation, f"Operation completed: {ticket_id}"
            )
        else:
            emoji = "❌"
            default_messages = {
                "update": f"Failed to update ticket: {ticket_id}",
                "close": f"Failed to close ticket: {ticket_id}",
                "delete": f"Failed to delete ticket: {ticket_id}",
                "comment": f"Failed to add comment to ticket: {ticket_id}",
                "workflow": f"Failed to update workflow state for ticket: {ticket_id}",
            }
            msg = message or default_messages.get(
                operation, f"Operation failed: {ticket_id}"
            )

        return f"{emoji} {msg}"

    def format_error(self, error: str) -> str:
        """
        Format an error message.

        Returns:
            Formatted error message
        """
        return f"❌ {error}"

    def format_info(self, info: str) -> str:
        """
        Format an informational message.

        Returns:
            Formatted info message
        """
        return f"ℹ️ {info}"

    def format_warning(self, warning: str) -> str:
        """
        Format a warning message.

        Returns:
            Formatted warning message
        """
        return f"⚠️ {warning}"
