"""
Configure command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to the interactive configuration
management interface, allowing users to enable/disable agents, edit templates,
and manage behavior files.
"""

import argparse

from ...constants import CLICommands
from .base_parser import add_common_arguments


def add_configure_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the configure subparser for interactive configuration management.

    WHY: Users need an interactive way to manage agent configurations,
    templates, and behavior files through a terminal-based interface.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured configure subparser
    """
    # Configure command - interactive configuration
    configure_parser = subparsers.add_parser(
        CLICommands.CONFIGURE.value,
        help="Interactive configuration interface for managing agents and behaviors",
        description="Launch an interactive Rich-based menu for configuring claude-mpm agents, templates, and behavior files",
    )

    # Add common arguments
    add_common_arguments(configure_parser)

    # Configuration scope options
    scope_group = configure_parser.add_argument_group("configuration scope")
    scope_group.add_argument(
        "--scope",
        choices=["project", "user"],
        default="project",
        help="Configuration scope to manage (default: project)",
    )
    # Note: --project-dir is already defined in base_parser.py

    # Direct navigation options (skip main menu)
    nav_group = configure_parser.add_argument_group("direct navigation")
    nav_group.add_argument(
        "--agents", action="store_true", help="Jump directly to agent management"
    )
    nav_group.add_argument(
        "--templates", action="store_true", help="Jump directly to template editing"
    )
    nav_group.add_argument(
        "--behaviors",
        action="store_true",
        help="Jump directly to behavior file management",
    )
    nav_group.add_argument(
        "--startup",
        action="store_true",
        help="Configure startup services and agents",
    )
    nav_group.add_argument(
        "--version-info",
        action="store_true",
        help="Display version information and exit",
    )

    # Non-interactive options
    noninteractive_group = configure_parser.add_argument_group(
        "non-interactive options"
    )
    noninteractive_group.add_argument(
        "--list-agents", action="store_true", help="List all available agents and exit"
    )
    noninteractive_group.add_argument(
        "--enable-agent",
        type=str,
        metavar="AGENT_NAME",
        help="Enable a specific agent and exit",
    )
    noninteractive_group.add_argument(
        "--disable-agent",
        type=str,
        metavar="AGENT_NAME",
        help="Disable a specific agent and exit",
    )
    noninteractive_group.add_argument(
        "--export-config",
        type=str,
        metavar="FILE",
        help="Export current configuration to a file",
    )
    noninteractive_group.add_argument(
        "--import-config",
        type=str,
        metavar="FILE",
        help="Import configuration from a file",
    )

    # Hook management options
    hooks_group = configure_parser.add_argument_group("hook management")
    hooks_group.add_argument(
        "--install-hooks",
        action="store_true",
        help="Install Claude MPM hooks for Claude Code integration",
    )
    hooks_group.add_argument(
        "--verify-hooks",
        action="store_true",
        help="Verify that Claude MPM hooks are properly installed",
    )
    hooks_group.add_argument(
        "--uninstall-hooks",
        action="store_true",
        help="Uninstall Claude MPM hooks",
    )
    hooks_group.add_argument(
        "--force",
        action="store_true",
        help="Force reinstallation of hooks even if they already exist",
    )

    # Display options
    display_group = configure_parser.add_argument_group("display options")
    display_group.add_argument(
        "--no-colors",
        action="store_true",
        help="Disable colored output in the interface",
    )
    display_group.add_argument(
        "--compact", action="store_true", help="Use compact display mode"
    )

    return configure_parser
