"""
MPM-Init command handler for claude-mpm CLI.

This module handles the execution of the mpm-init command.
"""

from pathlib import Path

from rich.console import Console

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
            "use_venv": getattr(args, "use_venv", False),
            "ast_analysis": getattr(args, "ast_analysis", True),
        }

        # Execute initialization (now synchronous)
        result = command.initialize_project(**init_params)

        # Return appropriate exit code
        if result.get("status") == "success":
            return 0
        if result.get("status") == "cancelled":
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
