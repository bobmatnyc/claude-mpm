"""
Agent management handler for the configure command.

WHY: Extracted from configure.py to keep the main command file focused on
routing. This handler covers the interactive agent management menu, agent
discovery + display (table, sources, source-info, pending states), bulk
enable/disable toggling, auto-deployment after toggle, and helpers used to
build the agents table (filtering, column widths, name formatting).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import questionary
from rich.text import Text

from ...utils.agent_filters import (
    apply_all_filters,
    get_deployed_agent_ids,
    normalize_agent_id_for_comparison,
)

if TYPE_CHECKING:
    from .configure import ConfigureCommand
    from .configure_models import AgentConfig


def _prompt():
    """Return the configure module's ``Prompt`` symbol.

    Tests patch ``claude_mpm.cli.commands.configure.Prompt`` to feed inputs;
    looking it up dynamically here keeps that patch effective even though the
    actual call site lives in this handler module.
    """
    from . import configure as _cfg

    return _cfg.Prompt


class AgentManagementHandler:
    """Handles agent management for the configure command."""

    def __init__(self, cmd: ConfigureCommand) -> None:
        self.cmd = cmd

    @property
    def console(self):
        return self.cmd.console

    @property
    def logger(self):
        return self.cmd.logger

    # ------------------------------------------------------------------
    # Interactive menu + agent discovery / display
    # ------------------------------------------------------------------

    def manage_agents(self) -> None:
        """Enhanced agent management with remote agent discovery and installation."""
        while True:
            self.console.clear()
            self.cmd.navigation.display_header()
            self.console.print("\n[bold blue]═══ Agent Management ═══[/bold blue]\n")

            # Load all agents with spinner (don't show partial state)
            agents = self.load_agents_with_spinner()

            if not agents:
                self.console.print("[yellow]No agents found[/yellow]")
                self.console.print(
                    "[dim]Configure sources with 'claude-mpm agent-source add'[/dim]\n"
                )
                _prompt().ask("\nPress Enter to continue")
                break

            # Now display everything at once (after all data loaded)
            self.display_agent_sources_and_list(agents)

            # Step 3: Simplified menu - only "Select Agents" option
            self.console.print()
            self.logger.debug("About to show agent management menu")
            try:
                choice = questionary.select(
                    "Agent Management:",
                    choices=[
                        "Select Agents",
                        questionary.Separator(),
                        "← Back to main menu",
                    ],
                    style=self.cmd.QUESTIONARY_STYLE,
                ).ask()

                if choice is None or choice == "← Back to main menu":
                    break

                # Map selection to action
                if choice == "Select Agents":
                    self.logger.debug("User selected 'Select Agents' from menu")
                    self.cmd._deploy_agents_unified(agents)
                    # Loop back to show updated state after deployment

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Operation cancelled[/yellow]")
                break
            except Exception as e:
                # Handle questionary menu failure
                self.logger.error(f"Agent management menu failed: {e}", exc_info=True)
                self.console.print("[red]Error: Interactive menu failed[/red]")
                self.console.print(f"[dim]Reason: {e}[/dim]")
                if not sys.stdin.isatty():
                    self.console.print(
                        "[dim]Interactive terminal required for this operation[/dim]"
                    )
                    self.console.print("[dim]Use command-line options instead:[/dim]")
                    self.console.print(
                        "[dim]  claude-mpm configure --list-agents[/dim]"
                    )
                    self.console.print(
                        "[dim]  claude-mpm configure --enable-agent <id>[/dim]"
                    )
                _prompt().ask("\nPress Enter to continue")
                break

    def load_agents_with_spinner(self) -> list[AgentConfig]:
        """Load agents with loading indicator, don't show partial state.

        Returns:
            List of discovered agents with deployment status set.
        """
        agents: list[AgentConfig] = []
        with self.console.status(
            "[bold blue]Loading agents...[/bold blue]", spinner="dots"
        ):
            try:
                if self.cmd.agent_manager is None:
                    return agents
                # Discover agents (includes both local and remote)
                agents = self.cmd.agent_manager.discover_agents(include_remote=True)

                # Set deployment status on each agent for display
                deployed_ids = get_deployed_agent_ids()
                for agent in agents:
                    # Use agent_id (technical ID) for comparison, not display name
                    agent_id = getattr(agent, "agent_id", agent.name)
                    normalized_id = normalize_agent_id_for_comparison(agent_id)
                    agent.is_deployed = normalized_id in deployed_ids

                # Filter BASE_AGENT from display (1M-502 Phase 1)
                agents = self.filter_agent_configs(agents, filter_deployed=False)

            except Exception as e:
                self.console.print(f"[red]Error discovering agents: {e}[/red]")
                self.logger.error(f"Agent discovery failed: {e}", exc_info=True)
                agents = []

        return agents

    def display_agent_sources_and_list(self, agents: list[AgentConfig]) -> None:
        """Display agent sources and agent list (only after all data loaded).

        Args:
            agents: List of discovered agents with deployment status.
        """
        from rich.table import Table

        # Step 1: Show configured sources
        self.console.print("[bold white]═══ Agent Sources ═══[/bold white]\n")

        sources = self.get_configured_sources()
        if sources:
            sources_table = Table(show_header=True, header_style="bold white")
            sources_table.add_column(
                "Source",
                style="bright_yellow",
                width=40,
                no_wrap=True,
                overflow="ellipsis",
            )
            sources_table.add_column("Status", style="green", width=15, no_wrap=True)
            sources_table.add_column("Agents", style="yellow", width=10, no_wrap=True)

            for source in sources:
                status = "✓ Active" if source.get("enabled", True) else "Disabled"
                agent_count = source.get("agent_count", "?")
                sources_table.add_row(source["identifier"], status, str(agent_count))

            self.console.print(sources_table)
        else:
            self.console.print("[yellow]No agent sources configured[/yellow]")
            self.console.print(
                "[dim]Default source 'bobmatnyc/claude-mpm-agents' will be used[/dim]\n"
            )

        # Step 2: Display available agents
        self.console.print("\n[bold white]═══ Available Agents ═══[/bold white]\n")

        if agents:
            # Show progress spinner while recommendation service processes agents
            with self.console.status(
                "[bold blue]Preparing agent list...[/bold blue]", spinner="dots"
            ):
                self.display_agents_with_source_info(agents)
        else:
            self.console.print("[yellow]No agents available[/yellow]")

    # ------------------------------------------------------------------
    # Toggle + auto-deploy
    # ------------------------------------------------------------------

    def toggle_agents_interactive(self, agents: list[AgentConfig]) -> None:
        """Interactive multi-agent enable/disable with batch save."""
        if self.cmd.agent_manager is None:
            return

        # Initialize pending states from current states
        for agent in agents:
            current_state = self.cmd.agent_manager.is_agent_enabled(agent.name)
            self.cmd.agent_manager.set_agent_enabled_deferred(agent.name, current_state)

        while True:
            # Display table with pending states
            self.cmd._display_agents_with_pending_states(agents)

            # Show menu
            self.console.print("\n[bold]Toggle Agent Status:[/bold]")
            text_toggle = Text("  ")
            text_toggle.append("[t]", style="bold blue")
            text_toggle.append(" Enter agent IDs to toggle (e.g., '1,3,5' or '1-4')")
            self.console.print(text_toggle)

            text_all = Text("  ")
            text_all.append("[a]", style="bold blue")
            text_all.append(" Enable all agents")
            self.console.print(text_all)

            text_none = Text("  ")
            text_none.append("[n]", style="bold blue")
            text_none.append(" Disable all agents")
            self.console.print(text_none)

            text_save = Text("  ")
            text_save.append("[s]", style="bold green")
            text_save.append(" Save changes and return")
            self.console.print(text_save)

            text_cancel = Text("  ")
            text_cancel.append("[c]", style="bold magenta")
            text_cancel.append(" Cancel (discard changes)")
            self.console.print(text_cancel)

            choice = (
                _prompt()
                .ask("[bold blue]Select an option[/bold blue]", default="s")
                .strip()
                .lower()
            )

            if choice == "s":
                if self.cmd.agent_manager.has_pending_changes():
                    self.cmd.agent_manager.commit_deferred_changes()
                    self.console.print("[green]✓ Changes saved successfully![/green]")

                    # Auto-deploy enabled agents to .claude/agents/
                    self.auto_deploy_enabled_agents(agents)
                else:
                    self.console.print("[yellow]No changes to save.[/yellow]")
                _prompt().ask("Press Enter to continue")
                break
            if choice == "c":
                self.cmd.agent_manager.discard_deferred_changes()
                self.console.print("[yellow]Changes discarded.[/yellow]")
                _prompt().ask("Press Enter to continue")
                break
            if choice == "a":
                for agent in agents:
                    self.cmd.agent_manager.set_agent_enabled_deferred(agent.name, True)
            elif choice == "n":
                for agent in agents:
                    self.cmd.agent_manager.set_agent_enabled_deferred(agent.name, False)
            elif choice == "t" or choice.replace(",", "").replace("-", "").isdigit():
                selected_ids = self.cmd._parse_id_selection(
                    choice if choice != "t" else _prompt().ask("Enter IDs"), len(agents)
                )
                for idx in selected_ids:
                    if 1 <= idx <= len(agents):
                        agent = agents[idx - 1]
                        current = self.cmd.agent_manager.get_pending_state(agent.name)
                        self.cmd.agent_manager.set_agent_enabled_deferred(
                            agent.name, not current
                        )

    def auto_deploy_enabled_agents(self, agents: list[AgentConfig]) -> None:
        """Auto-deploy enabled agents after saving configuration.

        WHY: When users enable agents, they expect them to be deployed
        automatically to .claude/agents/ so they're available for use.
        """
        if self.cmd.agent_manager is None:
            return
        try:
            # Get list of enabled agents from states
            enabled_agents = [
                agent
                for agent in agents
                if self.cmd.agent_manager.is_agent_enabled(agent.name)
            ]

            if not enabled_agents:
                return

            # Show deployment progress
            self.console.print(
                f"\n[bold blue]Deploying {len(enabled_agents)} enabled agent(s)...[/bold blue]"
            )

            # Deploy each enabled agent
            success_count = 0
            failed_count = 0

            for agent in enabled_agents:
                # Deploy to .claude/agents/ (project-level)
                try:
                    if self.cmd._deploy_single_agent(agent, show_feedback=False):
                        success_count += 1
                        self.console.print(f"[green]✓ Deployed: {agent.name}[/green]")
                    else:
                        failed_count += 1
                        self.console.print(f"[yellow]⚠ Skipped: {agent.name}[/yellow]")
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Failed to deploy {agent.name}: {e}")
                    self.console.print(f"[red]✗ Failed: {agent.name}[/red]")

            # Show summary
            if success_count > 0:
                self.console.print(
                    f"\n[green]✓ Successfully deployed {success_count} agent(s) to .claude/agents/[/green]"
                )
            if failed_count > 0:
                self.console.print(
                    f"[yellow]⚠ {failed_count} agent(s) failed or were skipped[/yellow]"
                )

        except Exception as e:
            self.logger.error(f"Auto-deployment failed: {e}", exc_info=True)
            self.console.print(f"[red]✗ Auto-deployment error: {e}[/red]")

    # ------------------------------------------------------------------
    # Sources / filtering / formatting helpers
    # ------------------------------------------------------------------

    def get_configured_sources(self) -> list[dict]:
        """Get list of configured agent sources with agent counts."""
        try:
            from claude_mpm.config.agent_sources import AgentSourceConfiguration

            config = AgentSourceConfiguration.load()

            # Convert repositories to source dictionaries
            sources = []
            for repo in config.repositories:
                # Extract identifier from repository
                identifier = repo.identifier

                # Count agents in cache
                # Note: identifier already includes subdirectory path
                # (e.g., "bobmatnyc/claude-mpm-agents/agents")
                cache_dir = (
                    Path.home() / ".claude-mpm" / "cache" / "agents" / identifier
                )
                agent_count = 0
                if cache_dir.exists():
                    # cache_dir IS the agents directory - no need to append /agents
                    agent_count = len(list(cache_dir.rglob("*.md")))

                sources.append(
                    {
                        "identifier": identifier,
                        "url": repo.url,
                        "enabled": repo.enabled,
                        "priority": repo.priority,
                        "agent_count": agent_count,
                    }
                )

            return sources
        except Exception as e:
            self.logger.warning(f"Failed to get configured sources: {e}")
            return []

    def filter_agent_configs(
        self, agents: list[AgentConfig], filter_deployed: bool = False
    ) -> list[AgentConfig]:
        """Filter AgentConfig objects using agent_filters utilities.

        Converts AgentConfig objects to dictionaries for filtering,
        then back to AgentConfig. Always filters BASE_AGENT.
        Optionally filters deployed agents.

        Args:
            agents: List of AgentConfig objects
            filter_deployed: Whether to filter out deployed agents (default: False)

        Returns:
            Filtered list of AgentConfig objects
        """
        # Convert AgentConfig to dict format for filtering
        agent_dicts = []
        for agent in agents:
            agent_dicts.append(
                {
                    "agent_id": agent.name,
                    "name": agent.name,
                    "description": agent.description,
                    "deployed": getattr(agent, "is_deployed", False),
                }
            )

        # Apply filters (always filter BASE_AGENT)
        filtered_dicts = apply_all_filters(
            agent_dicts, filter_base=True, filter_deployed=filter_deployed
        )

        # Convert back to AgentConfig objects
        filtered_names = {d["agent_id"] for d in filtered_dicts}
        return [a for a in agents if a.name in filtered_names]

    @staticmethod
    def calculate_column_widths(
        terminal_width: int, columns: dict[str, int]
    ) -> dict[str, int]:
        """Calculate dynamic column widths based on terminal size.

        Args:
            terminal_width: Current terminal width in characters
            columns: Dict mapping column names to minimum widths

        Returns:
            Dict mapping column names to calculated widths

        Design:
            - Ensures minimum widths are respected
            - Distributes extra space proportionally
            - Handles narrow terminals gracefully (minimum 80 chars)
        """
        # Ensure minimum terminal width
        min_terminal_width = 80
        terminal_width = max(terminal_width, min_terminal_width)

        # Calculate total minimum width needed
        total_min_width = sum(columns.values())

        # Account for table borders and padding (2 chars per column + 2 for edges)
        overhead = (len(columns) * 2) + 2
        available_width = terminal_width - overhead

        # If we have extra space, distribute proportionally
        if available_width > total_min_width:
            extra_space = available_width - total_min_width
            total_weight = sum(columns.values())

            result = {}
            for col_name, min_width in columns.items():
                # Distribute extra space based on minimum width proportion
                proportion = min_width / total_weight
                extra = int(extra_space * proportion)
                result[col_name] = min_width + extra
            return result
        # Terminal too narrow, use minimum widths
        return columns.copy()

    @staticmethod
    def format_display_name(name: str) -> str:
        """Format internal agent name to human-readable display name.

        Converts underscores/hyphens to spaces and title-cases.
        Examples:
            agentic_coder_optimizer -> Agentic Coder Optimizer
            python-engineer -> Python Engineer
            api_qa_agent -> Api Qa Agent

        Args:
            name: Internal agent name (may contain underscores, hyphens)

        Returns:
            Human-readable display name
        """
        return name.replace("_", " ").replace("-", " ").title()

    def display_agents_with_source_info(self, agents: list[AgentConfig]) -> None:
        """Display agents table with source information and installation status."""
        from rich.table import Table

        # Get recommended agents for this project
        try:
            recommended_agents = self.cmd.recommendation_service.get_recommended_agents(
                str(self.cmd.project_dir)
            )
        except Exception as e:
            self.logger.warning(f"Failed to get recommended agents: {e}")
            recommended_agents = set()

        # Get terminal width and calculate dynamic column widths
        terminal_width = shutil.get_terminal_size().columns
        min_widths = {
            "#": 4,
            "Agent ID": 30,
            "Name": 20,
            "Source": 15,
            "Status": 10,
        }
        widths = self.calculate_column_widths(terminal_width, min_widths)

        agents_table = Table(show_header=True, header_style="bold cyan")
        agents_table.add_column(
            "#", style="bright_black", width=widths["#"], no_wrap=True
        )
        agents_table.add_column(
            "Agent ID",
            style="bright_black",
            width=widths["Agent ID"],
            no_wrap=True,
            overflow="ellipsis",
        )
        agents_table.add_column(
            "Name",
            style="bright_cyan",
            width=widths["Name"],
            no_wrap=True,
            overflow="ellipsis",
        )
        agents_table.add_column(
            "Source",
            style="bright_yellow",
            width=widths["Source"],
            no_wrap=True,
        )
        agents_table.add_column(
            "Status", style="bright_black", width=widths["Status"], no_wrap=True
        )

        # FIX 3: Get deployed agent IDs once, before the loop (efficiency)
        deployed_ids = get_deployed_agent_ids()

        recommended_count = 0
        for idx, agent in enumerate(agents, 1):
            # Determine source with repo name
            source_type = getattr(agent, "source_type", "local")

            if source_type == "remote":
                # Get repo name from agent metadata
                source_dict = getattr(agent, "source_dict", {})
                repo_url = source_dict.get("source", "")

                # Extract repo name from URL
                if (
                    "bobmatnyc/claude-mpm" in repo_url
                    or "claude-mpm" in repo_url.lower()
                ):
                    source_label = "MPM Agents"
                elif "/" in repo_url:
                    # Extract last part of org/repo
                    parts = repo_url.rstrip("/").split("/")
                    if len(parts) >= 2:
                        source_label = f"{parts[-2]}/{parts[-1]}"
                    else:
                        source_label = "Community"
                else:
                    source_label = "Community"
            else:
                source_label = "Local"

            # FIX 2: Check actual deployment status from .claude/agents/ directory
            # Use agent_id (technical ID like "python-engineer") not display name
            agent_id = getattr(agent, "agent_id", agent.name)
            is_installed = normalize_agent_id_for_comparison(agent_id) in deployed_ids
            if is_installed:
                status = "[green]Installed[/green]"
            else:
                status = "Available"

            # Check if agent is recommended
            # Handle both hierarchical paths (e.g., "engineer/backend/python-engineer")
            # and leaf names (e.g., "python-engineer")
            agent_full_path = agent.name
            agent_leaf_name = (
                agent_full_path.split("/")[-1]
                if "/" in agent_full_path
                else agent_full_path
            )

            for recommended_id in recommended_agents:
                # Check if the recommended_id matches either the full path or
                # just the leaf name
                recommended_leaf = (
                    recommended_id.split("/")[-1]
                    if "/" in recommended_id
                    else recommended_id
                )
                if (
                    agent_full_path == recommended_id
                    or agent_leaf_name == recommended_leaf
                ):
                    recommended_count += 1
                    break

            # FIX 1: Show agent_id (technical ID) in first column, not display name
            agent_id_display = getattr(agent, "agent_id", agent.name)

            # Get display name and format it properly
            # Raw display_name from YAML may contain underscores
            # (e.g., "agentic_coder_optimizer")
            raw_display_name = getattr(agent, "display_name", agent.name)
            display_name = self.format_display_name(raw_display_name)

            agents_table.add_row(
                str(idx), agent_id_display, display_name, source_label, status
            )

        self.console.print(agents_table)

        # Show legend if there are recommended agents
        if recommended_count > 0:
            # Get detection summary for context
            try:
                summary = self.cmd.recommendation_service.get_detection_summary(
                    str(self.cmd.project_dir)
                )
                detected_langs = (
                    ", ".join(summary.get("detected_languages", [])) or "None"
                )
                self.console.print(
                    f"\n[dim]* = recommended for this project "
                    f"(detected: {detected_langs})[/dim]"
                )
            except Exception:
                self.console.print("\n[dim]* = recommended for this project[/dim]")

        # Show installed vs available count (use deployed_ids for accuracy)
        # Use agent_id (technical ID) for comparison, not display name
        installed_count = sum(
            1
            for a in agents
            if normalize_agent_id_for_comparison(getattr(a, "agent_id", a.name))
            in deployed_ids
        )
        available_count = len(agents) - installed_count
        self.console.print(
            f"\n[green]✓ {installed_count} installed[/green] | "
            f"[dim]{available_count} available[/dim] | "
            f"[yellow]{recommended_count} recommended[/yellow] | "
            f"[dim]Total: {len(agents)}[/dim]"
        )

    def manage_sources(self) -> None:
        """Interactive source management."""
        self.console.print("\n[bold white]═══ Manage Agent Sources ═══[/bold white]\n")
        self.console.print(
            "[dim]Use 'claude-mpm agent-source' command to add/remove sources[/dim]"
        )
        self.console.print("\nExamples:")
        self.console.print("  claude-mpm agent-source add <git-url>")
        self.console.print("  claude-mpm agent-source remove <identifier>")
        self.console.print("  claude-mpm agent-source list")
        _prompt().ask("\nPress Enter to continue")
