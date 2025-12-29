"""
Profile command parser for claude-mpm CLI.

WHY: This module provides the profile command for managing deployment profiles
that control which agents and skills are deployed.

DESIGN DECISION: Provides intuitive subcommands for listing, activating,
and inspecting profiles to reduce context usage by limiting deployed components.
"""

import argparse

from ...constants import CLICommands
from .base_parser import add_common_arguments


def add_profile_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the profile subparser for deployment profile management.

    WHY: Users need to manage which agents and skills are deployed to reduce
    context usage and improve performance. Profiles define enabled/disabled
    agents and skills for specific workflows.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured profile subparser
    """
    # Profile command with subcommands
    profile_parser = subparsers.add_parser(
        "profile",
        help="Manage deployment profiles for agents and skills",
        description="""
Deployment profile management for Claude MPM.

Profiles control which agents and skills are deployed, reducing context usage
by limiting available agents to only what's needed for your workflow.

Available commands:
  list      List all available profiles
  set       Set the active profile
  status    Show current active profile and filtering summary
  show      Show detailed configuration of a profile

Example workflows:
  # List available profiles
  claude-mpm profile list

  # Activate a profile
  claude-mpm profile set framework-development

  # Check current profile status
  claude-mpm profile status

  # View profile details
  claude-mpm profile show framework-development
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(profile_parser)

    # Add subcommands
    profile_subparsers = profile_parser.add_subparsers(
        dest="profile_command",
        help="Profile management commands",
        metavar="SUBCOMMAND",
    )

    # List subcommand
    list_parser = profile_subparsers.add_parser(
        "list",
        help="List all available deployment profiles",
        description="""
List all profiles found in .claude-mpm/profiles/ directory.

Shows profile names, descriptions, and indicates which profile is currently active.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(list_parser)

    # Set subcommand
    set_parser = profile_subparsers.add_parser(
        "set",
        help="Set the active deployment profile",
        description="""
Set the active deployment profile.

This updates configuration.yaml with the selected profile, which will be
applied on next startup or when running 'claude-mpm init'.

Examples:
  # Activate framework development profile
  claude-mpm profile set framework-development

  # Activate minimal profile for focused work
  claude-mpm profile set minimal
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(set_parser)
    set_parser.add_argument(
        "profile_name",
        help="Name of profile to activate (without .yaml extension)",
    )

    # Status subcommand
    status_parser = profile_subparsers.add_parser(
        "status",
        help="Show current active profile and filtering summary",
        description="""
Display current active profile with filtering summary.

Shows:
- Active profile name
- Number of agents enabled/disabled
- Number of skills enabled/disabled
- Disabled skill patterns
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(status_parser)

    # Show subcommand
    show_parser = profile_subparsers.add_parser(
        "show",
        help="Show detailed configuration of a profile",
        description="""
Display detailed configuration of a specific profile.

Shows complete lists of enabled/disabled agents and skills, including
glob patterns for skill filtering.

Examples:
  # Show framework development profile details
  claude-mpm profile show framework-development
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(show_parser)
    show_parser.add_argument(
        "profile_name",
        help="Name of profile to display (without .yaml extension)",
    )

    return profile_parser
