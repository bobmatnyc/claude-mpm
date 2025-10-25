"""Configuration persistence and version management for configure command.

WHY: Separate configuration import/export and version display logic from main
configure command to improve modularity. This handles all file I/O for
configuration backups and version information display.

DESIGN DECISIONS:
- Export/import configuration as JSON for portability
- Display version info for both MPM and Claude Code
- Support interactive and non-interactive modes
- Include validation for import operations
"""

import json
import subprocess
import sys
from pathlib import Path

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ..shared import CommandResult


class ConfigPersistence:
    """Handle configuration import/export and version information display.

    This class manages:
    - Exporting configuration to JSON files
    - Importing configuration from JSON files
    - Displaying version information (MPM, Claude Code, Python)
    - Both interactive and non-interactive display modes
    """

    def __init__(
        self,
        console: Console,
        version_service,  # VersionService instance
        agent_manager,  # SimpleAgentManager instance (can be None for version operations)
        get_template_path_fn,  # Function to get template path
        display_header_fn,  # Function to display header
        current_scope: str,
        project_dir: Path,
    ):
        """Initialize persistence handler.

        Args:
            console: Rich console for output
            version_service: VersionService for version info
            agent_manager: SimpleAgentManager for agent states (can be None for version operations)
            get_template_path_fn: Function(agent_name) -> Path
            display_header_fn: Function() -> None to display header
            current_scope: Current configuration scope (project/user)
            project_dir: Current project directory
        """
        self.console = console
        self.version_service = version_service
        self.agent_manager = agent_manager
        self._get_agent_template_path = get_template_path_fn
        self._display_header = display_header_fn
        self.current_scope = current_scope
        self.project_dir = project_dir

    def export_config(self, file_path: str) -> CommandResult:
        """Export configuration to a JSON file.

        Exports:
        - Current scope (project/user)
        - Agent enabled/disabled states
        - Template paths for each agent

        Args:
            file_path: Path to export configuration to

        Returns:
            CommandResult indicating success or failure
        """
        try:
            # Gather all configuration
            config_data = {"scope": self.current_scope, "agents": {}, "behaviors": {}}

            # Get agent states
            agents = self.agent_manager.discover_agents()
            for agent in agents:
                config_data["agents"][agent.name] = {
                    "enabled": self.agent_manager.is_agent_enabled(agent.name),
                    "template_path": str(self._get_agent_template_path(agent.name)),
                }

            # Write to file
            output_path = Path(file_path)
            with output_path.open("w") as f:
                json.dump(config_data, f, indent=2)

            return CommandResult.success_result(
                f"Configuration exported to {output_path}"
            )

        except Exception as e:
            return CommandResult.error_result(f"Failed to export configuration: {e}")

    def import_config(self, file_path: str) -> CommandResult:
        """Import configuration from a JSON file.

        Imports and applies:
        - Agent enabled/disabled states
        - (Future: behavior configurations)

        Args:
            file_path: Path to import configuration from

        Returns:
            CommandResult indicating success or failure
        """
        try:
            input_path = Path(file_path)
            if not input_path.exists():
                return CommandResult.error_result(f"File not found: {file_path}")

            with input_path.open() as f:
                config_data = json.load(f)

            # Apply agent states
            if "agents" in config_data:
                for agent_name, agent_config in config_data["agents"].items():
                    if "enabled" in agent_config:
                        self.agent_manager.set_agent_enabled(
                            agent_name, agent_config["enabled"]
                        )

            return CommandResult.success_result(
                f"Configuration imported from {input_path}"
            )

        except Exception as e:
            return CommandResult.error_result(f"Failed to import configuration: {e}")

    def show_version_info(self) -> CommandResult:
        """Show version information in non-interactive mode.

        Displays:
        - Claude MPM version and build number
        - Claude Code version (if available)
        - Python version

        Returns:
            CommandResult with version data
        """
        mpm_version = self.version_service.get_version()
        build_number = self.version_service.get_build_number()

        data = {
            "mpm_version": mpm_version,
            "build_number": build_number,
            "python_version": sys.version.split()[0],
        }

        # Try to get Claude version
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                data["claude_version"] = result.stdout.strip()
        except Exception:
            data["claude_version"] = "Unknown"

        # Print formatted output
        self.console.print(
            f"[bold]Claude MPM:[/bold] {mpm_version} (build {build_number})"
        )
        self.console.print(
            f"[bold]Claude Code:[/bold] {data.get('claude_version', 'Unknown')}"
        )
        self.console.print(f"[bold]Python:[/bold] {data['python_version']}")

        return CommandResult.success_result("Version information displayed", data=data)

    def show_version_info_interactive(self) -> None:
        """Show version information in interactive mode with panel display.

        Displays comprehensive version information in a formatted panel:
        - Claude MPM version and build number
        - Claude Code version with compatibility info
        - Python version
        - Current configuration scope and directory
        """
        self.console.clear()
        self._display_header()

        # Get version information
        mpm_version = self.version_service.get_version()
        build_number = self.version_service.get_build_number()

        # Try to get Claude Code version using the installer's method
        claude_version = "Unknown"
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()
            detected_version = installer.get_claude_version()
            if detected_version:
                is_compatible, _ = installer.is_version_compatible()
                claude_version = f"{detected_version} (Claude Code)"
                if not is_compatible:
                    claude_version += (
                        f" - Monitoring requires {installer.MIN_CLAUDE_VERSION}+"
                    )
            else:
                # Fallback to direct subprocess call
                result = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    claude_version = result.stdout.strip()
        except Exception:
            pass

        # Create version panel
        version_text = f"""
[bold cyan]Claude MPM[/bold cyan]
Version: {mpm_version}
Build: {build_number}

[bold cyan]Claude Code[/bold cyan]
Version: {claude_version}

[bold cyan]Python[/bold cyan]
Version: {sys.version.split()[0]}

[bold cyan]Configuration[/bold cyan]
Scope: {self.current_scope}
Directory: {self.project_dir}
        """

        panel = Panel(
            version_text.strip(),
            title="[bold]Version Information[/bold]",
            box=ROUNDED,
            style="green",
        )

        self.console.print(panel)
        Prompt.ask("\nPress Enter to continue")
