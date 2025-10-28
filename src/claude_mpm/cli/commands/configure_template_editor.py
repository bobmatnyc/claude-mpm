"""Template editing operations for configure command.

WHY: Agent templates control agent behavior, tools, and capabilities. Users need
to customize templates without manually editing JSON files. This module provides
interactive template editing with safety features.

DESIGN DECISIONS:
- Distinguish system templates (read-only) from custom templates (editable)
- Support external editor integration (respects $EDITOR environment variable)
- Field-level editing with dot notation (e.g., "config.timeout")
- Automatic backup and validation
- Visual diff display for template changes
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.text import Text

from .configure_models import AgentConfig
from .configure_paths import get_agent_template_path


class TemplateEditor:
    """Template CRUD operations for agent configuration.

    This class handles:
    - Interactive template editing with external editors
    - Field-level modifications (add/modify/remove)
    - System vs custom template management
    - Template reset and copy operations
    """

    def __init__(
        self,
        console: Console,
        agent_manager,  # SimpleAgentManager instance
        current_scope: str,
        project_dir: Path,
    ):
        """Initialize template editor.

        Args:
            console: Rich console for output
            agent_manager: SimpleAgentManager for state and paths
            current_scope: Current configuration scope (project/user)
            project_dir: Current project directory
        """
        self.console = console
        self.agent_manager = agent_manager
        self.current_scope = current_scope
        self.project_dir = project_dir

    def get_agent_template_path(self, agent_name: str) -> Path:
        """Get the path to an agent's template file.

        Resolves template path based on current scope:
        - Project scope: .claude-mpm/agents in project dir
        - User scope: .claude-mpm/agents in home dir
        - Fallback: System templates directory

        Args:
            agent_name: Name of the agent

        Returns:
            Path to agent template file
        """
        return get_agent_template_path(
            agent_name,
            self.current_scope,
            self.project_dir,
            self.agent_manager.templates_dir,
        )

    def customize_agent_template(self, agents: List[AgentConfig]) -> None:
        """Customize agent JSON template (entry point).

        Prompts for agent ID and launches the template editor.

        Args:
            agents: List of available agents
        """
        agent_id = Prompt.ask("Enter agent ID to customize")

        try:
            idx = int(agent_id) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]
                self.edit_agent_template(agent)
            else:
                self.console.print("[red]Invalid agent ID.[/red]")
                Prompt.ask("Press Enter to continue")
        except ValueError:
            self.console.print("[red]Invalid input. Please enter a number.[/red]")
            Prompt.ask("Press Enter to continue")

    def edit_agent_template(self, agent: AgentConfig) -> None:
        """Edit an agent's JSON template (main editor interface).

        This is the most complex method (CC=18) that:
        - Loads existing template or creates minimal template
        - Displays template with syntax highlighting
        - Provides editing options based on template type (system vs custom)
        - Routes to appropriate sub-operations

        Args:
            agent: Agent configuration to edit
        """
        self.console.clear()
        self.console.print(f"[bold]Editing template for: {agent.name}[/bold]\n")

        # Get current template
        template_path = self.get_agent_template_path(agent.name)

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
            text_1.append("[1]", style="bold blue")
            text_1.append(" Edit in external editor")
            self.console.print(text_1)

            text_2 = Text("  ")
            text_2.append("[2]", style="bold blue")
            text_2.append(" Add/modify a field")
            self.console.print(text_2)

            text_3 = Text("  ")
            text_3.append("[3]", style="bold blue")
            text_3.append(" Remove a field")
            self.console.print(text_3)

            text_4 = Text("  ")
            text_4.append("[4]", style="bold blue")
            text_4.append(" Reset to defaults")
            self.console.print(text_4)
        else:
            text_1 = Text("  ")
            text_1.append("[1]", style="bold blue")
            text_1.append(" Create customized copy")
            self.console.print(text_1)

            text_2 = Text("  ")
            text_2.append("[2]", style="bold blue")
            text_2.append(" View full template")
            self.console.print(text_2)

        text_b = Text("  ")
        text_b.append("[b]", style="bold blue")
        text_b.append(" Back")
        self.console.print(text_b)

        self.console.print()

        choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

        if is_system:
            if choice == "1":
                # Create a customized copy
                self.create_custom_template_copy(agent, template)
            elif choice == "2":
                # View full template
                self.view_full_template(template)
        elif choice == "1":
            self.edit_in_external_editor(template_path, template)
        elif choice == "2":
            self.modify_template_field(template, template_path)
        elif choice == "3":
            self.remove_template_field(template, template_path)
        elif choice == "4":
            self.reset_template(agent, template_path)

        if choice != "b":
            Prompt.ask("Press Enter to continue")

    def edit_in_external_editor(self, template_path: Path, template: Dict) -> None:
        """Open template in external editor.

        Uses $EDITOR environment variable (defaults to nano).
        Saves changes back to template file after editing.

        Args:
            template_path: Path to save edited template
            template: Current template dict to edit
        """
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
            with open(temp_path) as f:
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

    def modify_template_field(self, template: Dict, template_path: Path) -> None:
        """Add or modify a field in the template.

        Supports dot notation for nested fields (e.g., "config.timeout").
        Accepts JSON-formatted values.

        Args:
            template: Template dict to modify
            template_path: Path to save modified template
        """
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

    def remove_template_field(self, template: Dict, template_path: Path) -> None:
        """Remove a field from the template.

        Supports dot notation for nested fields.

        Args:
            template: Template dict to modify
            template_path: Path to save modified template
        """
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

    def reset_template(self, agent: AgentConfig, template_path: Path) -> None:
        """Reset template to defaults.

        Removes custom template file, reverting to system template.

        Args:
            agent: Agent configuration
            template_path: Path to custom template (will be deleted)
        """
        if Confirm.ask(f"[yellow]Reset '{agent.name}' template to defaults?[/yellow]"):
            # Remove custom template file
            template_path.unlink(missing_ok=True)
            self.console.print(
                f"[green]Template for '{agent.name}' reset to defaults![/green]"
            )

    def create_custom_template_copy(self, agent: AgentConfig, template: Dict) -> None:
        """Create a customized copy of a system template.

        Copies system template to project/user config directory for editing.

        Args:
            agent: Agent configuration
            template: System template to copy
        """
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

    def view_full_template(self, template: Dict) -> None:
        """View the full template without truncation.

        Uses pager for long templates.

        Args:
            template: Template dict to display
        """
        self.console.clear()
        self.console.print("[bold]Full Template View:[/bold]\n")

        json_str = json.dumps(template, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)

        # Use pager for long content
        with self.console.pager():
            self.console.print(syntax)

    def reset_agent_defaults(self, agents: List[AgentConfig]) -> None:
        """Reset an agent to default enabled state and remove custom template.

        This method:
        - Prompts for agent ID
        - Resets agent to enabled state
        - Removes any custom template overrides
        - Shows success/error messages

        Args:
            agents: List of available agents
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
                template_path = self.get_agent_template_path(agent.name)
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

    def edit_templates_interface(self) -> None:
        """Template editing interface (stub for future expansion)."""
        self.console.print("[yellow]Template editing interface - Coming soon![/yellow]")
        Prompt.ask("Press Enter to continue")
