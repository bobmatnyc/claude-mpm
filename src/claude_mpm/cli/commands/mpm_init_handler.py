"""
MPM-Init command handler for claude-mpm CLI.

This module handles the execution of the mpm-init command.
"""

from pathlib import Path

from rich.console import Console

from claude_mpm.core.enums import OperationResult

console = Console()

# ---------------------------------------------------------------------------
# Commit-cost hook installation helper
# ---------------------------------------------------------------------------

_HOOK_MARKER = "commit-cost-hook"
_HOOK_SNIPPET = (
    "\n# claude-mpm commit cost tracker\n"
    "# Embeds X-AI-* token trailers and normalises Co-Authored-By on every commit.\n"
    "commit-cost-hook 2>/dev/null || true\n"
)


def _install_commit_cost_hook(project_path: Path) -> None:
    """Ensure commit-cost-hook is called from .git/hooks/post-commit.

    If no post-commit hook exists, create a minimal one.  If one already
    exists but does not contain the marker, append the snippet.  If the
    marker is already present, do nothing.

    Fails silently so that mpm-init never breaks due to hook installation
    issues (e.g. no .git directory for non-git projects).
    """
    try:
        git_dir = project_path / ".git"
        if not git_dir.is_dir():
            return

        hook_path = git_dir / "hooks" / "post-commit"
        hook_path.parent.mkdir(parents=True, exist_ok=True)

        if hook_path.exists():
            existing = hook_path.read_text()
            if _HOOK_MARKER in existing:
                # Already installed
                return
            # Append the snippet to the existing hook
            hook_path.write_text(existing.rstrip("\n") + _HOOK_SNIPPET)
        else:
            # Create a new minimal post-commit hook
            hook_path.write_text("#!/bin/sh" + _HOOK_SNIPPET)
            hook_path.chmod(0o755)

        # Ensure the hook file is executable (in case we only appended)
        current_mode = hook_path.stat().st_mode
        hook_path.chmod(current_mode | 0o111)

        console.print(
            "[green]commit-cost-hook installed in .git/hooks/post-commit[/green]"
        )
    except Exception as exc:
        # Hook installation failure must never abort mpm-init
        console.print(
            f"[yellow]Warning: could not install commit-cost-hook: {exc}[/yellow]"
        )


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
            # Delegate to shared pause logic (also used by claude-mpm session pause)
            from .session_shared import handle_pause

            return handle_pause(args)

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

        # Install commit-cost-hook in .git/hooks/post-commit (idempotent).
        _install_commit_cost_hook(project_path)

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
