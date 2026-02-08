"""
Slack command parser for claude-mpm CLI.

WHY: This module provides the slack command for setting up Slack MPM integration.

DESIGN DECISION: Simple 'slack setup' command that runs the setup wizard script.
"""

import argparse

from .base_parser import add_common_arguments


def add_slack_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the slack subparser for Slack MPM setup.

    WHY: Provides a simple 'claude-mpm slack setup' command similar to oauth setup.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured slack subparser
    """
    # Slack command
    slack_parser = subparsers.add_parser(
        "slack",
        help="Set up Slack MPM integration",
        description="""
Set up Slack MPM integration.

Available commands:
  setup    Run the interactive Slack setup wizard

Example:
  claude-mpm slack setup
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(slack_parser)

    # Add subcommands
    slack_subparsers = slack_parser.add_subparsers(
        dest="slack_command", help="Slack commands", metavar="SUBCOMMAND"
    )

    # Setup subcommand
    setup_parser = slack_subparsers.add_parser(
        "setup",
        help="Set up Slack MPM integration",
        description="""
Run the interactive Slack setup wizard.

This will guide you through:
  • Creating or configuring a Slack app
  • Setting up OAuth credentials
  • Configuring event subscriptions
  • Testing the connection

Prerequisites:
  • Access to create apps in your Slack workspace
  • Admin permissions (or approval from workspace admin)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(setup_parser)

    return slack_parser
