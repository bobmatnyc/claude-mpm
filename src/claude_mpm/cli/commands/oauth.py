"""
OAuth management commands for claude-mpm CLI.

WHY: Users need a way to manage OAuth authentication for MCP services
that require OAuth2 flows (e.g., Google Workspace) directly from the terminal.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Reuse OAuth logic from commander/chat/repl.py
- Support multiple credential sources: .env.local, .env, environment variables
- Provide clear feedback during OAuth flow
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..shared import BaseCommand, CommandResult

console = Console()


def _load_oauth_credentials_from_env_files() -> tuple[str | None, str | None]:
    """Load OAuth credentials from .env files.

    Checks .env.local first (user overrides), then .env.
    Returns tuple of (client_id, client_secret), either may be None.
    """
    client_id = None
    client_secret = None

    # Priority order: .env.local first (user overrides), then .env
    env_files = [".env.local", ".env"]

    for env_file in env_files:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")

                            if key == "GOOGLE_OAUTH_CLIENT_ID" and not client_id:
                                client_id = value
                            elif (
                                key == "GOOGLE_OAUTH_CLIENT_SECRET"
                                and not client_secret
                            ):
                                client_secret = value

                    # If we found both, no need to check more files
                    if client_id and client_secret:
                        break
            except Exception:  # nosec B110 - intentionally ignore .env file read errors
                pass

    return client_id, client_secret


class OAuthCommand(BaseCommand):
    """OAuth management command for MCP services."""

    def __init__(self):
        super().__init__("oauth")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        # If no oauth_command specified, default to 'list'
        if not hasattr(args, "oauth_command") or not args.oauth_command:
            args.oauth_command = None  # Will show help
            return None

        valid_commands = ["list", "setup", "status", "revoke", "refresh"]
        if args.oauth_command not in valid_commands:
            return f"Unknown oauth command: {args.oauth_command}. Valid commands: {', '.join(valid_commands)}"

        # Validate service_name for commands that require it
        if args.oauth_command in ["setup", "status", "revoke", "refresh"]:
            if not hasattr(args, "service_name") or not args.service_name:
                return f"oauth {args.oauth_command} requires a service name"

        return None

    def run(self, args) -> CommandResult:
        """Execute the OAuth command."""
        # If no subcommand, show help
        if not hasattr(args, "oauth_command") or not args.oauth_command:
            self._show_help()
            return CommandResult.success_result("Help displayed")

        if args.oauth_command == "list":
            return self._list_services(args)
        if args.oauth_command == "setup":
            return self._setup_oauth(args)
        if args.oauth_command == "status":
            return self._show_status(args)
        if args.oauth_command == "revoke":
            return self._revoke_tokens(args)
        if args.oauth_command == "refresh":
            return self._refresh_tokens(args)

        return CommandResult.error_result(
            f"Unknown oauth command: {args.oauth_command}"
        )

    def _show_help(self) -> None:
        """Display OAuth command help."""
        help_text = """
[bold]OAuth Commands:[/bold]
  oauth list              List OAuth-capable MCP services
  oauth setup <service>   Set up OAuth authentication for a service
  oauth status <service>  Show OAuth token status for a service
  oauth revoke <service>  Revoke OAuth tokens for a service
  oauth refresh <service> Refresh OAuth tokens for a service

[bold]Examples:[/bold]
  claude-mpm oauth list
  claude-mpm oauth setup workspace-mcp
  claude-mpm oauth status workspace-mcp
