"""
Messages command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to cross-project messaging commands,
enabling asynchronous communication between Claude MPM instances.

DESIGN DECISION: Messages commands expose file-based inbox/outbox functionality via CLI
for sending, listing, reading, and replying to messages across projects.
"""

import argparse

from .base_parser import add_common_arguments


def add_messages_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the messages subparser with all messaging commands.

    WHY: Cross-project messaging has multiple subcommands for sending, listing,
    reading, and managing messages that need their own argument structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured messages subparser
    """
    # Messages command with subcommands
    messages_parser = subparsers.add_parser(
        "message", help="Send and receive messages between Claude MPM instances"
    )
    add_common_arguments(messages_parser)

    messages_subparsers = messages_parser.add_subparsers(
        dest="message_command", help="Message commands", metavar="SUBCOMMAND"
    )

    # Send command
    send_parser = messages_subparsers.add_parser(
        "send", help="Send a message to another project"
    )
    send_parser.add_argument(
        "to_project",
        help="Absolute path to target project (e.g., /Users/name/Projects/web-app)",
    )
    send_parser.add_argument("--body", "-b", help="Message body content")
    send_parser.add_argument(
        "--body-file",
        help="Read body from file (use '-' for stdin)",
    )
    send_parser.add_argument(
        "--subject", "-s", default="Message from Claude MPM", help="Message subject"
    )
    send_parser.add_argument(
        "--to-agent",
        default="pm",
        help="Target agent (pm, engineer, qa, ops, etc.)",
    )
    send_parser.add_argument(
        "--type",
        default="task",
        choices=["task", "request", "notification", "reply"],
        help="Message type (default: task)",
    )
    send_parser.add_argument(
        "--priority",
        default="normal",
        choices=["low", "normal", "high", "urgent"],
        help="Message priority (default: normal)",
    )
    send_parser.add_argument(
        "--from-agent", default="pm", help="Sending agent name (default: pm)"
    )
    send_parser.add_argument(
        "--attachments",
        nargs="+",
        help="File paths to attach (space-separated)",
    )

    # List command
    list_parser = messages_subparsers.add_parser("list", help="List messages in inbox")
    list_parser.add_argument(
        "--status",
        choices=["unread", "read", "archived"],
        help="Filter by message status",
    )
    list_parser.add_argument(
        "--agent", help="Filter by target agent (pm, engineer, qa, etc.)"
    )

    # Read command
    read_parser = messages_subparsers.add_parser("read", help="Read a specific message")
    read_parser.add_argument("message_id", help="Message ID to read")

    # Archive command
    archive_parser = messages_subparsers.add_parser("archive", help="Archive a message")
    archive_parser.add_argument("message_id", help="Message ID to archive")

    # Reply command
    reply_parser = messages_subparsers.add_parser("reply", help="Reply to a message")
    reply_parser.add_argument("message_id", help="Message ID to reply to")
    reply_parser.add_argument("--body", "-b", help="Reply body content")
    reply_parser.add_argument(
        "--body-file",
        help="Read body from file (use '-' for stdin)",
    )
    reply_parser.add_argument(
        "--subject", "-s", help="Reply subject (default: Re: <original subject>)"
    )
    reply_parser.add_argument(
        "--from-agent", default="pm", help="Sending agent name (default: pm)"
    )

    # Check command (quick status)
    messages_subparsers.add_parser(
        "check", help="Check for new messages (quick status)"
    )

    # Sessions command
    sessions_parser = messages_subparsers.add_parser(
        "sessions", help="List registered messaging sessions"
    )
    sessions_parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Show all sessions (including inactive/stale)",
    )

    # Shortcut command group
    shortcut_parser = messages_subparsers.add_parser(
        "shortcut", help="Manage project path shortcuts"
    )
    shortcut_subparsers = shortcut_parser.add_subparsers(
        dest="shortcut_command", help="Shortcut commands", metavar="SHORTCUT_SUBCOMMAND"
    )

    # shortcut add
    shortcut_add = shortcut_subparsers.add_parser(
        "add", help="Add or update a shortcut"
    )
    shortcut_add.add_argument(
        "name", help="Shortcut name (alphanumeric, underscores, hyphens)"
    )
    shortcut_add.add_argument("path", help="Absolute directory path to shortcut to")

    # shortcut list
    shortcut_subparsers.add_parser("list", help="List all shortcuts")

    # shortcut remove
    shortcut_remove = shortcut_subparsers.add_parser("remove", help="Remove a shortcut")
    shortcut_remove.add_argument("name", help="Shortcut name to remove")

    # shortcut resolve
    shortcut_resolve = shortcut_subparsers.add_parser(
        "resolve", help="Resolve a shortcut name to its path"
    )
    shortcut_resolve.add_argument("name", help="Shortcut name to resolve")

    return messages_parser
