"""
Tickets command implementation for claude-mpm.

WHY: This module provides comprehensive ticket management functionality, allowing users
to create, view, update, and manage tickets through the CLI. It integrates with
ai-trackdown-pytools for persistent ticket storage.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Maintain backward compatibility with existing ai-trackdown integration
- Support multiple output formats (json, yaml, table, text)
- Implement full CRUD operations plus search and workflow management
- Use service-oriented architecture to separate concerns
"""

import sys
from typing import Optional

from ...constants import TicketCommands
from ...services.ticket_services import (
    TicketCRUDService,
    TicketFormatterService,
    TicketSearchService,
    TicketValidationService,
    TicketWorkflowService,
)
from ..shared import BaseCommand, CommandResult


class TicketsCommand(BaseCommand):
    """Tickets command using shared utilities and service-oriented architecture."""

    def __init__(self):
        """Initialize the tickets command with services."""
        super().__init__("tickets")

        # Initialize services using dependency injection
        self.crud_service = TicketCRUDService()
        self.formatter = TicketFormatterService()
        self.validator = TicketValidationService()
        self.search_service = TicketSearchService()
        self.workflow_service = TicketWorkflowService()

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, "tickets_command") or not args.tickets_command:
            return "No tickets subcommand specified"

        valid_commands = [cmd.value for cmd in TicketCommands]
        if args.tickets_command not in valid_commands:
            return f"Unknown tickets command: {args.tickets_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the tickets command."""
        try:
            # Route to specific subcommand handlers
            command_map = {
                TicketCommands.CREATE.value: self._create_ticket,
                TicketCommands.LIST.value: self._list_tickets,
                TicketCommands.VIEW.value: self._view_ticket,
                TicketCommands.UPDATE.value: self._update_ticket,
                TicketCommands.CLOSE.value: self._close_ticket,
                TicketCommands.DELETE.value: self._delete_ticket,
                TicketCommands.SEARCH.value: self._search_tickets,
                TicketCommands.COMMENT.value: self._add_comment,
                TicketCommands.WORKFLOW.value: self._update_workflow,
            }

            if args.tickets_command in command_map:
                return command_map[args.tickets_command](args)
            return CommandResult.error_result(
                f"Unknown tickets command: {args.tickets_command}"
            )

        except Exception as e:
            self.logger.error(f"Error executing tickets command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing tickets command: {e}")

    def _create_ticket(self, args) -> CommandResult:
        """Create a new ticket using the CRUD service."""
        try:
            # Prepare parameters
            description = self.validator.sanitize_description(args.description)
            tags = self.validator.sanitize_tags(args.tags)

            # Validate creation parameters
            params = {"title": args.title, "type": args.type, "priority": args.priority}
            valid, error = self.validator.validate_create_params(params)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Create ticket via service
            result = self.crud_service.create_ticket(
                title=args.title,
                ticket_type=args.type,
                priority=args.priority,
                description=description,
                tags=tags,
                parent_epic=getattr(args, "parent_epic", None),
                parent_issue=getattr(args, "parent_issue", None),
            )

            if result["success"]:
                # Format and display output
                output_lines = self.formatter.format_ticket_created(
                    result["ticket_id"],
                    verbose=args.verbose,
                    type=args.type,
                    priority=args.priority,
                    tags=tags,
                    parent_epic=getattr(args, "parent_epic", None),
                    parent_issue=getattr(args, "parent_issue", None),
                )
                for line in output_lines:
                    print(line)
                return CommandResult.success_result(result["message"])
            print(self.formatter.format_error(result["error"]))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error creating ticket: {e}")
            return CommandResult.error_result(f"Error creating ticket: {e}")

    def _list_tickets(self, args) -> CommandResult:
        """List tickets using the CRUD service."""
        try:
            # Get pagination parameters
            page = getattr(args, "page", 1)
            page_size = getattr(args, "page_size", 20)
            limit = getattr(args, "limit", page_size)

            # Validate pagination
            valid, error = self.validator.validate_pagination(page, page_size)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Get filters
            type_filter = getattr(args, "type", None) or "all"
            status_filter = getattr(args, "status", None) or "all"

            # List tickets via service
            result = self.crud_service.list_tickets(
                limit=limit,
                page=page,
                page_size=page_size,
                type_filter=type_filter,
                status_filter=status_filter,
            )

            if result["success"]:
                # Format and display output
                output_lines = self.formatter.format_ticket_list(
                    result["tickets"],
                    page=page,
                    page_size=page_size,
                    verbose=getattr(args, "verbose", False),
                )
                for line in output_lines:
                    print(line)
                return CommandResult.success_result("Tickets listed successfully")
            print(self.formatter.format_error(result["error"]))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error listing tickets: {e}")
            return CommandResult.error_result(f"Error listing tickets: {e}")

    def _view_ticket(self, args) -> CommandResult:
        """View a specific ticket using the CRUD service."""
        try:
            # Get ticket ID
            ticket_id = getattr(args, "ticket_id", getattr(args, "id", None))

            # Validate ticket ID
            valid, error = self.validator.validate_ticket_id(ticket_id)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Get ticket via service
            ticket = self.crud_service.get_ticket(ticket_id)

            if ticket:
                # Format and display output
                output_lines = self.formatter.format_ticket_detail(
                    ticket, verbose=getattr(args, "verbose", False)
                )
                for line in output_lines:
                    print(line)
                return CommandResult.success_result("Ticket viewed successfully")
            error_msg = f"Ticket {ticket_id} not found"
            print(self.formatter.format_error(error_msg))
            return CommandResult.error_result(error_msg)

        except Exception as e:
            self.logger.error(f"Error viewing ticket: {e}")
            return CommandResult.error_result(f"Error viewing ticket: {e}")

    def _update_ticket(self, args) -> CommandResult:
        """Update a ticket using the CRUD service."""
        try:
            # Get ticket ID
            ticket_id = getattr(args, "ticket_id", getattr(args, "id", None))

            # Validate ticket ID
            valid, error = self.validator.validate_ticket_id(ticket_id)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Prepare update parameters
            description = None
            if args.description:
                description = self.validator.sanitize_description(args.description)

            tags = None
            if args.tags:
                tags = self.validator.sanitize_tags(args.tags)

            assignees = None
            if args.assign:
                assignees = [args.assign]

            # Validate update parameters
            update_params = {}
            if args.status:
                update_params["status"] = args.status
            if args.priority:
                update_params["priority"] = args.priority

            valid, error = self.validator.validate_update_params(update_params)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Update ticket via service
            result = self.crud_service.update_ticket(
                ticket_id=ticket_id,
                status=args.status,
                priority=args.priority,
                description=description,
                tags=tags,
                assignees=assignees,
            )

            if result["success"]:
                print(self.formatter.format_operation_result("update", ticket_id, True))
                return CommandResult.success_result(result["message"])
            print(self.formatter.format_operation_result("update", ticket_id, False))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error updating ticket: {e}")
            return CommandResult.error_result(f"Error updating ticket: {e}")

    def _close_ticket(self, args) -> CommandResult:
        """Close a ticket using the CRUD service."""
        try:
            # Get ticket ID
            ticket_id = getattr(args, "ticket_id", getattr(args, "id", None))

            # Validate ticket ID
            valid, error = self.validator.validate_ticket_id(ticket_id)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Get resolution
            resolution = getattr(args, "resolution", getattr(args, "comment", None))

            # Close ticket via service
            result = self.crud_service.close_ticket(ticket_id, resolution)

            if result["success"]:
                print(self.formatter.format_operation_result("close", ticket_id, True))
                return CommandResult.success_result(result["message"])
            print(self.formatter.format_operation_result("close", ticket_id, False))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error closing ticket: {e}")
            return CommandResult.error_result(f"Error closing ticket: {e}")

    def _delete_ticket(self, args) -> CommandResult:
        """Delete a ticket using the CRUD service."""
        try:
            # Get ticket ID
            ticket_id = getattr(args, "ticket_id", getattr(args, "id", None))

            # Validate ticket ID
            valid, error = self.validator.validate_ticket_id(ticket_id)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Confirm deletion unless forced
            if not args.force:
                sys.stdout.flush()

                # Check if we're in a TTY environment
                if not sys.stdin.isatty():
                    print(
                        f"Are you sure you want to delete ticket {ticket_id}? (y/N): ",
                        end="",
                        flush=True,
                    )
                    try:
                        response = sys.stdin.readline().strip().lower()
                        response = response.replace("\r", "").replace("\n", "").strip()
                    except (EOFError, KeyboardInterrupt):
                        response = "n"
                else:
                    try:
                        response = (
                            input(
                                f"Are you sure you want to delete ticket {ticket_id}? (y/N): "
                            )
                            .strip()
                            .lower()
                        )
                    except (EOFError, KeyboardInterrupt):
                        response = "n"

                if response != "y":
                    print("Deletion cancelled")
                    return CommandResult.success_result("Deletion cancelled")

            # Delete ticket via service
            result = self.crud_service.delete_ticket(ticket_id, args.force)

            if result["success"]:
                print(self.formatter.format_operation_result("delete", ticket_id, True))
                return CommandResult.success_result(result["message"])
            print(self.formatter.format_operation_result("delete", ticket_id, False))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error deleting ticket: {e}")
            return CommandResult.error_result(f"Error deleting ticket: {e}")

    def _search_tickets(self, args) -> CommandResult:
        """Search tickets using the search service."""
        try:
            # Validate search query
            valid, error = self.validator.validate_search_query(args.query)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Search tickets via service
            tickets = self.search_service.search_tickets(
                query=args.query,
                type_filter=args.type if args.type else "all",
                status_filter=args.status if args.status else "all",
                limit=args.limit,
            )

            # Format and display results
            output_lines = self.formatter.format_search_results(
                tickets, args.query, show_snippets=True
            )
            for line in output_lines:
                print(line)

            return CommandResult.success_result("Tickets searched successfully")

        except Exception as e:
            self.logger.error(f"Error searching tickets: {e}")
            return CommandResult.error_result(f"Error searching tickets: {e}")

    def _add_comment(self, args) -> CommandResult:
        """Add a comment to a ticket using the workflow service."""
        try:
            # Get ticket ID
            ticket_id = getattr(args, "ticket_id", getattr(args, "id", None))

            # Validate ticket ID
            valid, error = self.validator.validate_ticket_id(ticket_id)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Prepare comment
            comment = self.validator.sanitize_description(args.comment)

            # Validate comment
            valid, error = self.validator.validate_comment(comment)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Add comment via service
            result = self.workflow_service.add_comment(ticket_id, comment)

            if result["success"]:
                print(
                    self.formatter.format_operation_result("comment", ticket_id, True)
                )
                return CommandResult.success_result(result["message"])
            print(self.formatter.format_operation_result("comment", ticket_id, False))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error adding comment: {e}")
            return CommandResult.error_result(f"Error adding comment: {e}")

    def _update_workflow(self, args) -> CommandResult:
        """Update workflow state using the workflow service."""
        try:
            # Get ticket ID
            ticket_id = getattr(args, "ticket_id", getattr(args, "id", None))

            # Validate ticket ID
            valid, error = self.validator.validate_ticket_id(ticket_id)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Validate workflow state
            valid, error = self.validator.validate_workflow_state(args.state)
            if not valid:
                print(self.formatter.format_error(error))
                return CommandResult.error_result(error)

            # Get optional comment
            comment = getattr(args, "comment", None)

            # Update workflow via service
            result = self.workflow_service.transition_ticket(
                ticket_id, args.state, comment
            )

            if result["success"]:
                print(
                    self.formatter.format_operation_result(
                        "workflow", ticket_id, True, result["message"]
                    )
                )
                return CommandResult.success_result(result["message"])
            print(self.formatter.format_operation_result("workflow", ticket_id, False))
            return CommandResult.error_result(result["error"])

        except Exception as e:
            self.logger.error(f"Error updating workflow: {e}")
            return CommandResult.error_result(f"Error updating workflow: {e}")