"""
        console.print(help_text)

    def _list_services(self, args) -> CommandResult:
        """List OAuth-capable MCP services."""
        try:
            from claude_mpm.services.mcp_service_registry import MCPServiceRegistry

            services = MCPServiceRegistry.list_all()
            oauth_services = [s for s in services if s.oauth_provider]

            if not oauth_services:
                console.print("[yellow]No OAuth-capable services found.[/yellow]")
                return CommandResult.success_result("No OAuth services found")

            # Check output format
            output_format = getattr(args, "format", "table")

            if output_format == "json":
                data = [
                    {
                        "name": s.name,
                        "description": s.description,
                        "oauth_provider": s.oauth_provider,
                        "oauth_scopes": s.oauth_scopes,
                        "required_env": s.required_env,
                    }
                    for s in oauth_services
                ]
                console.print(json.dumps(data, indent=2))
                return CommandResult.success_result(
                    "Services listed", data={"services": data}
                )

            # Table format
            table = Table(title="OAuth-Capable MCP Services")
            table.add_column("Service", style="cyan")
            table.add_column("Provider", style="green")
            table.add_column("Description", style="white")

            for service in oauth_services:
                table.add_row(
                    service.name,
                    service.oauth_provider or "",
                    service.description,
                )

            console.print(table)
            return CommandResult.success_result(
                f"Found {len(oauth_services)} OAuth-capable service(s)"
            )

        except ImportError:
            return CommandResult.error_result("MCP Service Registry not available")
        except Exception as e:
            return CommandResult.error_result(f"Error listing services: {e}")

    def _setup_oauth(self, args) -> CommandResult:
        """Set up OAuth for a service."""
        service_name = args.service_name

        # Priority: 1) .env files, 2) environment variables, 3) interactive prompt
        client_id, client_secret = _load_oauth_credentials_from_env_files()

        # Fall back to environment variables if not found in .env files
        if not client_id:
            client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        if not client_secret:
            client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

        # If credentials missing, prompt for them interactively
        if not client_id or not client_secret:
            console.print("\n[yellow]Google OAuth credentials not found.[/yellow]")
            console.print("Checked: .env.local, .env, and environment variables.\n")
            console.print(
                "Get credentials from: https://console.cloud.google.com/apis/credentials\n"
            )
            console.print("[dim]Tip: Add to .env.local for automatic loading:[/dim]")
            console.print('[dim]  GOOGLE_OAUTH_CLIENT_ID="your-client-id"[/dim]')
            console.print(
                '[dim]  GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"[/dim]\n'  # pragma: allowlist secret
            )

            try:
                from prompt_toolkit import prompt as pt_prompt

                client_id = pt_prompt("Enter GOOGLE_OAUTH_CLIENT_ID: ")
                if not client_id.strip():
                    return CommandResult.error_result("Client ID is required")

                client_secret = pt_prompt(
                    "Enter GOOGLE_OAUTH_CLIENT_SECRET: ", is_password=True
                )
                if not client_secret.strip():
                    return CommandResult.error_result("Client Secret is required")

                # Set in environment for this session
                os.environ["GOOGLE_OAUTH_CLIENT_ID"] = client_id.strip()
                os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = client_secret.strip()
                console.print("\n[green]Credentials set for this session.[/green]")

            except (EOFError, KeyboardInterrupt):
                return CommandResult.error_result("Credential entry cancelled")
            except ImportError:
                return CommandResult.error_result(
                    "prompt_toolkit not available for interactive input. "
                    "Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables."
                )

        # Run OAuth flow
        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()

            callback_port = getattr(args, "port", 8085)
            no_browser = getattr(args, "no_browser", False)

            console.print(f"\n[cyan]Setting up OAuth for '{service_name}'...[/cyan]")
            console.print(
                f"Callback server listening on http://localhost:{callback_port}/callback"
            )

            if not no_browser:
                console.print("Opening browser for authentication...")
            else:
                console.print(
                    "[yellow]Browser auto-open disabled. Please open the URL manually.[/yellow]"
                )

            # Run async OAuth flow
            result = asyncio.run(manager.authenticate(service_name))

            if result.success:
                console.print(
                    f"\n[green]OAuth setup complete for '{service_name}'[/green]"
                )
                if result.expires_at:
                    console.print(f"  Token expires: {result.expires_at}")
                return CommandResult.success_result(
                    f"OAuth setup complete for '{service_name}'"
                )
            return CommandResult.error_result(f"OAuth setup failed: {result.error}")

        except ImportError as e:
            return CommandResult.error_result(f"OAuth module not available: {e}")
        except Exception as e:
            return CommandResult.error_result(f"Error during OAuth setup: {e}")

    def _show_status(self, args) -> CommandResult:
        """Show OAuth token status for a service."""
        service_name = args.service_name

        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()
            status = asyncio.run(manager.get_status(service_name))

            if status is None:
                console.print(
                    f"[yellow]No OAuth tokens found for '{service_name}'[/yellow]"
                )
                return CommandResult.success_result(
                    f"No tokens found for '{service_name}'"
                )

            # Check output format
            output_format = getattr(args, "format", "table")

            if output_format == "json":
                console.print(json.dumps(status, indent=2, default=str))
                return CommandResult.success_result("Status displayed", data=status)

            # Table format
            self._print_token_status(service_name, status)
            return CommandResult.success_result("Status displayed")

        except ImportError:
            return CommandResult.error_result("OAuth module not available")
        except Exception as e:
            return CommandResult.error_result(f"Error checking status: {e}")

    def _print_token_status(self, name: str, status: dict[str, Any]) -> None:
        """Print token status information."""
        panel_content = []
        panel_content.append(f"[bold]Service:[/bold] {name}")
        panel_content.append("[bold]Stored:[/bold] Yes")

        if status.get("valid"):
            panel_content.append("[bold]Status:[/bold] [green]Valid[/green]")
        else:
            panel_content.append("[bold]Status:[/bold] [red]Invalid/Expired[/red]")

        if status.get("expires_at"):
            panel_content.append(f"[bold]Expires:[/bold] {status['expires_at']}")

        if status.get("scopes"):
            scopes = ", ".join(status["scopes"])
            panel_content.append(f"[bold]Scopes:[/bold] {scopes}")

        panel = Panel(
            "\n".join(panel_content),
            title="OAuth Token Status",
            border_style="green" if status.get("valid") else "red",
        )
        console.print(panel)

    def _revoke_tokens(self, args) -> CommandResult:
        """Revoke OAuth tokens for a service."""
        service_name = args.service_name

        # Confirm unless -y flag
        if not getattr(args, "yes", False):
            console.print(
                f"[yellow]This will revoke OAuth tokens for '{service_name}'.[/yellow]"
            )
            try:
                from prompt_toolkit import prompt as pt_prompt

                confirm = pt_prompt("Are you sure? (y/N): ")
                if confirm.lower() not in ("y", "yes"):
                    return CommandResult.success_result("Revocation cancelled")
            except (EOFError, KeyboardInterrupt):
                return CommandResult.success_result("Revocation cancelled")
            except ImportError:
                # No prompt_toolkit, proceed without confirmation
                pass

        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()

            console.print(f"[cyan]Revoking OAuth tokens for '{service_name}'...[/cyan]")
            result = asyncio.run(manager.revoke(service_name))

            if result.success:
                console.print(
                    f"[green]OAuth tokens revoked for '{service_name}'[/green]"
                )
                return CommandResult.success_result(
                    f"Tokens revoked for '{service_name}'"
                )
            return CommandResult.error_result(f"Failed to revoke: {result.error}")

        except ImportError:
            return CommandResult.error_result("OAuth module not available")
        except Exception as e:
            return CommandResult.error_result(f"Error revoking tokens: {e}")

    def _refresh_tokens(self, args) -> CommandResult:
        """Refresh OAuth tokens for a service."""
        service_name = args.service_name

        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()

            console.print(
                f"[cyan]Refreshing OAuth tokens for '{service_name}'...[/cyan]"
            )
            result = asyncio.run(manager.refresh(service_name))

            if result.success:
                console.print(
                    f"[green]OAuth tokens refreshed for '{service_name}'[/green]"
                )
                if result.expires_at:
                    console.print(f"  New expiry: {result.expires_at}")
                return CommandResult.success_result(
                    f"Tokens refreshed for '{service_name}'"
                )
            return CommandResult.error_result(f"Failed to refresh: {result.error}")

        except ImportError:
            return CommandResult.error_result("OAuth module not available")
        except Exception as e:
            return CommandResult.error_result(f"Error refreshing tokens: {e}")


def manage_oauth(args) -> int:
    """Main entry point for OAuth management commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = OAuthCommand()
    result = command.execute(args)
    return result.exit_code
