"""
Config command parser for claude-mpm CLI.

WHY: This module provides the unified config command with subcommands for
auto-configuration, viewing, validation, and status checks.

DESIGN DECISION: 'config' provides both auto-configuration (default) and
manual configuration management through subcommands.
"""

import argparse
from pathlib import Path

from ...constants import CLICommands
from .base_parser import add_common_arguments


def add_config_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the unified config subparser with all configuration subcommands.

    WHY: 'config' provides comprehensive configuration management including
    auto-detection, manual viewing, validation, and status checks.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured config subparser
    """
    # Config command with subcommands
    config_parser = subparsers.add_parser(
        CLICommands.CONFIG.value,
        help="Unified configuration management with auto-detection and manual viewing",
        description="""
Unified configuration management for Claude MPM.

Available commands:
  auto        Auto-configure agents and skills based on detected toolchain (default)
  view        View current configuration settings
  validate    Validate configuration files
  status      Show configuration health and status

Running 'config' with no subcommand defaults to 'auto' in preview mode.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(config_parser)

    # Add subcommands
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Configuration commands", metavar="SUBCOMMAND"
    )

    # Auto-configure subcommand (default)
    auto_parser = config_subparsers.add_parser(
        "auto",
        help="Auto-configure agents and skills based on detected toolchain",
        description="""
Auto-configure agents and skills for your project based on detected toolchain.

This command analyzes your project to detect languages, frameworks, and
deployment targets, then recommends and deploys appropriate specialized
agents and skills automatically.

The command provides safety features including:
  • Preview mode to see changes before applying
  • Confidence thresholds to ensure quality matches
  • Validation gates to block invalid configurations
  • Rollback on failure to maintain consistency
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_arguments(auto_parser)

    # Configuration mode
    mode_group = auto_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--preview",
        "--dry-run",
        dest="preview",
        action="store_true",
        help="Show what would be configured without deploying (preview mode)",
    )
    mode_group.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts and deploy automatically",
    )

    # Scope selection
    scope_group = auto_parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--agents-only",
        action="store_true",
        help="Configure agents only (skip skills)",
    )
    scope_group.add_argument(
        "--skills-only",
        action="store_true",
        help="Configure skills only (skip agents)",
    )

    # Configuration options
    auto_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        metavar="FLOAT",
        help="Minimum confidence threshold for recommendations (0.0-1.0, default: 0.8)",
    )

    auto_parser.add_argument(
        "--project-path",
        type=Path,
        metavar="PATH",
        help="Project path to analyze (default: current directory)",
    )

    auto_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    # View subcommand
    view_parser = config_subparsers.add_parser(
        "view",
        help="View current configuration settings",
    )
    add_common_arguments(view_parser)

    view_parser.add_argument(
        "--section",
        type=str,
        metavar="SECTION",
        help="Specific configuration section to view (agents, memory, websocket, etc.)",
    )
    view_parser.add_argument(
        "--format",
        choices=["yaml", "json", "table", "text"],
        default="table",
        help="Output format (default: table)",
    )
    view_parser.add_argument(
        "--show-defaults",
        action="store_true",
        help="Include default values in output",
    )
    view_parser.add_argument(
        "--config-file",
        type=Path,
        metavar="PATH",
        help="Specific config file to view (default: all)",
    )

    # Validate subcommand
    validate_parser = config_subparsers.add_parser(
        "validate",
        help="Validate configuration files for correctness",
    )
    add_common_arguments(validate_parser)

    validate_parser.add_argument(
        "--config-file",
        type=Path,
        metavar="PATH",
        help="Validate specific config file (default: all)",
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Use strict validation rules",
    )
    validate_parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix validation errors automatically",
    )

    # Status subcommand
    status_parser = config_subparsers.add_parser(
        "status",
        help="Show configuration health and status",
    )
    add_common_arguments(status_parser)

    # Note: --verbose is provided by add_common_arguments()
    status_parser.add_argument(
        "--check-response-logging",
        action="store_true",
        help="Check response logging configuration",
    )
    status_parser.add_argument(
        "--format",
        choices=["yaml", "json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    status_parser.add_argument(
        "--config-file",
        type=Path,
        metavar="PATH",
        help="Specific config file to check (default: all)",
    )

    return config_parser
