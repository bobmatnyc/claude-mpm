"""Agent display and table rendering for configure command.

WHY: Separate agent display logic from main configure command to improve
modularity and reduce complexity. Agent display includes table rendering,
status indicators, and detailed agent information views.

DESIGN DECISIONS:
- Use Rich library for modern table formatting
- Support pending state visualization (enable/disable arrows)
- Show truncated descriptions in tables, full details in views
- Display template metadata when available
"""

import json
from typing import List

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .configure_models import AgentConfig


class AgentDisplay:
    """Handle agent display and table rendering.

    This class manages the visual presentation of agents in various formats:
    - Summary tables with status indicators
    - Pending state visualization with arrows
    - Detailed agent information panels
    """

    def __init__(
        self,
        console: Console,
        agent_manager,  # SimpleAgentManager instance
        get_template_path_fn,  # Function to get template path for an agent
        display_header_fn,  # Function to display configure header
    ):
        """Initialize agent display handler.

        Args:
            console: Rich console for output
            agent_manager: SimpleAgentManager instance for state queries
            get_template_path_fn: Function(agent_name) -> Path to get template path
            display_header_fn: Function() -> None to display configure header
        """
        self.console = console
        self.agent_manager = agent_manager
        self._get_agent_template_path = get_template_path_fn
        self._display_header = display_header_fn

    def display_agents_table(self, agents: List[AgentConfig]) -> None:
        """Display a table of available agents with status and metadata.

        Shows:
        - Agent ID (for selection)
        - Name and description
        - Installed/Available status
        - Model or tools information

        Args:
            agents: List of agent configurations to display
        """

        from ...utils.agent_filters import get_deployed_agent_ids

        table = Table(
            title=f"Available Agents ({len(agents)} total)",
            box=ROUNDED,
            show_lines=True,
        )

        table.add_column("ID", style="dim", width=3)
        table.add_column("Name", style="bold blue", width=22)
        table.add_column("Status", width=12)
        table.add_column("Description", style="bold", width=45)
        table.add_column("Model/Tools", style="dim", width=20)

        # Get deployed agent IDs
        deployed_ids = get_deployed_agent_ids()

        # Track installed count for summary
        installed_count = 0

        for idx, agent in enumerate(agents, 1):
            # Check if agent is deployed to .claude/agents/
            # Use agent_id (technical ID) for comparison, not display name
            agent_id = getattr(agent, "agent_id", agent.name)
            agent_leaf_name = agent_id.split("/")[-1]
            is_deployed = agent_leaf_name in deployed_ids

            # Increment installed count
            if is_deployed:
                installed_count += 1

            # Show "Installed" for deployed agents, "Available" otherwise
            status = "[green]Installed[/green]" if is_deployed else "Available"

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

            # Truncate description for table display with bright styling
            if len(agent.description) > 42:
                desc_display = f"[cyan]{agent.description[:42]}[/cyan][dim]...[/dim]"
            else:
                desc_display = f"[cyan]{agent.description}[/cyan]"

            table.add_row(str(idx), agent.name, status, desc_display, tools_display)

        self.console.print(table)

        # Display summary count
        self.console.print(f"\n📊 Agents: {installed_count} Installed / {len(agents)} Total")

    def display_agents_with_pending_states(self, agents: List[AgentConfig]) -> None:
        """Display agents table with pending state indicators.

        Shows arrows (→) for agents with pending state changes:
        - "✗ Disabled → ✓ Enabled" for pending enable
        - "✓ Enabled → ✗ Disabled" for pending disable

        Useful for batch operations where changes are deferred until save.

        Args:
            agents: List of agent configurations to display
        """
        has_pending = self.agent_manager.has_pending_changes()
        pending_count = len(self.agent_manager.deferred_changes) if has_pending else 0

        title = f"Available Agents ({len(agents)} total)"
        if has_pending:
            title += f" [yellow]({pending_count} change{'s' if pending_count != 1 else ''} pending)[/yellow]"

        table = Table(title=title, box=ROUNDED, show_lines=True, expand=True)
        table.add_column("ID", justify="right", style="bold blue", width=5)
        table.add_column("Name", style="bold", width=22)
        table.add_column("Status", width=20)
        table.add_column("Description", style="bold", width=45)

        for idx, agent in enumerate(agents, 1):
            current_state = self.agent_manager.is_agent_enabled(agent.name)
            pending_state = self.agent_manager.get_pending_state(agent.name)

            # Show pending status with arrow
            if current_state != pending_state:
                if pending_state:
                    status = "[yellow]✗ Disabled → ✓ Enabled[/yellow]"
                else:
                    status = "[yellow]✓ Enabled → ✗ Disabled[/yellow]"
            else:
                status = (
                    "[green]✓ Enabled[/green]"
                    if current_state
                    else "[dim]✗ Disabled[/dim]"
                )

            desc_display = Text()
            desc_display.append(
                (
                    agent.description[:42] + "..."
                    if len(agent.description) > 42
                    else agent.description
                ),
                style="",
            )

            table.add_row(str(idx), agent.name, status, desc_display)

        self.console.print(table)

    def view_agent_details(self, agents: List[AgentConfig]) -> None:
        """View detailed information about a selected agent.

        Displays comprehensive agent information in a panel:
        - Name, status, template path
        - Full description (not truncated)
        - Model and version information
        - Tags and tools
        - Whether it's a system or custom template

        Args:
            agents: List of available agents for selection
        """
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
[bold]Tags:[/bold] {", ".join(tags) if tags else "None"}
[bold]Tools:[/bold] {", ".join(tools[:5]) if tools else "None"}{"..." if len(tools) > 5 else ""}
"""
                    except Exception:
                        pass

                # Create detail panel
                detail_text = f"""
[bold]Name:[/bold] {agent.name}
[bold]Status:[/bold] {"[green]Enabled[/green]" if self.agent_manager.is_agent_enabled(agent.name) else "[red]Disabled[/red]"}
[bold]Template Path:[/bold] {template_path}
[bold]Is System Template:[/bold] {"Yes" if str(template_path).startswith(str(self.agent_manager.templates_dir)) else "No (Custom)"}
{extra_info}
                """

                panel = Panel(
                    detail_text.strip(),
                    title=f"[bold]{agent.name} Details[/bold]",
                    box=ROUNDED,
                    style="blue",
                )

                self.console.print(panel)

            else:
                self.console.print("[red]Invalid agent ID.[/red]")

        except ValueError:
            self.console.print("[red]Invalid input. Please enter a number.[/red]")

        Prompt.ask("\nPress Enter to continue")
