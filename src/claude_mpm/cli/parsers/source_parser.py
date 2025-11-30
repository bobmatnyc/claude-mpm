"""Source command parser for agent repository management.

WHY: This module provides CLI commands for managing agent source repositories
(Git repositories containing agent markdown files). Extracted into its own
module to support the single-tier deployment migration (Phase 2).

DESIGN DECISION: Source management is separate from agent deployment to
maintain clear separation of concerns:
- source commands: Manage repository configuration
- agents commands: Deploy and manage agents themselves
"""

import argparse

from .base_parser import add_common_arguments


def add_source_subparser(subparsers) -> argparse.ArgumentParser:
    """Add the source subparser with all repository management commands.

    WHY: Agent sources (Git repositories) need their own command group
    for managing repository configuration, priorities, and synchronization.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured source subparser
    """
    # Source command with subcommands
    source_parser = subparsers.add_parser(
        "source",
        help="Manage agent source repositories",
    )
    add_common_arguments(source_parser)

    source_subparsers = source_parser.add_subparsers(
        dest="source_command",
        help="Source repository commands",
        metavar="SUBCOMMAND",
    )

    # Add repository
    add_parser = source_subparsers.add_parser(
        "add",
        help="Add a new agent source repository",
    )
    add_parser.add_argument(
        "url",
        help="GitHub repository URL (e.g., https://github.com/owner/repo)",
    )
    add_parser.add_argument(
        "--subdirectory",
        "--subdir",
        help="Subdirectory path within repository (e.g., 'agents')",
    )
    add_parser.add_argument(
        "--priority",
        type=int,
        default=100,
        help="Priority for conflict resolution (lower = higher precedence, default: 100)",
    )
    add_parser.add_argument(
        "--disabled",
        action="store_true",
        help="Add repository but keep it disabled",
    )

    # Remove repository
    remove_parser = source_subparsers.add_parser(
        "remove",
        help="Remove an agent source repository",
    )
    remove_parser.add_argument(
        "identifier",
        help="Repository identifier (e.g., 'owner/repo' or 'owner/repo/subdirectory')",
    )

    # List repositories
    list_parser = source_subparsers.add_parser(
        "list",
        help="List configured agent source repositories",
    )
    list_parser.add_argument(
        "--all",
        action="store_true",
        dest="show_all",
        help="Show disabled repositories (default: only enabled)",
    )

    # Enable repository
    enable_parser = source_subparsers.add_parser(
        "enable",
        help="Enable a disabled repository",
    )
    enable_parser.add_argument(
        "identifier",
        help="Repository identifier to enable",
    )

    # Disable repository
    disable_parser = source_subparsers.add_parser(
        "disable",
        help="Disable a repository",
    )
    disable_parser.add_argument(
        "identifier",
        help="Repository identifier to disable",
    )

    # Disable system repository
    disable_system_parser = source_subparsers.add_parser(
        "disable-system",
        help="Disable or enable the default system repository",
    )
    disable_system_parser.add_argument(
        "--enable",
        action="store_true",
        help="Re-enable system repository instead of disabling",
    )

    # Sync repositories
    sync_parser = source_subparsers.add_parser(
        "sync",
        help="Sync agent sources from Git",
    )
    sync_parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync even if cache is fresh (ignore ETags)",
    )
    sync_parser.add_argument(
        "identifier",
        nargs="?",
        help="Optional: Sync only this repository (default: sync all)",
    )

    return source_parser
