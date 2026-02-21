"""
Cross-project messaging commands for claude-mpm CLI.

WHY: Enables users to send and receive messages between Claude MPM instances
running in different projects for coordinated asynchronous work.

DESIGN:
- Simple subcommands: send, list, read, archive, reply
- Rich console output for readability
- Integration with UnifiedPathManager for project detection
"""

from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table

from ...core.unified_paths import UnifiedPathManager
from ...services.communication.message_service import MessageService
from ...utils.console import console
from ..shared import BaseCommand, CommandResult


class MessagesCommand(BaseCommand):
    """Cross-project messaging command."""

    def __init__(self):
        super().__init__("messages")
        self.path_manager = UnifiedPathManager.get_instance()
        self.message_service = MessageService(self.path_manager.project_root)

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, "message_command") or not args.message_command:
            return "No message subcommand specified"

        valid_commands = ["send", "list", "read", "archive", "reply", "check"]
        if args.message_command not in valid_commands:
            return f"Unknown message command: {args.message_command}. Valid: {', '.join(valid_commands)}"

        # Validate send command args
        if args.message_command == "send":
            if not hasattr(args, "to_project") or not args.to_project:
                return "Missing required argument: --to-project"
            if not hasattr(args, "body") or not args.body:
                return "Missing required argument: --body"

        # Validate read/archive/reply commands
        if args.message_command in ["read", "archive", "reply"]:
            if not hasattr(args, "message_id") or not args.message_id:
                return (
                    f"Missing required argument for {args.message_command}: message_id"
                )

        return None

    def run(self, args) -> CommandResult:
        """Execute the messages command."""
        if args.message_command == "send":
            return self._send_message(args)
        if args.message_command == "list":
            return self._list_messages(args)
        if args.message_command == "read":
            return self._read_message(args)
        if args.message_command == "archive":
            return self._archive_message(args)
        if args.message_command == "reply":
            return self._reply_to_message(args)
        if args.message_command == "check":
            return self._check_messages(args)

        return CommandResult.error_result(
            f"Unknown message command: {args.message_command}"
        )

    def _send_message(self, args) -> CommandResult:
        """Send a message to another project."""
        try:
            # Resolve target project path
            to_project = Path(args.to_project).resolve()

            if not to_project.exists():
                return CommandResult.error_result(
                    f"Target project does not exist: {to_project}"
                )

            # Send message
            message = self.message_service.send_message(
                to_project=str(to_project),
                to_agent=getattr(args, "to_agent", "pm"),
                message_type=getattr(args, "type", "task"),
                subject=getattr(args, "subject", "Message from Claude MPM"),
                body=args.body,
                priority=getattr(args, "priority", "normal"),
                from_agent=getattr(args, "from_agent", "pm"),
                attachments=getattr(args, "attachments", None),
            )

            console.print(
                Panel(
                    f"[green]✓[/green] Message sent to [cyan]{to_project}[/cyan]\n"
                    f"Message ID: [yellow]{message.id}[/yellow]\n"
                    f"Target Agent: [cyan]{message.to_agent}[/cyan]\n"
                    f"Priority: [yellow]{message.priority}[/yellow]",
                    title="[bold]Message Sent[/bold]",
                    border_style="green",
                )
            )

            return CommandResult.success_result(f"Message sent: {message.id}")

        except Exception as e:
            return CommandResult.error_result(f"Failed to send message: {e}")

    def _list_messages(self, args) -> CommandResult:
        """List messages in inbox."""
        try:
            status_filter = getattr(args, "status", None)
            agent_filter = getattr(args, "agent", None)

            messages = self.message_service.list_messages(
                status=status_filter, agent=agent_filter
            )

            if not messages:
                console.print("[yellow]No messages in inbox[/yellow]")
                return CommandResult.success_result("No messages")

            # Create table
            table = Table(title="Inbox Messages", show_header=True, header_style="bold")
            table.add_column("ID", style="cyan")
            table.add_column("From", style="blue")
            table.add_column("Agent", style="magenta")
            table.add_column("Type", style="yellow")
            table.add_column("Priority", style="red")
            table.add_column("Status", style="green")
            table.add_column("Subject", style="white")
            table.add_column("Date", style="dim")

            for msg in messages:
                # Shorten project path for display
                from_project = Path(msg.from_project).name

                # Format date
                date_str = msg.created_at.strftime("%m/%d %H:%M")

                # Status emoji
                status_display = {
                    "unread": "📬 unread",
                    "read": "📭 read",
                    "archived": "📦 archived",
                }.get(msg.status, msg.status)

                # Priority color
                priority_style = {
                    "urgent": "[bold red]",
                    "high": "[red]",
                    "normal": "[yellow]",
                    "low": "[dim]",
                }.get(msg.priority, "")

                table.add_row(
                    msg.id[:16] + "...",
                    from_project,
                    msg.to_agent,
                    msg.type,
                    f"{priority_style}{msg.priority}[/]",
                    status_display,
                    msg.subject[:40] + ("..." if len(msg.subject) > 40 else ""),
                    date_str,
                )

            console.print(table)
            console.print(
                f"\n[dim]Total: {len(messages)} message(s) | "
                f"Use 'claude-mpm message read <id>' to view[/dim]"
            )

            return CommandResult.success_result(f"Listed {len(messages)} messages")

        except Exception as e:
            return CommandResult.error_result(f"Failed to list messages: {e}")

    def _read_message(self, args) -> CommandResult:
        """Read a specific message."""
        try:
            message = self.message_service.read_message(args.message_id)

            if not message:
                return CommandResult.error_result(
                    f"Message not found: {args.message_id}"
                )

            # Display message
            from_project = Path(message.from_project).name
            date_str = message.created_at.strftime("%Y-%m-%d %H:%M:%S")

            header = (
                f"[bold]From:[/bold] [cyan]{from_project}[/cyan] ({message.from_agent})\n"
                f"[bold]To:[/bold] {message.to_agent}\n"
                f"[bold]Type:[/bold] {message.type}\n"
                f"[bold]Priority:[/bold] {message.priority}\n"
                f"[bold]Date:[/bold] {date_str}\n"
                f"[bold]Status:[/bold] {message.status}"
            )

            console.print(Panel(header, title=f"[bold]{message.subject}[/bold]"))
            console.print()
            console.print(message.body)

            if message.attachments:
                console.print("\n[bold]Attachments:[/bold]")
                for attachment in message.attachments:
                    console.print(f"  • {attachment}")

            console.print(
                f"\n[dim]Reply with: claude-mpm message reply {message.id}[/dim]"
            )

            return CommandResult.success_result(f"Read message: {message.id}")

        except Exception as e:
            return CommandResult.error_result(f"Failed to read message: {e}")

    def _archive_message(self, args) -> CommandResult:
        """Archive a message."""
        try:
            success = self.message_service.archive_message(args.message_id)

            if not success:
                return CommandResult.error_result(
                    f"Message not found: {args.message_id}"
                )

            console.print(f"[green]✓[/green] Archived message: {args.message_id}")
            return CommandResult.success_result(f"Archived: {args.message_id}")

        except Exception as e:
            return CommandResult.error_result(f"Failed to archive message: {e}")

    def _reply_to_message(self, args) -> CommandResult:
        """Reply to a message."""
        try:
            if not hasattr(args, "body") or not args.body:
                return CommandResult.error_result("Missing required argument: --body")

            reply = self.message_service.reply_to_message(
                original_message_id=args.message_id,
                subject=getattr(args, "subject", "Re: Your message"),
                body=args.body,
                from_agent=getattr(args, "from_agent", "pm"),
            )

            if not reply:
                return CommandResult.error_result(
                    f"Original message not found: {args.message_id}"
                )

            console.print(
                f"[green]✓[/green] Reply sent: {reply.id}\n"
                f"[dim]Recipient will see it in their inbox[/dim]"
            )

            return CommandResult.success_result(f"Reply sent: {reply.id}")

        except Exception as e:
            return CommandResult.error_result(f"Failed to send reply: {e}")

    def _check_messages(self, args) -> CommandResult:
        """Check for new messages (quick status)."""
        try:
            unread_count = self.message_service.get_unread_count()

            if unread_count == 0:
                console.print("[green]✓[/green] No new messages")
                return CommandResult.success_result("No new messages")

            console.print(f"[yellow]📬 {unread_count} unread message(s)[/yellow]")
            console.print("[dim]Use 'claude-mpm message list' to view[/dim]")

            return CommandResult.success_result(f"{unread_count} unread messages")

        except Exception as e:
            return CommandResult.error_result(f"Failed to check messages: {e}")


def manage_messages(args) -> int:
    """Entry point for message management commands."""
    command = MessagesCommand()
    result = command.execute(args)
    return result.exit_code
