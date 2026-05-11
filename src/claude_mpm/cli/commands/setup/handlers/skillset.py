"""mcp-skillset USER-LEVEL setup handler (writes Claude Desktop config)."""

from __future__ import annotations

import json
import platform
from pathlib import Path

from ....constants import SetupService
from ....shared import CommandResult
from .._shared import console


class SkillsetMixin:
    """Mixin: mcp-skillset installation + Claude Desktop config write."""

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
            # Use centralized package installer
            console.print("[cyan]Checking mcp-skillset installation...[/cyan]")

            from .....services.package_installer import (
                InstallAction,
                PackageInstallerService,
                get_spec,
            )

            installer = PackageInstallerService()
            spec = get_spec(SetupService.MCP_SKILLSET)

            force = getattr(args, "force", False)
            upgrade = getattr(args, "upgrade", False)

            # Check if already installed and no flags set
            if installer.is_installed(spec) and not force and not upgrade:
                console.print("[green]✓ mcp-skillset already installed[/green]")
            else:
                console.print("[cyan]Detecting installation method...[/cyan]")
                success, message = installer.install(
                    spec, InstallAction.INSTALL, force=force, upgrade=upgrade
                )
                if success:
                    console.print(f"[green]✓ {message}[/green]")
                else:
                    return CommandResult.error_result(message)

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
                console.print("[dim]mcp-skillset already configured[/dim]")
                return CommandResult.success_result("mcp-skillset already configured")

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
