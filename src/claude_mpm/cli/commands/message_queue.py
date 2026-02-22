"""
Commands for managing the message queue consumer.
"""

import subprocess  # nosec B404
import sys
from pathlib import Path

import click

from ...services.communication.messaging_db import MessagingDatabase


def message_queue(args):
    """
    Handle message queue commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    subcommand = getattr(args, "queue_command", "status")

    if subcommand == "start":
        return start_queue(args)
    if subcommand == "status":
        return show_status(args)
    if subcommand == "cleanup":
        return cleanup_queue(args)
    click.echo(f"Unknown queue subcommand: {subcommand}")
    return 1


def start_queue(args):
    """Start the message queue consumer."""
    workers = getattr(args, "workers", 2)
    daemon = getattr(args, "daemon", False)

    if daemon:
        click.echo("Starting message queue consumer as daemon...")
        subprocess.Popen(  # nosec B603
            [
                sys.executable,
                "-m",
                "claude_mpm.services.communication.message_consumer",
                "-d",
                "-w",
                str(workers),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        click.echo("✅ Message queue consumer started in background")
    else:
        click.echo(f"Starting message queue consumer with {workers} workers...")
        click.echo("Press Ctrl+C to stop")
        subprocess.call(  # nosec B603
            [
                sys.executable,
                "-m",
                "claude_mpm.services.communication.message_consumer",
                "-w",
                str(workers),
            ]
        )

    return 0


def show_status(args):
    """Show message queue status."""
    try:
        # Check for pending messages in shared database
        db_path = Path.home() / ".claude-mpm" / "messaging.db"
        if db_path.exists():
            db = MessagingDatabase(db_path)
            unread_count = db.get_unread_count()
            click.echo(f"📬 Unread messages in system: {unread_count}")

            # Show queue database info
            queue_db = Path.home() / ".claude-mpm" / "message_queue.db"
            if queue_db.exists():
                size_kb = queue_db.stat().st_size / 1024
                click.echo(f"📦 Queue database size: {size_kb:.1f} KB")
            else:
                click.echo("📦 Queue database: Not initialized")

            # Show active sessions
            registry_db = Path.home() / ".claude-mpm" / "session-registry.db"
            if registry_db.exists():
                registry = MessagingDatabase(registry_db)
                sessions = registry.list_active_sessions()
                click.echo(f"🖥️  Active sessions: {len(sessions)}")
                for session in sessions[:5]:  # Show first 5
                    click.echo(
                        f"   - {session['project_name']} (PID: {session['pid']})"
                    )
        else:
            click.echo("Message system not initialized")

    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)
        return 1

    return 0


def cleanup_queue(args):
    """Clean up old messages and stale sessions."""
    try:
        click.echo("Cleaning up messaging system...")

        # Clean up old messages
        db_path = Path.home() / ".claude-mpm" / "messaging.db"
        if db_path.exists():
            from ...services.communication.message_service import MessageService

            # Use dummy project root
            service = MessageService(Path.cwd())
            deleted = service.cleanup_old_messages(days_to_keep=30)
            click.echo(f"✅ Deleted {deleted} old archived messages")

        # Clean up stale sessions
        registry_db = Path.home() / ".claude-mpm" / "session-registry.db"
        if registry_db.exists():
            registry = MessagingDatabase(registry_db)
            stale = registry.cleanup_stale_sessions(timeout_minutes=60)
            click.echo(f"✅ Marked {stale} stale sessions as inactive")

        click.echo("Cleanup complete!")

    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        return 1

    return 0
