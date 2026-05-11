"""Confluence integration setup handler."""

from __future__ import annotations

import json
from pathlib import Path

from ....shared import CommandResult
from .._shared import console


class ConfluenceMixin:
    """Mixin: Confluence credential prompt + MCP server wiring."""

    def _configure_confluence_mcp_server(self) -> None:
        """Configure confluence-mcp MCP server in .mcp.json after credentials setup."""
        try:
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

    def _setup_confluence(self, _args) -> CommandResult:
        """Set up Confluence integration with credential collection."""
        _ = _args  # args passed by caller dispatch; not used in this implementation
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
