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
            "  claude-mpm mpm-init                                    # Initialize/update current directory\n"
            "  claude-mpm mpm-init --catchup                          # Show recent git history for context\n"
            "  claude-mpm mpm-init --review                           # Review project state without changes\n"
            "  claude-mpm mpm-init --update                           # Update existing CLAUDE.md\n"
            "  claude-mpm mpm-init --quick-update                     # Quick update based on recent git activity\n"
            "  claude-mpm mpm-init --quick-update --non-interactive   # View activity report only\n"
            "  claude-mpm mpm-init --quick-update --days 7            # Analyze last 7 days\n"
            "  claude-mpm mpm-init --quick-update --export            # Export report to default location\n"
            "  claude-mpm mpm-init --quick-update --export report.md  # Export to specific file\n"
            "  claude-mpm mpm-init --organize                         # Organize project structure\n"
            "  claude-mpm mpm-init --project-type web                 # Initialize as web project\n"
            "  claude-mpm mpm-init --framework react                  # Initialize with React framework\n"
            "  claude-mpm mpm-init /path/to/project --force           # Force reinitialize project"
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
        "--update",
        action="store_true",
        help="Update existing CLAUDE.md instead of recreating (smart merge)",
    )
    init_group.add_argument(
        "--quick-update",
        action="store_true",
        help="Perform lightweight update based on recent git activity (default: 30 days)",
    )
    init_group.add_argument(
        "--catchup",
        action="store_true",
        help="Show recent commit history from all branches for PM context",
    )
    init_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Non-interactive mode - display report only without prompting for changes (use with --quick-update)",
    )
    init_group.add_argument(
        "--days",
        type=int,
        default=30,
        choices=[7, 14, 30, 60, 90],
        help="Number of days for git history analysis in quick update mode (default: 30)",
    )
    init_group.add_argument(
        "--export",
        type=str,
        nargs="?",
        const="auto",
        metavar="PATH",
        help="Export activity report to file (default: docs/reports/activity-report-{timestamp}.md)",
    )
    init_group.add_argument(
        "--review",
        action="store_true",
        help="Review project state without making changes (analysis only)",
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

    # Project organization options
    org_group = mpm_init_parser.add_argument_group("organization options")
    org_group.add_argument(
        "--organize",
        action="store_true",
        help="Organize misplaced files into proper directories",
    )
    org_group.add_argument(
        "--preserve-custom/--no-preserve-custom",
        default=True,
        dest="preserve_custom",
        help="Preserve custom sections when updating (default: preserve)",
    )
    org_group.add_argument(
        "--skip-archive",
        action="store_true",
        help="Skip archiving existing files before updating",
    )
    org_group.add_argument(
        "--archive-dir",
        type=str,
        default="docs/_archive",
        help="Directory for archiving old documentation (default: docs/_archive)",
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

    # Add subparsers for context commands
    subcommands = mpm_init_parser.add_subparsers(
        dest="subcommand",
        title="context management",
        description="Commands for managing project context",
    )

    # Context subcommand (primary name)
    context_parser = subcommands.add_parser(
        "context",
        help="Provide intelligent context for resuming work",
        description="Analyze git history to provide context for resuming work",
        epilog="Note: 'resume' is deprecated, use 'context' instead",
    )
    context_parser.add_argument(
        "--session-id",
        "-i",
        type=str,
        help="Unused (for compatibility) - will be removed in future version",
    )
    context_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of git history to analyze (default: 7)",
    )
    context_parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    # Resume subcommand (deprecated alias for backward compatibility)
    resume_parser = subcommands.add_parser(
        "resume",
        help="[DEPRECATED] Use 'context' instead",
        description="[DEPRECATED] This command is deprecated. Use 'context' instead.\n\n"
        "Analyze git history to provide context for resuming work",
    )
    resume_parser.add_argument(
        "--session-id",
        "-i",
        type=str,
        help="Unused (for compatibility) - will be removed in future version",
    )
    resume_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of git history to analyze (default: 7)",
    )
    resume_parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    # Pause subcommand - Create session pause documents
    pause_parser = subcommands.add_parser(
        "pause",
        help="Pause current session and save state",
        description="Create session pause documents for later resume. Captures git context, "
        "conversation state, todos, and working directory state.\n\n"
        "Creates three file formats:\n"
        "  - JSON: Machine-readable structured data\n"
        "  - YAML: Human-readable configuration style\n"
        "  - Markdown: Full documentation format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  claude-mpm mpm-init pause                          # Basic pause\n"
        "  claude-mpm mpm-init pause -m 'End of day'         # With message\n"
        "  claude-mpm mpm-init pause --no-commit             # Skip git commit\n"
        "  claude-mpm mpm-init pause --export session.json   # Export copy",
    )
    pause_parser.add_argument(
        "--message",
        "-m",
        type=str,
        default=None,
        help="Optional message describing pause reason or context",
    )
    pause_parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Skip git commit of session state",
    )
    pause_parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export session state to custom location",
    )
    pause_parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    # Set the command handler
    mpm_init_parser.set_defaults(command="mpm-init")
