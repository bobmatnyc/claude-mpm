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

import json
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from ..shared import BaseCommand, CommandResult

console = Console()


def parse_service_args(service_args: list[str]) -> list[dict[str, Any]]:
    """
    Parse service arguments into structured service configs.

    Args:
        service_args: Raw argument list (e.g., ['slack', 'oauth', '--oauth-service', 'gworkspace-mcp'])

    Returns:
        List of service configs with their options
        Example: [
            {'name': 'slack', 'options': {}},
            {'name': 'oauth', 'options': {'oauth_service': 'gworkspace-mcp'}}
        ]
    """
    if not service_args:
        return []

    valid_services = {
        "slack",
        "gworkspace-mcp",
        "oauth",
        "notion",
        "confluence",
        "kuzu-memory",
        "mcp-vector-search",
        "mcp-skillset",
        "mcp-ticketer",
    }

    # Pre-process service_args to split comma-separated values
    expanded_args = []
    for arg in service_args:
        if "," in arg:
            # Split on commas and add each part
            expanded_args.extend(
                [part.strip() for part in arg.split(",") if part.strip()]
            )
        else:
            expanded_args.append(arg)
    service_args = expanded_args

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
            f"Unknown argument: {arg}. Expected a service name (slack, gworkspace-mcp, oauth, notion, confluence, kuzu-memory, mcp-vector-search, mcp-skillset, mcp-ticketer) or a flag (--oauth-service, --no-browser, --no-launch, --force)"
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
                                "Example: claude-mpm setup oauth --oauth-service gworkspace-mcp"
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
            elif service_name == "gworkspace-mcp":
                result = self._setup_google_workspace(service_args)
            elif service_name == "notion":
                result = self._setup_notion(service_args)
            elif service_name == "confluence":
                result = self._setup_confluence(service_args)
            elif service_name == "kuzu-memory":
                result = self._setup_kuzu_memory(service_args)
            elif service_name == "mcp-vector-search":
                result = self._setup_mcp_vector_search(service_args)
            elif service_name == "mcp-skillset":
                result = self._setup_mcp_skillset(service_args)
            elif service_name == "mcp-ticketer":
                result = self._setup_mcp_ticketer(service_args)
            elif service_name == "oauth":
                result = self._setup_oauth(service_args)
            else:
                result = CommandResult.error_result(f"Unknown service: {service_name}")

            results.append((service_name, result))

            # Track failure but continue processing remaining services
            if not result.success:
                console.print(
                    f"\n[red]✗ Setup failed for {service_name}[/red]",
                    style="bold",
                )
                # Don't return early - continue processing remaining services
            else:
                console.print(
                    f"[green]✓ {service_name} setup complete![/green]",
                    style="bold",
                )

        # Report results
        successful = [r for r in results if r[1].success]
        failed = [r for r in results if not r[1].success]

        if successful:
            console.print(
                f"\n[green]✓ {len(successful)} service(s) set up successfully[/green]",
                style="bold",
            )

        if failed:
            console.print(
                f"\n[red]✗ {len(failed)} service(s) failed to set up[/red]",
                style="bold",
            )

        # Launch claude-mpm after all services are set up (unless --no-launch specified)
        # Only launch if at least one service succeeded
        no_launch = getattr(args, "no_launch", False)
        if not no_launch and len(successful) > 0:
            console.print("\n[cyan]Launching claude-mpm...[/cyan]\n")
            try:
                # Replace current process with claude-mpm
                os.execvp("claude-mpm", ["claude-mpm"])  # nosec B606 B607
            except OSError:
                # If execvp fails (e.g., claude-mpm not in PATH), try subprocess
                subprocess.run(["claude-mpm"], check=False)  # nosec B603 B607
                sys.exit(0)

        # Return failure if all services failed, success if any succeeded
        if len(failed) == len(results):
            return CommandResult.error_result(
                f"All {len(failed)} service(s) failed to set up"
            )
        return CommandResult.success_result(
            f"Set up {len(successful)}/{len(results)} service(s) successfully"
        )

    def _show_help(self) -> None:
        """Display setup command help."""
        help_text = """
[bold]Setup Command:[/bold]
  setup SERVICE [OPTIONS] [SERVICE [OPTIONS] ...]

[bold]Available Services:[/bold]
  slack                  Set up Slack MPM integration
  gworkspace-mcp         Set up Google Workspace MCP (includes OAuth)
  notion                 Set up Notion integration
  confluence             Set up Confluence integration
  kuzu-memory            Set up kuzu-memory graph-based memory backend
  mcp-vector-search      Set up mcp-vector-search semantic code search
  mcp-skillset           Set up mcp-skillset RAG-powered skills (USER-LEVEL)
  mcp-ticketer           Set up mcp-ticketer ticket management via MCP
  oauth                  Set up OAuth authentication

[bold]Service Options:[/bold]
  --oauth-service NAME   Service name for OAuth (required for 'oauth')
  --no-browser           Don't auto-open browser for authentication (oauth only)
  --no-launch            Don't auto-launch claude-mpm after setup (all services)
  --force                Force credential re-entry (oauth) or reinstall (mcp-vector-search, mcp-skillset)

[bold]Examples:[/bold]
  # Single service
  claude-mpm setup slack

  # Slack without auto-launch
  claude-mpm setup slack --no-launch

  # Multiple services (space-separated)
  claude-mpm setup slack gworkspace-mcp

  # Multiple services (comma-separated)
  claude-mpm setup slack,gworkspace-mcp,notion

  # Service with options
  claude-mpm setup oauth --oauth-service gworkspace-mcp --no-browser

  # Multiple services with options
  claude-mpm setup slack oauth --oauth-service gworkspace-mcp --no-launch

  # Set up mcp-vector-search
  claude-mpm setup mcp-vector-search

  # With force flag to reinstall
  claude-mpm setup mcp-vector-search --force

[dim]Note: Flags apply to the service that precedes them.[/dim]
"""
        console.print(help_text)

    def _remove_kuzu_memory_hooks(self) -> bool:
        """Remove kuzu-memory's independent hooks from Claude Code settings.

        This is called after setting up subservient mode to ensure kuzu-memory
        integrates through MPM's hook system instead of running independently.
        """
        settings_path = Path.home() / ".claude" / "settings.local.json"

        if not settings_path.exists():
            # No settings file, nothing to clean
            return True

        try:
            # Load settings
            with open(settings_path) as f:
                settings = json.load(f)

            hooks = settings.get("hooks", {})
            removed = []

            # Find and remove kuzu-memory hooks
            for hook_name, hook_config in list(hooks.items()):
                if isinstance(hook_config, dict):
                    command = hook_config.get("command", "")
                    if "kuzu-memory hooks" in command or "/kuzu-memory" in command:
                        del hooks[hook_name]
                        removed.append(hook_name)

            if removed:
                # Save cleaned settings
                settings["hooks"] = hooks
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=2)

                console.print(
                    f"[green]✓ Removed {len(removed)} kuzu-memory hooks: "
                    f"{', '.join(removed)}[/green]"
                )
                console.print(
                    "[dim]kuzu-memory will now integrate through claude-mpm hooks[/dim]"
                )

            return True

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not remove kuzu-memory hooks: {e}[/yellow]"
            )
            console.print(
                "[dim]You may need to manually remove them from "
                ".claude/settings.local.json[/dim]"
            )
            return False

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

    def _setup_kuzu_memory(self, args) -> CommandResult:
        """Set up kuzu-memory graph-based memory backend."""
        try:
            console.print(
                "\n[bold]Kuzu Memory Setup[/bold]\n"
                "This will replace static file-based memory with graph-based kuzu-memory.\n"
                "Kuzu-memory provides semantic search and enhanced context management.\n"
            )

            # Check if kuzu-memory is installed
            console.print("[cyan]Checking kuzu-memory installation...[/cyan]")
            try:
                import importlib.util

                spec = importlib.util.find_spec("kuzu_memory")
                is_installed = spec is not None
            except (ImportError, ModuleNotFoundError):
                is_installed = False

            # Detect how claude-mpm was installed
            if not is_installed:
                console.print("[cyan]Detecting installation method...[/cyan]")

                # Use existing detection utility
                from ...services.diagnostics.checks.installation_check import (
                    InstallationCheck,
                )

                checker = InstallationCheck()
                methods = checker._check_installation_method()

                # Determine primary method (priority: pipx > uv > pip)
                install_method = None
                detected_methods = methods.details.get("methods_detected", [])

                if "pipx" in detected_methods:
                    install_method = "pipx"
                elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
                    install_method = "uv"
                else:
                    # If in venv or development, use pip within that environment
                    # Otherwise use pip as default fallback
                    install_method = "pip"

                console.print(f"[dim]Detected: {install_method} installation[/dim]")

                console.print(
                    f"[yellow]Installing kuzu-memory>=1.6.33 via {install_method}...[/yellow]"
                )

                try:
                    if install_method == "pipx":
                        subprocess.run(
                            ["pipx", "install", "kuzu-memory>=1.6.33"],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    elif install_method == "uv":
                        subprocess.run(
                            [
                                "uv",
                                "tool",
                                "install",
                                "kuzu-memory>=1.6.33",
                                "--with",
                                "numpy",
                                "--python",
                                "3.13",
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    elif install_method == "pip":
                        subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "pip",
                                "install",
                                "--user",
                                "kuzu-memory>=1.6.33",
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    console.print(
                        f"[green]✓ kuzu-memory installed via {install_method}[/green]"
                    )

                except subprocess.CalledProcessError:
                    return CommandResult.error_result(
                        f"Failed to install kuzu-memory via {install_method}. "
                        f"Try manually: {install_method} install kuzu-memory>=1.6.33"
                    )
            else:
                console.print("[green]✓ kuzu-memory already installed[/green]")

            # Migrate existing static memory files if present
            console.print("\n[cyan]Checking for existing memory files...[/cyan]")
            static_memory_dir = Path.cwd() / ".claude-mpm" / "memories"
            memories_migrated = False

            if static_memory_dir.exists() and list(static_memory_dir.glob("*.md")):
                console.print(
                    "[yellow]Found existing static memory files. Migrating to kuzu-memory...[/yellow]"
                )

                # Count memory files
                memory_files = list(static_memory_dir.glob("*.md"))
                console.print(f"  Found {len(memory_files)} memory file(s)")

                # Migrate each memory file to kuzu-memory
                for memory_file in memory_files:
                    try:
                        content = memory_file.read_text()
                        agent_name = memory_file.stem

                        # Use kuzu-memory CLI to import the memory
                        import_result = subprocess.run(
                            [
                                "kuzu-memory",
                                "memory",
                                "learn",
                                content,
                                "--metadata",
                                f"agent={agent_name}",
                                "--metadata",
                                "source=mpm_static_migration",
                            ],
                            capture_output=True,
                            text=True,
                            check=False,
                        )  # nosec B603 B607

                        if import_result.returncode == 0:
                            console.print(
                                f"  [green]✓ Migrated {memory_file.name}[/green]"
                            )
                            memories_migrated = True
                        else:
                            console.print(
                                f"  [yellow]⚠ Could not migrate {memory_file.name}: {import_result.stderr}[/yellow]"
                            )

                    except Exception as e:
                        console.print(
                            f"  [yellow]⚠ Error migrating {memory_file.name}: {e}[/yellow]"
                        )

                if memories_migrated:
                    console.print(
                        "[green]✓ Memory files migrated to kuzu-memory[/green]"
                    )

                    # Create backup of static memory files
                    backup_dir = static_memory_dir.parent / "memories_backup"
                    backup_dir.mkdir(exist_ok=True)

                    for memory_file in memory_files:
                        shutil.copy2(memory_file, backup_dir / memory_file.name)

                    console.print(f"[green]✓ Backup created at: {backup_dir}[/green]")

                    # Archive original files to prevent re-import
                    console.print("\n[cyan]Archiving original files...[/cyan]")
                    archive_dir = static_memory_dir / ".migrated"
                    archive_dir.mkdir(exist_ok=True)

                    archived_count = 0
                    for memory_file in memory_files:
                        try:
                            dest = archive_dir / memory_file.name
                            memory_file.rename(dest)
                            console.print(f"  [dim]✓ Archived {memory_file.name}[/dim]")
                            archived_count += 1
                        except Exception as e:
                            console.print(
                                f"  [yellow]⚠ Could not archive {memory_file.name}: {e}[/yellow]"
                            )

                    if archived_count > 0:
                        # Create README in archive directory
                        from datetime import datetime, timezone

                        readme_content = f"""# Migrated Memory Files

These static memory files were migrated to kuzu-memory on {datetime.now(timezone.utc).isoformat()}.

**Status**: These files are archived and no longer active. The kuzu-memory graph database now manages all memories.

**Backup**: Backup copies exist in `../memories_backup/` for recovery if needed.

**Recovery**: If you need to restore these files, copy them back to `../` (parent directory).
"""
                        try:
                            (archive_dir / "README.md").write_text(readme_content)
                            console.print(
                                f"[green]✓ Archived {archived_count} file(s) to .migrated/[/green]"
                            )
                        except Exception as e:
                            console.print(
                                f"[yellow]Warning: Could not create archive README: {e}[/yellow]"
                            )
            else:
                console.print("  No existing memory files to migrate")

            # Update PROJECT-LOCAL configuration (not global)
            console.print("\n[cyan]Configuring kuzu-memory backend...[/cyan]")

            # Use project-local config in .claude-mpm/configuration.yaml
            config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"

            # Load existing config or create new
            import yaml

            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}

            # Set memory backend to kuzu
            if "memory" not in config:
                config["memory"] = {}

            config["memory"]["backend"] = "kuzu"

            # Set default kuzu config if not present
            if "kuzu" not in config["memory"]:
                config["memory"]["kuzu"] = {
                    "project_root": str(Path.cwd()),
                    "db_path": str(Path.cwd() / "kuzu-memories"),
                }

            # Save config
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            console.print(
                f"[green]✓ Project configuration updated: {config_path}[/green]"
            )

            # Create database directory
            db_path = Path(config["memory"]["kuzu"].get("db_path", "./kuzu-memories"))
            db_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Created database directory: {db_path}[/green]")

            # Create .kuzu-memory-config for subservient mode (v1.6.33+)
            kuzu_config_path = Path.cwd() / ".kuzu-memory-config"
            kuzu_config = {
                "mode": "subservient",
                "managed_by": "claude-mpm",
                "version": "1.0",
            }

            try:
                with open(kuzu_config_path, "w") as f:
                    yaml.dump(kuzu_config, f, default_flow_style=False)
                console.print(
                    f"[green]✓ Created subservient mode config: {kuzu_config_path}[/green]"
                )
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not create .kuzu-memory-config: {e}[/yellow]"
                )

            # Remove kuzu-memory's independent hooks
            console.print("\n[cyan]Cleaning up kuzu-memory hooks...[/cyan]")
            self._remove_kuzu_memory_hooks()

            console.print("\n[green]✓ Kuzu Memory setup complete![/green]")

            # Build what changed message
            what_changed = [
                "  1. kuzu-memory v1.6.33+ installed (or re-used if already installed)",
                "  2. Project-local configuration created (.claude-mpm/configuration.yaml)",
                "  3. Memory backend set to 'kuzu' for THIS PROJECT ONLY",
                "  4. Database directory created",
                "  5. Subservient mode enabled (MPM controls hooks, project-only)",
            ]

            if memories_migrated:
                what_changed.append(
                    "  6. Existing static memory files migrated and backed up"
                )

            console.print("\n[dim]What changed:[/dim]")
            console.print("\n".join(what_changed))

            console.print(
                "\n[dim]Next steps:[/dim]\n"
                "  1. Start Claude MPM to use graph-based memory\n"
                "  2. Your memories will be stored in the graph database\n"
                "  3. Use semantic search for better context retrieval\n"
                "\n[dim]Important:[/dim]\n"
                "  • Configuration is PROJECT-LOCAL (not global)\n"
                "  • Hooks are PROJECT-ONLY (not system-wide)\n"
                "  • kuzu-memory operates in subservient mode\n"
                "  • Each project can have its own memory backend configuration\n"
            )

            return CommandResult.success_result("Kuzu Memory setup completed")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error during setup: {e}")

    def _setup_mcp_vector_search(self, args) -> CommandResult:
        """Set up mcp-vector-search semantic code search."""
        try:
            console.print(
                "\n[bold]MCP Vector Search Setup[/bold]\n"
                "This will set up semantic code search with vector embeddings.\n"
            )

            # Check if mcp-vector-search is installed
            console.print("[cyan]Checking mcp-vector-search installation...[/cyan]")
            force = getattr(args, "force", False)

            # Try to import mcp-vector-search
            try:
                import importlib.util

                spec = importlib.util.find_spec("mcp_vector_search")
                is_installed = spec is not None
            except (ImportError, ModuleNotFoundError):
                is_installed = False

            # Detect how claude-mpm was installed
            if not is_installed or force:
                console.print("[cyan]Detecting installation method...[/cyan]")

                # Use existing detection utility
                from ...services.diagnostics.checks.installation_check import (
                    InstallationCheck,
                )

                checker = InstallationCheck()
                methods = checker._check_installation_method()

                # Determine primary method (priority: pipx > uv > pip)
                install_method = None
                detected_methods = methods.details.get("methods_detected", [])

                if "pipx" in detected_methods:
                    install_method = "pipx"
                elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
                    install_method = "uv"
                else:
                    # If in venv or development, use pip within that environment
                    # Otherwise use pip as default fallback
                    install_method = "pip"

                console.print(f"[dim]Detected: {install_method} installation[/dim]")

                action = "Reinstalling" if is_installed else "Installing"
                console.print(
                    f"[yellow]{action} mcp-vector-search via {install_method}...[/yellow]"
                )

                try:
                    if install_method == "pipx":
                        subprocess.run(
                            ["pipx", "install", "mcp-vector-search"],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    elif install_method == "uv":
                        subprocess.run(
                            [
                                "uv",
                                "tool",
                                "install",
                                "mcp-vector-search",
                                "--python",
                                "3.13",
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    elif install_method == "pip":
                        subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "pip",
                                "install",
                                "--user",
                                "mcp-vector-search",
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    console.print(
                        f"[green]✓ mcp-vector-search installed via {install_method}[/green]"
                    )

                except subprocess.CalledProcessError:
                    return CommandResult.error_result(
                        f"Failed to install mcp-vector-search via {install_method}. "
                        f"Try manually: {install_method} install mcp-vector-search"
                    )
            else:
                console.print("[green]✓ mcp-vector-search already installed[/green]")

            # Use MCPExternalServicesSetup to configure .mcp.json
            console.print(
                "\n[cyan]Configuring mcp-vector-search in .mcp.json...[/cyan]"
            )

            from .mcp_setup_external import MCPExternalServicesSetup

            handler = MCPExternalServicesSetup(console)

            # Load or create .mcp.json

            mcp_config_path = Path.cwd() / ".mcp.json"
            config = handler._load_config(mcp_config_path)

            if config is None:
                return CommandResult.error_result("Failed to load configuration")

            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Get configuration for mcp-vector-search
            project_path = Path.cwd()
            services = handler.get_project_services(project_path)
            service_info = services.get("mcp-vector-search")

            if not service_info:
                return CommandResult.error_result(
                    "mcp-vector-search service not found in registry"
                )

            # Setup the service
            success = handler._setup_service(
                config, "mcp-vector-search", service_info, force
            )

            if success:
                # Save configuration
                if handler._save_config(config, mcp_config_path):
                    console.print(
                        "\n[green]✓ MCP Vector Search setup complete![/green]"
                    )
                    console.print(
                        "\n[dim]What changed:[/dim]\n"
                        "  1. mcp-vector-search installed (or re-used if already installed)\n"
                        "  2. Configuration added to .mcp.json\n"
                        "  3. MCP server will be available in Claude Code\n"
                    )
                    console.print(
                        "\n[dim]Next steps:[/dim]\n"
                        "  1. Start Claude Code to use semantic code search\n"
                        "  2. Your code will be indexed for vector search\n"
                        "  3. Use search tools for better context retrieval\n"
                    )
                    return CommandResult.success_result(
                        "MCP Vector Search setup completed"
                    )
                return CommandResult.error_result("Failed to save configuration")
            return CommandResult.error_result("Failed to configure mcp-vector-search")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error during setup: {e}")

    def _setup_mcp_skillset(self, args) -> CommandResult:
        """Setup mcp-skillset as a USER-LEVEL MCP server.

        This configures mcp-skillset in Claude Desktop config (~/.claude-mpm/ or
        ~/Library/Application Support/Claude/claude_desktop_config.json),
        NOT in project .mcp.json.

        Args:
            args: Setup options (force flag supported)

        Returns:
            CommandResult indicating success or failure
        """
        console.print(
            "\n[bold cyan]Setting up mcp-skillset (USER-LEVEL)...[/bold cyan]"
        )
        console.print(
            "[dim]This will install mcp-skillset for ALL projects (not project-specific)[/dim]\n"
        )

        try:
            # Check if mcp-skillset is installed
            console.print("[cyan]Checking mcp-skillset installation...[/cyan]")
            try:
                import importlib.util

                spec = importlib.util.find_spec("mcp_skillset")
                is_installed = spec is not None
            except (ImportError, ModuleNotFoundError):
                is_installed = False

            # Install if needed
            force = getattr(args, "force", False)
            if not is_installed or force:
                console.print("[cyan]Detecting installation method...[/cyan]")

                # Use existing detection utility
                from ...services.diagnostics.checks.installation_check import (
                    InstallationCheck,
                )

                checker = InstallationCheck()
                methods = checker._check_installation_method()

                # Determine primary method (priority: pipx > uv > pip)
                install_method = None
                detected_methods = methods.details.get("methods_detected", [])

                if "pipx" in detected_methods:
                    install_method = "pipx"
                elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
                    install_method = "uv"
                else:
                    install_method = "pip"

                console.print(f"[dim]Detected: {install_method} installation[/dim]")

                action = "Reinstalling" if is_installed else "Installing"
                console.print(
                    f"[yellow]{action} mcp-skillset via {install_method}...[/yellow]"
                )

                try:
                    if install_method == "pipx":
                        subprocess.run(
                            ["pipx", "install", "mcp-skillset"],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    elif install_method == "uv":
                        subprocess.run(
                            [
                                "uv",
                                "tool",
                                "install",
                                "mcp-skillset",
                                "--python",
                                "3.13",
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    elif install_method == "pip":
                        subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "pip",
                                "install",
                                "--user",
                                "mcp-skillset",
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )  # nosec B603 B607

                    console.print(
                        f"[green]✓ mcp-skillset installed via {install_method}[/green]"
                    )

                except subprocess.CalledProcessError:
                    return CommandResult.error_result(
                        f"Failed to install mcp-skillset via {install_method}. "
                        f"Try manually: {install_method} install mcp-skillset"
                    )
            else:
                console.print("[green]✓ mcp-skillset already installed[/green]")

            # Configure in USER-LEVEL Claude Desktop config
            console.print(
                "\n[cyan]Configuring in Claude Desktop (user-level)...[/cyan]"
            )

            config_path = self._get_claude_desktop_config_path()
            if not config_path:
                return CommandResult.error_result(
                    "Could not determine Claude Desktop config path"
                )

            console.print(f"  Config: {config_path}")

            # Load or create config
            import json

            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    console.print(
                        f"[yellow]Warning: Could not read config: {e}[/yellow]"
                    )
                    config = {"mcpServers": {}}
            else:
                config = {"mcpServers": {}}

            # Ensure mcpServers exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check if already configured
            if "mcp-skillset" in config["mcpServers"] and not force:
                console.print("[yellow]⚠ mcp-skillset already configured[/yellow]")
                from rich.prompt import Confirm

                if not Confirm.ask("Overwrite existing configuration?", default=False):
                    console.print("[yellow]Skipping configuration[/yellow]")
                    return CommandResult.success_result(
                        "mcp-skillset already configured"
                    )

            # Add mcp-skillset configuration
            config["mcpServers"]["mcp-skillset"] = {
                "type": "stdio",
                "command": "mcp-skillset",
                "args": ["mcp"],
                "env": {},
            }

            # Save config
            try:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                    f.write("\n")

                console.print(
                    "[green]✓ Added mcp-skillset to Claude Desktop config[/green]"
                )
            except OSError as e:
                return CommandResult.error_result(f"Could not save config: {e}")

            console.print("\n[green]✓ mcp-skillset setup complete![/green]")
            console.print(
                "\n[dim]What changed:[/dim]\n"
                "  1. mcp-skillset installed (or re-used if already installed)\n"
                "  2. Configuration added to Claude Desktop config (USER-LEVEL)\n"
                "  3. MCP tools available across ALL projects\n"
                "  4. Skills optimization can now query mcp-skillset for recommendations\n"
            )
            console.print(
                "\n[dim]Next steps:[/dim]\n"
                "  1. Restart Claude Code to load mcp-skillset\n"
                "  2. Use: claude-mpm skills optimize --use-mcp-skillset\n"
                "  3. MCP tools will enhance skill recommendations\n"
            )

            return CommandResult.success_result("mcp-skillset setup completed")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            console.print(f"[red]✗ Failed to setup mcp-skillset: {e}[/red]")
            import traceback

            traceback.print_exc()
            return CommandResult.error_result(f"Failed to setup mcp-skillset: {e}")

    def _get_claude_desktop_config_path(self) -> Path | None:
        """Get Claude Desktop configuration path.

        Returns:
            Path to claude_desktop_config.json or None if not found
        """
        import platform

        possible_paths = [
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json",  # macOS
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
            Path.home()
            / "AppData"
            / "Roaming"
            / "Claude"
            / "claude_desktop_config.json",  # Windows
            Path.home() / ".claude" / "claude_desktop_config.json",  # Alternative
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Return platform-appropriate default
        system = platform.system()
        if system == "Darwin":  # macOS
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        if system == "Windows":
            return (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Claude"
                / "claude_desktop_config.json"
            )
        # Linux and others
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def _setup_mcp_ticketer(self, args) -> CommandResult:
        """Setup mcp-ticketer with MPM hook integration.

        Args:
            args: Setup options (currently unused)

        Returns:
            CommandResult indicating success or failure
        """
        console.print("\n[bold cyan]Setting up mcp-ticketer...[/bold cyan]")

        try:
            # Run mcp-ticketer setup with auto mode
            # This integrates with MPM's hook system automatically
            result = subprocess.run(
                ["mcp-ticketer", "setup", "--auto"],
                capture_output=True,
                text=True,
                check=False,
            )  # nosec B603 B607

            if result.returncode == 0:
                console.print("[green]✓ mcp-ticketer configured successfully[/green]")
                console.print("  [dim]Hooks integrated with MPM hook system[/dim]")
                return CommandResult.success_result("mcp-ticketer setup completed")

            console.print(
                "[yellow]⚠ mcp-ticketer setup completed with warnings:[/yellow]"
            )
            console.print(f"  {result.stderr.strip()}")
            return CommandResult.success_result(
                "mcp-ticketer setup completed with warnings"
            )

        except FileNotFoundError:
            console.print("[red]✗ mcp-ticketer not found. Install with:[/red]")
            console.print("  pip install mcp-ticketer")
            return CommandResult.error_result("mcp-ticketer not installed")
        except Exception as e:
            console.print(f"[red]✗ Failed to setup mcp-ticketer: {e}[/red]")
            return CommandResult.error_result(f"Failed to setup mcp-ticketer: {e}")

    def _setup_google_workspace(self, args) -> CommandResult:
        """Set up Google Workspace MCP (delegates to OAuth setup)."""
        console.print(
            "This will configure OAuth authentication for Google Workspace.\n"
        )

        # Check if gworkspace-mcp package is installed
        import subprocess  # nosec B404

        try:
            result = subprocess.run(  # nosec B603 B607
                ["which", "google-workspace-mcp"],
                check=False,
                capture_output=True,
                text=True,
            )
            is_installed = result.returncode == 0
        except Exception:
            is_installed = False

        # Install package if missing
        if not is_installed:
            console.print("[cyan]Installing gworkspace-mcp package...[/cyan]")
            try:
                subprocess.run(  # nosec B603 B607
                    ["uv", "tool", "install", "gworkspace-mcp"],
                    check=True,
                    capture_output=True,
                )
                console.print("[green]✓[/green] Package installed successfully\n")
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                return CommandResult(
                    success=False,
                    message=f"Failed to install gworkspace-mcp: {error_msg}",
                )

        # Delegate to OAuth setup with google-workspace-mcp as the service
        # Create args for oauth setup
        from argparse import Namespace

        from .oauth import manage_oauth

        oauth_args = Namespace(
            oauth_command="setup",
            service_name="gworkspace-mcp",  # Canonical service name
            no_browser=getattr(args, "no_browser", False),
            no_launch=getattr(args, "no_launch", False),
            force=getattr(args, "force", False),
        )

        exit_code = manage_oauth(oauth_args)

        # Register service in setup registry on success
        if exit_code == 0:
            try:
                from claude_mpm.services.setup_registry import SetupRegistry

                registry = SetupRegistry()

                # Get CLI help for the tool
                cli_help = ""
                try:
                    help_result = subprocess.run(  # nosec B603 B607
                        ["google-workspace-mcp", "--help"],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if help_result.returncode == 0:
                        cli_help = help_result.stdout
                except Exception:  # nosec B110
                    pass  # Help text is optional, failure is non-fatal

                # Register with known tools
                registry.add_service(
                    name="gworkspace-mcp",
                    service_type="mcp",
                    version="0.1.2",  # TODO: Get from package
                    tools=[
                        "search_gmail_messages",
                        "get_gmail_message_content",
                        "list_calendar_events",
                        "get_calendar_event",
                        "search_drive_files",
                        "get_drive_file_content",
                    ],
                    cli_help=cli_help,
                    config_location="user",
                )
            except Exception as e:
                console.print(
                    f"[dim]Warning: Could not update setup registry: {e}[/dim]"
                )

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
                "Example: claude-mpm setup oauth --oauth-service gworkspace-mcp"
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
