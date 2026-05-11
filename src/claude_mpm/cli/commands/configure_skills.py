"""
Skills management handler for configure command.

WHY: Extracted from configure.py to keep the main command file focused on
routing. This handler manages all skills-related interactive flows: install,
uninstall, configure for agents, view mappings, and auto-link.
"""

from __future__ import annotations

import shutil
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from questionary import Choice, Separator
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from .configure import ConfigureCommand


class SkillsHandler:
    """Handles skills management for the configure command."""

    def __init__(self, cmd: ConfigureCommand) -> None:
        self.cmd = cmd

    @property
    def console(self):
        return self.cmd.console

    def manage_skills(self) -> None:
        """Skills management interface with questionary checkbox selection."""
        from ...cli.interactive.skills_wizard import SkillsWizard
        from ...skills.skill_manager import get_manager

        wizard = SkillsWizard()
        manager = get_manager()

        while True:
            self.console.clear()
            self.cmd._display_header()

            self.console.print("\n[bold]Skills Management[/bold]")

            # Show action options
            self.console.print("\n[bold]Actions:[/bold]")
            self.console.print("  [1] Install/Uninstall skills")
            self.console.print("  [2] Configure skills for agents")
            self.console.print("  [3] View current skill mappings")
            self.console.print("  [4] Auto-link skills to agents")
            self.console.print("  [b] Back to main menu")
            self.console.print()

            choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

            if choice == "1":
                # Install/Uninstall skills with category-based selection
                self.manage_skill_installation()

            elif choice == "2":
                # Configure skills interactively
                self.console.clear()
                self.cmd._display_header()

                # Get list of enabled agents
                if self.cmd.agent_manager is None:
                    enabled_agents = []
                else:
                    agents = self.cmd.agent_manager.discover_agents()
                    # Filter BASE_AGENT from all agent operations (1M-502 Phase 1)
                    agents = self.cmd._filter_agent_configs(
                        agents, filter_deployed=False
                    )
                    enabled_agents = [
                        a.name
                        for a in agents
                        if self.cmd.agent_manager.get_pending_state(a.name)
                    ]

                if not enabled_agents:
                    self.console.print(
                        "[yellow]No agents are currently enabled.[/yellow]"
                    )
                    self.console.print(
                        "Please enable agents first in Agent Management."
                    )
                    Prompt.ask("\nPress Enter to continue")
                    continue

                # Run skills wizard
                success, mapping = wizard.run_interactive_selection(enabled_agents)

                if success:
                    # Save the configuration
                    manager.save_mappings_to_config()
                    self.console.print("\n[green]✓ Skills configuration saved![/green]")
                else:
                    self.console.print(
                        "\n[yellow]Skills configuration cancelled.[/yellow]"
                    )

                Prompt.ask("\nPress Enter to continue")

            elif choice == "3":
                # View current mappings
                self.console.clear()
                self.cmd._display_header()

                self.console.print("\n[bold]Current Skill Mappings:[/bold]\n")

                mappings = manager.list_agent_skill_mappings()
                if not mappings:
                    self.console.print("[dim]No skill mappings configured yet.[/dim]")
                else:
                    from rich.table import Table

                    table = Table(show_header=True, header_style="bold white")
                    table.add_column("Agent", style="white", no_wrap=True)
                    table.add_column("Skills", style="green", no_wrap=True)

                    for agent_id, skills in mappings.items():
                        skills_str = (
                            ", ".join(skills) if skills else "[dim](none)[/dim]"
                        )
                        table.add_row(agent_id, skills_str)

                    self.console.print(table)

                Prompt.ask("\nPress Enter to continue")

            elif choice == "4":
                # Auto-link skills
                self.console.clear()
                self.cmd._display_header()

                self.console.print("\n[bold]Auto-Linking Skills to Agents...[/bold]\n")

                # Get enabled agents
                if self.cmd.agent_manager is None:
                    enabled_agents = []
                else:
                    agents = self.cmd.agent_manager.discover_agents()
                    # Filter BASE_AGENT from all agent operations (1M-502 Phase 1)
                    agents = self.cmd._filter_agent_configs(
                        agents, filter_deployed=False
                    )
                    enabled_agents = [
                        a.name
                        for a in agents
                        if self.cmd.agent_manager.get_pending_state(a.name)
                    ]

                if not enabled_agents:
                    self.console.print(
                        "[yellow]No agents are currently enabled.[/yellow]"
                    )
                    self.console.print(
                        "Please enable agents first in Agent Management."
                    )
                    Prompt.ask("\nPress Enter to continue")
                    continue

                # Auto-link
                mapping = wizard._auto_link_skills(enabled_agents)

                # Display preview
                self.console.print("Auto-linked skills:\n")
                for agent_id, skills in mapping.items():
                    self.console.print(f"  [yellow]{agent_id}[/yellow]:")
                    for skill in skills:
                        self.console.print(f"    - {skill}")

                # Confirm
                confirm = Confirm.ask("\nApply this configuration?", default=True)

                if confirm:
                    wizard._apply_skills_configuration(mapping)
                    manager.save_mappings_to_config()
                    self.console.print("\n[green]✓ Auto-linking complete![/green]")
                else:
                    self.console.print("\n[yellow]Auto-linking cancelled.[/yellow]")

                Prompt.ask("\nPress Enter to continue")

            elif choice == "b":
                break
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
                Prompt.ask("\nPress Enter to continue")

    def detect_skill_patterns(self, skills: list[dict]) -> dict[str, list[dict]]:
        """Group skills by detected common prefixes.

        Args:
            skills: List of skill dictionaries

        Returns:
            Dict mapping pattern prefix to list of skills.
            Skills without pattern match go under "" (empty string) key.
        """
        # Count prefix occurrences (try 1-segment and 2-segment prefixes)
        prefix_counts = defaultdict(list)

        for skill in skills:
            skill_id = skill.get("name", skill.get("skill_id", ""))

            # Try to extract prefixes (split by hyphen)
            parts = skill_id.split("-")

            if len(parts) >= 2:
                # Try 2-segment prefix first (e.g., "toolchains-universal")
                two_seg_prefix = f"{parts[0]}-{parts[1]}"
                prefix_counts[two_seg_prefix].append(skill)

                # Also try 1-segment prefix (e.g., "digitalocean")
                one_seg_prefix = parts[0]
                if one_seg_prefix != two_seg_prefix:
                    prefix_counts[one_seg_prefix].append(skill)

        # Build pattern groups (require at least 2 skills per pattern)
        pattern_groups: dict[str, list[dict]] = defaultdict(list)
        used_skills: set[int] = set()

        # Prefer longer (more specific) prefixes
        sorted_prefixes = sorted(prefix_counts.keys(), key=lambda x: (-len(x), x))

        for prefix in sorted_prefixes:
            matching_skills = prefix_counts[prefix]

            # Only create a pattern group if we have 2+ skills and they're not already grouped
            available_skills = [s for s in matching_skills if id(s) not in used_skills]

            if len(available_skills) >= 2:
                pattern_groups[prefix] = available_skills
                used_skills.update(id(s) for s in available_skills)

        # Add ungrouped skills to "" (Other) group
        for skill in skills:
            if id(skill) not in used_skills:
                pattern_groups[""].append(skill)

        return dict(pattern_groups)

    def get_pattern_icon(self, prefix: str) -> str:
        """Get icon for a pattern prefix.

        Args:
            prefix: Pattern prefix (e.g., "digitalocean", "vercel")

        Returns:
            Emoji icon for the pattern
        """
        pattern_icons = {
            "digitalocean": "🌊",
            "aws": "☁️",
            "github": "🐙",
            "google": "🔍",
            "vercel": "▲",
            "netlify": "🦋",
            "universal-testing": "🧪",
            "universal-debugging": "🐛",
            "universal-security": "🔒",
            "toolchains-python": "🐍",
            "toolchains-typescript": "📘",
            "toolchains-javascript": "📒",
        }
        return pattern_icons.get(prefix, "📦")

    def manage_skill_installation(self) -> None:
        """Manage skill installation with category-based questionary checkbox selection."""
        import questionary

        # Get all skills
        all_skills = self.get_all_skills_from_git()
        if not all_skills:
            self.console.print(
                "[yellow]No skills available. Try syncing skills first.[/yellow]"
            )
            Prompt.ask("\nPress Enter to continue")
            return

        # Get deployed skills
        deployed = self.get_deployed_skill_ids()

        # Group by category
        grouped: dict[str, list[dict]] = {}
        for skill in all_skills:
            # Try to get category from tags or use toolchain
            category = None
            tags = skill.get("tags", [])

            # Look for category tag
            for tag in tags:
                if tag in [
                    "universal",
                    "python",
                    "typescript",
                    "javascript",
                    "go",
                    "rust",
                ]:
                    category = tag
                    break

            # Fallback to toolchain or universal
            if not category:
                category = skill.get("toolchain", "universal")

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(skill)

        # Category icons
        icons = {
            "universal": "🌐",
            "python": "🐍",
            "typescript": "📘",
            "javascript": "📒",
            "go": "🔷",
            "rust": "⚙️",
        }

        # Sort categories: universal first, then alphabetically
        categories = sorted(grouped.keys(), key=lambda x: (x != "universal", x))

        while True:
            # Show category selection first
            self.console.clear()
            self.cmd._display_header()
            self.console.print("\n[bold cyan]Skills Management[/bold cyan]")
            self.console.print(
                f"[dim]{len(all_skills)} skills available, {len(deployed)} installed[/dim]\n"
            )

            cat_choices = [
                Choice(
                    title=f"{icons.get(cat, '📦')} {cat.title()} ({len(grouped[cat])} skills)",
                    value=cat,
                )
                for cat in categories
            ]
            cat_choices.append(Choice(title="← Back to main menu", value="back"))

            selected_cat = questionary.select(
                "Select a category:",
                choices=cat_choices,
                style=self.cmd.QUESTIONARY_STYLE,
            ).ask()

            if selected_cat is None or selected_cat == "back":
                return

            # Show skills in category with checkbox selection
            category_skills = grouped[selected_cat]

            # Detect pattern groups within category
            pattern_groups = self.detect_skill_patterns(category_skills)

            # Build choices with pattern grouping and installation status
            skill_choices: list[Any] = []

            # Track which skills belong to which group for expansion later
            group_to_skills: dict[str, list[str]] = {}

            # Sort pattern groups: "" (Other) last, rest alphabetically
            sorted_patterns = sorted(pattern_groups.keys(), key=lambda x: (x == "", x))

            for pattern in sorted_patterns:
                pattern_skills = pattern_groups[pattern]

                # Skip empty groups
                if not pattern_skills:
                    continue

                # Collect skill IDs in this group
                skill_ids_in_group = []
                for skill in pattern_skills:
                    skill_id = skill.get("name", skill.get("skill_id", "unknown"))
                    skill_ids_in_group.append(skill_id)

                # Check if all skills in group are installed
                all_installed = all(
                    skill.get(
                        "deployment_name", skill.get("name", skill.get("skill_id"))
                    )
                    in deployed
                    or skill.get("name", skill.get("skill_id")) in deployed
                    for skill in pattern_skills
                )

                # Add pattern group header as selectable choice
                if pattern:
                    # Named pattern group
                    pattern_icon = self.get_pattern_icon(pattern)
                    skill_count = len(pattern_skills)
                    group_key = f"__group__:{pattern}"
                    group_to_skills[group_key] = skill_ids_in_group

                    skill_choices.append(
                        Choice(
                            title=f"{pattern_icon} {pattern} ({skill_count} skills) [Select All]",
                            value=group_key,
                            checked=all_installed,
                        )
                    )
                elif pattern_skills:
                    # "Other" group - only show if there are skills
                    group_key = "__group__:Other"
                    group_to_skills[group_key] = skill_ids_in_group

                    skill_choices.append(
                        Choice(
                            title=f"📦 Other ({len(pattern_skills)} skills) [Select All]",
                            value=group_key,
                            checked=all_installed,
                        )
                    )

                # Add skills in this pattern group
                for skill in sorted(pattern_skills, key=lambda x: x.get("name", "")):
                    skill_id = skill.get("name", skill.get("skill_id", "unknown"))
                    deploy_name = skill.get("deployment_name", skill_id)
                    description = skill.get("description", "")[:50]

                    # Check if installed
                    is_installed = deploy_name in deployed or skill_id in deployed

                    # Add indentation for pattern-grouped skills (all skills are indented)
                    skill_choices.append(
                        Choice(
                            title=f"    {skill_id} - {description}",
                            value=skill_id,
                            checked=is_installed,
                        )
                    )

                # Add spacing between pattern groups (not after last group)
                if pattern != sorted_patterns[-1]:
                    skill_choices.append(Separator())

            self.console.clear()
            self.cmd._display_header()
            self.console.print(
                f"\n{icons.get(selected_cat, '📦')} [bold]{selected_cat.title()}[/bold]"
            )
            self.console.print(
                "[dim]Use spacebar to toggle individual skills or entire groups, enter to confirm[/dim]\n"
            )

            selected = questionary.checkbox(
                "Select skills to install:",
                choices=skill_choices,
                style=self.cmd.QUESTIONARY_STYLE,
            ).ask()

            if selected is None:
                continue  # User cancelled, go back to category selection

            # Process group selections - expand to individual skills
            selected_set: set[str] = set()
            for item in selected:
                if item.startswith("__group__:"):
                    # Expand group selection to all skills in that group
                    selected_set.update(group_to_skills[item])
                else:
                    # Individual skill selection
                    selected_set.add(item)

            current_in_cat: set[str] = set()

            # Find currently installed skills in this category
            for skill in category_skills:
                skill_id = skill.get("name", skill.get("skill_id", "unknown"))
                deploy_name = skill.get("deployment_name", skill_id)
                if deploy_name in deployed or skill_id in deployed:
                    current_in_cat.add(skill_id)

            # Install newly selected
            to_install = selected_set - current_in_cat
            for skill_id in to_install:
                skill = next(
                    (
                        s
                        for s in category_skills
                        if s.get("name") == skill_id or s.get("skill_id") == skill_id
                    ),
                    None,
                )
                if skill:
                    self.install_skill_from_dict(skill)
                    self.console.print(f"[green]✓ Installed {skill_id}[/green]")

            # Uninstall deselected
            to_uninstall = current_in_cat - selected_set
            for skill_id in to_uninstall:
                # Find the skill to get deployment_name
                skill = next(
                    (
                        s
                        for s in category_skills
                        if s.get("name") == skill_id or s.get("skill_id") == skill_id
                    ),
                    None,
                )
                if skill:
                    deploy_name = skill.get("deployment_name", skill_id)
                    # Use the name that's actually in deployed set
                    name_to_uninstall = (
                        deploy_name if deploy_name in deployed else skill_id
                    )
                    self.uninstall_skill_by_name(name_to_uninstall)
                    self.console.print(f"[yellow]✗ Uninstalled {skill_id}[/yellow]")

            # Update deployed set for next iteration
            deployed = self.get_deployed_skill_ids()

            # Show completion message
            if to_install or to_uninstall:
                Prompt.ask("\nPress Enter to continue")

    def get_all_skills_from_git(self) -> list:
        """Get all skills from Git-based skill manager.

        Returns:
            List of skill dicts with full metadata from GitSkillSourceManager.
        """
        from ...config.skill_sources import SkillSourceConfiguration
        from ...services.skills.git_skill_source_manager import GitSkillSourceManager

        try:
            config = SkillSourceConfiguration()
            manager = GitSkillSourceManager(config)
            return manager.get_all_skills()
        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Could not load Git skills: {e}[/yellow]"
            )
            return []

    def display_skills_table_grouped(self) -> None:
        """Display skills in a table grouped by category, like agents."""
        from rich import box
        from rich.table import Table

        # Get all skills from Git manager
        all_skills = self.get_all_skills_from_git()
        deployed_ids = self.get_deployed_skill_ids()

        if not all_skills:
            self.console.print(
                "[yellow]No skills available. Try syncing skills first.[/yellow]"
            )
            return

        # Group skills by category/toolchain
        grouped: dict[str, list[dict]] = {}
        for skill in all_skills:
            # Try to get category from tags or use toolchain
            category = None
            tags = skill.get("tags", [])

            # Look for category tag
            for tag in tags:
                if tag in [
                    "universal",
                    "python",
                    "typescript",
                    "javascript",
                    "go",
                    "rust",
                ]:
                    category = tag
                    break

            # Fallback to toolchain or universal
            if not category:
                category = skill.get("toolchain", "universal")

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(skill)

        # Sort categories: universal first, then alphabetically
        categories = sorted(grouped.keys(), key=lambda x: (x != "universal", x))

        # Track global skill number across all categories
        skill_counter = 0

        for category in categories:
            category_skills = grouped[category]

            # Category header with icon
            icons = {
                "universal": "🌐",
                "python": "🐍",
                "typescript": "📘",
                "javascript": "📒",
                "go": "🔷",
                "rust": "⚙️",
            }
            icon = icons.get(category, "📦")
            self.console.print(
                f"\n{icon} [bold cyan]{category.title()}[/bold cyan] ({len(category_skills)} skills)"
            )

            # Create table for this category
            table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
            table.add_column("#", style="dim", width=4)
            table.add_column("Skill ID", style="cyan", width=35)
            table.add_column("Description", style="white", width=45)
            table.add_column("Status", style="green", width=12)

            for skill in sorted(category_skills, key=lambda x: x.get("name", "")):
                skill_counter += 1
                skill_id = skill.get("name", skill.get("skill_id", "unknown"))
                # Use deployment_name for matching if available
                deploy_name = skill.get("deployment_name", skill_id)
                description = skill.get("description", "")[:45]

                # Check if installed - handle both deployment_name and skill_id
                is_installed = deploy_name in deployed_ids or skill_id in deployed_ids
                status = "[green]✓ Installed[/green]" if is_installed else "Available"

                table.add_row(str(skill_counter), skill_id, description, status)

            self.console.print(table)

        # Summary
        total = len(all_skills)
        installed = sum(
            1
            for s in all_skills
            if s.get("deployment_name", s.get("name", "")) in deployed_ids
            or s.get("name", "") in deployed_ids
        )
        self.console.print(
            f"\n[dim]Showing {total} skills ({installed} installed)[/dim]"
        )

    def get_deployed_skill_ids(self) -> set:
        """Get set of deployed skill IDs from scope-aware skills directory.

        Returns:
            Set of skill directory names and common variations for matching.
        """
        skills_dir = self.cmd._ctx.skills_dir
        if not skills_dir.exists():
            return set()

        # Each deployed skill is a directory in .claude/skills/
        deployed_ids: set[str] = set()
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                # Add both the directory name and common variations
                deployed_ids.add(skill_dir.name)
                # Also add without prefix for matching (e.g., universal-testing -> testing)
                if skill_dir.name.startswith("universal-"):
                    deployed_ids.add(skill_dir.name.replace("universal-", "", 1))

        return deployed_ids

    def install_skill(self, skill) -> None:
        """Install a skill to scope-aware skills directory."""
        # Target directory
        target_dir = self.cmd._ctx.skills_dir / skill.skill_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy skill file(s)
        if skill.path.is_file():
            # Single file skill - copy to skill.md in target directory
            shutil.copy2(skill.path, target_dir / "skill.md")
        elif skill.path.is_dir():
            # Directory-based skill - copy all contents
            for item in skill.path.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)

    def uninstall_skill(self, skill) -> None:
        """Uninstall a skill from scope-aware skills directory."""
        target_dir = self.cmd._ctx.skills_dir / skill.skill_id
        if target_dir.exists():
            shutil.rmtree(target_dir)

    def install_skill_from_dict(self, skill_dict: dict) -> None:
        """Install a skill from Git skill dict to scope-aware skills directory.

        Args:
            skill_dict: Skill metadata dict from GitSkillSourceManager.get_all_skills()
        """
        skill_id = skill_dict.get("name", skill_dict.get("skill_id", "unknown"))
        content = skill_dict.get("content", "")

        if not content:
            self.console.print(
                f"[yellow]Warning: Skill '{skill_id}' has no content[/yellow]"
            )
            return

        # Target directory using deployment_name if available
        deploy_name = skill_dict.get("deployment_name", skill_id)
        target_dir = self.cmd._ctx.skills_dir / deploy_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # Write skill content to skill.md
        skill_file = target_dir / "skill.md"
        skill_file.write_text(content, encoding="utf-8")

    def uninstall_skill_by_name(self, skill_name: str) -> None:
        """Uninstall a skill by name from scope-aware skills directory.

        Args:
            skill_name: Name of skill directory to remove
        """
        target_dir = self.cmd._ctx.skills_dir / skill_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
