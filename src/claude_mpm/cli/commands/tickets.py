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
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional

from ...constants import TicketCommands
from ...core.logger import get_logger
from ..shared import BaseCommand, CommandResult


class TicketsCommand(BaseCommand):
    """Tickets command using shared utilities."""

    def __init__(self):
        super().__init__("tickets")

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, 'tickets_command') or not args.tickets_command:
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
            else:
                return CommandResult.error_result(f"Unknown tickets command: {args.tickets_command}")

        except Exception as e:
            self.logger.error(f"Error executing tickets command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing tickets command: {e}")

    def _create_ticket(self, args) -> CommandResult:
        """Create a new ticket."""
        try:
            exit_code = create_ticket_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Ticket created successfully")
            else:
                return CommandResult.error_result("Failed to create ticket", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error creating ticket: {e}")
            return CommandResult.error_result(f"Error creating ticket: {e}")

    def _list_tickets(self, args) -> CommandResult:
        """List tickets."""
        try:
            exit_code = list_tickets_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Tickets listed successfully")
            else:
                return CommandResult.error_result("Failed to list tickets", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error listing tickets: {e}")
            return CommandResult.error_result(f"Error listing tickets: {e}")

    def _view_ticket(self, args) -> CommandResult:
        """View a specific ticket."""
        try:
            exit_code = view_ticket_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Ticket viewed successfully")
            else:
                return CommandResult.error_result("Failed to view ticket", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error viewing ticket: {e}")
            return CommandResult.error_result(f"Error viewing ticket: {e}")

    def _update_ticket(self, args) -> CommandResult:
        """Update a ticket."""
        try:
            exit_code = update_ticket_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Ticket updated successfully")
            else:
                return CommandResult.error_result("Failed to update ticket", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error updating ticket: {e}")
            return CommandResult.error_result(f"Error updating ticket: {e}")

    def _close_ticket(self, args) -> CommandResult:
        """Close a ticket."""
        try:
            exit_code = close_ticket_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Ticket closed successfully")
            else:
                return CommandResult.error_result("Failed to close ticket", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error closing ticket: {e}")
            return CommandResult.error_result(f"Error closing ticket: {e}")

    def _delete_ticket(self, args) -> CommandResult:
        """Delete a ticket."""
        try:
            exit_code = delete_ticket_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Ticket deleted successfully")
            else:
                return CommandResult.error_result("Failed to delete ticket", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error deleting ticket: {e}")
            return CommandResult.error_result(f"Error deleting ticket: {e}")

    def _search_tickets(self, args) -> CommandResult:
        """Search tickets."""
        try:
            exit_code = search_tickets_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Tickets searched successfully")
            else:
                return CommandResult.error_result("Failed to search tickets", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error searching tickets: {e}")
            return CommandResult.error_result(f"Error searching tickets: {e}")

    def _add_comment(self, args) -> CommandResult:
        """Add a comment to a ticket."""
        try:
            exit_code = add_comment_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Comment added successfully")
            else:
                return CommandResult.error_result("Failed to add comment", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error adding comment: {e}")
            return CommandResult.error_result(f"Error adding comment: {e}")

    def _update_workflow(self, args) -> CommandResult:
        """Update workflow state."""
        try:
            exit_code = update_workflow_legacy(args)
            if exit_code == 0:
                return CommandResult.success_result("Workflow updated successfully")
            else:
                return CommandResult.error_result("Failed to update workflow", exit_code=exit_code)
        except Exception as e:
            self.logger.error(f"Error updating workflow: {e}")
            return CommandResult.error_result(f"Error updating workflow: {e}")


def manage_tickets(args):
    """
    Main entry point for tickets command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = TicketsCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, 'format') and args.format in ['json', 'yaml']:
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


def manage_tickets_legacy(args):
    """
    Legacy ticket command dispatcher.

    WHY: This contains the original manage_tickets logic, preserved during migration
    to BaseCommand pattern. Will be gradually refactored into the TicketsCommand class.

    DESIGN DECISION: We use a subcommand pattern similar to git, allowing for
    intuitive command structure like 'claude-mpm tickets create "title"'.

    Args:
        args: Parsed command line arguments with 'tickets_command' attribute

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    # Handle case where no subcommand is provided - default to list
    if not hasattr(args, "tickets_command") or not args.tickets_command:
        # Default to list command for backward compatibility
        args.tickets_command = TicketCommands.LIST.value
        # Set default limit if not present
        if not hasattr(args, "limit"):
            args.limit = 10
        if not hasattr(args, "verbose"):
            args.verbose = False

    # Map subcommands to handler functions
    handlers = {
        TicketCommands.CREATE.value: create_ticket_legacy,
        TicketCommands.LIST.value: list_tickets_legacy,
        TicketCommands.VIEW.value: view_ticket_legacy,
        TicketCommands.UPDATE.value: update_ticket_legacy,
        TicketCommands.CLOSE.value: close_ticket_legacy,
        TicketCommands.DELETE.value: delete_ticket_legacy,
        TicketCommands.SEARCH.value: search_tickets_legacy,
        TicketCommands.COMMENT.value: add_comment_legacy,
        TicketCommands.WORKFLOW.value: update_workflow_legacy,
    }

    # Execute the appropriate handler
    handler = handlers.get(args.tickets_command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 1
        except Exception as e:
            logger.error(f"Error executing {args.tickets_command}: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1
    else:
        logger.error(f"Unknown ticket command: {args.tickets_command}")
        return 1


def create_ticket_legacy(args):
    """
    Create a new ticket.

    WHY: Users need to create tickets to track work items, bugs, and features.
    This command provides a streamlined interface for ticket creation.

    DESIGN DECISION: We parse description from remaining args to allow natural
    command line usage like: tickets create "title" -d This is a description

    Args:
        args: Arguments with title, type, priority, description, tags, etc.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    try:
        from ...services.ticket_manager import TicketManager
    except ImportError:
        from claude_mpm.services.ticket_manager import TicketManager

    ticket_manager = TicketManager()

    # Parse description from remaining args or use default
    description = " ".join(args.description) if args.description else ""

    # Parse tags
    tags = args.tags.split(",") if args.tags else []

    # Create ticket with all provided parameters
    ticket_id = ticket_manager.create_ticket(
        title=args.title,
        ticket_type=args.type,
        description=description,
        priority=args.priority,
        tags=tags,
        source="claude-mpm-cli",
        parent_epic=getattr(args, "parent_epic", None),
        parent_issue=getattr(args, "parent_issue", None),
    )

    if ticket_id:
        print(f"✅ Created ticket: {ticket_id}")
        if args.verbose:
            print(f"   Type: {args.type}")
            print(f"   Priority: {args.priority}")
            if tags:
                print(f"   Tags: {', '.join(tags)}")
            if getattr(args, "parent_epic", None):
                print(f"   Parent Epic: {args.parent_epic}")
            if getattr(args, "parent_issue", None):
                print(f"   Parent Issue: {args.parent_issue}")
        return 0
    else:
        print("❌ Failed to create ticket")
        return 1


def list_tickets_legacy(args):
    """
    List recent tickets with optional filtering.

    WHY: Users need to review tickets created during Claude sessions. This command
    provides a quick way to see recent tickets with their status and metadata.

    DESIGN DECISION: We show tickets in a compact format with emoji status indicators
    for better visual scanning. Filters allow focusing on specific ticket types/statuses.

    Args:
        args: Arguments with limit, type filter, status filter, verbose flag

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    try:
        # Get pagination parameters
        page = getattr(args, "page", 1)
        page_size = getattr(args, "page_size", 20)
        limit = getattr(args, "limit", page_size)  # Use page_size as default limit

        # Validate pagination parameters
        if page < 1:
            print("❌ Page number must be 1 or greater")
            return 1
        if page_size < 1:
            print("❌ Page size must be 1 or greater")
            return 1

        # Try to use ai-trackdown CLI directly for better pagination support
        tickets = []
        try:
            # Build aitrackdown command with pagination
            cmd = ["aitrackdown", "status", "tasks"]

            # Calculate offset for pagination
            offset = (page - 1) * page_size
            total_needed = offset + page_size

            # Request more tickets than needed to handle filtering
            cmd.extend(["--limit", str(total_needed * 2)])

            # Add filters
            type_filter = getattr(args, "type", None) or "all"
            if type_filter != "all" and type_filter is not None:
                cmd.extend(["--type", type_filter])

            status_filter = getattr(args, "status", None) or "all"
            if status_filter != "all" and status_filter is not None:
                cmd.extend(["--status", status_filter])

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse JSON output
            if result.stdout.strip():
                try:
                    all_tickets = json.loads(result.stdout)
                    if isinstance(all_tickets, list):
                        # Apply pagination
                        start_idx = offset
                        end_idx = start_idx + page_size
                        tickets = all_tickets[start_idx:end_idx]
                    else:
                        tickets = []
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to parse aitrackdown JSON output, falling back to stub"
                    )
                    tickets = []

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"aitrackdown command failed: {e}, falling back to stub")
            # Fallback to stub implementation
            try:
                from ...services.ticket_manager import TicketManager
            except ImportError:
                from claude_mpm.services.ticket_manager import TicketManager

            ticket_manager = TicketManager()
            all_tickets = ticket_manager.list_recent_tickets(limit=limit * 2)

            # Apply filters and pagination manually for stub
            filtered_tickets = []
            for ticket in all_tickets:
                # Type filter
                if type_filter != "all":
                    ticket_type = ticket.get("metadata", {}).get(
                        "ticket_type", "unknown"
                    )
                    if ticket_type != type_filter:
                        continue

                # Status filter
                if status_filter != "all":
                    if ticket.get("status") != status_filter:
                        continue

                filtered_tickets.append(ticket)

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            tickets = filtered_tickets[start_idx:end_idx]

        if not tickets:
            print("No tickets found matching criteria")
            if page > 1:
                print(f"Try a lower page number (current: {page})")
            return 0

        # Display pagination info
        total_shown = len(tickets)
        print(f"Tickets (page {page}, showing {total_shown} tickets):")
        print("-" * 80)

        for ticket in tickets:
            # Use emoji to indicate status visually
            status_emoji = {
                "open": "🔵",
                "in_progress": "🟡",
                "done": "🟢",
                "closed": "⚫",
                "blocked": "🔴",
            }.get(ticket.get("status", "unknown"), "⚪")

            print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")

            if getattr(args, "verbose", False):
                ticket_type = ticket.get("metadata", {}).get("ticket_type", "task")
                print(
                    f"   Type: {ticket_type} | Status: {ticket['status']} | Priority: {ticket['priority']}"
                )
                if ticket.get("tags"):
                    print(f"   Tags: {', '.join(ticket['tags'])}")
                print(f"   Created: {ticket['created_at']}")
                print()

        # Show pagination navigation hints
        if total_shown == page_size:
            print("-" * 80)
            print(f"📄 Page {page} | Showing {total_shown} tickets")
            print(
                f"💡 Next page: claude-mpm tickets list --page {page + 1} --page-size {page_size}"
            )
            if page > 1:
                print(
                    f"💡 Previous page: claude-mpm tickets list --page {page - 1} --page-size {page_size}"
                )

        return 0

    except ImportError:
        logger.error("ai-trackdown-pytools not installed")
        print("Error: ai-trackdown-pytools not installed")
        print("Install with: pip install ai-trackdown-pytools")
        return 1
    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        print(f"Error: {e}")
        return 1


def view_ticket_legacy(args):
    """
    View a specific ticket in detail.

    WHY: Users need to see full ticket details including description, metadata,
    and all associated information for understanding context and status.

    Args:
        args: Arguments with ticket id and verbose flag

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    try:
        from ...services.ticket_manager import TicketManager
    except ImportError:
        from claude_mpm.services.ticket_manager import TicketManager

    ticket_manager = TicketManager()
    # Handle both 'id' and 'ticket_id' attributes for compatibility
    ticket_id = getattr(args, 'ticket_id', getattr(args, 'id', None))
    if not ticket_id:
        print("❌ No ticket ID provided")
        return 1
    ticket = ticket_manager.get_ticket(ticket_id)

    if not ticket:
        print(f"❌ Ticket {ticket_id} not found")
        return 1

    print(f"Ticket: {ticket['id']}")
    print("=" * 80)
    print(f"Title: {ticket['title']}")
    print(f"Type: {ticket.get('metadata', {}).get('ticket_type', 'unknown')}")
    print(f"Status: {ticket['status']}")
    print(f"Priority: {ticket['priority']}")

    if ticket.get("tags"):
        print(f"Tags: {', '.join(ticket['tags'])}")

    if ticket.get("assignees"):
        print(f"Assignees: {', '.join(ticket['assignees'])}")

    # Show parent references if they exist
    metadata = ticket.get("metadata", {})
    if metadata.get("parent_epic"):
        print(f"Parent Epic: {metadata['parent_epic']}")
    if metadata.get("parent_issue"):
        print(f"Parent Issue: {metadata['parent_issue']}")

    print(f"\nDescription:")
    print("-" * 40)
    print(ticket.get("description", "No description"))

    print(f"\nCreated: {ticket['created_at']}")
    print(f"Updated: {ticket['updated_at']}")

    if args.verbose and ticket.get("metadata"):
        print(f"\nMetadata:")
        print("-" * 40)
        for key, value in ticket["metadata"].items():
            if key not in [
                "parent_epic",
                "parent_issue",
                "ticket_type",
            ]:  # Already shown above
                print(f"  {key}: {value}")

    return 0


def update_ticket_legacy(args):
    """
    Update a ticket's properties.

    WHY: Tickets need to be updated as work progresses, priorities change,
    or additional information becomes available.

    DESIGN DECISION: For complex updates, we delegate to aitrackdown CLI
    for operations not directly supported by our TicketManager interface.

    Args:
        args: Arguments with ticket id and update fields

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    try:
        from ...services.ticket_manager import TicketManager
    except ImportError:
        from claude_mpm.services.ticket_manager import TicketManager

    ticket_manager = TicketManager()

    # Handle both 'id' and 'ticket_id' attributes for compatibility
    ticket_id = getattr(args, 'ticket_id', getattr(args, 'id', None))
    if not ticket_id:
        print("❌ No ticket ID provided")
        return 1

    # Build update dictionary
    updates = {}

    if args.status:
        updates["status"] = args.status

    if args.priority:
        updates["priority"] = args.priority

    if args.description:
        updates["description"] = " ".join(args.description)

    if args.tags:
        updates["tags"] = args.tags.split(",")

    if args.assign:
        updates["assignees"] = [args.assign]

    if not updates:
        print("❌ No updates specified")
        return 1

    # Try to update using TicketManager
    success = ticket_manager.update_task(ticket_id, **updates)

    if success:
        print(f"✅ Updated ticket: {ticket_id}")
        return 0
    else:
        # Fallback to aitrackdown CLI for status transitions
        if args.status:
            logger.info("Attempting update via aitrackdown CLI")
            cmd = ["aitrackdown", "transition", ticket_id, args.status]

            # Add comment with other updates
            comment_parts = []
            if args.priority:
                comment_parts.append(f"Priority: {args.priority}")
            if args.assign:
                comment_parts.append(f"Assigned to: {args.assign}")
            if args.tags:
                comment_parts.append(f"Tags: {args.tags}")

            if comment_parts:
                comment = " | ".join(comment_parts)
                cmd.extend(["--comment", comment])

            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(f"✅ Updated ticket: {ticket_id}")
                return 0
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to update via CLI: {e}")
                print(f"❌ Failed to update ticket: {ticket_id}")
                return 1
        else:
            print(f"❌ Failed to update ticket: {ticket_id}")
            return 1


def close_ticket_legacy(args):
    """
    Close a ticket.

    WHY: Tickets need to be closed when work is completed or no longer relevant.

    Args:
        args: Arguments with ticket id and optional resolution

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    try:
        from ...services.ticket_manager import TicketManager
    except ImportError:
        from claude_mpm.services.ticket_manager import TicketManager

    ticket_manager = TicketManager()

    # Handle both 'id' and 'ticket_id' attributes for compatibility
    ticket_id = getattr(args, 'ticket_id', getattr(args, 'id', None))
    if not ticket_id:
        print("❌ No ticket ID provided")
        return 1

    # Try to close using TicketManager
    resolution = getattr(args, "resolution", getattr(args, "comment", None))
    success = ticket_manager.close_task(ticket_id, resolution=resolution)

    if success:
        print(f"✅ Closed ticket: {ticket_id}")
        return 0
    else:
        # Fallback to aitrackdown CLI
        logger.info("Attempting close via aitrackdown CLI")
        cmd = ["aitrackdown", "close", ticket_id]

        if resolution:
            cmd.extend(["--comment", resolution])

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ Closed ticket: {ticket_id}")
            return 0
        except subprocess.CalledProcessError:
            print(f"❌ Failed to close ticket: {ticket_id}")
            return 1


def delete_ticket_legacy(args):
    """
    Delete a ticket.

    WHY: Sometimes tickets are created in error or are no longer needed
    and should be removed from the system.

    DESIGN DECISION: We delegate to aitrackdown CLI as deletion is a
    destructive operation that should use the official tool.

    Args:
        args: Arguments with ticket id and force flag

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    # Handle both 'id' and 'ticket_id' attributes for compatibility
    ticket_id = getattr(args, 'ticket_id', getattr(args, 'id', None))
    if not ticket_id:
        print("❌ No ticket ID provided")
        return 1

    # Confirm deletion unless forced
    if not args.force:
        sys.stdout.flush()  # Ensure prompt is displayed before input

        # Check if we're in a TTY environment for proper input handling
        if not sys.stdin.isatty():
            # In non-TTY environment (like pipes), use readline
            print(
                f"Are you sure you want to delete ticket {ticket_id}? (y/N): ",
                end="",
                flush=True,
            )
            try:
                response = sys.stdin.readline().strip().lower()
                # Handle various line endings and control characters
                response = response.replace("\r", "").replace("\n", "").strip()
            except (EOFError, KeyboardInterrupt):
                response = "n"
        else:
            # In TTY environment, use normal input()
            try:
                response = (
                    input(f"Are you sure you want to delete ticket {ticket_id}? (y/N): ")
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                response = "n"

        if response != "y":
            print("Deletion cancelled")
            return 0

    # Use aitrackdown CLI for deletion
    cmd = ["aitrackdown", "delete", ticket_id]
    if args.force:
        cmd.append("--force")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Deleted ticket: {ticket_id}")
        return 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to delete ticket: {ticket_id}")
        return 1


def search_tickets_legacy(args):
    """
    Search tickets by query string.

    WHY: Users need to find specific tickets based on content, tags, or other criteria.

    DESIGN DECISION: We perform simple text matching on ticket data. For more advanced
    search, users should use the aitrackdown CLI directly.

    Args:
        args: Arguments with search query and filters

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    try:
        from ...services.ticket_manager import TicketManager
    except ImportError:
        from claude_mpm.services.ticket_manager import TicketManager

    ticket_manager = TicketManager()

    # Get all available tickets for searching
    all_tickets = ticket_manager.list_recent_tickets(limit=100)

    # Search tickets
    query = args.query.lower()
    matched_tickets = []

    for ticket in all_tickets:
        # Check if query matches title, description, or tags
        if (
            query in ticket.get("title", "").lower()
            or query in ticket.get("description", "").lower()
            or any(query in tag.lower() for tag in ticket.get("tags", []))
        ):
            # Apply type filter
            if args.type != "all":
                ticket_type = ticket.get("metadata", {}).get("ticket_type", "unknown")
                if ticket_type != args.type:
                    continue

            # Apply status filter
            if args.status != "all":
                if ticket.get("status") != args.status:
                    continue

            matched_tickets.append(ticket)
            if len(matched_tickets) >= args.limit:
                break

    if not matched_tickets:
        print(f"No tickets found matching '{args.query}'")
        return 0

    print(f"Search results for '{args.query}' (showing {len(matched_tickets)}):")
    print("-" * 80)

    for ticket in matched_tickets:
        status_emoji = {
            "open": "🔵",
            "in_progress": "🟡",
            "done": "🟢",
            "closed": "⚫",
            "blocked": "🔴",
        }.get(ticket.get("status", "unknown"), "⚪")

        print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")

        # Show snippet of description if it contains the query
        desc = ticket.get("description", "")
        if query in desc.lower():
            # Find and show context around the match
            idx = desc.lower().index(query)
            start = max(0, idx - 30)
            end = min(len(desc), idx + len(query) + 30)
            snippet = desc[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(desc):
                snippet = snippet + "..."
            print(f"   {snippet}")

    return 0


def add_comment_legacy(args):
    """
    Add a comment to a ticket.

    WHY: Comments allow tracking progress, decisions, and additional context
    on tickets over time.

    DESIGN DECISION: We delegate to aitrackdown CLI as it has proper comment
    tracking infrastructure.

    Args:
        args: Arguments with ticket id and comment text

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    # Handle both 'id' and 'ticket_id' attributes for compatibility
    ticket_id = getattr(args, 'ticket_id', getattr(args, 'id', None))
    if not ticket_id:
        print("❌ No ticket ID provided")
        return 1

    # Join comment parts into single string
    comment = " ".join(args.comment) if isinstance(args.comment, list) else args.comment

    # Use aitrackdown CLI for comments
    cmd = ["aitrackdown", "comment", ticket_id, comment]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Added comment to ticket: {ticket_id}")
        return 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to add comment to ticket: {ticket_id}")
        return 1


def update_workflow_legacy(args):
    """
    Update ticket workflow state.

    WHY: Workflow states track the progress of tickets through defined stages
    like todo, in_progress, ready, tested, done.

    DESIGN DECISION: We use aitrackdown's transition command for workflow updates
    as it maintains proper state machine transitions.

    Args:
        args: Arguments with ticket id, new state, and optional comment

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")

    # Handle both 'id' and 'ticket_id' attributes for compatibility
    ticket_id = getattr(args, 'ticket_id', getattr(args, 'id', None))
    if not ticket_id:
        print("❌ No ticket ID provided")
        return 1

    # Map workflow states to status if needed
    state_mapping = {
        "todo": "open",
        "in_progress": "in_progress",
        "ready": "ready",
        "tested": "tested",
        "done": "done",
        "blocked": "blocked",
    }

    # Use aitrackdown transition command
    cmd = ["aitrackdown", "transition", ticket_id, args.state]

    if getattr(args, "comment", None):
        cmd.extend(["--comment", args.comment])

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Updated workflow state for {ticket_id} to: {args.state}")
        return 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to update workflow state for ticket: {ticket_id}")
        return 1


# Maintain backward compatibility with the old list_tickets function signature
def list_tickets_legacy(args):
    """
    Legacy list_tickets function for backward compatibility.

    WHY: The old CLI interface expected a simple list_tickets function.
    This wrapper maintains that interface while using the new implementation.

    Args:
        args: Parsed command line arguments with 'limit' attribute
    """
    # Call the new list_tickets function
    return list_tickets(args)