# ========================================
# Backward compatibility functions
# ========================================


def manage_tickets(args):
    """
    Main entry point for tickets command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = TicketsCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code


def list_tickets(args):
    """
    Compatibility function for list_tickets.

    This maintains backward compatibility for imports while using the new TicketsCommand pattern.
    """
    # Create a tickets command and execute the list subcommand
    args.tickets_command = TicketCommands.LIST.value
    return manage_tickets(args)


# ========================================
# Legacy function stubs for compatibility
# ========================================


def manage_tickets_legacy(args):
    """Legacy wrapper - redirects to new implementation."""
    return manage_tickets(args)


def create_ticket_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.CREATE.value
    return manage_tickets(args)


def list_tickets_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.LIST.value
    return manage_tickets(args)


def view_ticket_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.VIEW.value
    return manage_tickets(args)


def update_ticket_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.UPDATE.value
    return manage_tickets(args)


def close_ticket_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.CLOSE.value
    return manage_tickets(args)


def delete_ticket_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.DELETE.value
    return manage_tickets(args)


def search_tickets_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.SEARCH.value
    return manage_tickets(args)


def add_comment_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.COMMENT.value
    return manage_tickets(args)


def update_workflow_legacy(args):
    """Legacy wrapper - uses new service implementation."""
    args.tickets_command = TicketCommands.WORKFLOW.value
    return manage_tickets(args)
