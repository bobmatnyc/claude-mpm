from pathlib import Path

"""
Config command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to configuration management,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Configuration commands handle validation and management
of claude-mpm settings and warrant their own module.
"""

import argparse

from ...constants import CLICommands, ConfigCommands
from .base_parser import add_common_arguments


def add_config_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the config subparser with all configuration management commands.

    WHY: Configuration management has multiple subcommands for validation,
    viewing, and editing that need their own argument structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured config subparser
    """
    # Config command with subcommands
    config_parser = subparsers.add_parser(
        CLICommands.CONFIG.value, help="Validate and manage configuration"
    )
    add_common_arguments(config_parser)

    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config commands", metavar="SUBCOMMAND"
    )

    # Validate config
    validate_config_parser = config_subparsers.add_parser(
        ConfigCommands.VALIDATE.value, help="Validate configuration files"
    )
    validate_config_parser.add_argument(
        "--config-file",
        type=Path,
        help="Specific config file to validate (default: all)",
    )
    validate_config_parser.add_argument(
        "--strict", action="store_true", help="Use strict validation rules"
    )
    validate_config_parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix validation errors automatically",
    )

    # View config
    view_config_parser = config_subparsers.add_parser(
        ConfigCommands.VIEW.value, help="View current configuration"
    )
    view_config_parser.add_argument(
        "--section", help="Specific configuration section to view"
    )
    view_config_parser.add_argument(
        "--format",
        choices=["yaml", "json", "table"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    view_config_parser.add_argument(
        "--show-defaults", action="store_true", help="Include default values in output"
    )

    # Status config
    status_config_parser = config_subparsers.add_parser(
        ConfigCommands.STATUS.value, help="Show configuration status"
    )
    status_config_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed status information"
    )

    return config_parser
