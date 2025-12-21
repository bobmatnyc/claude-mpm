"""
Auto-Configuration Parser for Claude MPM CLI
============================================

WHY: This module provides argument parsing for auto-configuration commands,
enabling users to customize detection, recommendation, and deployment behavior.

DESIGN DECISION: Follows existing parser patterns in the codebase, using
add_common_arguments for consistency. Provides sensible defaults while
allowing full customization.

Part of TSK-0054: Auto-Configuration Feature - Phase 5
"""

import argparse
from pathlib import Path

from .base_parser import add_common_arguments


def add_auto_configure_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the auto-configure subparser for automated agent configuration.

    WHY: Auto-configuration simplifies onboarding by detecting project toolchain
    and deploying appropriate agents automatically.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured auto-configure subparser
    """
    # Auto-configure command
    auto_configure_parser = subparsers.add_parser(
        "auto-configure",
        help="Auto-configure agents based on project toolchain detection",
        description="""
Auto-configure agents for your project based on detected toolchain.

This command analyzes your project to detect languages, frameworks, and
deployment targets, then recommends and deploys appropriate specialized
agents automatically.

The command provides safety features including:
  • Preview mode to see changes before applying
  • Confidence thresholds to ensure quality matches
  • Validation gates to block invalid configurations
  • Rollback on failure to maintain consistency
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive configuration with confirmation
  claude-mpm auto-configure

  # Preview configuration without deploying
  claude-mpm auto-configure --preview

  # Auto-approve deployment (for scripts)
  claude-mpm auto-configure --yes

  # Require 90% confidence for recommendations
  claude-mpm auto-configure --min-confidence 0.9

  # JSON output for scripting
  claude-mpm auto-configure --json

  # Configure specific project directory
  claude-mpm auto-configure --project-path /path/to/project
        """,
    )
    add_common_arguments(auto_configure_parser)

    # Configuration mode
    mode_group = auto_configure_parser.add_mutually_exclusive_group()
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
    scope_group = auto_configure_parser.add_mutually_exclusive_group()
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
    auto_configure_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        metavar="FLOAT",
        help="Minimum confidence threshold for recommendations (0.0-1.0, default: 0.8)",
    )

    auto_configure_parser.add_argument(
        "--project-path",
        type=Path,
        metavar="PATH",
        help="Project path to analyze (default: current directory)",
    )

    return auto_configure_parser
