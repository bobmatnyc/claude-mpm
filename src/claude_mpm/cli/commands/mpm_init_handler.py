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
        from .mpm_init.core import MPMInitCommand

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

        if subcommand == "pause":
            # Handle pause subcommand
            from datetime import datetime, timezone

            from claude_mpm.services.cli.session_pause_manager import (
                SessionPauseManager,
            )

            # Get project path
            project_path = (
                Path(args.project_path) if hasattr(args, "project_path") else Path.cwd()
            )

            console.print("\n[cyan]Creating session pause...[/cyan]")

            # Create pause session
            pause_manager = SessionPauseManager(project_path)
            session_id = pause_manager.create_pause_session(
                message=getattr(args, "message", None),
                skip_commit=getattr(args, "no_commit", False),
                export_path=getattr(args, "export", None),
            )

            # Display success message
            console.print()
            console.print("[green]✅ Session Paused Successfully[/green]", style="bold")
            console.print()
            console.print(f"[cyan]Session ID:[/cyan] {session_id}")
            console.print(
                f"[cyan]Paused At:[/cyan] {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            console.print(f"[cyan]Location:[/cyan] .claude-mpm/sessions/{session_id}.*")

            # Show what was captured
            console.print()
            console.print("[blue]📝 Files Created:[/blue]")
            console.print(f"  • [dim]{session_id}.json[/dim] - Machine-readable data")
            console.print(f"  • [dim]{session_id}.yaml[/dim] - Human-readable config")
            console.print(f"  • [dim]{session_id}.md[/dim] - Full documentation")
            console.print("  • [dim]LATEST-SESSION.txt[/dim] - Quick reference pointer")

            # Git commit info
            if not getattr(args, "no_commit", False) and pause_manager._is_git_repo():
                console.print()
                console.print("[green]✓[/green] Git commit created")

            # Export info
            if getattr(args, "export", None):
                console.print()
                console.print(f"[green]✓[/green] Exported to: {args.export}")

            # Show message if provided
            if getattr(args, "message", None):
                console.print()
                console.print(f"[yellow]Context:[/yellow] {args.message}")

            # Resume instructions
            console.print()
            console.print("[yellow]Resume with:[/yellow] claude-mpm mpm-init context")
            console.print(
                "[yellow]Quick view:[/yellow] cat .claude-mpm/sessions/LATEST-SESSION.txt"
            )
            console.print()

            return 0

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
