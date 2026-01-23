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


def _ensure_mcp_configured(service_name: str, project_dir: Path) -> bool:
    """Ensure MCP server is configured in .mcp.json after OAuth setup.

    Args:
        service_name: The service name (e.g., "workspace-mcp")
        project_dir: Directory where .mcp.json should be created/updated

    Returns:
        True if configuration was added/updated, False if already configured or not applicable
    """
    if service_name != "workspace-mcp":
        return False  # Only handle workspace-mcp for now

    mcp_config_path = project_dir / ".mcp.json"

    # Default config for google-workspace-mcp
    server_config = {"command": "google-workspace-mcp", "args": []}

    if mcp_config_path.exists():
        # Load existing config
        try:
            with open(mcp_config_path) as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[yellow]Warning: Could not read .mcp.json: {e}[/yellow]")
            config = {"mcpServers": {}}
    else:
        config = {"mcpServers": {}}

    # Ensure mcpServers key exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Check if already configured correctly
    if "google-workspace-mcp" in config["mcpServers"]:
        existing = config["mcpServers"]["google-workspace-mcp"]
        if existing.get("command") == "google-workspace-mcp":
            console.print("[dim]MCP server already configured in .mcp.json[/dim]")
            return False

    # Add/update google-workspace-mcp entry
    config["mcpServers"]["google-workspace-mcp"] = server_config

    # Write back
    try:
        with open(mcp_config_path, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Add trailing newline

        if mcp_config_path.exists():
            console.print("[green]✓ Added google-workspace-mcp to .mcp.json[/green]")
        return True
    except OSError as e:
        console.print(f"[yellow]Warning: Could not write .mcp.json: {e}[/yellow]")
        return False


def _save_credentials_to_env_file(client_id: str, client_secret: str) -> str | None:
    """Save credentials to existing .env file.

    Prefers .env.local, falls back to .env.
    Only saves if file already exists (doesn't create new files).

    Returns:
        Filename where saved, or None if no file exists.
    """
    for env_file in [".env.local", ".env"]:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            # Read existing content
            content = env_path.read_text()
            lines = content.splitlines()

            # Track if we updated existing keys
            updated_id = False
            updated_secret = False
            new_lines = []

            for line in lines:
                if line.strip().startswith("GOOGLE_OAUTH_CLIENT_ID="):
                    new_lines.append(f'GOOGLE_OAUTH_CLIENT_ID="{client_id}"')
                    updated_id = True
                elif line.strip().startswith("GOOGLE_OAUTH_CLIENT_SECRET="):
                    new_lines.append(
                        f'GOOGLE_OAUTH_CLIENT_SECRET="{client_secret}"  # pragma: allowlist secret'
                    )
                    updated_secret = True
                else:
                    new_lines.append(line)

            # Add keys if not updated
            if not updated_id:
                new_lines.append(f'GOOGLE_OAUTH_CLIENT_ID="{client_id}"')
            if not updated_secret:
                new_lines.append(
                    f'GOOGLE_OAUTH_CLIENT_SECRET="{client_secret}"  # pragma: allowlist secret'
                )

            # Write back
            env_path.write_text("\n".join(new_lines) + "\n")
            return env_file

    return None


def _detect_google_credentials() -> tuple[str | None, str | None, str | None]:
    """Detect Google OAuth credentials from environment or .env files.

    Checks in order:
    1. Environment variables
    2. .env.local
    3. .env

    Returns:
        Tuple of (client_id, client_secret, source) where source indicates
        where credentials were found ("environment", ".env.local", ".env")
        or (None, None, None) if not found.
    """
    # Check environment variables first
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    if client_id and client_secret:
        return client_id, client_secret, "environment"

    # Check .env files in priority order
    for env_file in [".env.local", ".env"]:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            file_client_id = None
            file_client_secret = None
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

                            if key == "GOOGLE_OAUTH_CLIENT_ID":
                                file_client_id = value
                            elif key == "GOOGLE_OAUTH_CLIENT_SECRET":
                                file_client_secret = value

                if file_client_id and file_client_secret:
                    return file_client_id, file_client_secret, env_file
            except Exception:  # nosec B110 - intentionally ignore .env file read errors
                pass

    return None, None, None


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
        force_prompt = getattr(args, "force", False)

        # Get service info from registry to get provider and scopes
        try:
            from claude_mpm.services.mcp_service_registry import MCPServiceRegistry

            service = MCPServiceRegistry.get(service_name)
            if not service:
                return CommandResult.error_result(f"Service '{service_name}' not found")

            provider_name = service.oauth_provider
            if not provider_name:
                return CommandResult.error_result(
                    f"Service '{service_name}' does not use OAuth"
                )

            scopes = service.oauth_scopes or None
        except ImportError:
            return CommandResult.error_result("MCP Service Registry not available")

        client_id = None
        client_secret = None
        source = None
        credentials_were_prompted = False

        # Auto-detect credentials unless --force is specified
        if not force_prompt:
            client_id, client_secret, source = _detect_google_credentials()

            if client_id and client_secret:
                # Display where credentials were found
                console.print(f"[green]Using credentials from {source}[/green]")
                # Set credentials in environment so OAuth provider can access them
                os.environ["GOOGLE_OAUTH_CLIENT_ID"] = client_id
                os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = client_secret
        else:
            console.print("[dim]--force specified, skipping auto-detection[/dim]")

        # If credentials missing (or --force), prompt for them interactively
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
                client_id = client_id.strip()
                client_secret = client_secret.strip()
                os.environ["GOOGLE_OAUTH_CLIENT_ID"] = client_id
                os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = client_secret
                credentials_were_prompted = True
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
            from claude_mpm.auth.callback_server import DEFAULT_PORT
            from claude_mpm.auth.providers.google import OAuthError

            manager = OAuthManager()

            # Get the actual callback port from the server
            callback_port = DEFAULT_PORT
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

            # Run async OAuth flow - authenticate returns OAuthToken directly
            # and raises OAuthError on failure
            token = asyncio.run(
                manager.authenticate(
                    service_name=service_name,
                    provider_name=provider_name,
                    scopes=scopes,
                    open_browser=not no_browser,
                )
            )

            # Success - token was returned
            console.print(f"\n[green]OAuth setup complete for '{service_name}'[/green]")
            if token.expires_at:
                console.print(f"  Token expires: {token.expires_at}")

            # Ensure MCP server is configured in .mcp.json
            _ensure_mcp_configured(service_name, Path.cwd())

            # Save credentials to .env file if they were manually entered
            if credentials_were_prompted:
                saved_to = _save_credentials_to_env_file(client_id, client_secret)
                if saved_to:
                    console.print(f"[green]✓ Saved credentials to {saved_to}[/green]")

            return CommandResult.success_result(
                f"OAuth setup complete for '{service_name}'"
            )

        except OAuthError as e:
            return CommandResult.error_result(f"OAuth setup failed: {e}")
        except ImportError as e:
            return CommandResult.error_result(f"OAuth module not available: {e}")
        except Exception as e:
            return CommandResult.error_result(f"Error during OAuth setup: {e}")

    def _show_status(self, args) -> CommandResult:
        """Show OAuth token status for a service."""
        service_name = args.service_name

        try:
            from claude_mpm.auth import OAuthManager
            from claude_mpm.auth.models import TokenStatus

            manager = OAuthManager()
            # get_status is synchronous and returns (TokenStatus, StoredToken | None)
            token_status, stored_token = manager.get_status(service_name)

            if token_status == TokenStatus.MISSING or stored_token is None:
                console.print(
                    f"[yellow]No OAuth tokens found for '{service_name}'[/yellow]"
                )
                return CommandResult.success_result(
                    f"No tokens found for '{service_name}'"
                )

            # Build status dict for display
            is_valid = token_status == TokenStatus.VALID
            status_data = {
                "valid": is_valid,
                "status": token_status.name,
                "expires_at": stored_token.token.expires_at,
                "scopes": stored_token.token.scopes,
            }

            # Check output format
            output_format = getattr(args, "format", "table")

            if output_format == "json":
                console.print(json.dumps(status_data, indent=2, default=str))
                return CommandResult.success_result(
                    "Status displayed", data=status_data
                )

            # Table format
            self._print_token_status(service_name, status_data)
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
            # revoke() returns bool directly
            revoked = asyncio.run(manager.revoke(service_name))

            if revoked:
                console.print(
                    f"[green]OAuth tokens revoked for '{service_name}'[/green]"
                )
                return CommandResult.success_result(
                    f"Tokens revoked for '{service_name}'"
                )
            return CommandResult.error_result(
                f"Failed to revoke tokens for '{service_name}'"
            )

        except ImportError:
            return CommandResult.error_result("OAuth module not available")
        except Exception as e:
            return CommandResult.error_result(f"Error revoking tokens: {e}")

    def _refresh_tokens(self, args) -> CommandResult:
        """Refresh OAuth tokens for a service."""
        service_name = args.service_name

        try:
            from claude_mpm.auth import OAuthManager
            from claude_mpm.auth.providers.google import OAuthError

            manager = OAuthManager()

            console.print(
                f"[cyan]Refreshing OAuth tokens for '{service_name}'...[/cyan]"
            )
            # refresh_if_needed() returns Optional[OAuthToken]
            token = asyncio.run(manager.refresh_if_needed(service_name))

            if token is not None:
                console.print(
                    f"[green]OAuth tokens refreshed for '{service_name}'[/green]"
                )
                if token.expires_at:
                    console.print(f"  New expiry: {token.expires_at}")
                return CommandResult.success_result(
                    f"Tokens refreshed for '{service_name}'"
                )
            return CommandResult.error_result(
                f"Failed to refresh tokens for '{service_name}' - no token found or no refresh token available"
            )

        except OAuthError as e:
            return CommandResult.error_result(f"Failed to refresh: {e}")
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
