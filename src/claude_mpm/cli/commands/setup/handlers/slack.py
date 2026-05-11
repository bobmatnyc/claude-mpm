"""Slack integration handlers (slack-mpm + legacy slack-user-proxy)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

from ....shared import CommandResult
from .._shared import console


class SlackMixin:
    """Mixin: slack-mpm + legacy Slack setup methods."""

    def _configure_slack_mpm_in_mcp_json(
        self, slack_mpm_path: str | None = None
    ) -> None:
        """Configure slack-mpm MCP server in .mcp.json."""
        mcp_config_path = Path.cwd() / ".mcp.json"

        # Build server config — prefer uv run with directory if we know the path
        if slack_mpm_path:
            server_config = {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "--directory", slack_mpm_path, "slack-mpm", "mcp"],
                "env": {},
            }
        else:
            # Fall back to installed binary
            server_config = {
                "type": "stdio",
                "command": "slack-mpm",
                "args": ["mcp"],
                "env": {},
            }

        # Load or create .mcp.json
        if mcp_config_path.exists():
            try:
                with open(mcp_config_path) as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                config = {"mcpServers": {}}
        else:
            config = {"mcpServers": {}}

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        if "slack-mpm" in config["mcpServers"]:
            console.print("[dim]slack-mpm already configured in .mcp.json[/dim]")
            return

        config["mcpServers"]["slack-mpm"] = server_config

        try:
            with open(mcp_config_path, "w") as f:
                json.dump(config, f, indent=2)
                f.write("\n")
            console.print("[green]✓ Added slack-mpm to .mcp.json[/green]")
        except OSError as e:
            console.print(f"[yellow]Warning: Could not write .mcp.json: {e}[/yellow]")

    def _setup_slack_mpm(self, _args) -> CommandResult:
        """Set up slack-mpm — validates SLACK_BOT_TOKEN and configures .mcp.json."""
        _ = _args  # args passed by caller dispatch; not used in this implementation

        console.print(
            "\n[bold]Slack MCP Setup[/bold]\n"
            "Connects Claude to your Slack workspace via the slack-mpm server.\n"
            "Requires a Slack bot token (SLACK_BOT_TOKEN=xoxb-...).\n"
        )

        # --- Step 1: Locate slack-mpm binary or local project ---
        slack_mpm_project = Path.home() / "Projects" / "slack-mpm"
        slack_mpm_binary = shutil.which("slack-mpm")
        using_local = (
            slack_mpm_project.exists()
            and (slack_mpm_project / "pyproject.toml").exists()
        )

        if using_local:
            console.print(
                f"[cyan]Found local slack-mpm project at {slack_mpm_project}[/cyan]"
            )
            run_cmd = ["uv", "run", "--directory", str(slack_mpm_project), "slack-mpm"]
            slack_mpm_path: str | None = str(slack_mpm_project)
        elif slack_mpm_binary:
            console.print(
                f"[cyan]Found installed slack-mpm at {slack_mpm_binary}[/cyan]"
            )
            run_cmd = [slack_mpm_binary]
            slack_mpm_path = None
        else:
            console.print(
                "[yellow]slack-mpm not found locally or installed.[/yellow]\n"
                "[dim]Install it:[/dim]\n"
                "  git clone https://github.com/bobmatnyc/slack-mpm ~/Projects/slack-mpm\n"
                "  cd ~/Projects/slack-mpm && uv sync\n"
            )
            return CommandResult.error_result(
                "slack-mpm not found. Clone the project to ~/Projects/slack-mpm."
            )

        # --- Step 2: Check for SLACK_BOT_TOKEN ---
        # Load from .env / .env.local in CWD
        from dotenv import dotenv_values

        env_vars: dict[str, str | None] = {}
        for env_file in [Path.cwd() / ".env", Path.cwd() / ".env.local"]:
            if env_file.exists():
                env_vars.update(dotenv_values(env_file))

        token = env_vars.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")

        if not token:
            console.print(
                "\n[yellow]SLACK_BOT_TOKEN not found.[/yellow]\n"
                "[dim]Create a .env.local file with:[/dim]\n"
                "  SLACK_BOT_TOKEN=xoxb-your-token-here\n\n"
                "[dim]Get a bot token at: https://api.slack.com/apps[/dim]\n"
                "[dim]Required bot scopes: channels:read, channels:write, chat:write,\n"
                "  users:read, files:read, reactions:write[/dim]\n"
            )
            return CommandResult.error_result(
                "SLACK_BOT_TOKEN required. Set it in .env.local."
            )

        console.print(f"[dim]Bot token found: {token[:6]}...{token[-4:]}[/dim]")

        # --- Step 3: Validate token via slack-mpm setup ---
        console.print("\n[cyan]Validating Slack token...[/cyan]")
        try:
            env = os.environ.copy()
            env["SLACK_BOT_TOKEN"] = token
            result = subprocess.run(  # nosec B603
                run_cmd + ["setup"],
                check=False,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                console.print(result.stdout)
                console.print("[green]✓ Token validated successfully[/green]")
            else:
                console.print(
                    f"[red]Token validation failed:[/red]\n{result.stdout}{result.stderr}"
                )
                return CommandResult.error_result("Slack token validation failed.")
        except subprocess.TimeoutExpired:
            return CommandResult.error_result("Token validation timed out.")
        except Exception as e:
            return CommandResult.error_result(f"Failed to run slack-mpm setup: {e}")

        # --- Step 4: Configure .mcp.json ---
        self._configure_slack_mpm_in_mcp_json(slack_mpm_path=slack_mpm_path)

        # --- Step 5: Register with setup registry ---
        try:
            from claude_mpm.services.setup_registry import SetupRegistry

            registry = SetupRegistry()
            registry.add_service(
                name="slack-mpm",
                service_type="mcp",
                version="0.1.0",
                tools=[
                    "list_channels",
                    "get_channel_info",
                    "create_channel",
                    "send_message",
                    "update_message",
                    "delete_message",
                    "add_reaction",
                    "remove_reaction",
                    "pin_message",
                    "list_users",
                    "get_user_info",
                    "get_user_by_email",
                    "upload_file",
                    "list_files",
                    "get_workspace_info",
                    "auth_test",
                    "schedule_message",
                    "add_reminder",
                ],
            )
            console.print("[green]✓ Registered slack-mpm in setup registry[/green]")
        except Exception:
            pass  # Registry is optional, non-fatal

        console.print(
            "\n[bold green]✓ slack-mpm setup complete![/bold green]\n"
            "[dim]The MCP server is now configured in .mcp.json.\n"
            "Claude Code will load it automatically when you open this project.[/dim]\n"
        )

        return CommandResult.success_result("slack-mpm setup complete")

    def _configure_slack_mpm_server(self) -> None:
        """Configure slack-user-proxy MCP server in .mcp.json after OAuth setup."""
        try:
            mcp_config_path = Path.cwd() / ".mcp.json"

            # Get the slack-user-proxy configuration from service registry
            try:
                from .....services.mcp_service_registry import MCPServiceRegistry

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

    def _setup_slack(self, _args) -> CommandResult:
        """Run the Slack setup script."""
        _ = _args  # args passed by caller dispatch; not used in this implementation
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
                self._configure_slack_mpm_server()

                # Also configure slack-mpm if available
                self._configure_slack_mpm_in_mcp_json()

                return CommandResult.success_result("Slack setup completed")

            return CommandResult.error_result(
                f"Setup script exited with code {result.returncode}"
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error running setup: {e}")
