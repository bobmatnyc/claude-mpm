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
            elif service_name == "notion":
                result = self._setup_notion(service_args)
            elif service_name == "confluence":
                result = self._setup_confluence(service_args)
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
  notion                 Set up Notion integration
  confluence             Set up Confluence integration
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

    def _configure_slack_mcp_server(self) -> None:
        """Configure slack-user-proxy MCP server in .mcp.json after OAuth setup."""
        try:
            import json

            mcp_config_path = Path.cwd() / ".mcp.json"

            # Get the slack-user-proxy configuration from service registry
            try:
                from ...services.mcp_service_registry import MCPServiceRegistry

                service = MCPServiceRegistry.get("slack-user-proxy")
                if not service:
                    console.print(
                        "[yellow]Warning: slack-user-proxy not found in service registry[/yellow]"
                    )
                    return

                # Generate config using console script entry point
                # slack-user-proxy is available once claude-mpm is installed
                server_config = {
                    "type": "stdio",
                    "command": "slack-user-proxy",
                    "args": [],
                    "env": {},
                }
            except ImportError:
                # Fallback if registry not available
                server_config = {
                    "type": "stdio",
                    "command": "slack-user-proxy",
                    "args": [],
                    "env": {},
                }

            # Load or create .mcp.json
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path) as f:
                        config = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    console.print(
                        f"[yellow]Warning: Could not read .mcp.json: {e}[/yellow]"
                    )
                    config = {"mcpServers": {}}
            else:
                config = {"mcpServers": {}}

            # Ensure mcpServers key exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check if already configured
            if "slack-user-proxy" in config["mcpServers"]:
                console.print(
                    "[dim]slack-user-proxy already configured in .mcp.json[/dim]"
                )
                return

            # Add slack-user-proxy entry
            config["mcpServers"]["slack-user-proxy"] = server_config

            # Write back
            try:
                with open(mcp_config_path, "w") as f:
                    json.dump(config, f, indent=2)
                    f.write("\n")  # Add trailing newline

                console.print("[green]✓ Added slack-user-proxy to .mcp.json[/green]")
            except OSError as e:
                console.print(
                    f"[yellow]Warning: Could not write .mcp.json: {e}[/yellow]"
                )

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not configure MCP server: {e}[/yellow]"
            )

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

                # Configure slack-user-proxy MCP server
                self._configure_slack_mcp_server()

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

    def _configure_notion_mcp_server(self) -> None:
        """Configure notion-mcp MCP server in .mcp.json after credentials setup."""
        try:
            import json

            mcp_config_path = Path.cwd() / ".mcp.json"

            # Generate config using console script entry point
            server_config = {
                "type": "stdio",
                "command": "notion-mcp",
                "args": [],
                "env": {},
            }

            # Load or create .mcp.json
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path) as f:
                        config = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    console.print(
                        f"[yellow]Warning: Could not read .mcp.json: {e}[/yellow]"
                    )
                    config = {"mcpServers": {}}
            else:
                config = {"mcpServers": {}}

            # Ensure mcpServers key exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check if already configured
            if "notion-mcp" in config["mcpServers"]:
                console.print("[dim]notion-mcp already configured in .mcp.json[/dim]")
                return

            # Add notion-mcp entry
            config["mcpServers"]["notion-mcp"] = server_config

            # Write back
            try:
                with open(mcp_config_path, "w") as f:
                    json.dump(config, f, indent=2)
                    f.write("\n")  # Add trailing newline

                console.print("[green]✓ Added notion-mcp to .mcp.json[/green]")
            except OSError as e:
                console.print(
                    f"[yellow]Warning: Could not write .mcp.json: {e}[/yellow]"
                )

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not configure MCP server: {e}[/yellow]"
            )

    def _setup_notion(self, args) -> CommandResult:
        """Set up Notion integration with credential collection."""
        try:
            console.print(
                "\n[bold]Notion Integration Setup[/bold]\n"
                "To use Notion, you need an Integration Token from Notion.\n"
                "Visit: https://www.notion.so/my-integrations\n"
            )

            # Check for existing credentials
            env_local = Path.cwd() / ".env.local"
            api_key_exists = False

            if env_local.exists():
                with open(env_local) as f:
                    if "NOTION_API_KEY" in f.read():
                        api_key_exists = True

            if api_key_exists:
                console.print(
                    "[dim]NOTION_API_KEY already configured in .env.local[/dim]\n"
                )
            else:
                # Prompt for API key
                from rich.prompt import Prompt

                api_key = Prompt.ask(
                    "[cyan]Notion Integration Token (secret_...)[/cyan]",
                    password=True,
                )

                if not api_key.startswith("secret_"):
                    console.print(
                        "[yellow]Warning: Notion tokens usually start with 'secret_'[/yellow]"
                    )

                # Optionally ask for default database ID
                database_id = Prompt.ask(
                    "[cyan]Default Database ID (optional, press Enter to skip)[/cyan]",
                    default="",
                )

                # Save to .env.local
                with open(env_local, "a") as f:
                    f.write(
                        f'\nNOTION_API_KEY="{api_key}"  # pragma: allowlist secret\n'
                    )
                    if database_id:
                        f.write(f'NOTION_DATABASE_ID="{database_id}"\n')

                console.print(f"[green]✓ Credentials saved to {env_local}[/green]")

            # Configure MCP server
            self._configure_notion_mcp_server()

            console.print("\n[green]✓ Notion setup complete![/green]")
            console.print(
                "\n[dim]Next steps:[/dim]\n"
                "  1. Share your database with the Notion integration\n"
                "  2. Use 'claude-mpm tools notion' for bulk operations\n"
                "  3. MCP tools are available in Claude Code\n"
            )

            return CommandResult.success_result("Notion setup completed")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error during setup: {e}")

    def _configure_confluence_mcp_server(self) -> None:
        """Configure confluence-mcp MCP server in .mcp.json after credentials setup."""
        try:
            import json

            mcp_config_path = Path.cwd() / ".mcp.json"

            # Generate config using console script entry point
            server_config = {
                "type": "stdio",
                "command": "confluence-mcp",
                "args": [],
                "env": {},
            }

            # Load or create .mcp.json
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path) as f:
                        config = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    console.print(
                        f"[yellow]Warning: Could not read .mcp.json: {e}[/yellow]"
                    )
                    config = {"mcpServers": {}}
            else:
                config = {"mcpServers": {}}

            # Ensure mcpServers key exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check if already configured
            if "confluence-mcp" in config["mcpServers"]:
                console.print(
                    "[dim]confluence-mcp already configured in .mcp.json[/dim]"
                )
                return

            # Add confluence-mcp entry
            config["mcpServers"]["confluence-mcp"] = server_config

            # Write back
            try:
                with open(mcp_config_path, "w") as f:
                    json.dump(config, f, indent=2)
                    f.write("\n")  # Add trailing newline

                console.print("[green]✓ Added confluence-mcp to .mcp.json[/green]")
            except OSError as e:
                console.print(
                    f"[yellow]Warning: Could not write .mcp.json: {e}[/yellow]"
                )

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not configure MCP server: {e}[/yellow]"
            )

    def _setup_confluence(self, args) -> CommandResult:
        """Set up Confluence integration with credential collection."""
        try:
            console.print(
                "\n[bold]Confluence Integration Setup[/bold]\n"
                "To use Confluence, you need:\n"
                "  1. Your Confluence site URL (e.g., https://yoursite.atlassian.net)\n"
                "  2. Your email address\n"
                "  3. An API token from https://id.atlassian.com/manage-profile/security/api-tokens\n"
            )

            # Check for existing credentials
            env_local = Path.cwd() / ".env.local"
            url_exists = False

            if env_local.exists():
                with open(env_local) as f:
                    if "CONFLUENCE_URL" in f.read():
                        url_exists = True

            if url_exists:
                console.print(
                    "[dim]Confluence credentials already configured in .env.local[/dim]\n"
                )
            else:
                # Prompt for credentials
                from rich.prompt import Prompt

                url = Prompt.ask(
                    "[cyan]Confluence URL (e.g., https://yoursite.atlassian.net)[/cyan]"
                )

                email = Prompt.ask("[cyan]Your email address[/cyan]")

                api_token = Prompt.ask(
                    "[cyan]API Token[/cyan]",
                    password=True,
                )

                # Save to .env.local
                with open(env_local, "a") as f:
                    f.write(f'\nCONFLUENCE_URL="{url}"\n')
                    f.write(f'CONFLUENCE_EMAIL="{email}"\n')
                    f.write(
                        f'CONFLUENCE_API_TOKEN="{api_token}"  # pragma: allowlist secret\n'
                    )

                console.print(f"[green]✓ Credentials saved to {env_local}[/green]")

            # Configure MCP server
            self._configure_confluence_mcp_server()

            console.print("\n[green]✓ Confluence setup complete![/green]")
            console.print(
                "\n[dim]Next steps:[/dim]\n"
                "  1. Use 'claude-mpm tools confluence' for bulk operations\n"
                "  2. MCP tools are available in Claude Code\n"
            )

            return CommandResult.success_result("Confluence setup completed")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error during setup: {e}")

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
