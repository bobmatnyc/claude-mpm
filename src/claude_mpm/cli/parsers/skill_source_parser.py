"""Skill source command parser for skill repository management.

WHY: This module provides CLI commands for managing skill source repositories
(Git repositories containing skill JSON files). Parallel to agent source management
but for the Skills feature (single-tier Git-based skills system).

DESIGN DECISION: Skill source management is separate from skill deployment to
maintain clear separation of concerns:
- skill-source commands: Manage repository configuration
- skills commands: View and interact with skills themselves
"""

import argparse

from .base_parser import add_common_arguments


def add_skill_source_subparser(subparsers) -> argparse.ArgumentParser:
    """Add the skill-source subparser with all repository management commands.

    WHY: Skill sources (Git repositories) need their own command group
    for managing repository configuration, priorities, and synchronization.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured skill-source subparser
    """
    # Skill source command with subcommands
    skill_source_parser = subparsers.add_parser(
        "skill-source",
        help="Manage skill source repositories",
    )
    add_common_arguments(skill_source_parser)

    skill_source_subparsers = skill_source_parser.add_subparsers(
        dest="skill_source_command",
        help="Skill source repository commands",
        metavar="SUBCOMMAND",
    )

    # Add repository
    add_parser = skill_source_subparsers.add_parser(
        "add",
        help="Add a new skill source repository",
    )
    add_parser.add_argument(
        "url",
        help="Git repository URL (e.g., https://github.com/owner/repo)",
    )
    add_parser.add_argument(
        "--branch",
        default="main",
        help="Git branch to use (default: main)",
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
    remove_parser = skill_source_subparsers.add_parser(
        "remove",
        help="Remove a skill source repository",
    )
    remove_parser.add_argument(
        "source_id",
        help="Source identifier (e.g., repository name)",
    )
    remove_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # List repositories
    list_parser = skill_source_subparsers.add_parser(
        "list",
        help="List configured skill source repositories",
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
    update_parser = skill_source_subparsers.add_parser(
        "update",
        help="Update (sync) skill sources from Git",
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
    enable_parser = skill_source_subparsers.add_parser(
        "enable",
        help="Enable a disabled repository",
    )
    enable_parser.add_argument(
        "source_id",
        help="Source identifier to enable",
    )

    # Disable repository
    disable_parser = skill_source_subparsers.add_parser(
        "disable",
        help="Disable a repository",
    )
    disable_parser.add_argument(
        "source_id",
        help="Source identifier to disable",
    )

    # Show repository details
    show_parser = skill_source_subparsers.add_parser(
        "show",
        help="Show details for a skill source",
    )
    show_parser.add_argument(
        "source_id",
        help="Source identifier to show",
    )
    show_parser.add_argument(
        "--skills",
        action="store_true",
        help="Also list skills from this source",
    )

    return skill_source_parser
