"""
Unified setup commands for claude-mpm CLI.

WHY: Users need a consistent way to set up various services and integrations.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Unified command structure: claude-mpm setup [services...]
- Support multiple services in one command with service-specific options
- Flags after a service name apply to that service
- Delegate to service-specific handlers
"""

import os
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

from rich.console import Console

from ..shared import BaseCommand, CommandResult

console = Console()


def parse_service_args(service_args: list[str]) -> list[dict[str, Any]]:
    """
    Parse service arguments into structured service configs.

    Args:
        service_args: Raw argument list (e.g., ['slack', 'oauth', '--oauth-service', 'google-workspace-mcp'])

    Returns:
        List of service configs with their options
        Example: [
            {'name': 'slack', 'options': {}},
            {'name': 'oauth', 'options': {'oauth_service': 'google-workspace-mcp'}}
        ]
    """
    if not service_args:
        return []

    valid_services = {"slack", "google-workspace-mcp", "oauth"}
    services = []
    current_service = None
    current_options = {}

    i = 0
    while i < len(service_args):
        arg = service_args[i]

        # Check if this is a service name
        if arg in valid_services:
            # Save previous service if exists
            if current_service:
                services.append({"name": current_service, "options": current_options})

            # Start new service
            current_service = arg
            current_options = {}
            i += 1
            continue

        # Check if this is a flag
        if arg.startswith("--"):
            if not current_service:
                raise ValueError(
                    f"Flag {arg} found before any service name. "
                    "Flags must come after the service they apply to."
                )

            flag_name = arg[2:].replace("-", "_")

            # Check if flag expects a value
            if flag_name in {"oauth_service"}:
                # Flag expects a value
                if i + 1 >= len(service_args):
                    raise ValueError(f"Flag {arg} requires a value")
                current_options[flag_name] = service_args[i + 1]
                i += 2
            else:
                # Boolean flag
                current_options[flag_name] = True
                i += 1
            continue

        # Unknown argument
        raise ValueError(
            f"Unknown argument: {arg}. Expected a service name (slack, google-workspace-mcp, oauth) or a flag (--oauth-service, --no-browser, --no-launch, --force)"
        )

    # Save last service
    if current_service:
        services.append({"name": current_service, "options": current_options})

    return services


class SetupCommand(BaseCommand):
    """Unified setup command for all services."""

    def __init__(self):
        super().__init__("setup")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # Parse service_args if present
        if hasattr(args, "service_args") and args.service_args:
            try:
                services = parse_service_args(args.service_args)
                args.parsed_services = services

                # Validate OAuth requirements
                for service in services:
                    if service["name"] == "oauth":
                        if "oauth_service" not in service["options"]:
                            return (
                                "OAuth setup requires --oauth-service flag. "
                                "Example: claude-mpm setup oauth --oauth-service google-workspace-mcp"
                            )

                return None
            except ValueError as e:
                return str(e)

        return None

    def run(self, args) -> CommandResult:
        """Execute the setup command."""
        # If no services, show help
        if not hasattr(args, "parsed_services") or not args.parsed_services:
            self._show_help()
            return CommandResult.success_result("Help displayed")

        services = args.parsed_services

        # Process multiple services in sequence
        results = []
        for service_config in services:
            service_name = service_config["name"]
            service_options = service_config["options"]

            console.print(f"\n[bold cyan]Setting up {service_name}...[/bold cyan]")

            # Create a namespace object with the service options
            from argparse import Namespace

            service_args = Namespace(**service_options)

            if service_name == "slack":
                result = self._setup_slack(service_args)
            elif service_name == "google-workspace-mcp":
                result = self._setup_google_workspace(service_args)
            elif service_name == "oauth":
                result = self._setup_oauth(service_args)
            else:
                result = CommandResult.error_result(f"Unknown service: {service_name}")

            results.append((service_name, result))

            # Stop on first failure
            if not result.success:
                console.print(
                    f"\n[red]✗ Setup failed for {service_name}[/red]",
                    style="bold",
                )
                return result

            console.print(
                f"[green]✓ {service_name} setup complete![/green]",
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
[bold]Setup Command:[/bold]
  setup SERVICE [OPTIONS] [SERVICE [OPTIONS] ...]

[bold]Available Services:[/bold]
  slack                  Set up Slack MPM integration
  google-workspace-mcp   Set up Google Workspace MCP (includes OAuth)
  oauth                  Set up OAuth authentication

[bold]Service Options:[/bold]
  --oauth-service NAME   Service name for OAuth (required for 'oauth')
  --no-browser           Don't auto-open browser (oauth only)
  --no-launch            Don't auto-launch claude-mpm after setup (all services)
  --force                Force credential re-entry (oauth only)

[bold]Examples:[/bold]
  # Single service
  claude-mpm setup slack

  # Slack without auto-launch
  claude-mpm setup slack --no-launch

  # Multiple services
  claude-mpm setup slack google-workspace-mcp

  # Service with options
  claude-mpm setup oauth --oauth-service google-workspace-mcp --no-browser

  # Multiple services with options
  claude-mpm setup slack oauth --oauth-service google-workspace-mcp --no-launch

[dim]Note: Flags apply to the service that precedes them.[/dim]
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

                # Launch claude-mpm unless --no-launch was specified
                no_launch = getattr(args, "no_launch", False)
                if not no_launch:
                    console.print("\n[cyan]Launching claude-mpm...[/cyan]\n")
                    try:
                        # Replace current process with claude-mpm
                        os.execvp("claude-mpm", ["claude-mpm"])  # nosec B606 B607
                    except OSError:
                        # If execvp fails (e.g., claude-mpm not in PATH), try subprocess
                        import sys

                        subprocess.run(["claude-mpm"], check=False)  # nosec B603 B607
                        sys.exit(0)

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

        # Delegate to OAuth setup with google-workspace-mcp as the service
        # Create args for oauth setup
        from argparse import Namespace

        from .oauth import manage_oauth

        oauth_args = Namespace(
            oauth_command="setup",
            service_name="google-workspace-mcp",
            no_browser=getattr(args, "no_browser", False),
            no_launch=getattr(args, "no_launch", False),
            force=getattr(args, "force", False),
        )

        exit_code = manage_oauth(oauth_args)
        return CommandResult(
            success=exit_code == 0,
            exit_code=exit_code,
            message="Google Workspace MCP setup",
        )

    def _setup_oauth(self, args) -> CommandResult:
        """Set up OAuth for a service (delegates to OAuth command)."""
        # Get service name from arguments
        service_name = getattr(args, "oauth_service", None)
        if not service_name:
            return CommandResult.error_result(
                "OAuth setup requires --oauth-service flag. "
                "Example: claude-mpm setup oauth --oauth-service google-workspace-mcp"
            )

        # Delegate to OAuth setup
        from argparse import Namespace

        from .oauth import manage_oauth

        oauth_args = Namespace(
            oauth_command="setup",
            service_name=service_name,
            no_browser=getattr(args, "no_browser", False),
            no_launch=getattr(args, "no_launch", False),
            force=getattr(args, "force", False),
        )

        exit_code = manage_oauth(oauth_args)
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

    # Print error message if command failed
    if not result.success and result.message:
        console.print(f"\n[red]Error:[/red] {result.message}\n", style="bold")

    return result.exit_code
