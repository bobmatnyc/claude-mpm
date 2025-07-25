#!/usr/bin/env python3
"""
Ticket Management Wrapper for ai-trackdown

A simplified interface for creating and managing tickets using ai-trackdown-pytools.
This wrapper provides an intuitive CLI that aliases ai-trackdown commands.

Usage:
    ticket create <title> [options]
    ticket list [options]
    ticket view <id>
    ticket update <id> [options]
    ticket close <id>
    ticket help

Examples:
    ticket create "Fix login bug" -t bug -p high
    ticket create "Add dark mode feature" -t feature -d "Users want dark mode support"
    ticket list --limit 10
    ticket view TSK-0001
    ticket update TSK-0001 -s in_progress
    ticket close TSK-0001
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List
import subprocess

from claude_mpm.services.ticket_manager import TicketManager
from claude_mpm.core.logger import get_logger


class TicketCLI:
    """CLI wrapper for ticket management."""
    
    def __init__(self):
        self.logger = get_logger("ticket_cli")
        self.ticket_manager = TicketManager()
        
    def create(self, args):
        """Create a new ticket."""
        # Parse description from remaining args or use default
        description = " ".join(args.description) if args.description else ""
        
        # Parse tags
        tags = args.tags.split(",") if args.tags else []
        
        # Create ticket
        ticket_id = self.ticket_manager.create_ticket(
            title=args.title,
            ticket_type=args.type,
            description=description,
            priority=args.priority,
            tags=tags,
            source="ticket-cli"
        )
        
        if ticket_id:
            print(f"✅ Created ticket: {ticket_id}")
            if args.verbose:
                print(f"   Type: {args.type}")
                print(f"   Priority: {args.priority}")
                if tags:
                    print(f"   Tags: {', '.join(tags)}")
        else:
            print("❌ Failed to create ticket")
            sys.exit(1)
    
    def list(self, args):
        """List recent tickets."""
        tickets = self.ticket_manager.list_recent_tickets(limit=args.limit)
        
        if not tickets:
            print("No tickets found.")
            return
        
        print(f"Recent tickets (showing {len(tickets)}):")
        print("-" * 80)
        
        for ticket in tickets:
            status_emoji = "🔵" if ticket['status'] == 'open' else "✅"
            print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")
            
            if args.verbose:
                print(f"   Status: {ticket['status']} | Priority: {ticket['priority']}")
                if ticket.get('tags'):
                    print(f"   Tags: {', '.join(ticket['tags'])}")
                print(f"   Created: {ticket['created_at']}")
                print()
    
    def view(self, args):
        """View a specific ticket."""
        ticket = self.ticket_manager.get_ticket(args.id)
        
        if not ticket:
            print(f"❌ Ticket {args.id} not found")
            sys.exit(1)
        
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
        
        print(f"\nDescription:")
        print("-" * 40)
        print(ticket.get('description', 'No description'))
        
        print(f"\nCreated: {ticket['created_at']}")
        print(f"Updated: {ticket['updated_at']}")
        
        if args.verbose and ticket.get('metadata'):
            print(f"\nMetadata:")
            print("-" * 40)
            for key, value in ticket['metadata'].items():
                print(f"  {key}: {value}")
    
    def update(self, args):
        """Update a ticket (using ai-trackdown directly)."""
        # For update operations, delegate to ai-trackdown CLI
        cmd = ["ai-trackdown", "update", args.id]
        
        if args.status:
            cmd.extend(["--status", args.status])
        if args.priority:
            cmd.extend(["--priority", args.priority])
        if args.assign:
            cmd.extend(["--assign", args.assign])
        if args.tags:
            cmd.extend(["--tags", args.tags])
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Updated ticket: {args.id}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to update ticket: {args.id}")
            sys.exit(1)
    
    def close(self, args):
        """Close a ticket."""
        # Use update with status=closed
        cmd = ["ai-trackdown", "update", args.id, "--status", "closed"]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Closed ticket: {args.id}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to close ticket: {args.id}")
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Simplified ticket management for ai-trackdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ticket create "Fix login bug" -t bug -p high
  ticket create "Add feature" -t feature -d "Detailed description here"
  ticket list
  ticket list -v --limit 20
  ticket view TSK-0001
  ticket update TSK-0001 -s in_progress
  ticket close TSK-0001

Ticket Types:
  task     - General task (default)
  bug      - Bug report
  feature  - Feature request
  issue    - General issue
  
Priority Levels:
  low, medium (default), high, critical
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new ticket')
    create_parser.add_argument('title', help='Ticket title')
    create_parser.add_argument('-t', '--type', default='task',
                              choices=['task', 'bug', 'feature', 'issue'],
                              help='Ticket type (default: task)')
    create_parser.add_argument('-p', '--priority', default='medium',
                              choices=['low', 'medium', 'high', 'critical'],
                              help='Priority level (default: medium)')
    create_parser.add_argument('-d', '--description', nargs='*',
                              help='Ticket description')
    create_parser.add_argument('--tags', help='Comma-separated tags')
    create_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Verbose output')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent tickets')
    list_parser.add_argument('--limit', type=int, default=10,
                            help='Number of tickets to show (default: 10)')
    list_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Show detailed ticket information')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View a specific ticket')
    view_parser.add_argument('id', help='Ticket ID (e.g., TSK-0001)')
    view_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Show metadata')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update a ticket')
    update_parser.add_argument('id', help='Ticket ID')
    update_parser.add_argument('-s', '--status',
                              choices=['open', 'in_progress', 'closed', 'on_hold'],
                              help='Update status')
    update_parser.add_argument('-p', '--priority',
                              choices=['low', 'medium', 'high', 'critical'],
                              help='Update priority')
    update_parser.add_argument('-a', '--assign', help='Assign to user')
    update_parser.add_argument('--tags', help='Update tags (comma-separated)')
    
    # Close command
    close_parser = subparsers.add_parser('close', help='Close a ticket')
    close_parser.add_argument('id', help='Ticket ID')
    
    # Help command
    help_parser = subparsers.add_parser('help', help='Show this help message')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command
    if not args.command or args.command == 'help':
        parser.print_help()
        return 0
    
    # Execute command
    cli = TicketCLI()
    
    try:
        if args.command == 'create':
            cli.create(args)
        elif args.command == 'list':
            cli.list(args)
        elif args.command == 'view':
            cli.view(args)
        elif args.command == 'update':
            cli.update(args)
        elif args.command == 'close':
            cli.close(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())