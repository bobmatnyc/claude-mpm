"""
MPM-Init command handler for claude-mpm CLI.

This module handles the execution of the mpm-init command.
"""

from pathlib import Path

from rich.console import Console

from claude_mpm.core.enums import OperationResult

console = Console()


def manage_mpm_init(args):
    """
    Handle mpm-init command execution.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Import the command implementation
        from .mpm_init import MPMInitCommand

        # Handle context subcommands
        subcommand = getattr(args, "subcommand", None)

        if subcommand in ("context", "resume"):
            # Show deprecation warning for 'resume'
            if subcommand == "resume":
                console.print(
                    "[yellow]⚠️  Warning: 'resume' is deprecated. Use 'context' instead.[/yellow]"
                )
                console.print("[dim]Run: claude-mpm mpm-init context[/dim]\n")

            # Get project path
            project_path = (
                Path(args.project_path) if hasattr(args, "project_path") else Path.cwd()
            )

            # Create command instance
            command = MPMInitCommand(project_path)

            # Handle context with optional session ID and days
            result = command.handle_context(
                session_id=getattr(args, "session_id", None),
                days=getattr(args, "days", 7),
            )

            # Return appropriate exit code
            if result.get("status") in (
                OperationResult.SUCCESS,
                OperationResult.CONTEXT_READY,
            ):
                return 0
            return 1

        # Handle special flags
        if getattr(args, "list_templates", False):
            # List available templates
            console.print("\n[bold cyan]Available Project Templates:[/bold cyan]")
            console.print("  • web-react: React web application")
            console.print("  • web-vue: Vue.js web application")
            console.print("  • api-fastapi: FastAPI REST API")
            console.print("  • api-django: Django REST framework")
            console.print("  • cli-python: Python CLI application")
            console.print("  • library-python: Python library")
            console.print("  • fullstack-nextjs: Next.js fullstack app")
            console.print("  • ml-pytorch: PyTorch ML project")
            console.print("  • data-pipeline: Data pipeline with ETL")
            console.print()
            return 0

        # Get project path
        project_path = (
            Path(args.project_path) if hasattr(args, "project_path") else Path.cwd()
        )

        # Create command instance
        command = MPMInitCommand(project_path)

        # Prepare initialization parameters
        init_params = {
            "project_type": getattr(args, "project_type", None),
            "framework": getattr(args, "framework", None),
            "force": getattr(args, "force", False),
            "verbose": getattr(args, "verbose", False),
            "ast_analysis": getattr(args, "ast_analysis", True),
            "update_mode": getattr(args, "update", False),
            "review_only": getattr(args, "review", False),
            "organize_files": getattr(args, "organize", False),
            "preserve_custom": getattr(args, "preserve_custom", True),
            "skip_archive": getattr(args, "skip_archive", False),
            "dry_run": getattr(args, "dry_run", False),
            "quick_update": getattr(args, "quick_update", False),
            "non_interactive": getattr(args, "non_interactive", False),
            "days": getattr(args, "days", 30),
            "export": getattr(args, "export", None),
        }

        # Execute initialization (now synchronous)
        result = command.initialize_project(**init_params)

        # Return appropriate exit code
        if result.get("status") == OperationResult.SUCCESS:
            return 0
        if result.get("status") == OperationResult.CANCELLED:
            return 130  # User cancelled
        return 1  # Error

    except ImportError as e:
        console.print(f"[red]Error: Required module not available: {e}[/red]")
        console.print("[yellow]Ensure claude-mpm is properly installed[/yellow]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Initialization cancelled by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Error executing mpm-init: {e}[/red]")
        import traceback

        if getattr(args, "verbose", False):
            traceback.print_exc()
        return 1
