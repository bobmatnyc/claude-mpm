"""
Unified setup commands for claude-mpm CLI.

WHY: Users need a consistent way to set up various services and integrations.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Unified command structure: claude-mpm setup [services...]
- Support multiple services in one command
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
        # If no services specified, show help
        if not hasattr(args, "services") or not args.services:
            return None

        # Validate OAuth setup requirements
        if "oauth" in args.services:
            if not hasattr(args, "oauth_service") or not args.oauth_service:
                return (
                    "OAuth setup requires --oauth-service flag. "
                    "Example: claude-mpm setup oauth --oauth-service google-workspace-mcp"
                )

        return None

    def run(self, args) -> CommandResult:
        """Execute the setup command."""
        # If no services, show help
        if not hasattr(args, "services") or not args.services:
            self._show_help()
            return CommandResult.success_result("Help displayed")

        # Process multiple services in sequence
        results = []
        for service in args.services:
            console.print(f"\n[bold cyan]Setting up {service}...[/bold cyan]")

            if service == "slack":
                result = self._setup_slack(args)
            elif service == "google-workspace-mcp":
                result = self._setup_google_workspace(args)
            elif service == "oauth":
                result = self._setup_oauth(args)
            else:
                result = CommandResult.error_result(f"Unknown service: {service}")

            results.append((service, result))

            # Stop on first failure
            if not result.success:
                console.print(
                    f"\n[red]✗ Setup failed for {service}[/red]",
                    style="bold",
                )
                return result

            console.print(
                f"[green]✓ {service} setup complete![/green]",
                style="bold",
            )

        # All setups succeeded
        console.print(
            f"\n[green]✓ All {len(results)} service(s) set up successfully![/green]",
            style="bold",
        )
        return CommandResult.success_result(
            f"Set up {len(results)} service(s) successfully"
        )

    def _show_help(self) -> None:
        """Display setup command help."""
        help_text = """
[bold]Setup Commands:[/bold]
  setup SERVICE [SERVICE...]   Set up one or more services

[bold]Available Services:[/bold]
  slack                  Set up Slack MPM integration
  google-workspace-mcp   Set up Google Workspace MCP integration
  oauth                  Set up OAuth authentication (requires --oauth-service)

[bold]Examples:[/bold]
  claude-mpm setup slack
  claude-mpm setup google-workspace-mcp
  claude-mpm setup slack google-workspace-mcp  [dim]# Multiple services[/dim]
  claude-mpm setup oauth --oauth-service google-workspace-mcp

[bold]OAuth Options:[/bold]
  --oauth-service NAME   Service name for OAuth setup
  --no-browser           Don't auto-open browser
  --no-launch            Don't auto-launch claude-mpm after setup
  --force                Force credential re-entry
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
        service_name = getattr(args, "oauth_service", None)
        if not service_name:
            return CommandResult.error_result(
                "OAuth setup requires --oauth-service flag. "
                "Example: claude-mpm setup oauth --oauth-service google-workspace-mcp"
            )

        # Create args for oauth setup
        args.oauth_command = "setup"
        args.service_name = service_name

        exit_code = manage_oauth(args)
        return CommandResult(
            success=exit_code == 0,
            exit_code=exit_code,
            message=f"OAuth setup for {service_name}",
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
