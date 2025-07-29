"""
Tickets command implementation for claude-mpm.

WHY: This module handles ticket listing functionality, allowing users to view
recent tickets created during Claude sessions.
"""

from ...core.logger import get_logger


def list_tickets(args):
    """
    List recent tickets.
    
    WHY: Users need to review tickets created during Claude sessions. This command
    provides a quick way to see recent tickets with their status and metadata.
    
    DESIGN DECISION: We show tickets in a compact format with emoji status indicators
    for better visual scanning. The limit is configurable to allow users to see more
    or fewer tickets as needed.
    
    Args:
        args: Parsed command line arguments with 'limit' attribute
    """
    logger = get_logger("cli")
    
    try:
        try:
            from ...services.ticket_manager import TicketManager
        except ImportError:
            from claude_mpm.services.ticket_manager import TicketManager
        
        ticket_manager = TicketManager()
        tickets = ticket_manager.list_recent_tickets(limit=args.limit)
        
        if not tickets:
            print("No tickets found")
            return
        
        print(f"Recent tickets (showing {len(tickets)}):")
        print("-" * 80)
        
        for ticket in tickets:
            # Use emoji to indicate status visually
            status_emoji = {
                "open": "🔵",
                "in_progress": "🟡",
                "done": "🟢",
                "closed": "⚫"
            }.get(ticket['status'], "⚪")
            
            print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")
            print(f"   Priority: {ticket['priority']} | Tags: {', '.join(ticket['tags'])}")
            print(f"   Created: {ticket['created_at']}")
            print()
            
    except ImportError:
        logger.error("ai-trackdown-pytools not installed")
        print("Error: ai-trackdown-pytools not installed")
        print("Install with: pip install ai-trackdown-pytools")
    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        print(f"Error: {e}")