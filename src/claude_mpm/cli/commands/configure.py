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
from .agent_state_manager import SimpleAgentManager
from .configure_agent_display import AgentDisplay
from .configure_behavior_manager import BehaviorManager
from .configure_hook_manager import HookManager
from .configure_models import AgentConfig
from .configure_navigation import ConfigNavigation
from .configure_paths import get_agent_template_path, get_config_directory
from .configure_persistence import ConfigPersistence
from .configure_validators import validate_args as validate_configure_args
from .configure_validators import parse_id_selection


class ConfigureCommand(BaseCommand):
    """Interactive configuration management command."""

    def __init__(self):
        super().__init__("configure")
        self.console = default_console
        self.version_service = VersionService()
        self.current_scope = "project"
        self.project_dir = Path.cwd()
        self.agent_manager = None
        self.hook_manager = HookManager(self.console)
        self.behavior_manager = None  # Initialized when scope is set
        self._agent_display = None  # Lazy-initialized
        self._persistence = None  # Lazy-initialized
        self._navigation = None  # Lazy-initialized

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        return validate_configure_args(args)

    @property
    def agent_display(self) -> AgentDisplay:
        """Lazy-initialize agent display handler."""
        if self._agent_display is None:
            if self.agent_manager is None:
                raise RuntimeError("agent_manager must be initialized before agent_display")
            self._agent_display = AgentDisplay(
                self.console,
                self.agent_manager,
                self._get_agent_template_path,
                self._display_header
            )
        return self._agent_display

    @property
    def persistence(self) -> ConfigPersistence:
        """Lazy-initialize persistence handler."""
        if self._persistence is None:
            # Note: agent_manager might be None for version_info calls
            self._persistence = ConfigPersistence(
                self.console,
                self.version_service,
                self.agent_manager,  # Can be None for version operations
                self._get_agent_template_path,
                self._display_header,
                self.current_scope,
                self.project_dir
            )
        return self._persistence

    @property
    def navigation(self) -> ConfigNavigation:
        """Lazy-initialize navigation handler."""
        if self._navigation is None:
            self._navigation = ConfigNavigation(self.console, self.project_dir)
            # Sync scope from main command
            self._navigation.current_scope = self.current_scope
        return self._navigation

    def run(self, args) -> CommandResult:
        """Execute the configure command."""
        # Set configuration scope
        self.current_scope = getattr(args, "scope", "project")
        if getattr(args, "project_dir", None):
            self.project_dir = Path(args.project_dir)

        # Initialize agent manager and behavior manager with appropriate config directory
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm"
        else:
            config_dir = Path.home() / ".claude-mpm"
        self.agent_manager = SimpleAgentManager(config_dir)
        self.behavior_manager = BehaviorManager(
            config_dir, self.current_scope, self.console
        )

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
                elif choice == "l":
                    # Check for pending agent changes
                    if self.agent_manager and self.agent_manager.has_pending_changes():
                        should_save = Confirm.ask(
                            "[yellow]You have unsaved agent changes. Save them before launching?[/yellow]",
                            default=True,
                        )
                        if should_save:
                            self.agent_manager.commit_deferred_changes()
                            self.console.print("[green]✓ Agent changes saved[/green]")
                        else:
                            self.agent_manager.discard_deferred_changes()
                            self.console.print(
                                "[yellow]⚠ Agent changes discarded[/yellow]"
                            )

                    # Save all configuration
                    self.console.print("\n[cyan]Saving configuration...[/cyan]")
                    if self._save_all_configuration():
                        # Launch Claude MPM (this will replace the process if successful)
                        self._launch_claude_mpm()
                        # If execvp fails, we'll return here and break
                        break
                    self.console.print(
                        "[red]✗ Failed to save configuration. Not launching.[/red]"
                    )
                    Prompt.ask("\nPress Enter to continue")
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
        # Sync scope to navigation before display
        self.navigation.current_scope = self.current_scope
        self.navigation.display_header()

    def _show_main_menu(self) -> str:
        """Show the main menu and get user choice."""
        # Sync scope to navigation before display
        self.navigation.current_scope = self.current_scope
        return self.navigation.show_main_menu()

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

            # Use Text objects to properly display shortcuts with styling
            text_t = Text("  ")
            text_t.append("[t]", style="cyan bold")
            text_t.append(" Toggle agents (enable/disable multiple)")
            self.console.print(text_t)

            text_c = Text("  ")
            text_c.append("[c]", style="cyan bold")
            text_c.append(" Customize agent template")
            self.console.print(text_c)

            text_v = Text("  ")
            text_v.append("[v]", style="cyan bold")
            text_v.append(" View agent details")
            self.console.print(text_v)

            text_r = Text("  ")
            text_r.append("[r]", style="cyan bold")
            text_r.append(" Reset agent to defaults")
            self.console.print(text_r)

            text_b = Text("  ")
            text_b.append("[b]", style="cyan bold")
            text_b.append(" Back to main menu")
            self.console.print(text_b)

            self.console.print()

            choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="b")

            if choice == "b":
                break
            if choice == "t":
                self._toggle_agents_interactive(agents)
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
        self.agent_display.display_agents_table(agents)

    def _display_agents_with_pending_states(self, agents: List[AgentConfig]) -> None:
        """Display agents table with pending state indicators."""
        self.agent_display.display_agents_with_pending_states(agents)

    def _toggle_agents_interactive(self, agents: List[AgentConfig]) -> None:
        """Interactive multi-agent enable/disable with batch save."""

        # Initialize pending states from current states
        for agent in agents:
            current_state = self.agent_manager.is_agent_enabled(agent.name)
            self.agent_manager.set_agent_enabled_deferred(agent.name, current_state)

        while True:
            # Display table with pending states
            self._display_agents_with_pending_states(agents)

            # Show menu
            self.console.print("\n[bold]Toggle Agent Status:[/bold]")
            text_toggle = Text("  ")
            text_toggle.append("[t]", style="cyan bold")
            text_toggle.append(" Enter agent IDs to toggle (e.g., '1,3,5' or '1-4')")
            self.console.print(text_toggle)

            text_all = Text("  ")
            text_all.append("[a]", style="cyan bold")
            text_all.append(" Enable all agents")
            self.console.print(text_all)

            text_none = Text("  ")
            text_none.append("[n]", style="cyan bold")
            text_none.append(" Disable all agents")
            self.console.print(text_none)

            text_save = Text("  ")
            text_save.append("[s]", style="green bold")
            text_save.append(" Save changes and return")
            self.console.print(text_save)

            text_cancel = Text("  ")
            text_cancel.append("[c]", style="yellow bold")
            text_cancel.append(" Cancel (discard changes)")
            self.console.print(text_cancel)

            choice = (
                Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="s")
                .strip()
                .lower()
            )

            if choice == "s":
                if self.agent_manager.has_pending_changes():
                    self.agent_manager.commit_deferred_changes()
                    self.console.print("[green]✓ Changes saved successfully![/green]")
                else:
                    self.console.print("[yellow]No changes to save.[/yellow]")
                Prompt.ask("Press Enter to continue")
                break
            if choice == "c":
                self.agent_manager.discard_deferred_changes()
                self.console.print("[yellow]Changes discarded.[/yellow]")
                Prompt.ask("Press Enter to continue")
                break
            if choice == "a":
                for agent in agents:
                    self.agent_manager.set_agent_enabled_deferred(agent.name, True)
            elif choice == "n":
                for agent in agents:
                    self.agent_manager.set_agent_enabled_deferred(agent.name, False)
            elif choice == "t" or choice.replace(",", "").replace("-", "").isdigit():
                selected_ids = self._parse_id_selection(
                    choice if choice != "t" else Prompt.ask("Enter IDs"), len(agents)
                )
                for idx in selected_ids:
                    if 1 <= idx <= len(agents):
                        agent = agents[idx - 1]
                        current = self.agent_manager.get_pending_state(agent.name)
                        self.agent_manager.set_agent_enabled_deferred(
                            agent.name, not current
                        )

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
            text_1 = Text("  ")
            text_1.append("[1]", style="cyan bold")
            text_1.append(" Edit in external editor")
            self.console.print(text_1)

            text_2 = Text("  ")
            text_2.append("[2]", style="cyan bold")
            text_2.append(" Add/modify a field")
            self.console.print(text_2)

            text_3 = Text("  ")
            text_3.append("[3]", style="cyan bold")
            text_3.append(" Remove a field")
            self.console.print(text_3)

            text_4 = Text("  ")
            text_4.append("[4]", style="cyan bold")
            text_4.append(" Reset to defaults")
            self.console.print(text_4)
        else:
            text_1 = Text("  ")
            text_1.append("[1]", style="cyan bold")
            text_1.append(" Create customized copy")
            self.console.print(text_1)

            text_2 = Text("  ")
            text_2.append("[2]", style="cyan bold")
            text_2.append(" View full template")
            self.console.print(text_2)

        text_b = Text("  ")
        text_b.append("[b]", style="cyan bold")
        text_b.append(" Back")
        self.console.print(text_b)

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
        return get_agent_template_path(
            agent_name,
            self.current_scope,
            self.project_dir,
            self.agent_manager.templates_dir,
        )

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

    def _reset_agent_defaults(self, agents: List[AgentConfig]) -> None:
        """Reset an agent to default enabled state and remove custom template.

        This method:
        - Prompts for agent ID
        - Resets agent to enabled state
        - Removes any custom template overrides
        - Shows success/error messages
        """
        agent_id = Prompt.ask("Enter agent ID to reset to defaults")

        try:
            idx = int(agent_id) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]

                # Confirm the reset action
                if not Confirm.ask(
                    f"[yellow]Reset '{agent.name}' to defaults? This will:[/yellow]\n"
                    "  - Enable the agent\n"
                    "  - Remove custom template (if any)\n"
                    "[yellow]Continue?[/yellow]"
                ):
                    self.console.print("[yellow]Reset cancelled.[/yellow]")
                    Prompt.ask("Press Enter to continue")
                    return

                # Enable the agent
                self.agent_manager.set_agent_enabled(agent.name, True)

                # Remove custom template if exists
                template_path = self._get_agent_template_path(agent.name)
                if template_path.exists() and not str(template_path).startswith(
                    str(self.agent_manager.templates_dir)
                ):
                    # This is a custom template, remove it
                    template_path.unlink(missing_ok=True)
                    self.console.print(
                        f"[green]✓ Removed custom template for '{agent.name}'[/green]"
                    )

                self.console.print(
                    f"[green]✓ Agent '{agent.name}' reset to defaults![/green]"
                )
                self.console.print(
                    "[dim]Agent is now enabled with system template.[/dim]"
                )
            else:
                self.console.print("[red]Invalid agent ID.[/red]")

        except ValueError:
            self.console.print("[red]Invalid input. Please enter a number.[/red]")

        Prompt.ask("Press Enter to continue")

    def _view_agent_details(self, agents: List[AgentConfig]) -> None:
        """View detailed information about an agent."""
        self.agent_display.view_agent_details(agents)

    def _edit_templates(self) -> None:
        """Template editing interface."""
        self.console.print("[yellow]Template editing interface - Coming soon![/yellow]")
        Prompt.ask("Press Enter to continue")

    def _manage_behaviors(self) -> None:
        """Behavior file management interface."""
        # Note: BehaviorManager handles its own loop and clears screen
        # but doesn't display our header. We'll need to update BehaviorManager
        # to accept a header callback in the future. For now, just delegate.
        self.behavior_manager.manage_behaviors()

    def _display_behavior_files(self) -> None:
        """Display current behavior files."""
        self.behavior_manager.display_behavior_files()

    def _edit_identity_config(self) -> None:
        """Edit identity configuration."""
        self.behavior_manager.edit_identity_config()

    def _edit_workflow_config(self) -> None:
        """Edit workflow configuration."""
        self.behavior_manager.edit_workflow_config()

    def _import_behavior_file(self) -> None:
        """Import a behavior file."""
        self.behavior_manager.import_behavior_file()

    def _export_behavior_file(self) -> None:
        """Export a behavior file."""
        self.behavior_manager.export_behavior_file()

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

        text_a = Text("  ")
        text_a.append("[a]", style="cyan bold")
        text_a.append(" Enable all")
        self.console.print(text_a)

        text_n = Text("  ")
        text_n.append("[n]", style="cyan bold")
        text_n.append(" Disable all")
        self.console.print(text_n)

        text_b = Text("  ")
        text_b.append("[b]", style="cyan bold")
        text_b.append(" Back to previous menu")
        self.console.print(text_b)

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

        text_a = Text("  ")
        text_a.append("[a]", style="cyan bold")
        text_a.append(" Enable all")
        self.console.print(text_a)

        text_n = Text("  ")
        text_n.append("[n]", style="cyan bold")
        text_n.append(" Disable all")
        self.console.print(text_n)

        text_b = Text("  ")
        text_b.append("[b]", style="cyan bold")
        text_b.append(" Back to previous menu")
        self.console.print(text_b)

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
            table.add_column("Description", style="bold cyan", width=45)

            for idx, agent in enumerate(agents, 1):
                # Agent is ENABLED if NOT in disabled list
                is_enabled = agent.name not in disabled_agents
                status = (
                    "[green]✓ Enabled[/green]"
                    if is_enabled
                    else "[red]✗ Disabled[/red]"
                )
                # Format description with bright styling
                if len(agent.description) > 42:
                    desc_display = (
                        f"[cyan]{agent.description[:42]}[/cyan][dim]...[/dim]"
                    )
                else:
                    desc_display = f"[cyan]{agent.description}[/cyan]"
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
        return parse_id_selection(selection, max_id)

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

    def _save_all_configuration(self) -> bool:
        """Save all configuration changes across all contexts.

        Returns:
            bool: True if all saves successful, False otherwise
        """
        try:
            # 1. Save any pending agent changes
            if self.agent_manager and self.agent_manager.has_pending_changes():
                self.agent_manager.commit_deferred_changes()
                self.console.print("[green]✓ Agent changes saved[/green]")

            # 2. Save configuration file
            config = Config()

            # Determine config file path based on scope
            if self.current_scope == "project":
                config_file = self.project_dir / ".claude-mpm" / "configuration.yaml"
            else:
                config_file = Path.home() / ".claude-mpm" / "configuration.yaml"

            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Save with suppressed logging to avoid duplicate messages
            import logging

            root_logger = logging.getLogger("claude_mpm")
            original_level = root_logger.level
            root_logger.setLevel(logging.WARNING)

            try:
                config.save(config_file, format="yaml")
            finally:
                root_logger.setLevel(original_level)

            self.console.print(f"[green]✓ Configuration saved to {config_file}[/green]")
            return True

        except Exception as e:
            self.console.print(f"[red]✗ Error saving configuration: {e}[/red]")
            import traceback

            traceback.print_exc()
            return False

    def _launch_claude_mpm(self) -> None:
        """Launch Claude MPM run command, replacing current process."""
        self.navigation.launch_claude_mpm()

    def _switch_scope(self) -> None:
        """Switch between project and user scope."""
        self.navigation.switch_scope()
        # Sync scope back from navigation
        self.current_scope = self.navigation.current_scope

    def _show_version_info_interactive(self) -> None:
        """Show version information in interactive mode."""
        self.persistence.show_version_info_interactive()

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
        return self.persistence.export_config(file_path)

    def _import_config(self, file_path: str) -> CommandResult:
        """Import configuration from a file."""
        return self.persistence.import_config(file_path)

    def _show_version_info(self) -> CommandResult:
        """Show version information in non-interactive mode."""
        return self.persistence.show_version_info()

    def _install_hooks(self, force: bool = False) -> CommandResult:
        """Install Claude MPM hooks for Claude Code integration."""
        # Share logger with hook manager for consistent error logging
        self.hook_manager.logger = self.logger
        return self.hook_manager.install_hooks(force=force)

    def _verify_hooks(self) -> CommandResult:
        """Verify that Claude MPM hooks are properly installed."""
        # Share logger with hook manager for consistent error logging
        self.hook_manager.logger = self.logger
        return self.hook_manager.verify_hooks()

    def _uninstall_hooks(self) -> CommandResult:
        """Uninstall Claude MPM hooks."""
        # Share logger with hook manager for consistent error logging
        self.hook_manager.logger = self.logger
        return self.hook_manager.uninstall_hooks()

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
        return self.behavior_manager.run_behavior_management()

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
