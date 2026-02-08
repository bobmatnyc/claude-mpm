"""
Unified setup commands for claude-mpm CLI.

WHY: Users need a consistent way to set up various services and integrations.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Unified command structure: claude-mpm setup [service]
- Delegate to service-specific handlers
- Support multiple services: slack, google-workspace-mcp, oauth
"""

import os
import subprocess  # nosec B404
from pathlib import Path

from rich.console import Console

from ..shared import BaseCommand, CommandResult

console = Console()


class SetupCommand(BaseCommand):
    """Unified setup command for all services."""

    def __init__(self):
        super().__init__("setup")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # If no service specified, show help
        if not hasattr(args, "service") or not args.service:
            args.service = None
            return None

        valid_services = ["slack", "google-workspace-mcp", "oauth"]
        if args.service not in valid_services:
            return f"Unknown service: {args.service}. Valid services: {', '.join(valid_services)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the setup command."""
        # If no service, show help
        if not hasattr(args, "service") or not args.service:
            self._show_help()
            return CommandResult.success_result("Help displayed")

        if args.service == "slack":
            return self._setup_slack(args)
        if args.service == "google-workspace-mcp":
            return self._setup_google_workspace(args)
        if args.service == "oauth":
            return self._setup_oauth(args)

        return CommandResult.error_result(f"Unknown service: {args.service}")

    def _show_help(self) -> None:
        """Display setup command help."""
        help_text = """
[bold]Setup Commands:[/bold]
  setup slack                  Set up Slack MPM integration
  setup google-workspace-mcp   Set up Google Workspace MCP integration
  setup oauth <service>        Set up OAuth authentication for a service

[bold]Examples:[/bold]
  claude-mpm setup slack
  claude-mpm setup google-workspace-mcp
  claude-mpm setup oauth google-workspace-mcp
"""
        console.print(help_text)

    def _setup_slack(self, args) -> CommandResult:
        """Run the Slack setup script."""
        try:
            # Find the setup script in the installed package
            import claude_mpm

            package_dir = Path(claude_mpm.__file__).parent
            script_path = package_dir / "scripts" / "setup" / "setup-slack-app.sh"

            if not script_path.exists():
                return CommandResult.error_result(
                    f"Setup script not found at: {script_path}\n"
                    "This may be due to an older version. "
                    "Try: uv tool upgrade claude-mpm"
                )

            # Make sure script is executable
            script_path.chmod(0o755)

            console.print("[cyan]Running Slack setup wizard...[/cyan]\n")

            # Run the script
            result = subprocess.run(
                ["bash", str(script_path)],
                check=False,
                env=os.environ.copy(),
            )  # nosec B603 B607

            if result.returncode == 0:
                console.print("\n[green]✓ Slack setup complete![/green]")
                return CommandResult.success_result("Slack setup completed")

            return CommandResult.error_result(
                f"Setup script exited with code {result.returncode}"
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error running setup: {e}")

    def _setup_google_workspace(self, args) -> CommandResult:
        """Set up Google Workspace MCP (delegates to OAuth setup)."""
        console.print("[cyan]Setting up Google Workspace MCP integration...[/cyan]\n")
        console.print(
            "This will configure OAuth authentication for Google Workspace.\n"
        )

        # Delegate to OAuth setup
        from .oauth import manage_oauth

        # Create args for oauth setup
        args.oauth_command = "setup"
        args.service_name = "google-workspace-mcp"

        return CommandResult(
            success=True,
            exit_code=manage_oauth(args),
            message="Google Workspace MCP setup delegated to OAuth",
        )

    def _setup_oauth(self, args) -> CommandResult:
        """Set up OAuth for a service (delegates to OAuth command)."""
        # Delegate to OAuth setup
        from .oauth import manage_oauth

        # Get service name from arguments
        service_name = getattr(args, "service_name", None)
        if not service_name:
            return CommandResult.error_result(
                "oauth setup requires a service name. "
                "Example: claude-mpm setup oauth google-workspace-mcp"
            )

        # Create args for oauth setup
        args.oauth_command = "setup"
        args.service_name = service_name

        return CommandResult(
            success=True,
            exit_code=manage_oauth(args),
            message=f"OAuth setup delegated for {service_name}",
        )


def manage_setup(args) -> int:
    """Main entry point for setup commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = SetupCommand()
    result = command.execute(args)
    return result.exit_code
