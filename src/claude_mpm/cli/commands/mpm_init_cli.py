"""
MPM-Init Command - Initialize projects for optimal Claude Code and Claude MPM success.

This command delegates to the Agentic Coder Optimizer agent to establish clear,
single-path project standards for documentation, tooling, and workflows.

Enhanced with AST inspection capabilities for generating comprehensive developer
documentation with code structure analysis.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

# Import the core command class from the mpm_init subpackage
from claude_mpm.cli.commands.mpm_init.core import MPMInitCommand
from claude_mpm.core.enums import OperationResult

console = Console()


@click.group(name="mpm-init", invoke_without_command=True)
@click.option(
    "--project-type",
    type=click.Choice(
        ["web", "api", "cli", "library", "mobile", "desktop", "fullstack"]
    ),
    help="Type of project to initialize",
)
@click.option(
    "--framework",
    type=str,
    help="Specific framework (e.g., react, django, fastapi, express)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinitialization even if project is already configured",
)
@click.option(
    "--update",
    is_flag=True,
    help="Update existing CLAUDE.md instead of recreating",
)
@click.option(
    "--review",
    is_flag=True,
    help="Review project state without making changes",
)
@click.option(
    "--organize",
    is_flag=True,
    help="Automatically organize misplaced files into proper directories",
)
@click.option(
    "--auto-safe/--no-auto-safe",
    default=True,
    help="Only move files with high confidence (default: safe mode on)",
)
@click.option(
    "--preserve-custom/--no-preserve-custom",
    default=True,
    help="Preserve custom sections when updating (default: preserve)",
)
@click.option(
    "--skip-archive",
    is_flag=True,
    help="Skip archiving existing files before updating",
)
@click.option(
    "--verbose", is_flag=True, help="Show detailed output during initialization"
)
@click.option(
    "--ast-analysis/--no-ast-analysis",
    default=True,
    help="Enable/disable AST analysis for enhanced documentation (default: enabled)",
)
@click.option(
    "--quick-update",
    is_flag=True,
    help="Perform lightweight update based on recent git activity (default: 30 days)",
)
@click.option(
    "--catchup",
    is_flag=True,
    help="Show recent commit history from all branches for PM context",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Non-interactive mode - display report only without prompting (use with --quick-update)",
)
@click.option(
    "--days",
    type=int,
    default=30,
    help="Number of days for git history analysis in quick update mode (default: 30)",
)
@click.option(
    "--export",
    type=str,
    default=None,
    help="Export activity report to file (default: docs/reports/activity-report-{timestamp}.md)",
)
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    default=".",
)
@click.pass_context
def mpm_init(
    ctx,
    project_type,
    framework,
    force,
    update,
    review,
    organize,
    auto_safe,
    preserve_custom,
    skip_archive,
    verbose,
    ast_analysis,
    quick_update,
    catchup,
    non_interactive,
    days,
    export,
    project_path,
):
    """
    Initialize or update a project for optimal use with Claude Code and Claude MPM.

    This command uses the Agentic Coder Optimizer agent to:
    - Create or update comprehensive CLAUDE.md documentation
    - Establish single-path workflows (ONE way to do ANYTHING)
    - Configure development tools and standards
    - Set up memory systems for project knowledge
    - Optimize for AI agent understanding
    - Perform AST analysis for enhanced developer documentation

    Context Management:
    - resume: Analyze git history to provide context for resuming work
    - --catchup: Show recent commit history for PM context

    Update Mode:
    When CLAUDE.md exists, the command offers to update rather than recreate,
    preserving custom content while refreshing standard sections.

    Examples:
        claude-mpm mpm-init                           # Initialize/update current directory
        claude-mpm mpm-init --catchup                 # Show recent git history for context
        claude-mpm mpm-init --review                  # Review project state without changes
        claude-mpm mpm-init --update                  # Force update mode
        claude-mpm mpm-init --organize                # Organize misplaced files
        claude-mpm mpm-init --project-type web        # Initialize as web project
        claude-mpm mpm-init /path/to/project --force  # Force reinitialize project
    """
    # If a subcommand is being invoked, don't run the main command
    if ctx.invoked_subcommand is not None:
        return

    try:
        # Create command instance
        command = MPMInitCommand(Path(project_path))

        # Run initialization (now synchronous)
        result = command.initialize_project(
            project_type=project_type,
            framework=framework,
            force=force,
            verbose=verbose,
            ast_analysis=ast_analysis,
            update_mode=update,
            review_only=review,
            organize_files=organize,
            preserve_custom=preserve_custom,
            skip_archive=skip_archive,
            quick_update=quick_update,
            catchup=catchup,
            non_interactive=non_interactive,
            days=days,
            export=export,
        )

        # Exit with appropriate code
        if result["status"] == OperationResult.SUCCESS:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Initialization cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Initialization failed: {e}[/red]")
        sys.exit(1)


@mpm_init.command(name="context")
@click.option(
    "--session-id",
    "-i",
    type=str,
    help="Unused (for compatibility) - will be removed in future version",
)
@click.option(
    "--days",
    type=int,
    default=7,
    help="Number of days of git history to analyze (default: 7)",
)
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    default=".",
)
def context_command(session_id, days, project_path):
    """
    Provide intelligent context for resuming work based on git history.

    Analyzes recent git history and generates a Research agent delegation
    prompt for intelligent project context reconstruction.

    Examples:
        claude-mpm mpm-init context                  # Analyze last 7 days
        claude-mpm mpm-init context --days 14        # Analyze last 14 days
        claude-mpm mpm-init context --days 30        # Analyze last 30 days

    Note: 'resume' is deprecated, use 'context' instead.
    """
    try:
        command = MPMInitCommand(Path(project_path))

        result = command.handle_context(session_id=session_id, days=days)

        if (
            result["status"] == OperationResult.SUCCESS
            or result["status"] == OperationResult.CONTEXT_READY
        ):
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Context analysis cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Context analysis failed: {e}[/red]")
        sys.exit(1)


# Resume command - NEW: reads from stop event logs
@mpm_init.command(name="resume")
@click.option(
    "--list",
    "list_sessions",
    is_flag=True,
    help="List available sessions from logs",
)
@click.option(
    "--session-id",
    "-s",
    type=str,
    help="Resume specific session by ID",
)
@click.option(
    "--last",
    type=int,
    help="Show last N sessions",
)
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    default=".",
)
def resume_command(list_sessions, session_id, last, project_path):
    """
    Resume work from previous session using stop event logs.

    Reads from:
    - .claude-mpm/resume-logs/ (structured summaries, preferred)
    - .claude-mpm/responses/ (raw conversation logs, fallback)

    Examples:
        claude-mpm mpm-init resume                    # Show latest session
        claude-mpm mpm-init resume --list             # List all sessions
        claude-mpm mpm-init resume --session-id ID    # Resume specific session
        claude-mpm mpm-init resume --last 5           # Show last 5 sessions
    """
    from claude_mpm.services.cli.resume_service import ResumeService

    try:
        service = ResumeService(Path(project_path))

        # Handle --list flag
        if list_sessions:
            sessions = service.list_sessions()
            if not sessions:
                console.print("[yellow]No sessions found in response logs.[/yellow]")
                console.print(
                    "[dim]Sessions are stored in .claude-mpm/responses/[/dim]\n"
                )
                sys.exit(1)

            # Limit by --last if specified
            if last and last > 0:
                sessions = sessions[:last]

            console.print(
                f"\n[bold cyan]📋 Available Sessions ({len(sessions)})[/bold cyan]\n"
            )

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Session ID", style="cyan", width=25)
            table.add_column("Time", style="yellow", width=20)
            table.add_column("Agent", style="green", width=15)
            table.add_column("Stop Reason", style="white", width=20)
            table.add_column("Tokens", style="dim", width=10)

            for session in sessions:
                time_str = session.timestamp.strftime("%Y-%m-%d %H:%M")
                tokens_str = (
                    f"{session.token_usage // 1000}k"
                    if session.token_usage > 0
                    else "-"
                )

                table.add_row(
                    session.session_id,
                    time_str,
                    session.last_agent,
                    session.stop_reason,
                    tokens_str,
                )

            console.print(table)
            console.print()
            sys.exit(0)

        # Handle --session-id
        if session_id:
            context = service.get_session_context(session_id)
            if not context:
                console.print(f"[red]Session '{session_id}' not found.[/red]")
                console.print("[dim]Use --list to see available sessions.[/dim]\n")
                sys.exit(1)
        else:
            # Default: get latest session
            context = service.get_latest_session()
            if not context:
                console.print("[yellow]No sessions found in logs.[/yellow]")
                console.print(
                    "[dim]Sessions are stored in .claude-mpm/responses/[/dim]\n"
                )
                sys.exit(1)

        # Display context
        display_text = service.format_resume_display(context)
        console.print(display_text)

        # Ask if user wants to continue
        should_continue = Confirm.ask(
            "\n[bold]Would you like to continue this work?[/bold]", default=True
        )

        if should_continue:
            console.print(
                "\n[green]✅ Great! Use this context to continue your work.[/green]\n"
            )
            sys.exit(0)
        else:
            console.print("\n[cyan]Starting fresh session instead.[/cyan]\n")
            sys.exit(0)

    except KeyboardInterrupt:
        console.print("\n[yellow]Resume cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        from claude_mpm.core.logging_utils import get_logger

        logger = get_logger(__name__)
        logger.error(f"Resume failed: {e}")
        console.print(f"[red]Resume failed: {e}[/red]")
        sys.exit(1)


# Export for CLI registration
__all__ = ["mpm_init"]
