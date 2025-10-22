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


def add_agents_detect_subparser(agents_subparsers) -> argparse.ArgumentParser:
    """
    Add the agents detect subparser for toolchain detection.

    WHY: Allows users to see what toolchain is detected without making changes,
    useful for debugging and verification.

    Args:
        agents_subparsers: The agents subparsers object

    Returns:
        The configured detect subparser
    """
    detect_parser = agents_subparsers.add_parser(
        "detect",
        help="Detect project toolchain without deploying",
        description="""
Detect and display project toolchain without making any changes.

This command analyzes your project to detect:
  • Programming languages and versions
  • Frameworks and libraries
  • Deployment targets and platforms

Useful for debugging toolchain detection and verifying what would be
detected before running auto-configure.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect toolchain in current directory
  claude-mpm agents detect

  # Detect with verbose output showing evidence
  claude-mpm agents detect --verbose

  # JSON output for scripting
  claude-mpm agents detect --json

  # Detect specific project
  claude-mpm agents detect --project-path /path/to/project
        """,
    )
    add_common_arguments(detect_parser)

    detect_parser.add_argument(
        "--project-path",
        type=Path,
        metavar="PATH",
        help="Project path to analyze (default: current directory)",
    )

    return detect_parser


def add_agents_recommend_subparser(
    agents_subparsers,
) -> argparse.ArgumentParser:
    """
    Add the agents recommend subparser for agent recommendations.

    WHY: Allows users to see what agents would be recommended without deploying,
    useful for reviewing recommendations before committing to deployment.

    Args:
        agents_subparsers: The agents subparsers object

    Returns:
        The configured recommend subparser
    """
    recommend_parser = agents_subparsers.add_parser(
        "recommend",
        help="Show recommended agents without deploying",
        description="""
Show recommended agents based on project toolchain without deploying.

This command analyzes your project toolchain and recommends appropriate
agents with detailed reasoning for each recommendation. No changes are
made to your project.

Useful for:
  • Reviewing recommendations before deployment
  • Understanding why agents are recommended
  • Adjusting confidence thresholds
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show recommendations with reasoning
  claude-mpm agents recommend

  # Require 90% confidence for recommendations
  claude-mpm agents recommend --min-confidence 0.9

  # JSON output for scripting
  claude-mpm agents recommend --json

  # Hide detailed reasoning
  claude-mpm agents recommend --no-reasoning

  # Recommend for specific project
  claude-mpm agents recommend --project-path /path/to/project
        """,
    )
    add_common_arguments(recommend_parser)

    recommend_parser.add_argument(
        "--project-path",
        type=Path,
        metavar="PATH",
        help="Project path to analyze (default: current directory)",
    )

    recommend_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        metavar="FLOAT",
        help="Minimum confidence threshold for recommendations (0.0-1.0, default: 0.8)",
    )

    recommend_parser.add_argument(
        "--show-reasoning",
        action="store_true",
        default=True,
        help="Show detailed reasoning for recommendations (default)",
    )

    recommend_parser.add_argument(
        "--no-reasoning",
        dest="show_reasoning",
        action="store_false",
        help="Hide detailed reasoning for recommendations",
    )

    return recommend_parser
