"""
Interactive configuration management command for claude-mpm CLI.

WHY: Users need an intuitive, interactive way to manage agent configurations,
edit templates, and configure behavior files without manually editing JSON/YAML files.

DESIGN DECISIONS:
- Use Rich for modern TUI with menus, tables, and panels
- Support both project-level and user-level configurations
- Provide non-interactive options for scripting
- Allow direct navigation to specific sections
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ...core.config import Config
from ...services.mcp_config_manager import MCPConfigManager
from ...services.version_service import VersionService
from ...utils.console import console as default_console
from ..shared import BaseCommand, CommandResult


class AgentConfig:
    """Simple agent configuration model."""

    def __init__(
        self, name: str, description: str = "", dependencies: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.dependencies = dependencies or []


class SimpleAgentManager:
    """Simple agent state management that discovers real agents from templates."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "agent_states.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_states()
        # Path to agent templates directory
        self.templates_dir = (
            Path(__file__).parent.parent.parent / "agents" / "templates"
        )
        # Add logger for error reporting
        import logging

        self.logger = logging.getLogger(__name__)

    def _load_states(self):
        """Load agent states from file."""
        if self.config_file.exists():
            with self.config_file.open() as f:
                self.states = json.load(f)
        else:
            self.states = {}

    def _save_states(self):
        """Save agent states to file."""
        with self.config_file.open("w") as f:
            json.dump(self.states, f, indent=2)

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if an agent is enabled."""
        return self.states.get(agent_name, {}).get("enabled", True)

    def set_agent_enabled(self, agent_name: str, enabled: bool):
        """Set agent enabled state."""
        if agent_name not in self.states:
            self.states[agent_name] = {}
        self.states[agent_name]["enabled"] = enabled
        self._save_states()

    def discover_agents(self) -> List[AgentConfig]:
        """Discover available agents from template JSON files."""
        agents = []

        # Scan templates directory for JSON files
        if not self.templates_dir.exists():
            # Fallback to a minimal set if templates dir doesn't exist
            return [
                AgentConfig("engineer", "Engineering agent (templates not found)", []),
                AgentConfig("research", "Research agent (templates not found)", []),
            ]

        try:
            # Read all JSON template files
            for template_file in sorted(self.templates_dir.glob("*.json")):
                # Skip backup files
                if "backup" in template_file.name.lower():
                    continue

                try:
                    with template_file.open() as f:
                        template_data = json.load(f)

                    # Extract agent information from template
                    agent_id = template_data.get("agent_id", template_file.stem)

                    # Get metadata for display info
                    metadata = template_data.get("metadata", {})
                    metadata.get("name", agent_id)
                    description = metadata.get(
                        "description", "No description available"
                    )

                    # Extract capabilities/tools as dependencies for display
                    capabilities = template_data.get("capabilities", {})
                    tools = capabilities.get("tools", [])
                    # Ensure tools is a list before slicing
                    if not isinstance(tools, list):
                        tools = []
                    # Show first few tools as "dependencies" for UI purposes
                    display_tools = tools[:3] if len(tools) > 3 else tools

                    # Normalize agent ID (remove -agent suffix if present, replace underscores)
                    normalized_id = agent_id.replace("-agent", "").replace("_", "-")

                    agents.append(
                        AgentConfig(
                            name=normalized_id,
                            description=(
                                description[:80] + "..."
                                if len(description) > 80
                                else description
                            ),
                            dependencies=display_tools,
                        )
                    )

                except (json.JSONDecodeError, KeyError) as e:
                    # Log malformed templates but continue
                    self.logger.debug(
                        f"Skipping malformed template {template_file.name}: {e}"
                    )
                    continue
                except Exception as e:
                    # Log unexpected errors but continue processing other templates
                    self.logger.debug(
                        f"Error processing template {template_file.name}: {e}"
                    )
                    continue

        except Exception as e:
            # If there's a catastrophic error reading templates directory
            self.logger.error(f"Failed to read templates directory: {e}")
            return [
                AgentConfig("engineer", f"Error accessing templates: {e!s}", []),
                AgentConfig("research", "Research agent", []),
            ]

        # Sort agents by name for consistent display
        agents.sort(key=lambda a: a.name)

        return (
            agents
            if agents
            else [
                AgentConfig("engineer", "No agents found in templates", []),
            ]
        )


class ConfigureCommand(BaseCommand):
    """Interactive configuration management command."""

    def __init__(self):
        super().__init__("configure")
        self.console = default_console
        self.version_service = VersionService()
        self.current_scope = "project"
        self.project_dir = Path.cwd()
        self.agent_manager = None

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Check for conflicting direct navigation options
        nav_options = [
            getattr(args, "agents", False),
            getattr(args, "templates", False),
            getattr(args, "behaviors", False),
            getattr(args, "startup", False),
            getattr(args, "version_info", False),
        ]
        if sum(nav_options) > 1:
            return "Only one direct navigation option can be specified at a time"

        # Check for conflicting non-interactive options
        if getattr(args, "enable_agent", None) and getattr(args, "disable_agent", None):
            return "Cannot enable and disable agents at the same time"

        return None

    def run(self, args) -> CommandResult:
        """Execute the configure command."""
        # Set configuration scope
        self.current_scope = getattr(args, "scope", "project")
        if getattr(args, "project_dir", None):
            self.project_dir = Path(args.project_dir)

        # Initialize agent manager with appropriate config directory
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm"
        else:
            config_dir = Path.home() / ".claude-mpm"
        self.agent_manager = SimpleAgentManager(config_dir)

        # Disable colors if requested
        if getattr(args, "no_colors", False):
            self.console = Console(color_system=None)

        # Handle non-interactive options first
        if getattr(args, "list_agents", False):
            return self._list_agents_non_interactive()

        if getattr(args, "enable_agent", None):
            return self._enable_agent_non_interactive(args.enable_agent)

        if getattr(args, "disable_agent", None):
            return self._disable_agent_non_interactive(args.disable_agent)

        if getattr(args, "export_config", None):
            return self._export_config(args.export_config)

        if getattr(args, "import_config", None):
            return self._import_config(args.import_config)

        if getattr(args, "version_info", False):
            return self._show_version_info()

        # Handle hook installation
        if getattr(args, "install_hooks", False):
            return self._install_hooks(force=getattr(args, "force", False))

        if getattr(args, "verify_hooks", False):
            return self._verify_hooks()

        if getattr(args, "uninstall_hooks", False):
            return self._uninstall_hooks()

        # Handle direct navigation options
        if getattr(args, "agents", False):
            return self._run_agent_management()

        if getattr(args, "templates", False):
            return self._run_template_editing()

        if getattr(args, "behaviors", False):
            return self._run_behavior_management()

        if getattr(args, "startup", False):
            return self._run_startup_configuration()

        # Launch interactive TUI
        return self._run_interactive_tui(args)

    def _run_interactive_tui(self, args) -> CommandResult:
        """Run the main interactive menu interface."""
        # Rich-based menu interface
        try:
            self.console.clear()

            while True:
                # Display main menu
                self._display_header()
                choice = self._show_main_menu()

                if choice == "1":
                    self._manage_agents()
                elif choice == "2":
                    self._edit_templates()
                elif choice == "3":
                    self._manage_behaviors()
                elif choice == "4":
                    # If user saves and wants to proceed to startup, exit the configurator
                    if self._manage_startup_configuration():
                        self.console.print(
                            "\n[green]Configuration saved. Exiting configurator...[/green]"
                        )
                        break
                elif choice == "5":
                    self._switch_scope()
                elif choice == "6":
                    self._show_version_info_interactive()
                elif choice == "q":
                    self.console.print(
                        "\n[green]Configuration complete. Goodbye![/green]"
                    )
                    break
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")

            return CommandResult.success_result("Configuration completed")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Configuration cancelled.[/yellow]")
            return CommandResult.success_result("Configuration cancelled")
        except Exception as e:
            self.logger.error(f"Configuration error: {e}", exc_info=True)
            return CommandResult.error_result(f"Configuration failed: {e}")

    def _display_header(self) -> None:
        """Display the TUI header."""
        self.console.clear()

        # Get version for display
        from claude_mpm import __version__

        # Create header panel
        header_text = Text()
        header_text.append("Claude MPM ", style="bold cyan")
        header_text.append("Configuration Interface", style="bold white")
        header_text.append(f"\nv{__version__}", style="dim cyan")

        scope_text = Text(f"Scope: {self.current_scope.upper()}", style="yellow")
        dir_text = Text(f"Directory: {self.project_dir}", style="dim")

        header_content = Columns([header_text], align="center")
        subtitle_content = f"{scope_text} | {dir_text}"

        header_panel = Panel(
            header_content,
            subtitle=subtitle_content,
            box=ROUNDED,
            style="blue",
            padding=(1, 2),
        )

        self.console.print(header_panel)
        self.console.print()

    def _show_main_menu(self) -> str:
        """Show the main menu and get user choice."""
        menu_items = [
            ("1", "Agent Management", "Enable/disable agents and customize settings"),
            ("2", "Template Editing", "Edit agent JSON templates"),
            ("3", "Behavior Files", "Manage identity and workflow configurations"),
            (
                "4",
                "Startup Configuration",
                "Configure MCP services and agents to start",
            ),
            ("5", "Switch Scope", f"Current: {self.current_scope}"),
            ("6", "Version Info", "Display MPM and Claude versions"),
            ("q", "Quit", "Exit configuration interface"),
        ]

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="cyan", width=3)
        table.add_column("Option", style="bold white", width=20)
        table.add_column("Description", style="dim")

        for key, option, desc in menu_items:
            table.add_row(f"[{key}]", option, desc)

        menu_panel = Panel(
            table, title="[bold]Main Menu[/bold]", box=ROUNDED, style="green"
        )

        self.console.print(menu_panel)
        self.console.print()

        return Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="q")

    def _manage_agents(self) -> None:
        """Agent management interface."""
        while True:
            self.console.clear()
            self._display_header()

            # Display available agents
            agents = self.agent_manager.discover_agents()
            self._display_agents_table(agents)

            # Show agent menu
            self.console.print("\n[bold]Agent Management Options:[/bold]")
            self.console.print("  [cyan][e][/cyan] Enable an agent")
            self.console.print("  [cyan][d][/cyan] Disable an agent")
            self.console.print("  [cyan][c][/cyan] Customize agent template")
            self.console.print("  [cyan][v][/cyan] View agent details")
            self.console.print("  [cyan][r][/cyan] Reset agent to defaults")
            self.console.print("  [cyan][b][/cyan] Back to main menu")
            self.console.print()

            choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="b")

            if choice == "b":
                break
            if choice == "e":
                self._enable_agent_interactive(agents)
            elif choice == "d":
                self._disable_agent_interactive(agents)
            elif choice == "c":
                self._customize_agent_template(agents)
            elif choice == "v":
                self._view_agent_details(agents)
            elif choice == "r":
                self._reset_agent_defaults(agents)
            else:
                self.console.print("[red]Invalid choice.[/red]")
                Prompt.ask("Press Enter to continue")

    def _display_agents_table(self, agents: List[AgentConfig]) -> None:
        """Display a table of available agents."""
        table = Table(
            title=f"Available Agents ({len(agents)} total)",
            box=ROUNDED,
            show_lines=True,
        )

        table.add_column("ID", style="dim", width=3)
        table.add_column("Name", style="cyan", width=22)
        table.add_column("Status", width=12)
        table.add_column("Description", style="white", width=45)
        table.add_column("Model/Tools", style="dim", width=20)

        for idx, agent in enumerate(agents, 1):
            # Check if agent is enabled
            is_enabled = self.agent_manager.is_agent_enabled(agent.name)
            status = (
                "[green]✓ Enabled[/green]" if is_enabled else "[red]✗ Disabled[/red]"
            )

            # Format tools/dependencies - show first 2 tools
            tools_display = ""
            if agent.dependencies:
                if len(agent.dependencies) > 2:
                    tools_display = f"{', '.join(agent.dependencies[:2])}..."
                else:
                    tools_display = ", ".join(agent.dependencies)
            else:
                # Try to get model from template
                try:
                    template_path = self._get_agent_template_path(agent.name)
                    if template_path.exists():
                        with template_path.open() as f:
                            template = json.load(f)
                        model = template.get("capabilities", {}).get("model", "default")
                        tools_display = f"Model: {model}"
                    else:
                        tools_display = "Default"
                except Exception:
                    tools_display = "Default"

            # Truncate description for table display
            desc_display = (
                agent.description[:42] + "..."
                if len(agent.description) > 42
                else agent.description
            )

            table.add_row(str(idx), agent.name, status, desc_display, tools_display)

        self.console.print(table)

    def _enable_agent_interactive(self, agents: List[AgentConfig]) -> None:
        """Interactive agent enabling."""
        agent_id = Prompt.ask("Enter agent ID to enable (or 'all' for all agents)")

        if agent_id.lower() == "all":
            if Confirm.ask("[yellow]Enable ALL agents?[/yellow]"):
                for agent in agents:
                    self.agent_manager.set_agent_enabled(agent.name, True)
                self.console.print("[green]All agents enabled successfully![/green]")
        else:
            try:
                idx = int(agent_id) - 1
                if 0 <= idx < len(agents):
                    agent = agents[idx]
                    self.agent_manager.set_agent_enabled(agent.name, True)
                    self.console.print(
                        f"[green]Agent '{agent.name}' enabled successfully![/green]"
                    )
                else:
                    self.console.print("[red]Invalid agent ID.[/red]")
            except ValueError:
                self.console.print("[red]Invalid input. Please enter a number.[/red]")

        Prompt.ask("Press Enter to continue")

    def _disable_agent_interactive(self, agents: List[AgentConfig]) -> None:
        """Interactive agent disabling."""
        agent_id = Prompt.ask("Enter agent ID to disable (or 'all' for all agents)")

        if agent_id.lower() == "all":
            if Confirm.ask("[yellow]Disable ALL agents?[/yellow]"):
                for agent in agents:
                    self.agent_manager.set_agent_enabled(agent.name, False)
                self.console.print("[green]All agents disabled successfully![/green]")
        else:
            try:
                idx = int(agent_id) - 1
                if 0 <= idx < len(agents):
                    agent = agents[idx]
                    self.agent_manager.set_agent_enabled(agent.name, False)
                    self.console.print(
                        f"[green]Agent '{agent.name}' disabled successfully![/green]"
                    )
                else:
                    self.console.print("[red]Invalid agent ID.[/red]")
            except ValueError:
                self.console.print("[red]Invalid input. Please enter a number.[/red]")

        Prompt.ask("Press Enter to continue")

    def _customize_agent_template(self, agents: List[AgentConfig]) -> None:
        """Customize agent JSON template."""
        agent_id = Prompt.ask("Enter agent ID to customize")

        try:
            idx = int(agent_id) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]
                self._edit_agent_template(agent)
            else:
                self.console.print("[red]Invalid agent ID.[/red]")
                Prompt.ask("Press Enter to continue")
        except ValueError:
            self.console.print("[red]Invalid input. Please enter a number.[/red]")
            Prompt.ask("Press Enter to continue")

    def _edit_agent_template(self, agent: AgentConfig) -> None:
        """Edit an agent's JSON template."""
        self.console.clear()
        self.console.print(f"[bold]Editing template for: {agent.name}[/bold]\n")

        # Get current template
        template_path = self._get_agent_template_path(agent.name)

        if template_path.exists():
            with template_path.open() as f:
                template = json.load(f)
            is_system = str(template_path).startswith(
                str(self.agent_manager.templates_dir)
            )
        else:
            # Create a minimal template structure based on system templates
            template = {
                "schema_version": "1.2.0",
                "agent_id": agent.name,
                "agent_version": "1.0.0",
                "agent_type": agent.name.replace("-", "_"),
                "metadata": {
                    "name": agent.name.replace("-", " ").title() + " Agent",
                    "description": agent.description,
                    "tags": [agent.name],
                    "author": "Custom",
                    "created_at": "",
                    "updated_at": "",
                },
                "capabilities": {
                    "model": "opus",
                    "tools": (
                        agent.dependencies
                        if agent.dependencies
                        else ["Read", "Write", "Edit", "Bash"]
                    ),
                },
                "instructions": {
                    "base_template": "BASE_AGENT_TEMPLATE.md",
                    "custom_instructions": "",
                },
            }
            is_system = False

        # Display current template
        if is_system:
            self.console.print(
                "[yellow]Viewing SYSTEM template (read-only). Customization will create a local copy.[/yellow]\n"
            )

        self.console.print("[bold]Current Template:[/bold]")
        # Truncate for display if too large
        display_template = template.copy()
        if (
            "instructions" in display_template
            and isinstance(display_template["instructions"], dict)
            and (
                "custom_instructions" in display_template["instructions"]
                and len(str(display_template["instructions"]["custom_instructions"]))
                > 200
            )
        ):
            display_template["instructions"]["custom_instructions"] = (
                display_template["instructions"]["custom_instructions"][:200] + "..."
            )

        json_str = json.dumps(display_template, indent=2)
        # Limit display to first 50 lines for readability
        lines = json_str.split("\n")
        if len(lines) > 50:
            json_str = "\n".join(lines[:50]) + "\n... (truncated for display)"

        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        self.console.print(syntax)
        self.console.print()

        # Editing options
        self.console.print("[bold]Editing Options:[/bold]")
        if not is_system:
            self.console.print("  [cyan][1][/cyan] Edit in external editor")
            self.console.print("  [cyan][2][/cyan] Add/modify a field")
            self.console.print("  [cyan][3][/cyan] Remove a field")
            self.console.print("  [cyan][4][/cyan] Reset to defaults")
        else:
            self.console.print("  [cyan][1][/cyan] Create customized copy")
            self.console.print("  [cyan][2][/cyan] View full template")
        self.console.print("  [cyan][b][/cyan] Back")
        self.console.print()

        choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="b")

        if is_system:
            if choice == "1":
                # Create a customized copy
                self._create_custom_template_copy(agent, template)
            elif choice == "2":
                # View full template
                self._view_full_template(template)
        elif choice == "1":
            self._edit_in_external_editor(template_path, template)
        elif choice == "2":
            self._modify_template_field(template, template_path)
        elif choice == "3":
            self._remove_template_field(template, template_path)
        elif choice == "4":
            self._reset_template(agent, template_path)

        if choice != "b":
            Prompt.ask("Press Enter to continue")

    def _get_agent_template_path(self, agent_name: str) -> Path:
        """Get the path to an agent's template file."""
        # First check for custom template in project/user config
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm" / "agents"
        else:
            config_dir = Path.home() / ".claude-mpm" / "agents"

        config_dir.mkdir(parents=True, exist_ok=True)
        custom_template = config_dir / f"{agent_name}.json"

        # If custom template exists, return it
        if custom_template.exists():
            return custom_template

        # Otherwise, look for the system template
        # Handle various naming conventions
        possible_names = [
            f"{agent_name}.json",
            f"{agent_name.replace('-', '_')}.json",
            f"{agent_name}-agent.json",
            f"{agent_name.replace('-', '_')}_agent.json",
        ]

        for name in possible_names:
            system_template = self.agent_manager.templates_dir / name
            if system_template.exists():
                return system_template

        # Return the custom template path for new templates
        return custom_template

    def _edit_in_external_editor(self, template_path: Path, template: Dict) -> None:
        """Open template in external editor."""
        import subprocess
        import tempfile

        # Write current template to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(template, f, indent=2)
            temp_path = f.name

        # Get editor from environment
        editor = os.environ.get("EDITOR", "nano")

        try:
            # Open in editor
            subprocess.call([editor, temp_path])

            # Read back the edited content
            with temp_path.open() as f:
                new_template = json.load(f)

            # Save to actual template path
            with template_path.open("w") as f:
                json.dump(new_template, f, indent=2)

            self.console.print("[green]Template updated successfully![/green]")

        except Exception as e:
            self.console.print(f"[red]Error editing template: {e}[/red]")
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def _modify_template_field(self, template: Dict, template_path: Path) -> None:
        """Add or modify a field in the template."""
        field_name = Prompt.ask(
            "Enter field name (use dot notation for nested, e.g., 'config.timeout')"
        )
        field_value = Prompt.ask("Enter field value (JSON format)")

        try:
            # Parse the value as JSON
            value = json.loads(field_value)

            # Navigate to the field location
            parts = field_name.split(".")
            current = template

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value
            current[parts[-1]] = value

            # Save the template
            with template_path.open("w") as f:
                json.dump(template, f, indent=2)

            self.console.print(
                f"[green]Field '{field_name}' updated successfully![/green]"
            )

        except json.JSONDecodeError:
            self.console.print("[red]Invalid JSON value. Please try again.[/red]")
        except Exception as e:
            self.console.print(f"[red]Error updating field: {e}[/red]")

    def _remove_template_field(self, template: Dict, template_path: Path) -> None:
        """Remove a field from the template."""
        field_name = Prompt.ask(
            "Enter field name to remove (use dot notation for nested)"
        )

        try:
            # Navigate to the field location
            parts = field_name.split(".")
            current = template

            for part in parts[:-1]:
                if part not in current:
                    raise KeyError(f"Field '{field_name}' not found")
                current = current[part]

            # Remove the field
            if parts[-1] in current:
                del current[parts[-1]]

                # Save the template
                with template_path.open("w") as f:
                    json.dump(template, f, indent=2)

                self.console.print(
                    f"[green]Field '{field_name}' removed successfully![/green]"
                )
            else:
                self.console.print(f"[red]Field '{field_name}' not found.[/red]")

        except Exception as e:
            self.console.print(f"[red]Error removing field: {e}[/red]")

    def _reset_template(self, agent: AgentConfig, template_path: Path) -> None:
        """Reset template to defaults."""
        if Confirm.ask(f"[yellow]Reset '{agent.name}' template to defaults?[/yellow]"):
            # Remove custom template file
            template_path.unlink(missing_ok=True)
            self.console.print(
                f"[green]Template for '{agent.name}' reset to defaults![/green]"
            )

    def _create_custom_template_copy(self, agent: AgentConfig, template: Dict) -> None:
        """Create a customized copy of a system template."""
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm" / "agents"
        else:
            config_dir = Path.home() / ".claude-mpm" / "agents"

        config_dir.mkdir(parents=True, exist_ok=True)
        custom_path = config_dir / f"{agent.name}.json"

        if custom_path.exists() and not Confirm.ask(
            "[yellow]Custom template already exists. Overwrite?[/yellow]"
        ):
            return

        # Save the template copy
        with custom_path.open("w") as f:
            json.dump(template, f, indent=2)

        self.console.print(f"[green]Created custom template at: {custom_path}[/green]")
        self.console.print("[green]You can now edit this template.[/green]")

    def _view_full_template(self, template: Dict) -> None:
        """View the full template without truncation."""
        self.console.clear()
        self.console.print("[bold]Full Template View:[/bold]\n")

        json_str = json.dumps(template, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)

        # Use pager for long content

        with self.console.pager():
            self.console.print(syntax)

    def _view_agent_details(self, agents: List[AgentConfig]) -> None:
        """View detailed information about an agent."""
        agent_id = Prompt.ask("Enter agent ID to view")

        try:
            idx = int(agent_id) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]

                self.console.clear()
                self._display_header()

                # Try to load full template for more details
                template_path = self._get_agent_template_path(agent.name)
                extra_info = ""

                if template_path.exists():
                    try:
                        with template_path.open() as f:
                            template = json.load(f)

                        # Extract additional information
                        metadata = template.get("metadata", {})
                        capabilities = template.get("capabilities", {})

                        # Get full description if available
                        full_desc = metadata.get("description", agent.description)

                        # Get model and tools
                        model = capabilities.get("model", "default")
                        tools = capabilities.get("tools", [])

                        # Get tags
                        tags = metadata.get("tags", [])

                        # Get version info
                        agent_version = template.get("agent_version", "N/A")
                        schema_version = template.get("schema_version", "N/A")

                        extra_info = f"""
[bold]Full Description:[/bold]
{full_desc}

[bold]Model:[/bold] {model}
[bold]Agent Version:[/bold] {agent_version}
[bold]Schema Version:[/bold] {schema_version}
[bold]Tags:[/bold] {', '.join(tags) if tags else 'None'}
[bold]Tools:[/bold] {', '.join(tools[:5]) if tools else 'None'}{'...' if len(tools) > 5 else ''}
"""
                    except Exception:
                        pass

                # Create detail panel
                detail_text = f"""
[bold]Name:[/bold] {agent.name}
[bold]Status:[/bold] {'[green]Enabled[/green]' if self.agent_manager.is_agent_enabled(agent.name) else '[red]Disabled[/red]'}
[bold]Template Path:[/bold] {template_path}
[bold]Is System Template:[/bold] {'Yes' if str(template_path).startswith(str(self.agent_manager.templates_dir)) else 'No (Custom)'}
{extra_info}
                """

                panel = Panel(
                    detail_text.strip(),
                    title=f"[bold]{agent.name} Details[/bold]",
                    box=ROUNDED,
                    style="cyan",
                )

                self.console.print(panel)

            else:
                self.console.print("[red]Invalid agent ID.[/red]")

        except ValueError:
            self.console.print("[red]Invalid input. Please enter a number.[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _edit_templates(self) -> None:
        """Template editing interface."""
        self.console.print("[yellow]Template editing interface - Coming soon![/yellow]")
        Prompt.ask("Press Enter to continue")

    def _manage_behaviors(self) -> None:
        """Behavior file management interface."""
        while True:
            self.console.clear()
            self._display_header()

            self.console.print("[bold]Behavior File Management[/bold]\n")

            # Display current behavior files
            self._display_behavior_files()

            # Show behavior menu
            self.console.print("\n[bold]Options:[/bold]")
            self.console.print("  [cyan][1][/cyan] Edit identity configuration")
            self.console.print("  [cyan][2][/cyan] Edit workflow configuration")
            self.console.print("  [cyan][3][/cyan] Import behavior file")
            self.console.print("  [cyan][4][/cyan] Export behavior file")
            self.console.print("  [cyan][b][/cyan] Back to main menu")
            self.console.print()

            choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="b")

            if choice == "b":
                break
            if choice == "1":
                self._edit_identity_config()
            elif choice == "2":
                self._edit_workflow_config()
            elif choice == "3":
                self._import_behavior_file()
            elif choice == "4":
                self._export_behavior_file()
            else:
                self.console.print("[red]Invalid choice.[/red]")
                Prompt.ask("Press Enter to continue")

    def _display_behavior_files(self) -> None:
        """Display current behavior files."""
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm" / "behaviors"
        else:
            config_dir = Path.home() / ".claude-mpm" / "behaviors"

        config_dir.mkdir(parents=True, exist_ok=True)

        table = Table(title="Behavior Files", box=ROUNDED)
        table.add_column("File", style="cyan", width=30)
        table.add_column("Size", style="dim", width=10)
        table.add_column("Modified", style="white", width=20)

        identity_file = config_dir / "identity.yaml"
        workflow_file = config_dir / "workflow.yaml"

        for file_path in [identity_file, workflow_file]:
            if file_path.exists():
                stat = file_path.stat()
                size = f"{stat.st_size} bytes"
                modified = f"{stat.st_mtime:.0f}"  # Simplified timestamp
                table.add_row(file_path.name, size, modified)
            else:
                table.add_row(file_path.name, "[dim]Not found[/dim]", "-")

        self.console.print(table)

    def _edit_identity_config(self) -> None:
        """Edit identity configuration."""
        self.console.print(
            "[yellow]Identity configuration editor - Coming soon![/yellow]"
        )
        Prompt.ask("Press Enter to continue")

    def _edit_workflow_config(self) -> None:
        """Edit workflow configuration."""
        self.console.print(
            "[yellow]Workflow configuration editor - Coming soon![/yellow]"
        )
        Prompt.ask("Press Enter to continue")

    def _import_behavior_file(self) -> None:
        """Import a behavior file."""
        file_path = Prompt.ask("Enter path to behavior file to import")

        try:
            source = Path(file_path)
            if not source.exists():
                self.console.print(f"[red]File not found: {file_path}[/red]")
                return

            # Determine target directory
            if self.current_scope == "project":
                config_dir = self.project_dir / ".claude-mpm" / "behaviors"
            else:
                config_dir = Path.home() / ".claude-mpm" / "behaviors"

            config_dir.mkdir(parents=True, exist_ok=True)

            # Copy file
            import shutil

            target = config_dir / source.name
            shutil.copy2(source, target)

            self.console.print(f"[green]Successfully imported {source.name}![/green]")

        except Exception as e:
            self.console.print(f"[red]Error importing file: {e}[/red]")

        Prompt.ask("Press Enter to continue")

    def _export_behavior_file(self) -> None:
        """Export a behavior file."""
        self.console.print("[yellow]Behavior file export - Coming soon![/yellow]")
        Prompt.ask("Press Enter to continue")

    def _manage_startup_configuration(self) -> bool:
        """Manage startup configuration for MCP services and agents.

        Returns:
            bool: True if user saved and wants to proceed to startup, False otherwise
        """
        # Temporarily suppress INFO logging during Config initialization
        import logging

        root_logger = logging.getLogger("claude_mpm")
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)

        try:
            # Load current configuration ONCE at the start
            config = Config()
            startup_config = self._load_startup_configuration(config)
        finally:
            # Restore original logging level
            root_logger.setLevel(original_level)

        proceed_to_startup = False
        while True:
            self.console.clear()
            self._display_header()

            self.console.print("[bold]Startup Configuration Management[/bold]\n")
            self.console.print(
                "[dim]Configure which MCP services, hook services, and system agents "
                "are enabled when Claude MPM starts.[/dim]\n"
            )

            # Display current configuration (using in-memory state)
            self._display_startup_configuration(startup_config)

            # Show menu options
            self.console.print("\n[bold]Options:[/bold]")
            self.console.print("  [cyan]1[/cyan] - Configure MCP Services")
            self.console.print("  [cyan]2[/cyan] - Configure Hook Services")
            self.console.print("  [cyan]3[/cyan] - Configure System Agents")
            self.console.print("  [cyan]4[/cyan] - Enable All")
            self.console.print("  [cyan]5[/cyan] - Disable All")
            self.console.print("  [cyan]6[/cyan] - Reset to Defaults")
            self.console.print(
                "  [cyan]s[/cyan] - Save configuration and start claude-mpm"
            )
            self.console.print("  [cyan]b[/cyan] - Cancel and return without saving")
            self.console.print()

            choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="s")

            if choice == "b":
                break
            if choice == "1":
                self._configure_mcp_services(startup_config, config)
            elif choice == "2":
                self._configure_hook_services(startup_config, config)
            elif choice == "3":
                self._configure_system_agents(startup_config, config)
            elif choice == "4":
                self._enable_all_services(startup_config, config)
            elif choice == "5":
                self._disable_all_services(startup_config, config)
            elif choice == "6":
                self._reset_to_defaults(startup_config, config)
            elif choice == "s":
                # Save and exit if successful
                if self._save_startup_configuration(startup_config, config):
                    proceed_to_startup = True
                    break
            else:
                self.console.print("[red]Invalid choice.[/red]")
                Prompt.ask("Press Enter to continue")

        return proceed_to_startup

    def _load_startup_configuration(self, config: Config) -> Dict:
        """Load current startup configuration from config."""
        startup_config = config.get("startup", {})

        # Ensure all required sections exist
        if "enabled_mcp_services" not in startup_config:
            # Get available MCP services from MCPConfigManager
            mcp_manager = MCPConfigManager()
            available_services = list(mcp_manager.STATIC_MCP_CONFIGS.keys())
            startup_config["enabled_mcp_services"] = available_services.copy()

        if "enabled_hook_services" not in startup_config:
            # Default hook services (health-monitor enabled by default)
            startup_config["enabled_hook_services"] = [
                "monitor",
                "dashboard",
                "response-logger",
                "health-monitor",
            ]

        if "disabled_agents" not in startup_config:
            # NEW LOGIC: Track DISABLED agents instead of enabled
            # By default, NO agents are disabled (all agents enabled)
            startup_config["disabled_agents"] = []

        return startup_config

    def _display_startup_configuration(self, startup_config: Dict) -> None:
        """Display current startup configuration in a table."""
        table = Table(
            title="Current Startup Configuration", box=ROUNDED, show_lines=True
        )

        table.add_column("Category", style="cyan", width=20)
        table.add_column("Enabled Services", style="white", width=50)
        table.add_column("Count", style="dim", width=10)

        # MCP Services
        mcp_services = startup_config.get("enabled_mcp_services", [])
        mcp_display = ", ".join(mcp_services[:3]) + (
            "..." if len(mcp_services) > 3 else ""
        )
        table.add_row(
            "MCP Services",
            mcp_display if mcp_services else "[dim]None[/dim]",
            str(len(mcp_services)),
        )

        # Hook Services
        hook_services = startup_config.get("enabled_hook_services", [])
        hook_display = ", ".join(hook_services[:3]) + (
            "..." if len(hook_services) > 3 else ""
        )
        table.add_row(
            "Hook Services",
            hook_display if hook_services else "[dim]None[/dim]",
            str(len(hook_services)),
        )

        # System Agents - show count of ENABLED agents (total - disabled)
        all_agents = self.agent_manager.discover_agents() if self.agent_manager else []
        disabled_agents = startup_config.get("disabled_agents", [])
        enabled_count = len(all_agents) - len(disabled_agents)

        # Show first few enabled agent names
        enabled_names = [a.name for a in all_agents if a.name not in disabled_agents]
        agent_display = ", ".join(enabled_names[:3]) + (
            "..." if len(enabled_names) > 3 else ""
        )
        table.add_row(
            "System Agents",
            agent_display if enabled_names else "[dim]All Disabled[/dim]",
            f"{enabled_count}/{len(all_agents)}",
        )

        self.console.print(table)

    def _configure_mcp_services(self, startup_config: Dict, config: Config) -> None:
        """Configure which MCP services to enable at startup."""
        self.console.clear()
        self._display_header()
        self.console.print("[bold]Configure MCP Services[/bold]\n")

        # Get available MCP services
        mcp_manager = MCPConfigManager()
        available_services = list(mcp_manager.STATIC_MCP_CONFIGS.keys())
        enabled_services = set(startup_config.get("enabled_mcp_services", []))

        # Display services with checkboxes
        table = Table(box=ROUNDED, show_lines=True)
        table.add_column("ID", style="dim", width=5)
        table.add_column("Service", style="cyan", width=25)
        table.add_column("Status", width=15)
        table.add_column("Description", style="white", width=45)

        service_descriptions = {
            "kuzu-memory": "Graph-based memory system for agents",
            "mcp-ticketer": "Ticket and issue tracking integration",
            "mcp-browser": "Browser automation and web scraping",
            "mcp-vector-search": "Semantic code search capabilities",
        }

        for idx, service in enumerate(available_services, 1):
            status = (
                "[green]✓ Enabled[/green]"
                if service in enabled_services
                else "[red]✗ Disabled[/red]"
            )
            description = service_descriptions.get(service, "MCP service")
            table.add_row(str(idx), service, status, description)

        self.console.print(table)
        self.console.print("\n[bold]Commands:[/bold]")
        self.console.print("  Enter service IDs to toggle (e.g., '1,3' or '1-4')")
        self.console.print("  [cyan][a][/cyan] Enable all")
        self.console.print("  [cyan][n][/cyan] Disable all")
        self.console.print("  [cyan][b][/cyan] Back to previous menu")
        self.console.print()

        choice = Prompt.ask("[bold cyan]Toggle services[/bold cyan]", default="b")

        if choice == "b":
            return
        if choice == "a":
            startup_config["enabled_mcp_services"] = available_services.copy()
            self.console.print("[green]All MCP services enabled![/green]")
        elif choice == "n":
            startup_config["enabled_mcp_services"] = []
            self.console.print("[green]All MCP services disabled![/green]")
        else:
            # Parse service IDs
            try:
                selected_ids = self._parse_id_selection(choice, len(available_services))
                for idx in selected_ids:
                    service = available_services[idx - 1]
                    if service in enabled_services:
                        enabled_services.remove(service)
                        self.console.print(f"[red]Disabled {service}[/red]")
                    else:
                        enabled_services.add(service)
                        self.console.print(f"[green]Enabled {service}[/green]")
                startup_config["enabled_mcp_services"] = list(enabled_services)
            except (ValueError, IndexError) as e:
                self.console.print(f"[red]Invalid selection: {e}[/red]")

        Prompt.ask("Press Enter to continue")

    def _configure_hook_services(self, startup_config: Dict, config: Config) -> None:
        """Configure which hook services to enable at startup."""
        self.console.clear()
        self._display_header()
        self.console.print("[bold]Configure Hook Services[/bold]\n")

        # Available hook services
        available_services = [
            ("monitor", "Real-time event monitoring server (SocketIO)"),
            ("dashboard", "Web-based dashboard interface"),
            ("response-logger", "Agent response logging"),
            ("health-monitor", "Service health and recovery monitoring"),
        ]

        enabled_services = set(startup_config.get("enabled_hook_services", []))

        # Display services with checkboxes
        table = Table(box=ROUNDED, show_lines=True)
        table.add_column("ID", style="dim", width=5)
        table.add_column("Service", style="cyan", width=25)
        table.add_column("Status", width=15)
        table.add_column("Description", style="white", width=45)

        for idx, (service, description) in enumerate(available_services, 1):
            status = (
                "[green]✓ Enabled[/green]"
                if service in enabled_services
                else "[red]✗ Disabled[/red]"
            )
            table.add_row(str(idx), service, status, description)

        self.console.print(table)
        self.console.print("\n[bold]Commands:[/bold]")
        self.console.print("  Enter service IDs to toggle (e.g., '1,3' or '1-4')")
        self.console.print("  [cyan][a][/cyan] Enable all")
        self.console.print("  [cyan][n][/cyan] Disable all")
        self.console.print("  [cyan][b][/cyan] Back to previous menu")
        self.console.print()

        choice = Prompt.ask("[bold cyan]Toggle services[/bold cyan]", default="b")

        if choice == "b":
            return
        if choice == "a":
            startup_config["enabled_hook_services"] = [s[0] for s in available_services]
            self.console.print("[green]All hook services enabled![/green]")
        elif choice == "n":
            startup_config["enabled_hook_services"] = []
            self.console.print("[green]All hook services disabled![/green]")
        else:
            # Parse service IDs
            try:
                selected_ids = self._parse_id_selection(choice, len(available_services))
                for idx in selected_ids:
                    service = available_services[idx - 1][0]
                    if service in enabled_services:
                        enabled_services.remove(service)
                        self.console.print(f"[red]Disabled {service}[/red]")
                    else:
                        enabled_services.add(service)
                        self.console.print(f"[green]Enabled {service}[/green]")
                startup_config["enabled_hook_services"] = list(enabled_services)
            except (ValueError, IndexError) as e:
                self.console.print(f"[red]Invalid selection: {e}[/red]")

        Prompt.ask("Press Enter to continue")

    def _configure_system_agents(self, startup_config: Dict, config: Config) -> None:
        """Configure which system agents to deploy at startup.

        NEW LOGIC: Uses disabled_agents list. All agents from templates are enabled by default.
        """
        while True:
            self.console.clear()
            self._display_header()
            self.console.print("[bold]Configure System Agents[/bold]\n")
            self.console.print(
                "[dim]All agents discovered from templates are enabled by default. "
                "Mark agents as disabled to prevent deployment.[/dim]\n"
            )

            # Discover available agents from template files
            agents = self.agent_manager.discover_agents()
            disabled_agents = set(startup_config.get("disabled_agents", []))

            # Display agents with checkboxes
            table = Table(box=ROUNDED, show_lines=True)
            table.add_column("ID", style="dim", width=5)
            table.add_column("Agent", style="cyan", width=25)
            table.add_column("Status", width=15)
            table.add_column("Description", style="white", width=45)

            for idx, agent in enumerate(agents, 1):
                # Agent is ENABLED if NOT in disabled list
                is_enabled = agent.name not in disabled_agents
                status = (
                    "[green]✓ Enabled[/green]"
                    if is_enabled
                    else "[red]✗ Disabled[/red]"
                )
                desc_display = (
                    agent.description[:42] + "..."
                    if len(agent.description) > 42
                    else agent.description
                )
                table.add_row(str(idx), agent.name, status, desc_display)

            self.console.print(table)
            self.console.print("\n[bold]Commands:[/bold]")
            self.console.print("  Enter agent IDs to toggle (e.g., '1,3' or '1-4')")
            self.console.print("  [cyan]a[/cyan] - Enable all (clear disabled list)")
            self.console.print("  [cyan]n[/cyan] - Disable all")
            self.console.print("  [cyan]b[/cyan] - Back to previous menu")
            self.console.print()

            choice = Prompt.ask("[bold cyan]Select option[/bold cyan]", default="b")

            if choice == "b":
                return
            if choice == "a":
                # Enable all = empty disabled list
                startup_config["disabled_agents"] = []
                self.console.print("[green]All agents enabled![/green]")
                Prompt.ask("Press Enter to continue")
            elif choice == "n":
                # Disable all = all agents in disabled list
                startup_config["disabled_agents"] = [agent.name for agent in agents]
                self.console.print("[green]All agents disabled![/green]")
                Prompt.ask("Press Enter to continue")
            else:
                # Parse agent IDs
                try:
                    selected_ids = self._parse_id_selection(choice, len(agents))
                    for idx in selected_ids:
                        agent = agents[idx - 1]
                        if agent.name in disabled_agents:
                            # Currently disabled, enable it (remove from disabled list)
                            disabled_agents.remove(agent.name)
                            self.console.print(f"[green]Enabled {agent.name}[/green]")
                        else:
                            # Currently enabled, disable it (add to disabled list)
                            disabled_agents.add(agent.name)
                            self.console.print(f"[red]Disabled {agent.name}[/red]")
                    startup_config["disabled_agents"] = list(disabled_agents)
                    # Refresh the display to show updated status immediately
                except (ValueError, IndexError) as e:
                    self.console.print(f"[red]Invalid selection: {e}[/red]")
                    Prompt.ask("Press Enter to continue")

    def _parse_id_selection(self, selection: str, max_id: int) -> List[int]:
        """Parse ID selection string (e.g., '1,3,5' or '1-4')."""
        ids = set()
        parts = selection.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                # Range selection
                start, end = part.split("-")
                start_id = int(start.strip())
                end_id = int(end.strip())
                if start_id < 1 or end_id > max_id or start_id > end_id:
                    raise ValueError(f"Invalid range: {part}")
                ids.update(range(start_id, end_id + 1))
            else:
                # Single ID
                id_num = int(part)
                if id_num < 1 or id_num > max_id:
                    raise ValueError(f"Invalid ID: {id_num}")
                ids.add(id_num)

        return sorted(ids)

    def _enable_all_services(self, startup_config: Dict, config: Config) -> None:
        """Enable all services and agents."""
        if Confirm.ask("[yellow]Enable ALL services and agents?[/yellow]"):
            # Enable all MCP services
            mcp_manager = MCPConfigManager()
            startup_config["enabled_mcp_services"] = list(
                mcp_manager.STATIC_MCP_CONFIGS.keys()
            )

            # Enable all hook services
            startup_config["enabled_hook_services"] = [
                "monitor",
                "dashboard",
                "response-logger",
                "health-monitor",
            ]

            # Enable all agents (empty disabled list)
            startup_config["disabled_agents"] = []

            self.console.print("[green]All services and agents enabled![/green]")
            Prompt.ask("Press Enter to continue")

    def _disable_all_services(self, startup_config: Dict, config: Config) -> None:
        """Disable all services and agents."""
        if Confirm.ask("[yellow]Disable ALL services and agents?[/yellow]"):
            startup_config["enabled_mcp_services"] = []
            startup_config["enabled_hook_services"] = []
            # Disable all agents = add all to disabled list
            agents = self.agent_manager.discover_agents()
            startup_config["disabled_agents"] = [agent.name for agent in agents]

            self.console.print("[green]All services and agents disabled![/green]")
            self.console.print(
                "[yellow]Note: You may need to enable at least some services for Claude MPM to function properly.[/yellow]"
            )
            Prompt.ask("Press Enter to continue")

    def _reset_to_defaults(self, startup_config: Dict, config: Config) -> None:
        """Reset startup configuration to defaults."""
        if Confirm.ask("[yellow]Reset startup configuration to defaults?[/yellow]"):
            # Reset to default values
            mcp_manager = MCPConfigManager()
            startup_config["enabled_mcp_services"] = list(
                mcp_manager.STATIC_MCP_CONFIGS.keys()
            )
            startup_config["enabled_hook_services"] = [
                "monitor",
                "dashboard",
                "response-logger",
                "health-monitor",
            ]
            # Default: All agents enabled (empty disabled list)
            startup_config["disabled_agents"] = []

            self.console.print(
                "[green]Startup configuration reset to defaults![/green]"
            )
            Prompt.ask("Press Enter to continue")

    def _save_startup_configuration(self, startup_config: Dict, config: Config) -> bool:
        """Save startup configuration to config file and return whether to proceed to startup.

        Returns:
            bool: True if should proceed to startup, False to continue in menu
        """
        try:
            # Update the startup configuration
            config.set("startup", startup_config)

            # IMPORTANT: Also update agent_deployment.disabled_agents so the deployment
            # system actually uses the configured disabled agents list
            config.set(
                "agent_deployment.disabled_agents",
                startup_config.get("disabled_agents", []),
            )

            # Determine config file path
            if self.current_scope == "project":
                config_file = self.project_dir / ".claude-mpm" / "configuration.yaml"
            else:
                config_file = Path.home() / ".claude-mpm" / "configuration.yaml"

            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Temporarily suppress INFO logging to avoid duplicate save messages
            import logging

            root_logger = logging.getLogger("claude_mpm")
            original_level = root_logger.level
            root_logger.setLevel(logging.WARNING)

            try:
                # Save configuration (this will log at INFO level which we've suppressed)
                config.save(config_file, format="yaml")
            finally:
                # Restore original logging level
                root_logger.setLevel(original_level)

            self.console.print(
                f"[green]✓ Startup configuration saved to {config_file}[/green]"
            )
            self.console.print(
                "\n[cyan]Applying configuration and launching Claude MPM...[/cyan]\n"
            )

            # Launch claude-mpm run command to get full startup cycle
            # This ensures:
            # 1. Configuration is loaded
            # 2. Enabled agents are deployed
            # 3. Disabled agents are removed from .claude/agents/
            # 4. MCP services and hooks are started
            try:
                # Use execvp to replace the current process with claude-mpm run
                # This ensures a clean transition from configurator to Claude MPM
                os.execvp("claude-mpm", ["claude-mpm", "run"])
            except Exception as e:
                self.console.print(
                    f"[yellow]Could not launch Claude MPM automatically: {e}[/yellow]"
                )
                self.console.print(
                    "[cyan]Please run 'claude-mpm' manually to start.[/cyan]"
                )
                Prompt.ask("Press Enter to continue")
                return True

            # This line will never be reached if execvp succeeds
            return True

        except Exception as e:
            self.console.print(f"[red]Error saving configuration: {e}[/red]")
            Prompt.ask("Press Enter to continue")
            return False

    def _switch_scope(self) -> None:
        """Switch between project and user scope."""
        self.current_scope = "user" if self.current_scope == "project" else "project"
        self.console.print(f"[green]Switched to {self.current_scope} scope[/green]")
        Prompt.ask("Press Enter to continue")

    def _show_version_info_interactive(self) -> None:
        """Show version information in interactive mode."""
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
                import subprocess

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

    # Non-interactive command methods

    def _list_agents_non_interactive(self) -> CommandResult:
        """List agents in non-interactive mode."""
        agents = self.agent_manager.discover_agents()

        data = []
        for agent in agents:
            data.append(
                {
                    "name": agent.name,
                    "enabled": self.agent_manager.is_agent_enabled(agent.name),
                    "description": agent.description,
                    "dependencies": agent.dependencies,
                }
            )

        # Print as JSON for scripting
        print(json.dumps(data, indent=2))

        return CommandResult.success_result("Agents listed", data={"agents": data})

    def _enable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Enable an agent in non-interactive mode."""
        try:
            self.agent_manager.set_agent_enabled(agent_name, True)
            return CommandResult.success_result(f"Agent '{agent_name}' enabled")
        except Exception as e:
            return CommandResult.error_result(f"Failed to enable agent: {e}")

    def _disable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Disable an agent in non-interactive mode."""
        try:
            self.agent_manager.set_agent_enabled(agent_name, False)
            return CommandResult.success_result(f"Agent '{agent_name}' disabled")
        except Exception as e:
            return CommandResult.error_result(f"Failed to disable agent: {e}")

    def _export_config(self, file_path: str) -> CommandResult:
        """Export configuration to a file."""
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

    def _import_config(self, file_path: str) -> CommandResult:
        """Import configuration from a file."""
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

    def _show_version_info(self) -> CommandResult:
        """Show version information in non-interactive mode."""
        mpm_version = self.version_service.get_version()
        build_number = self.version_service.get_build_number()

        data = {
            "mpm_version": mpm_version,
            "build_number": build_number,
            "python_version": sys.version.split()[0],
        }

        # Try to get Claude version
        try:
            import subprocess

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

    def _install_hooks(self, force: bool = False) -> CommandResult:
        """Install Claude MPM hooks for Claude Code integration."""
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()

            # Check Claude Code version compatibility first
            is_compatible, version_message = installer.is_version_compatible()
            self.console.print("[cyan]Checking Claude Code version...[/cyan]")
            self.console.print(version_message)

            if not is_compatible:
                self.console.print(
                    "\n[yellow]⚠ Hook monitoring is not available for your Claude Code version.[/yellow]"
                )
                self.console.print(
                    "The dashboard and other features will work without real-time monitoring."
                )
                self.console.print(
                    f"\n[dim]To enable monitoring, upgrade Claude Code to version {installer.MIN_CLAUDE_VERSION} or higher.[/dim]"
                )
                return CommandResult.success_result(
                    "Version incompatible with hook monitoring",
                    data={"compatible": False, "message": version_message},
                )

            # Check current status
            status = installer.get_status()
            if status["installed"] and not force:
                self.console.print("[yellow]Hooks are already installed.[/yellow]")
                self.console.print("Use --force to reinstall.")

                if not status["valid"]:
                    self.console.print("\n[red]However, there are issues:[/red]")
                    for issue in status["issues"]:
                        self.console.print(f"  - {issue}")

                return CommandResult.success_result(
                    "Hooks already installed", data=status
                )

            # Install hooks
            self.console.print("[cyan]Installing Claude MPM hooks...[/cyan]")
            success = installer.install_hooks(force=force)

            if success:
                self.console.print("[green]✓ Hooks installed successfully![/green]")
                self.console.print("\nYou can now use /mpm commands in Claude Code:")
                self.console.print("  /mpm         - Show help")
                self.console.print("  /mpm status  - Show claude-mpm status")

                # Verify installation
                is_valid, issues = installer.verify_hooks()
                if not is_valid:
                    self.console.print(
                        "\n[yellow]Warning: Installation completed but verification found issues:[/yellow]"
                    )
                    for issue in issues:
                        self.console.print(f"  - {issue}")

                return CommandResult.success_result("Hooks installed successfully")
            self.console.print("[red]✗ Hook installation failed[/red]")
            return CommandResult.error_result("Hook installation failed")

        except ImportError:
            self.console.print("[red]Error: HookInstaller module not found[/red]")
            self.console.print("Please ensure claude-mpm is properly installed.")
            return CommandResult.error_result("HookInstaller module not found")
        except Exception as e:
            self.logger.error(f"Hook installation error: {e}", exc_info=True)
            return CommandResult.error_result(f"Hook installation failed: {e}")

    def _verify_hooks(self) -> CommandResult:
        """Verify that Claude MPM hooks are properly installed."""
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()
            status = installer.get_status()

            self.console.print("[bold]Hook Installation Status[/bold]\n")

            # Show Claude Code version and compatibility
            if status.get("claude_version"):
                self.console.print(f"Claude Code Version: {status['claude_version']}")
                if status.get("version_compatible"):
                    self.console.print(
                        "[green]✓[/green] Version compatible with hook monitoring"
                    )
                else:
                    self.console.print(
                        f"[yellow]⚠[/yellow] {status.get('version_message', 'Version incompatible')}"
                    )
                    self.console.print()
            else:
                self.console.print(
                    "[yellow]Claude Code version could not be detected[/yellow]"
                )
            self.console.print()

            if status["installed"]:
                self.console.print(
                    f"[green]✓[/green] Hooks installed at: {status['hook_script']}"
                )
            else:
                self.console.print("[red]✗[/red] Hooks not installed")

            if status["settings_file"]:
                self.console.print(
                    f"[green]✓[/green] Settings file: {status['settings_file']}"
                )
            else:
                self.console.print("[red]✗[/red] Settings file not found")

            if status.get("configured_events"):
                self.console.print(
                    f"[green]✓[/green] Configured events: {', '.join(status['configured_events'])}"
                )
            else:
                self.console.print("[red]✗[/red] No events configured")

            if status["valid"]:
                self.console.print("\n[green]All checks passed![/green]")
            else:
                self.console.print("\n[red]Issues found:[/red]")
                for issue in status["issues"]:
                    self.console.print(f"  - {issue}")

            return CommandResult.success_result(
                "Hook verification complete", data=status
            )

        except ImportError:
            self.console.print("[red]Error: HookInstaller module not found[/red]")
            return CommandResult.error_result("HookInstaller module not found")
        except Exception as e:
            self.logger.error(f"Hook verification error: {e}", exc_info=True)
            return CommandResult.error_result(f"Hook verification failed: {e}")

    def _uninstall_hooks(self) -> CommandResult:
        """Uninstall Claude MPM hooks."""
        try:
            from ...hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()

            # Confirm uninstallation
            if not Confirm.ask(
                "[yellow]Are you sure you want to uninstall Claude MPM hooks?[/yellow]"
            ):
                return CommandResult.success_result("Uninstallation cancelled")

            self.console.print("[cyan]Uninstalling Claude MPM hooks...[/cyan]")
            success = installer.uninstall_hooks()

            if success:
                self.console.print("[green]✓ Hooks uninstalled successfully![/green]")
                return CommandResult.success_result("Hooks uninstalled successfully")
            self.console.print("[red]✗ Hook uninstallation failed[/red]")
            return CommandResult.error_result("Hook uninstallation failed")

        except ImportError:
            self.console.print("[red]Error: HookInstaller module not found[/red]")
            return CommandResult.error_result("HookInstaller module not found")
        except Exception as e:
            self.logger.error(f"Hook uninstallation error: {e}", exc_info=True)
            return CommandResult.error_result(f"Hook uninstallation failed: {e}")

    def _run_agent_management(self) -> CommandResult:
        """Jump directly to agent management."""
        try:
            self._manage_agents()
            return CommandResult.success_result("Agent management completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Agent management cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Agent management failed: {e}")

    def _run_template_editing(self) -> CommandResult:
        """Jump directly to template editing."""
        try:
            self._edit_templates()
            return CommandResult.success_result("Template editing completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Template editing cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Template editing failed: {e}")

    def _run_behavior_management(self) -> CommandResult:
        """Jump directly to behavior management."""
        try:
            self._manage_behaviors()
            return CommandResult.success_result("Behavior management completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Behavior management cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Behavior management failed: {e}")

    def _run_startup_configuration(self) -> CommandResult:
        """Jump directly to startup configuration."""
        try:
            proceed = self._manage_startup_configuration()
            if proceed:
                return CommandResult.success_result(
                    "Startup configuration saved, proceeding to startup"
                )
            return CommandResult.success_result("Startup configuration completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Startup configuration cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Startup configuration failed: {e}")


def manage_configure(args) -> int:
    """Main entry point for configuration management command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = ConfigureCommand()
    result = command.execute(args)

    # Print result if needed
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code
