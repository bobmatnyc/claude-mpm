"""
MPM-Init parser module for claude-mpm CLI.

WHY: This module handles the mpm-init command parser configuration,
providing a clean interface for initializing projects with optimal
Claude Code and Claude MPM standards.
"""

import argparse
from typing import Any


def add_mpm_init_subparser(subparsers: Any) -> None:
    """
    Add the mpm-init subparser to the main parser.

    WHY: The mpm-init command sets up projects for optimal use with
    Claude Code and Claude MPM by delegating to the Agentic Coder Optimizer.

    Args:
        subparsers: The subparsers object to add the mpm-init command to
    """
    mpm_init_parser = subparsers.add_parser(
        "mpm-init",
        help="Initialize project for optimal Claude Code and Claude MPM usage",
        description=(
            "Initialize a project with comprehensive documentation, single-path workflows, "
            "and optimized structure for AI agent understanding. Uses the Agentic Coder "
            "Optimizer agent to establish clear standards and remove ambiguity."
        ),
        epilog=(
            "Examples:\n"
            "  claude-mpm mpm-init                          # Initialize current directory\n"
            "  claude-mpm mpm-init --project-type web       # Initialize as web project\n"
            "  claude-mpm mpm-init --framework react        # Initialize with React framework\n"
            "  claude-mpm mpm-init /path/to/project --force # Force reinitialize project"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Project configuration options
    config_group = mpm_init_parser.add_argument_group("project configuration")
    config_group.add_argument(
        "--project-type",
        choices=[
            "web",
            "api",
            "cli",
            "library",
            "mobile",
            "desktop",
            "fullstack",
            "data",
            "ml",
        ],
        help="Type of project to initialize (auto-detected if not specified)",
    )
    config_group.add_argument(
        "--framework",
        type=str,
        help="Specific framework to configure (e.g., react, vue, django, fastapi, express)",
    )
    config_group.add_argument(
        "--language",
        choices=["python", "javascript", "typescript", "go", "rust", "java", "cpp"],
        help="Primary programming language (auto-detected if not specified)",
    )

    # Initialization options
    init_group = mpm_init_parser.add_argument_group("initialization options")
    init_group.add_argument(
        "--force",
        action="store_true",
        help="Force reinitialization even if project is already configured",
    )
    init_group.add_argument(
        "--minimal",
        action="store_true",
        help="Create minimal configuration (CLAUDE.md only, no additional setup)",
    )
    init_group.add_argument(
        "--comprehensive",
        action="store_true",
        help="Create comprehensive setup including CI/CD, testing, and deployment configs",
    )
    init_group.add_argument(
        "--use-venv",
        action="store_true",
        help="Use traditional Python venv instead of mamba/conda environment",
    )
    init_group.add_argument(
        "--ast-analysis",
        action="store_true",
        default=True,
        dest="ast_analysis",
        help="Enable AST analysis for enhanced developer documentation (default: enabled)",
    )
    init_group.add_argument(
        "--no-ast-analysis",
        action="store_false",
        dest="ast_analysis",
        help="Disable AST analysis for documentation generation",
    )

    # Template options
    template_group = mpm_init_parser.add_argument_group("template options")
    template_group.add_argument(
        "--template",
        type=str,
        help="Use a specific template from claude-mpm templates library",
    )
    template_group.add_argument(
        "--list-templates", action="store_true", help="List available project templates"
    )

    # Output options
    output_group = mpm_init_parser.add_argument_group("output options")
    output_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    output_group.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output during initialization",
    )

    # Path argument
    mpm_init_parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    # Set the command handler
    mpm_init_parser.set_defaults(command="mpm-init")
