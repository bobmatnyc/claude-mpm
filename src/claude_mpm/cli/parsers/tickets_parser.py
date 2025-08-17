"""
Tickets command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to ticket management commands,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Ticket commands have their own complex subcommand structure
that warrants a dedicated module.
"""

import argparse

from ...constants import CLICommands, TicketCommands
from .base_parser import add_common_arguments


def add_tickets_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the tickets subparser with all ticket management commands.

    WHY: Ticket management has multiple subcommands (create, list, view, etc.)
    that need their own argument structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured tickets subparser
    """
    # Tickets command with subcommands
    tickets_parser = subparsers.add_parser(
        CLICommands.TICKETS.value, help="Manage tickets and tracking"
    )
    add_common_arguments(tickets_parser)

    tickets_subparsers = tickets_parser.add_subparsers(
        dest="tickets_command", help="Ticket commands", metavar="SUBCOMMAND"
    )

    # Create ticket
    create_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.CREATE.value, help="Create a new ticket"
    )
    create_ticket_parser.add_argument("title", help="Ticket title")
    create_ticket_parser.add_argument(
        "-t",
        "--type",
        default="task",
        choices=["task", "bug", "feature", "issue", "epic"],
        help="Ticket type (default: task)",
    )
    create_ticket_parser.add_argument(
        "-p",
        "--priority",
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Priority level (default: medium)",
    )
    create_ticket_parser.add_argument(
        "-d",
        "--description",
        nargs="*",
        help="Ticket description (multiple words allowed)",
    )
    create_ticket_parser.add_argument("--tags", help="Comma-separated list of tags")
    create_ticket_parser.add_argument(
        "--parent-epic", help="Parent epic ID for this ticket"
    )
    create_ticket_parser.add_argument(
        "--parent-issue", help="Parent issue ID for this ticket"
    )

    # List tickets
    list_tickets_parser = tickets_subparsers.add_parser(
        TicketCommands.LIST.value, help="List tickets"
    )
    list_tickets_parser.add_argument(
        "-t",
        "--type",
        choices=["task", "bug", "feature", "issue", "epic"],
        help="Filter by ticket type",
    )
    list_tickets_parser.add_argument(
        "-s",
        "--status",
        choices=["open", "in_progress", "closed", "all"],
        default="open",
        help="Filter by status (default: open)",
    )
    list_tickets_parser.add_argument(
        "-p",
        "--priority",
        choices=["low", "medium", "high", "critical"],
        help="Filter by priority",
    )
    list_tickets_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of tickets to show (default: 20)",
    )
    list_tickets_parser.add_argument(
        "--page", type=int, default=1, help="Page number for pagination (default: 1)"
    )
    list_tickets_parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="Number of tickets per page (default: 20)",
    )
    list_tickets_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed ticket information"
    )

    # View ticket
    view_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.VIEW.value, help="View ticket details"
    )
    view_ticket_parser.add_argument("ticket_id", help="Ticket ID to view")
    view_ticket_parser.add_argument(
        "--with-comments", action="store_true", help="Include comments in the view"
    )

    # Update ticket
    update_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.UPDATE.value, help="Update ticket"
    )
    update_ticket_parser.add_argument("ticket_id", help="Ticket ID to update")
    update_ticket_parser.add_argument(
        "-p",
        "--priority",
        choices=["low", "medium", "high", "critical"],
        help="Update priority",
    )
    update_ticket_parser.add_argument(
        "-s",
        "--status",
        choices=["open", "in_progress", "closed"],
        help="Update status",
    )
    update_ticket_parser.add_argument("--title", help="Update title")
    update_ticket_parser.add_argument("--description", help="Update description")
    update_ticket_parser.add_argument("--add-tags", help="Comma-separated tags to add")
    update_ticket_parser.add_argument(
        "--remove-tags", help="Comma-separated tags to remove"
    )

    # Close ticket
    close_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.CLOSE.value, help="Close ticket"
    )
    close_ticket_parser.add_argument("ticket_id", help="Ticket ID to close")
    close_ticket_parser.add_argument("--comment", help="Closing comment")

    # Delete ticket
    delete_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.DELETE.value, help="Delete ticket"
    )
    delete_ticket_parser.add_argument("ticket_id", help="Ticket ID to delete")
    delete_ticket_parser.add_argument(
        "--force", action="store_true", help="Force deletion without confirmation"
    )
    delete_ticket_parser.add_argument(
        "--archive", action="store_true", help="Archive instead of permanent deletion"
    )

    # Search tickets
    search_tickets_parser = tickets_subparsers.add_parser(
        TicketCommands.SEARCH.value, help="Search tickets"
    )
    search_tickets_parser.add_argument(
        "query", help="Search query (searches title and description)"
    )
    search_tickets_parser.add_argument(
        "-t",
        "--type",
        choices=["task", "bug", "feature", "issue", "epic"],
        help="Filter by ticket type",
    )
    search_tickets_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of results (default: 10)"
    )

    # Comment on ticket
    comment_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.COMMENT.value, help="Add comment to ticket"
    )
    comment_ticket_parser.add_argument("ticket_id", help="Ticket ID to comment on")
    comment_ticket_parser.add_argument("comment", help="Comment text")

    # Workflow management
    workflow_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.WORKFLOW.value, help="Manage ticket workflow"
    )
    workflow_ticket_parser.add_argument("ticket_id", help="Ticket ID")
    workflow_ticket_parser.add_argument(
        "state",
        choices=["open", "in_progress", "review", "testing", "closed"],
        help="New workflow state",
    )
    workflow_ticket_parser.add_argument("--comment", help="Workflow transition comment")

    return tickets_parser
