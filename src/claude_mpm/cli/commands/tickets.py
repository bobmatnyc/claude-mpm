"""
Tickets command implementation for claude-mpm.

WHY: This module provides comprehensive ticket management functionality, allowing users
to create, view, update, and manage tickets through the CLI. It integrates with
ai-trackdown-pytools for persistent ticket storage.

DESIGN DECISION: We implement full CRUD operations plus search and workflow management
to provide a complete ticket management system within the claude-mpm CLI. The commands
mirror the scripts/ticket.py interface for consistency.
"""

import sys
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...core.logger import get_logger
from ...constants import TicketCommands


def manage_tickets(args):
    """
    Main ticket command dispatcher.
    
    WHY: This function routes ticket subcommands to their appropriate handlers,
    providing a single entry point for all ticket-related operations.
    
    DESIGN DECISION: We use a subcommand pattern similar to git, allowing for
    intuitive command structure like 'claude-mpm tickets create "title"'.
    
    Args:
        args: Parsed command line arguments with 'tickets_command' attribute
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger("cli.tickets")
    
    # Handle case where no subcommand is provided - default to list
    if not hasattr(args, 'tickets_command') or not args.tickets_command:
        # Default to list command for backward compatibility
        args.tickets_command = TicketCommands.LIST.value
        # Set default limit if not present
        if not hasattr(args, 'limit'):
            args.limit = 10
        if not hasattr(args, 'verbose'):
            args.verbose = False
    
    # Map subcommands to handler functions
    handlers = {
        TicketCommands.CREATE.value: create_ticket,
        TicketCommands.LIST.value: list_tickets,
        TicketCommands.VIEW.value: view_ticket,
        TicketCommands.UPDATE.value: update_ticket,
        TicketCommands.CLOSE.value: close_ticket,
        TicketCommands.DELETE.value: delete_ticket,
        TicketCommands.SEARCH.value: search_tickets,
        TicketCommands.COMMENT.value: add_comment,
        TicketCommands.WORKFLOW.value: update_workflow,
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
            if hasattr(args, 'debug') and args.debug:
                import traceback
                traceback.print_exc()
            return 1
    else:
        logger.error(f"Unknown ticket command: {args.tickets_command}")
        return 1


def create_ticket(args):
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
        parent_epic=getattr(args, 'parent_epic', None),
        parent_issue=getattr(args, 'parent_issue', None)
    )
    
    if ticket_id:
        print(f"✅ Created ticket: {ticket_id}")
        if args.verbose:
            print(f"   Type: {args.type}")
            print(f"   Priority: {args.priority}")
            if tags:
                print(f"   Tags: {', '.join(tags)}")
            if getattr(args, 'parent_epic', None):
                print(f"   Parent Epic: {args.parent_epic}")
            if getattr(args, 'parent_issue', None):
                print(f"   Parent Issue: {args.parent_issue}")
        return 0
    else:
        print("❌ Failed to create ticket")
        return 1


def list_tickets(args):
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
        try:
            from ...services.ticket_manager import TicketManager
        except ImportError:
            from claude_mpm.services.ticket_manager import TicketManager
        
        ticket_manager = TicketManager()
        
        # Get tickets with limit
        limit = getattr(args, 'limit', 10)
        tickets = ticket_manager.list_recent_tickets(limit=limit * 2)  # Get extra for filtering
        
        # Apply filters if specified
        filtered_tickets = []
        for ticket in tickets:
            # Type filter
            type_filter = getattr(args, 'type', 'all')
            if type_filter != 'all':
                ticket_type = ticket.get('metadata', {}).get('ticket_type', 'unknown')
                if ticket_type != type_filter:
                    continue
            
            # Status filter
            status_filter = getattr(args, 'status', 'all')
            if status_filter != 'all':
                if ticket.get('status') != status_filter:
                    continue
            
            filtered_tickets.append(ticket)
            if len(filtered_tickets) >= limit:
                break
        
        if not filtered_tickets:
            print("No tickets found matching criteria")
            return 0
        
        print(f"Recent tickets (showing {len(filtered_tickets)}):")
        print("-" * 80)
        
        for ticket in filtered_tickets:
            # Use emoji to indicate status visually
            status_emoji = {
                "open": "🔵",
                "in_progress": "🟡",
                "done": "🟢",
                "closed": "⚫",
                "blocked": "🔴"
            }.get(ticket.get('status', 'unknown'), "⚪")
            
            print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")
            
            if getattr(args, 'verbose', False):
                ticket_type = ticket.get('metadata', {}).get('ticket_type', 'task')
                print(f"   Type: {ticket_type} | Status: {ticket['status']} | Priority: {ticket['priority']}")
                if ticket.get('tags'):
                    print(f"   Tags: {', '.join(ticket['tags'])}")
                print(f"   Created: {ticket['created_at']}")
                print()
        
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


def view_ticket(args):
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
    ticket = ticket_manager.get_ticket(args.id)
    
    if not ticket:
        print(f"❌ Ticket {args.id} not found")
        return 1
    
    print(f"Ticket: {ticket['id']}")
    print("=" * 80)
    print(f"Title: {ticket['title']}")
    print(f"Type: {ticket.get('metadata', {}).get('ticket_type', 'unknown')}")
    print(f"Status: {ticket['status']}")
    print(f"Priority: {ticket['priority']}")
    
    if ticket.get('tags'):
        print(f"Tags: {', '.join(ticket['tags'])}")
    
    if ticket.get('assignees'):
        print(f"Assignees: {', '.join(ticket['assignees'])}")
    
    # Show parent references if they exist
    metadata = ticket.get('metadata', {})
    if metadata.get('parent_epic'):
        print(f"Parent Epic: {metadata['parent_epic']}")
    if metadata.get('parent_issue'):
        print(f"Parent Issue: {metadata['parent_issue']}")
    
    print(f"\nDescription:")
    print("-" * 40)
    print(ticket.get('description', 'No description'))
    
    print(f"\nCreated: {ticket['created_at']}")
    print(f"Updated: {ticket['updated_at']}")
    
    if args.verbose and ticket.get('metadata'):
        print(f"\nMetadata:")
        print("-" * 40)
        for key, value in ticket['metadata'].items():
            if key not in ['parent_epic', 'parent_issue', 'ticket_type']:  # Already shown above
                print(f"  {key}: {value}")
    
    return 0


def update_ticket(args):
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
    
    # Build update dictionary
    updates = {}
    
    if args.status:
        updates['status'] = args.status
    
    if args.priority:
        updates['priority'] = args.priority
    
    if args.description:
        updates['description'] = " ".join(args.description)
    
    if args.tags:
        updates['tags'] = args.tags.split(",")
    
    if args.assign:
        updates['assignees'] = [args.assign]
    
    if not updates:
        print("❌ No updates specified")
        return 1
    
    # Try to update using TicketManager
    success = ticket_manager.update_task(args.id, **updates)
    
    if success:
        print(f"✅ Updated ticket: {args.id}")
        return 0
    else:
        # Fallback to aitrackdown CLI for status transitions
        if args.status:
            logger.info("Attempting update via aitrackdown CLI")
            cmd = ["aitrackdown", "transition", args.id, args.status]
            
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
                print(f"✅ Updated ticket: {args.id}")
                return 0
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to update via CLI: {e}")
                print(f"❌ Failed to update ticket: {args.id}")
                return 1
        else:
            print(f"❌ Failed to update ticket: {args.id}")
            return 1


def close_ticket(args):
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
    
    # Try to close using TicketManager
    resolution = getattr(args, 'resolution', None)
    success = ticket_manager.close_task(args.id, resolution=resolution)
    
    if success:
        print(f"✅ Closed ticket: {args.id}")
        return 0
    else:
        # Fallback to aitrackdown CLI
        logger.info("Attempting close via aitrackdown CLI")
        cmd = ["aitrackdown", "close", args.id]
        
        if resolution:
            cmd.extend(["--comment", resolution])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ Closed ticket: {args.id}")
            return 0
        except subprocess.CalledProcessError:
            print(f"❌ Failed to close ticket: {args.id}")
            return 1


def delete_ticket(args):
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
    
    # Confirm deletion unless forced
    if not args.force:
        response = input(f"Are you sure you want to delete ticket {args.id}? (y/N): ")
        if response.lower() != 'y':
            print("Deletion cancelled")
            return 0
    
    # Use aitrackdown CLI for deletion
    cmd = ["aitrackdown", "delete", args.id]
    if args.force:
        cmd.append("--force")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Deleted ticket: {args.id}")
        return 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to delete ticket: {args.id}")
        return 1


def search_tickets(args):
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
        if (query in ticket.get('title', '').lower() or
            query in ticket.get('description', '').lower() or
            any(query in tag.lower() for tag in ticket.get('tags', []))):
            
            # Apply type filter
            if args.type != 'all':
                ticket_type = ticket.get('metadata', {}).get('ticket_type', 'unknown')
                if ticket_type != args.type:
                    continue
            
            # Apply status filter
            if args.status != 'all':
                if ticket.get('status') != args.status:
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
            "blocked": "🔴"
        }.get(ticket.get('status', 'unknown'), "⚪")
        
        print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")
        
        # Show snippet of description if it contains the query
        desc = ticket.get('description', '')
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


def add_comment(args):
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
    
    # Join comment parts into single string
    comment = " ".join(args.comment)
    
    # Use aitrackdown CLI for comments
    cmd = ["aitrackdown", "comment", args.id, comment]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Added comment to ticket: {args.id}")
        return 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to add comment to ticket: {args.id}")
        return 1


def update_workflow(args):
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
    
    # Map workflow states to status if needed
    state_mapping = {
        'todo': 'open',
        'in_progress': 'in_progress',
        'ready': 'ready',
        'tested': 'tested',
        'done': 'done',
        'blocked': 'blocked'
    }
    
    # Use aitrackdown transition command
    cmd = ["aitrackdown", "transition", args.id, args.state]
    
    if getattr(args, 'comment', None):
        cmd.extend(["--comment", args.comment])
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Updated workflow state for {args.id} to: {args.state}")
        return 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to update workflow state for ticket: {args.id}")
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