"""
Memory command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to memory management commands,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Memory commands handle agent memory files and have their own
subcommand structure that benefits from separation.
"""

import argparse

from ...constants import CLICommands, MemoryCommands
from .base_parser import add_common_arguments


def add_memory_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the memory subparser with all memory management commands.

    WHY: Memory management has multiple subcommands for initialization,
    listing, and management that need their own argument structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured memory subparser
    """
    # Memory command with subcommands
    memory_parser = subparsers.add_parser(
        CLICommands.MEMORY.value, help="Manage agent memory files"
    )
    add_common_arguments(memory_parser)

    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", help="Memory commands", metavar="SUBCOMMAND"
    )

    # Init command
    init_parser = memory_subparsers.add_parser(
        MemoryCommands.INIT.value,
        help="Initialize project-specific memories via PM agent",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Force initialization even if memories already exist",
    )
    init_parser.add_argument(
        "--template", help="Memory template to use for initialization"
    )

    # List command
    list_parser = memory_subparsers.add_parser(
        MemoryCommands.SHOW.value, help="List available memory files"
    )
    list_parser.add_argument(
        "--type", choices=["project", "user", "system"], help="Filter by memory type"
    )
    list_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed memory information"
    )

    # View command
    view_parser = memory_subparsers.add_parser(
        MemoryCommands.VIEW.value, help="View memory file contents"
    )
    view_parser.add_argument("memory_name", help="Name of the memory file to view")
    view_parser.add_argument(
        "--raw", action="store_true", help="Show raw memory content without formatting"
    )

    # Edit command
    edit_parser = memory_subparsers.add_parser(
        MemoryCommands.ADD.value, help="Edit memory file"
    )
    edit_parser.add_argument("memory_name", help="Name of the memory file to edit")
    edit_parser.add_argument("--editor", help="Editor to use (overrides default)")

    # Create command
    create_parser = memory_subparsers.add_parser(
        MemoryCommands.BUILD.value, help="Create new memory file"
    )
    create_parser.add_argument("memory_name", help="Name of the memory file to create")
    create_parser.add_argument(
        "--type",
        choices=["project", "user"],
        default="project",
        help="Type of memory to create (default: project)",
    )
    create_parser.add_argument("--template", help="Template to use for the new memory")
    create_parser.add_argument("--content", help="Initial content for the memory file")

    # Delete command
    delete_parser = memory_subparsers.add_parser(
        MemoryCommands.CLEAN.value, help="Delete memory file"
    )
    delete_parser.add_argument("memory_name", help="Name of the memory file to delete")
    delete_parser.add_argument(
        "--force", action="store_true", help="Force deletion without confirmation"
    )
    delete_parser.add_argument(
        "--backup", action="store_true", help="Create backup before deletion"
    )

    # Sync command
    sync_parser = memory_subparsers.add_parser(
        MemoryCommands.OPTIMIZE.value, help="Sync memory files across environments"
    )
    sync_parser.add_argument(
        "--source",
        choices=["project", "user", "system"],
        help="Source memory type to sync from",
    )
    sync_parser.add_argument(
        "--target", choices=["project", "user"], help="Target memory type to sync to"
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing",
    )

    # Validate command
    validate_parser = memory_subparsers.add_parser(
        MemoryCommands.STATUS.value, help="Validate memory file format and content"
    )
    validate_parser.add_argument(
        "memory_name",
        nargs="?",
        help="Name of specific memory file to validate (default: all)",
    )
    validate_parser.add_argument(
        "--strict", action="store_true", help="Use strict validation rules"
    )

    return memory_parser
