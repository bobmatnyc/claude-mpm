"""
Agent deployment handler for the configure command.

WHAT: Provides all interactive agent install/remove flows for the configure
command, including the unified checkbox UI, preset-driven installation,
recommended-agent selection, single-agent primitives, and removal helpers.

WHY: Extracted from configure.py to keep the main command file focused on
routing. This handler covers all interactive deployment/installation flows
for agents:

- Unified select-to-install/remove checkbox UI (deploy_agents_unified)
- Preset-driven installation (deploy_agents_preset)
- Toolchain-recommended installation (select_recommended_agents)
- Single-agent installation primitives (deploy_single_agent)
- Detailed agent info viewer (view_agent_details_enhanced)
- Removal flows
- Path helpers used by removal (agent_file_paths, deployment_state_paths)

References
----------
SPEC-CLI-01~1 : docs/specs/cli.md#SPEC-CLI-01~1
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import questionary
from questionary import Choice, Separator
from rich.prompt import Confirm

from ...utils.agent_filters import (
    normalize_agent_id,
    normalize_agent_id_for_comparison,
)
from .configure_models import AgentConfig

if TYPE_CHECKING:
    from rich.prompt import Prompt

    from .configure import ConfigureCommand


def _prompt() -> type[Prompt]:
    """Return the configure module's ``Prompt`` symbol.

    Tests patch ``claude_mpm.cli.commands.configure.Prompt`` to feed inputs;
    looking it up dynamically here keeps that patch effective even though the
    actual call site lives in this handler module.
    """
    from . import configure as _cfg

    return _cfg.Prompt


class AgentDeploymentHandler:
    """Handles agent install/remove flows for the configure command."""

    def __init__(self, cmd: ConfigureCommand) -> None:
        self.cmd = cmd

    @property
    def console(self):
        return self.cmd.console

    @property
    def logger(self):
        return self.cmd.logger

    # ------------------------------------------------------------------
    # Unified select/install UI
    # ------------------------------------------------------------------

    def deploy_agents_unified(self, agents: list[AgentConfig]) -> None:
        """Unified agent selection with inline controls for recommended,
        presets, and collections.

        WHAT: Accepts a list of AgentConfig objects, presents an interactive
        checkbox UI grouped by collection and category, and installs or removes
        agents based on the user's final selection; required agents are always
        preserved and the filesystem is left unchanged if the user cancels.

        WHY: Replaces separate install and remove flows with a single checkbox
        that makes the current deployment state immediately visible; a re-display
        loop works around questionary's lack of native bulk-selection controls by
        intercepting sentinel values and re-presenting the widget with updated
        pre-checked state.

        :spec: SPEC-CLI-01~1

        Design:
        - Single nested checkbox list with grouped agents by source/category
        - Inline controls at top: Select all, Select recommended, Select presets
        - Asterisk (*) marks recommended agents
        - Visual hierarchy: Source → Category → Individual agents
        - Loop with visual feedback: Controls update checkmarks immediately
        """
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        from claude_mpm.utils.agent_filters import (
            filter_base_agents,
            get_deployed_agent_ids,
        )

        # Filter BASE_AGENT but keep deployed agents visible
        all_agents = filter_base_agents(
            [
                {
                    "agent_id": getattr(a, "agent_id", a.name),
                    "name": a.name,
                    "description": a.description,
                    "deployed": getattr(a, "is_deployed", False),
                }
                for a in agents
            ]
        )

        if not all_agents:
            self.console.print("[yellow]No agents available[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        # Get deployed agent IDs and recommended agents
        deployed_ids = get_deployed_agent_ids()

        try:
            recommended_agent_ids = (
                self.cmd.recommendation_service.get_recommended_agents(
                    str(self.cmd.project_dir)
                )
            )
        except Exception as e:
            self.logger.warning(f"Failed to get recommended agents: {e}")
            recommended_agent_ids = set()

        # Build mapping: normalized name -> full path for deployed agents
        # Use agent_id (technical ID) for comparison, not display name
        deployed_full_paths: set[str] = set()
        for agent in agents:
            agent_id = getattr(agent, "agent_id", agent.name)
            normalized_id = normalize_agent_id_for_comparison(agent_id)
            if normalized_id in deployed_ids:
                # Store agent_id for selection tracking (not display name)
                deployed_full_paths.add(agent_id)

        # Track current selection state (starts with deployed, updated in loop)
        current_selection = deployed_full_paths.copy()

        # Group agents by source/collection
        agent_map: dict[str, AgentConfig] = {}
        collections: dict[str, list[AgentConfig]] = defaultdict(list)

        for agent in agents:
            # Use agent_id (technical ID) for comparison, not display name
            agent_id = getattr(agent, "agent_id", agent.name)
            if agent_id in {a["agent_id"] for a in all_agents}:
                # Determine collection ID
                source_type = getattr(agent, "source_type", "local")
                if source_type == "remote":
                    source_dict = getattr(agent, "source_dict", {})
                    repo_url = source_dict.get("source", "")
                    if "/" in repo_url:
                        parts = repo_url.rstrip("/").split("/")
                        if len(parts) >= 2:
                            # Use more readable collection name
                            if (
                                "bobmatnyc/claude-mpm" in repo_url
                                or "claude-mpm" in repo_url.lower()
                            ):
                                collection_id = "MPM Agents"
                            else:
                                collection_id = f"{parts[-2]}/{parts[-1]}"
                        else:
                            collection_id = "Community Agents"
                    else:
                        collection_id = "Community Agents"
                else:
                    collection_id = "Local Agents"

                collections[collection_id].append(agent)
                agent_map[agent_id] = agent

        # Monkey-patch questionary symbols for better visibility
        questionary.prompts.common.INDICATOR_SELECTED = "[✓]"  # type: ignore[attr-defined]
        questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"  # type: ignore[attr-defined]

        # MAIN LOOP: Re-display UI when controls are used
        while True:
            # Build unified checkbox choices with inline controls
            choices: list = []

            for collection_id in sorted(collections.keys()):
                agents_in_collection = collections[collection_id]

                # Count selected/total agents in collection
                # Use agent_id for selection tracking, not display name
                selected_count = sum(
                    1
                    for agent in agents_in_collection
                    if getattr(agent, "agent_id", agent.name) in current_selection
                )
                total_count = len(agents_in_collection)

                # Add collection header
                choices.append(
                    Separator(
                        f"\n── {collection_id} ({selected_count}/{total_count} selected) ──"
                    )
                )

                # Determine if all agents in collection are selected
                all_selected = selected_count == total_count

                # Add inline control: Select/Deselect all from this collection
                if all_selected:
                    deselect_value = f"__DESELECT_ALL_{collection_id}__"
                    choices.append(
                        Choice(
                            f"  [Deselect all from {collection_id}]",  # nosec B608
                            value=deselect_value,
                            checked=False,
                        )
                    )
                else:
                    select_value = f"__SELECT_ALL_{collection_id}__"
                    choices.append(
                        Choice(
                            f"  [Select all from {collection_id}]",  # nosec B608
                            value=select_value,
                            checked=False,
                        )
                    )

                # Add inline control: Select recommended from this collection
                recommended_in_collection = [
                    a
                    for a in agents_in_collection
                    if any(
                        a.name == rec_id
                        or a.name.split("/")[-1] == rec_id.split("/")[-1]
                        for rec_id in recommended_agent_ids
                    )
                ]
                if recommended_in_collection:
                    recommended_selected = sum(
                        1
                        for a in recommended_in_collection
                        if a.name in current_selection
                    )
                    if recommended_selected == len(recommended_in_collection):
                        choices.append(
                            Choice(
                                f"  [Deselect recommended ({len(recommended_in_collection)} agents)]",
                                value=f"__DESELECT_REC_{collection_id}__",
                                checked=False,
                            )
                        )
                    else:
                        choices.append(
                            Choice(
                                f"  [Select recommended ({len(recommended_in_collection)} agents)]",
                                value=f"__SELECT_REC_{collection_id}__",
                                checked=False,
                            )
                        )

                # Add separator before individual agents
                choices.append(Separator())

                # Group agents by category within collection (if hierarchical)
                category_groups: dict[str, list[AgentConfig]] = defaultdict(list)
                for agent in sorted(agents_in_collection, key=lambda a: a.name):
                    # Extract category from hierarchical path
                    # (e.g., "engineer/backend/python-engineer")
                    parts = agent.name.split("/")
                    if len(parts) > 1:
                        category = "/".join(parts[:-1])  # e.g., "engineer/backend"
                    else:
                        category = ""  # No category
                    category_groups[category].append(agent)

                # Display agents grouped by category
                for category in sorted(category_groups.keys()):
                    agents_in_category = category_groups[category]

                    # Add category separator if hierarchical
                    if category:
                        choices.append(Separator(f"  {category}/"))

                    # Add individual agents
                    for agent in agents_in_category:
                        # Use agent_id (technical ID) for all tracking/selection
                        agent_id = getattr(agent, "agent_id", agent.name)
                        agent_leaf_name = agent_id.split("/")[-1]
                        raw_display_name = getattr(
                            agent, "display_name", agent_leaf_name
                        )
                        display_name = self.cmd._format_display_name(raw_display_name)

                        # Check if agent is required (cannot be unchecked)
                        required_agents = set(self.cmd.unified_config.agents.required)
                        is_required = (
                            agent_leaf_name in required_agents
                            or agent_id in required_agents
                        )

                        # Format choice text with [Required] indicator
                        if is_required:
                            choice_text = f"    {display_name} [Required]"
                        else:
                            choice_text = f"    {display_name}"

                        # Required agents are always selected
                        is_selected = is_required or agent_id in current_selection

                        # Add to current selection if required
                        if is_required:
                            current_selection.add(agent_id)

                        choices.append(
                            Choice(
                                title=choice_text,
                                value=agent_id,  # Use agent_id for value
                                checked=is_selected,
                                disabled="required" if is_required else None,
                            )
                        )

            self.console.print("\n[bold cyan]Select Agents to Install[/bold cyan]")
            self.console.print("[dim][✓] Checked = Installed (uncheck to remove)[/dim]")
            self.console.print(
                "[dim][ ] Unchecked = Available (check to install)[/dim]"
            )
            self.console.print("[dim][Required] = Core agents (always installed)[/dim]")
            self.console.print(
                "[dim]Use arrow keys to navigate, space to toggle, Enter to apply[/dim]\n"
            )

            try:
                selected_values = questionary.checkbox(
                    "Select agents:",
                    choices=choices,
                    instruction="(Space to toggle, Enter to continue)",
                    style=self.cmd.QUESTIONARY_STYLE,
                ).ask()
            except Exception as e:
                self.logger.error(f"Questionary checkbox failed: {e}", exc_info=True)
                self.console.print(
                    "[red]Error: Could not display interactive menu[/red]"
                )
                self.console.print(f"[dim]Reason: {e}[/dim]")
                if not sys.stdin.isatty():
                    self.console.print("[dim]Interactive terminal required. Use:[/dim]")
                    self.console.print(
                        "[dim]  --list-agents to see available agents[/dim]"
                    )
                _prompt().ask("\nPress Enter to continue")
                return

            if selected_values is None:
                self.console.print("[yellow]No changes made[/yellow]")
                _prompt().ask("\nPress Enter to continue")
                return

            # Check for inline control selections
            controls_selected = [v for v in selected_values if v.startswith("__")]

            if controls_selected:
                # Process controls and update current_selection
                for control in controls_selected:
                    if control.startswith("__SELECT_ALL_"):
                        collection_id = control.replace("__SELECT_ALL_", "").replace(
                            "__", ""
                        )
                        # Add all agents from this collection to current_selection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            current_selection.add(agent_id)
                    elif control.startswith("__DESELECT_ALL_"):
                        collection_id = control.replace("__DESELECT_ALL_", "").replace(
                            "__", ""
                        )
                        # Remove all agents from this collection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            current_selection.discard(agent_id)
                    elif control.startswith("__SELECT_REC_"):
                        collection_id = control.replace("__SELECT_REC_", "").replace(
                            "__", ""
                        )
                        # Add all recommended agents from this collection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            if any(
                                agent_id == rec_id
                                or agent_id.split("/")[-1] == rec_id.split("/")[-1]
                                for rec_id in recommended_agent_ids
                            ):
                                current_selection.add(agent_id)
                    elif control.startswith("__DESELECT_REC_"):
                        collection_id = control.replace("__DESELECT_REC_", "").replace(
                            "__", ""
                        )
                        # Remove all recommended agents from this collection
                        for agent in collections[collection_id]:
                            agent_id = getattr(agent, "agent_id", agent.name)
                            if any(
                                agent_id == rec_id
                                or agent_id.split("/")[-1] == rec_id.split("/")[-1]
                                for rec_id in recommended_agent_ids
                            ):
                                current_selection.discard(agent_id)

                # Loop back to re-display with updated selections
                continue

            # No controls selected - use the individual selections as final
            final_selection = set(selected_values)

            # Ensure required agents are always in the final selection
            required_agents = set(self.cmd.unified_config.agents.required)
            for agent in agents:
                agent_id = getattr(agent, "agent_id", agent.name)
                agent_leaf_name = agent_id.split("/")[-1]
                if agent_leaf_name in required_agents or agent_id in required_agents:
                    final_selection.add(agent_id)

            break

        # Determine changes
        to_deploy = final_selection - deployed_full_paths
        to_remove = deployed_full_paths - final_selection

        # Prevent removal of required agents
        required_agents = set(self.cmd.unified_config.agents.required)
        to_remove_filtered: set[str] = set()
        for agent_id in to_remove:
            agent_leaf_name = agent_id.split("/")[-1]
            if (
                agent_leaf_name not in required_agents
                and agent_id not in required_agents
            ):
                to_remove_filtered.add(agent_id)
            else:
                self.console.print(
                    f"[yellow]⚠ Cannot remove required agent: {agent_id}[/yellow]"
                )
        to_remove = to_remove_filtered

        if not to_deploy and not to_remove:
            self.console.print("[yellow]No changes needed[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        # Show what will happen
        self.console.print("\n[bold]Changes to apply:[/bold]")
        if to_deploy:
            self.console.print(f"[green]Install {len(to_deploy)} agent(s)[/green]")
            for agent_id in to_deploy:
                self.console.print(f"  + {agent_id}")
        if to_remove:
            self.console.print(f"[red]Remove {len(to_remove)} agent(s)[/red]")
            for agent_id in to_remove:
                self.console.print(f"  - {agent_id}")

        # Confirm
        if not Confirm.ask("\nApply these changes?", default=True):
            self.console.print("[yellow]Changes cancelled[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        # Execute changes
        deploy_success = 0
        deploy_fail = 0
        remove_success = 0
        remove_fail = 0

        # Install new agents
        for agent_id in to_deploy:
            agent = agent_map.get(agent_id)
            if agent and self.cmd._deploy_single_agent(agent, show_feedback=False):
                deploy_success += 1
                self.console.print(f"[green]✓ Installed: {agent_id}[/green]")
            else:
                deploy_fail += 1
                self.console.print(f"[red]✗ Failed to install: {agent_id}[/red]")

        # Remove agents
        for agent_id in to_remove:
            try:
                # Extract leaf name to match deployed filename
                leaf_name = agent_id.split("/")[-1] if "/" in agent_id else agent_id
                normalized_leaf = normalize_agent_id_for_comparison(leaf_name)

                # Remove from scope-aware path (primary) + legacy locations
                # _agent_file_paths already normalizes and checks both variants
                paths_to_check = self.cmd._agent_file_paths(leaf_name)

                removed = False
                for path in paths_to_check:
                    if path.exists():
                        path.unlink()
                        removed = True

                # Also remove from virtual deployment state
                # Check both raw and normalized keys for safety
                keys_to_check = {leaf_name, normalized_leaf}
                for state_path in self.cmd._deployment_state_paths():
                    if state_path.exists():
                        try:
                            with state_path.open() as f:
                                state = json.load(f)
                            agents_in_state = state.get("last_check_results", {}).get(
                                "agents", {}
                            )
                            for key in keys_to_check:
                                if key in agents_in_state:
                                    del agents_in_state[key]
                                    removed = True
                            if removed:
                                with state_path.open("w") as f:
                                    json.dump(state, f, indent=2)
                        except (json.JSONDecodeError, KeyError):
                            pass

                if removed:
                    remove_success += 1
                    self.console.print(f"[green]✓ Removed: {agent_id}[/green]")
                else:
                    remove_fail += 1
                    self.console.print(f"[yellow]⚠ Not found: {agent_id}[/yellow]")
            except Exception as e:
                remove_fail += 1
                self.console.print(f"[red]✗ Failed to remove {agent_id}: {e}[/red]")

        # Show summary
        self.console.print()
        if deploy_success > 0:
            self.console.print(f"[green]✓ Installed {deploy_success} agent(s)[/green]")
        if deploy_fail > 0:
            self.console.print(f"[red]✗ Failed to install {deploy_fail} agent(s)[/red]")
        if remove_success > 0:
            self.console.print(f"[green]✓ Removed {remove_success} agent(s)[/green]")
        if remove_fail > 0:
            self.console.print(f"[red]✗ Failed to remove {remove_fail} agent(s)[/red]")

        _prompt().ask("\nPress Enter to continue")

    # ------------------------------------------------------------------
    # Preset / recommended installation
    # ------------------------------------------------------------------

    def deploy_agents_preset(self) -> None:
        """Install agents using preset configuration."""
        try:
            from claude_mpm.services.agents.agent_preset_service import (
                AgentPresetService,
            )
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            source_manager = GitSourceManager()
            preset_service = AgentPresetService(source_manager)

            presets = preset_service.list_presets()

            if not presets:
                self.console.print("[yellow]No presets available[/yellow]")
                _prompt().ask("\nPress Enter to continue")
                return

            self.console.print("\n[bold white]═══ Available Presets ═══[/bold white]\n")
            for idx, preset in enumerate(presets, 1):
                self.console.print(f"  {idx}. [white]{preset['name']}[/white]")
                self.console.print(f"     {preset['description']}")
                self.console.print(f"     [dim]Agents: {len(preset['agents'])}[/dim]\n")

            selection = _prompt().ask("\nEnter preset number (or 'c' to cancel)")
            if selection.lower() == "c":
                return

            idx = int(selection) - 1
            if 0 <= idx < len(presets):
                preset_name = presets[idx]["name"]

                # Resolve and deploy preset
                resolution = preset_service.resolve_agents(preset_name)

                if resolution.get("missing_agents"):
                    self.console.print(
                        f"[red]Missing agents: {len(resolution['missing_agents'])}[/red]"
                    )
                    for agent_id in resolution["missing_agents"]:
                        self.console.print(f"  • {agent_id}")
                    _prompt().ask("\nPress Enter to continue")
                    return

                # Confirm installation
                self.console.print(
                    f"\n[bold]Preset '{preset_name}' includes {len(resolution['agents'])} agents[/bold]"
                )
                if Confirm.ask("Install all agents?", default=True):
                    installed = 0
                    for agent in resolution["agents"]:
                        # Convert dict to AgentConfig-like object for installation
                        agent_config = AgentConfig(
                            name=agent.get("agent_id", "unknown"),
                            description=agent.get("metadata", {}).get(
                                "description", ""
                            ),
                            dependencies=[],
                        )
                        agent_config.source_dict = agent
                        agent_config.full_agent_id = agent.get("agent_id", "unknown")

                        if self.cmd._deploy_single_agent(
                            agent_config, show_feedback=False
                        ):
                            installed += 1

                    self.console.print(
                        f"\n[green]✓ Installed {installed}/{len(resolution['agents'])} agents[/green]"
                    )

                _prompt().ask("\nPress Enter to continue")
            else:
                self.console.print("[red]Invalid selection[/red]")
                _prompt().ask("\nPress Enter to continue")

        except Exception as e:
            self.console.print(f"[red]Error installing preset: {e}[/red]")
            self.logger.error(f"Preset installation failed: {e}", exc_info=True)
            _prompt().ask("\nPress Enter to continue")

    def select_recommended_agents(self, agents: list[AgentConfig]) -> None:
        """Select and install recommended agents based on toolchain detection."""
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        self.console.clear()
        self.console.print(
            "\n[bold white]═══ Recommended Agents for This Project ═══[/bold white]\n"
        )

        # Get recommended agent IDs
        try:
            recommended_agent_ids = (
                self.cmd.recommendation_service.get_recommended_agents(
                    str(self.cmd.project_dir)
                )
            )
        except Exception as e:
            self.console.print(f"[red]Error detecting toolchain: {e}[/red]")
            self.logger.error(f"Toolchain detection failed: {e}", exc_info=True)
            _prompt().ask("\nPress Enter to continue")
            return

        if not recommended_agent_ids:
            self.console.print("[yellow]No recommended agents found[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        # Get detection summary
        try:
            summary = self.cmd.recommendation_service.get_detection_summary(
                str(self.cmd.project_dir)
            )

            self.console.print("[bold]Detected Project Stack:[/bold]")
            if summary.get("detected_languages"):
                self.console.print(
                    f"  Languages: [cyan]{', '.join(summary['detected_languages'])}[/cyan]"
                )
            if summary.get("detected_frameworks"):
                self.console.print(
                    f"  Frameworks: [cyan]{', '.join(summary['detected_frameworks'])}[/cyan]"
                )
            self.console.print(
                f"  Detection Quality: [{'green' if summary.get('detection_quality') == 'high' else 'yellow'}]{summary.get('detection_quality', 'unknown')}[/]"
            )
            self.console.print()
        except Exception:  # nosec B110 - Suppress broad except for failed safety check
            # Silent failure on safety check - non-critical feature
            pass

        # Build mapping: agent_id -> AgentConfig
        agent_map = {agent.name: agent for agent in agents}

        # Also check leaf names for matching
        for agent in agents:
            leaf_name = agent.name.split("/")[-1] if "/" in agent.name else agent.name
            if leaf_name not in agent_map:
                agent_map[leaf_name] = agent

        # Find matching agents from available agents
        matched_agents: list[AgentConfig] = []
        for recommended_id in recommended_agent_ids:
            # Try full path match first
            if recommended_id in agent_map:
                matched_agents.append(agent_map[recommended_id])
            else:
                # Try leaf name match
                recommended_leaf = (
                    recommended_id.split("/")[-1]
                    if "/" in recommended_id
                    else recommended_id
                )
                if recommended_leaf in agent_map:
                    matched_agents.append(agent_map[recommended_leaf])

        if not matched_agents:
            self.console.print(
                "[yellow]No matching agents found in available sources[/yellow]"
            )
            _prompt().ask("\nPress Enter to continue")
            return

        # Display recommended agents
        self.console.print(
            f"[bold]Recommended Agents ({len(matched_agents)}):[/bold]\n"
        )

        from rich.table import Table

        rec_table = Table(show_header=True, header_style="bold white")
        rec_table.add_column("#", style="dim", width=4)
        rec_table.add_column("Agent ID", style="cyan", width=40)
        rec_table.add_column("Status", style="white", width=15)

        for idx, agent in enumerate(matched_agents, 1):
            is_installed = getattr(agent, "is_deployed", False)
            status = (
                "[green]Already Installed[/green]"
                if is_installed
                else "[yellow]Not Installed[/yellow]"
            )
            rec_table.add_row(str(idx), agent.name, status)

        self.console.print(rec_table)

        # Count how many need installation
        to_install = [a for a in matched_agents if not getattr(a, "is_deployed", False)]
        already_installed = len(matched_agents) - len(to_install)

        self.console.print()
        if already_installed > 0:
            self.console.print(
                f"[green]✓ {already_installed} already installed[/green]"
            )
        if to_install:
            self.console.print(
                f"[yellow]⚠ {len(to_install)} need installation[/yellow]"
            )
        else:
            self.console.print(
                "[green]✓ All recommended agents are already installed![/green]"
            )
            _prompt().ask("\nPress Enter to continue")
            return

        # Ask for confirmation
        self.console.print()
        if not Confirm.ask(
            f"Install {len(to_install)} recommended agent(s)?", default=True
        ):
            self.console.print("[yellow]Installation cancelled[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        # Install agents
        self.console.print("\n[bold]Installing recommended agents...[/bold]\n")

        success_count = 0
        fail_count = 0

        for agent in to_install:
            try:
                if self.cmd._deploy_single_agent(agent, show_feedback=False):
                    success_count += 1
                    self.console.print(f"[green]✓ Installed: {agent.name}[/green]")
                else:
                    fail_count += 1
                    self.console.print(f"[red]✗ Failed: {agent.name}[/red]")
            except Exception as e:
                fail_count += 1
                self.console.print(f"[red]✗ Failed: {agent.name} - {e}[/red]")

        # Show summary
        self.console.print()
        if success_count > 0:
            self.console.print(
                f"[green]✓ Successfully installed {success_count} agent(s)[/green]"
            )
        if fail_count > 0:
            self.console.print(f"[red]✗ Failed to install {fail_count} agent(s)[/red]")

        _prompt().ask("\nPress Enter to continue")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def agent_file_paths(self, agent_name: str) -> list[Path]:
        """Return the list of paths to check for an agent file.

        The primary path is the active scope's agents_dir. Legacy locations
        (project .claude-mpm/agents/, project .claude/agents/, user
        ~/.claude/agents/) are included as secondary cleanup targets so that
        agents deployed to the wrong location by older code are still found
        and removed.

        Normalizes agent_name (underscore -> dash, lowercase, strip -agent
        suffix) and also checks the raw name for backward compatibility with
        agents deployed before normalization was added.
        """
        normalized = normalize_agent_id_for_comparison(agent_name)

        # Build the set of name variants to check
        names_to_check = [normalized]
        if agent_name != normalized:
            names_to_check.append(agent_name)  # Also check raw for backward compat

        dirs_to_check = [
            self.cmd._ctx.agents_dir,
            Path.cwd() / ".claude-mpm" / "agents",
            Path.cwd() / ".claude" / "agents",
            Path.home() / ".claude" / "agents",
        ]

        # Build paths for all name variants across all locations, deduplicated
        seen: set[Path] = set()
        paths: list[Path] = []
        for name in names_to_check:
            for d in dirs_to_check:
                p = d / f"{name}.md"
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        return paths

    def deployment_state_paths(self) -> list[Path]:
        """Return the list of deployment state file paths to check.

        Includes the active scope path plus legacy locations for cleanup.
        """
        primary = self.cmd._ctx.agents_dir / ".mpm_deployment_state"
        legacy_paths = [
            Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
            Path.home() / ".claude" / "agents" / ".mpm_deployment_state",
        ]
        seen = {primary}
        paths = [primary]
        for p in legacy_paths:
            if p not in seen:
                seen.add(p)
                paths.append(p)
        return paths

    # ------------------------------------------------------------------
    # Single-agent install / remove / detail
    # ------------------------------------------------------------------

    def deploy_single_agent(
        self, agent: AgentConfig, show_feedback: bool = True
    ) -> bool:
        """Install a single agent to the appropriate location."""
        try:
            # Check if this is a remote agent with source_dict
            source_dict = getattr(agent, "source_dict", None)
            full_agent_id = getattr(agent, "full_agent_id", agent.name)

            if source_dict:
                # Deploy remote agent using its source file
                source_file = Path(source_dict.get("source_file", ""))
                if not source_file.exists():
                    if show_feedback:
                        self.console.print(
                            f"[red]✗ Source file not found: {source_file}[/red]"
                        )
                    return False

                # Deploy to scope-aware agents directory
                target_dir = self.cmd._ctx.agents_dir

                if show_feedback:
                    self.console.print(
                        f"\n[white]Installing {full_agent_id}...[/white]"
                    )

                from claude_mpm.services.agents.deployment_utils import (
                    deploy_agent_file,
                )

                # NOTE: deploy_agent_file derives the target filename from
                # source_file.name (not full_agent_id).  This works because
                # cache files are named after their agent IDs in production.
                deploy_result = deploy_agent_file(
                    source_file=source_file,
                    deployment_dir=target_dir,
                    cleanup_legacy=True,
                    ensure_frontmatter=True,
                    force=True,  # CRITICAL: configure expects always-write semantics
                )

                if not deploy_result.success:
                    if show_feedback:
                        self.console.print(
                            f"[red]✗ Failed to install {full_agent_id}: {deploy_result.error}[/red]"
                        )
                    return False

                if show_feedback:
                    action = deploy_result.action
                    self.console.print(
                        f"[green]✓ Successfully installed {full_agent_id} ({action})[/green]"
                    )
                    _prompt().ask("\nPress Enter to continue")

                return True
            # Legacy local template installation (not implemented here)
            if show_feedback:
                self.console.print(
                    "[yellow]Local template installation not yet implemented[/yellow]"
                )
                _prompt().ask("\nPress Enter to continue")
            return False

        except Exception as e:
            self.logger.error(f"Agent installation failed: {e}", exc_info=True)
            if show_feedback:
                self.console.print(f"[red]Error installing agent: {e}[/red]")
                _prompt().ask("\nPress Enter to continue")
            return False

    def remove_agents(self, agents: list[AgentConfig]) -> None:
        """Remove installed agents."""
        # Filter to installed agents only
        installed = [a for a in agents if getattr(a, "is_deployed", False)]

        if not installed:
            self.console.print("[yellow]No agents are currently installed[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        self.console.print(f"\n[bold]Installed agents ({len(installed)}):[/bold]")
        for idx, agent in enumerate(installed, 1):
            raw_display_name = getattr(agent, "display_name", agent.name)
            display_name = self.cmd._format_display_name(raw_display_name)
            self.console.print(f"  {idx}. {agent.name} - {display_name}")

        selection = _prompt().ask("\nEnter agent number to remove (or 'c' to cancel)")
        if selection.lower() == "c":
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(installed):
                agent = installed[idx]
                full_agent_id = getattr(agent, "full_agent_id", agent.name)
                # Normalize so that e.g. "dart_engineer" -> "dart-engineer"
                full_agent_id = normalize_agent_id(full_agent_id)

                # Determine possible file names (normalized leaf name)
                file_names = [f"{full_agent_id}.md"]

                # Remove from active scope's agents directory
                removed = False
                scope_agent_dir = self.cmd._ctx.agents_dir

                for file_name in file_names:
                    scope_file = scope_agent_dir / file_name

                    if scope_file.exists():
                        scope_file.unlink()
                        removed = True
                        self.console.print(f"[green]✓ Removed {scope_file}[/green]")

                if removed:
                    self.console.print(
                        f"[green]✓ Successfully removed {full_agent_id}[/green]"
                    )
                else:
                    self.console.print("[yellow]Agent files not found[/yellow]")

                _prompt().ask("\nPress Enter to continue")
            else:
                self.console.print("[red]Invalid selection[/red]")
                _prompt().ask("\nPress Enter to continue")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection[/red]")
            _prompt().ask("\nPress Enter to continue")

    def view_agent_details_enhanced(self, agents: list[AgentConfig]) -> None:
        """View detailed agent information with enhanced remote agent details."""
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            _prompt().ask("\nPress Enter to continue")
            return

        self.console.print(f"\n[bold]Available agents ({len(agents)}):[/bold]")
        for idx, agent in enumerate(agents, 1):
            raw_display_name = getattr(agent, "display_name", agent.name)
            display_name = self.cmd._format_display_name(raw_display_name)
            self.console.print(f"  {idx}. {agent.name} - {display_name}")

        selection = _prompt().ask("\nEnter agent number to view (or 'c' to cancel)")
        if selection.lower() == "c":
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]

                self.console.clear()
                self.console.print("\n[bold white]═══ Agent Details ═══[/bold white]\n")

                # Basic info
                self.console.print(f"[bold]ID:[/bold] {agent.name}")
                raw_display_name = getattr(agent, "display_name", "N/A")
                display_name = (
                    self.cmd._format_display_name(raw_display_name)
                    if raw_display_name != "N/A"
                    else "N/A"
                )
                self.console.print(f"[bold]Name:[/bold] {display_name}")
                self.console.print(f"[bold]Description:[/bold] {agent.description}")

                # Source info
                source_type = getattr(agent, "source_type", "local")
                self.console.print(f"[bold]Source Type:[/bold] {source_type}")

                if source_type == "remote":
                    source_dict = getattr(agent, "source_dict", {})
                    category = source_dict.get("category", "N/A")
                    source = source_dict.get("source", "N/A")
                    version = source_dict.get("version", "N/A")

                    self.console.print(f"[bold]Category:[/bold] {category}")
                    self.console.print(f"[bold]Source:[/bold] {source}")
                    self.console.print(f"[bold]Version:[/bold] {version[:16]}...")

                # Installation status
                is_installed = getattr(agent, "is_deployed", False)
                status = "Installed" if is_installed else "Available"
                self.console.print(f"[bold]Status:[/bold] {status}")

                _prompt().ask("\nPress Enter to continue")
            else:
                self.console.print("[red]Invalid selection[/red]")
                _prompt().ask("\nPress Enter to continue")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection[/red]")
            _prompt().ask("\nPress Enter to continue")
