"""
Profile management commands for claude-mpm CLI.

WHY: Users need a simple way to manage deployment profiles from the command
line. Profiles control which agents and skills are deployed, reducing context
usage by limiting available agents to only what's needed.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Provide clear, actionable output with standardized error handling
- Support profile listing, activation, and status reporting
- Integrate with ConfigLoader for profile persistence
"""

from pathlib import Path
from typing import Any, Dict

import yaml
from rich.console import Console
from rich.table import Table

from ...core.shared.config_loader import ConfigLoader
from ...services.profile_manager import ProfileManager
from ...utils.console import console
from ..shared import BaseCommand, CommandResult


class ProfileCommand(BaseCommand):
    """Profile management command for agents and skills filtering."""

    def __init__(self):
        super().__init__("profile")
        # ProfileManager will auto-detect project directory
        self.profile_manager = ProfileManager()
        self.config_loader = ConfigLoader()

    def validate_args(self, args) -> str:
        """Validate command arguments."""
        if not hasattr(args, "profile_command") or not args.profile_command:
            return "Profile command required. Use: list, set, status, or show"

        valid_commands = ["list", "set", "status", "show"]
        if args.profile_command not in valid_commands:
            return (
                f"Unknown profile command: {args.profile_command}. "
                f"Valid commands: {', '.join(valid_commands)}"
            )

        # Validate set command has profile name
        if args.profile_command == "set":
            if not hasattr(args, "profile_name") or not args.profile_name:
                return "Profile name required for 'set' command"

        # Validate show command has profile name
        if args.profile_command == "show":
            if not hasattr(args, "profile_name") or not args.profile_name:
                return "Profile name required for 'show' command"

        return None

    def run(self, args) -> CommandResult:
        """Execute the profile command."""
        try:
            if args.profile_command == "list":
                return self._list_profiles(args)
            elif args.profile_command == "set":
                return self._set_profile(args)
            elif args.profile_command == "status":
                return self._show_status(args)
            elif args.profile_command == "show":
                return self._show_profile(args)
            else:
                return CommandResult.error_result(
                    f"Unknown profile command: {args.profile_command}"
                )
        except Exception as e:
            return CommandResult.error_result(f"Profile command failed: {e}")

    def _list_profiles(self, args) -> CommandResult:
        """List all available profiles."""
        profiles = self.profile_manager.list_available_profiles()

        if not profiles:
            console.print("[yellow]No profiles found in .claude-mpm/profiles/[/yellow]")
            return CommandResult.success_result("No profiles available")

        # Load current active profile
        main_config = self.config_loader.load_main_config()
        active_profile = main_config.get("active_profile")

        # Create table
        table = Table(title="Available Deployment Profiles")
        table.add_column("Profile", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")

        for profile_name in profiles:
            description = self.profile_manager.get_profile_description(profile_name)
            status = "✓ Active" if profile_name == active_profile else ""

            table.add_row(
                profile_name, description or "(no description)", status or "-"
            )

        console.print(table)

        return CommandResult.success_result(
            f"Found {len(profiles)} profile(s)", {"profiles": profiles}
        )

    def _set_profile(self, args) -> CommandResult:
        """Set active profile."""
        profile_name = args.profile_name

        # Validate profile exists
        available_profiles = self.profile_manager.list_available_profiles()
        if profile_name not in available_profiles:
            return CommandResult.error_result(
                f"Profile '{profile_name}' not found. "
                f"Available profiles: {', '.join(available_profiles)}"
            )

        # Load profile to validate it
        success = self.profile_manager.load_profile(profile_name)
        if not success:
            return CommandResult.error_result(
                f"Failed to load profile '{profile_name}'"
            )

        # Update configuration.yaml
        config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"
        if not config_path.exists():
            # Create configuration.yaml if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_data = {"active_profile": profile_name}
        else:
            # Load existing configuration
            with config_path.open("r") as f:
                config_data = yaml.safe_load(f) or {}
            config_data["active_profile"] = profile_name

        # Save configuration
        with config_path.open("w") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

        # Show summary
        summary = self.profile_manager.get_filtering_summary()
        console.print(f"[green]✓[/green] Active profile set to: [cyan]{profile_name}[/cyan]")
        console.print(
            f"  Agents enabled: [cyan]{summary['enabled_agents_count']}[/cyan]"
        )
        console.print(
            f"  Skills enabled: [cyan]{summary['enabled_skills_count']}[/cyan]"
        )
        console.print(
            f"  Skill patterns disabled: [cyan]{summary['disabled_patterns_count']}[/cyan]"
        )
        console.print(
            "\n[yellow]Note:[/yellow] Restart Claude Code or run [cyan]claude-mpm init[/cyan] "
            "to apply profile filtering."
        )

        return CommandResult.success_result(
            f"Profile '{profile_name}' activated",
            {"profile": profile_name, "summary": summary},
        )

    def _show_status(self, args) -> CommandResult:
        """Show current profile status."""
        # Load current active profile
        main_config = self.config_loader.load_main_config()
        active_profile = main_config.get("active_profile")

        if not active_profile:
            console.print(
                "[yellow]No active profile[/yellow] - All agents and skills enabled"
            )
            return CommandResult.success_result(
                "No active profile", {"active_profile": None}
            )

        # Load profile
        success = self.profile_manager.load_profile(active_profile)
        if not success:
            return CommandResult.error_result(
                f"Failed to load active profile '{active_profile}'"
            )

        # Get summary
        summary = self.profile_manager.get_filtering_summary()

        # Display status
        console.print(f"[green]Active Profile:[/green] [cyan]{active_profile}[/cyan]")
        console.print()

        # Agents section
        console.print("[bold]Agents:[/bold]")
        console.print(f"  Enabled: [cyan]{summary['enabled_agents_count']}[/cyan]")
        console.print(f"  Disabled: [cyan]{summary['disabled_agents_count']}[/cyan]")

        # Skills section
        console.print()
        console.print("[bold]Skills:[/bold]")
        console.print(f"  Enabled: [cyan]{summary['enabled_skills_count']}[/cyan]")
        console.print(
            f"  Disabled patterns: [cyan]{summary['disabled_patterns_count']}[/cyan]"
        )

        return CommandResult.success_result(
            f"Profile '{active_profile}' status",
            {"active_profile": active_profile, "summary": summary},
        )

    def _show_profile(self, args) -> CommandResult:
        """Show detailed profile configuration."""
        profile_name = args.profile_name

        # Validate profile exists
        available_profiles = self.profile_manager.list_available_profiles()
        if profile_name not in available_profiles:
            return CommandResult.error_result(
                f"Profile '{profile_name}' not found. "
                f"Available profiles: {', '.join(available_profiles)}"
            )

        # Load profile
        success = self.profile_manager.load_profile(profile_name)
        if not success:
            return CommandResult.error_result(
                f"Failed to load profile '{profile_name}'"
            )

        # Display profile details
        console.print(f"[bold]Profile:[/bold] [cyan]{profile_name}[/cyan]")
        console.print()

        # Show enabled agents
        enabled_agents = self.profile_manager.get_enabled_agents()
        if enabled_agents:
            console.print("[bold]Enabled Agents:[/bold]")
            for agent in sorted(enabled_agents):
                console.print(f"  • {agent}")
            console.print()

        # Show disabled agents
        disabled_agents = self.profile_manager.get_disabled_agents()
        if disabled_agents:
            console.print("[bold]Disabled Agents:[/bold]")
            for agent in sorted(disabled_agents):
                console.print(f"  • {agent}")
            console.print()

        # Show enabled skills
        enabled_skills = self.profile_manager.get_enabled_skills()
        if enabled_skills:
            console.print("[bold]Enabled Skills:[/bold]")
            for skill in sorted(enabled_skills):
                console.print(f"  • {skill}")
            console.print()

        # Show disabled skill patterns
        disabled_patterns = self.profile_manager.get_disabled_skill_patterns()
        if disabled_patterns:
            console.print("[bold]Disabled Skill Patterns:[/bold]")
            for pattern in disabled_patterns:
                console.print(f"  • {pattern}")

        return CommandResult.success_result(
            f"Profile '{profile_name}' details",
            {
                "profile": profile_name,
                "enabled_agents": list(enabled_agents),
                "disabled_agents": list(disabled_agents),
                "enabled_skills": list(enabled_skills),
                "disabled_patterns": disabled_patterns,
            },
        )
