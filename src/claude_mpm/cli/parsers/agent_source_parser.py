"""Agent source command parser for agent repository management.

WHY: This module provides CLI commands for managing agent source repositories
(Git repositories containing agent markdown files). Parallel to skill source management
but for the agent deployment system (multi-tier Git-based agents).

DESIGN DECISION: Agent source management is separate from agent deployment to
maintain clear separation of concerns:
- agent-source commands: Manage repository configuration
- agents commands: View and interact with agents themselves

IMPLEMENTATION NOTE: This module is adapted from skill_source_parser.py, following
the same proven patterns but for agent repositories instead of skills.
"""

import argparse

from .base_parser import add_common_arguments


def add_agent_source_subparser(subparsers) -> argparse.ArgumentParser:
    """Add the agent-source subparser with all repository management commands.

    WHY: Agent sources (Git repositories) need their own command group
    for managing repository configuration, priorities, and synchronization.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured agent-source subparser
    """
    # Agent source command with subcommands
    agent_source_parser = subparsers.add_parser(
        "agent-source",
        help="Manage agent source repositories",
    )
    add_common_arguments(agent_source_parser)

    agent_source_subparsers = agent_source_parser.add_subparsers(
        dest="agent_source_command",
        help="Agent source repository commands",
        metavar="SUBCOMMAND",
    )

    # Add repository
    add_parser = agent_source_subparsers.add_parser(
        "add",
        help="Add a new agent source repository",
    )
    add_parser.add_argument(
        "url",
        help="Git repository URL (e.g., https://github.com/owner/repo)",
    )
    add_parser.add_argument(
        "--subdirectory",
        help="Subdirectory within repository containing agents (e.g., 'agents')",
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
    add_parser.add_argument(
        "--test",
        action="store_true",
        help="Test repository access without saving to configuration",
    )
    add_parser.add_argument(
        "--no-test",
        action="store_true",
        dest="skip_test",
        help="Skip immediate testing (not recommended)",
    )

    # Remove repository
    remove_parser = agent_source_subparsers.add_parser(
        "remove",
        help="Remove an agent source repository",
    )
    remove_parser.add_argument(
        "source_id",
        help="Source identifier (e.g., 'owner/repo' or 'owner/repo/subdirectory')",
    )
    remove_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # List repositories
    list_parser = agent_source_subparsers.add_parser(
        "list",
        help="List configured agent source repositories",
    )
    list_parser.add_argument(
        "--by-priority",
        action="store_true",
        dest="by_priority",
        help="Sort by priority (lowest first)",
    )
    list_parser.add_argument(
        "--enabled-only",
        action="store_true",
        dest="enabled_only",
        help="Show only enabled repositories",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Update/sync repositories
    update_parser = agent_source_subparsers.add_parser(
        "update",
        help="Update (sync) agent sources from Git",
    )
    update_parser.add_argument(
        "source_id",
        nargs="?",
        help="Optional: Update only this repository (default: update all)",
    )
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if cache is fresh",
    )

    # Enable repository
    enable_parser = agent_source_subparsers.add_parser(
        "enable",
        help="Enable a disabled repository",
    )
    enable_parser.add_argument(
        "source_id",
        help="Source identifier to enable",
    )

    # Disable repository
    disable_parser = agent_source_subparsers.add_parser(
        "disable",
        help="Disable a repository",
    )
    disable_parser.add_argument(
        "source_id",
        help="Source identifier to disable",
    )

    # Show repository details
    show_parser = agent_source_subparsers.add_parser(
        "show",
        help="Show details for an agent source",
    )
    show_parser.add_argument(
        "source_id",
        help="Source identifier to show",
    )
    show_parser.add_argument(
        "--agents",
        action="store_true",
        help="Also list agents from this source",
    )

    return agent_source_parser
