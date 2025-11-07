"""
Skills command implementation for claude-mpm.

WHY: This module provides CLI commands for managing Claude Code skills,
exposing SkillsService functionality for skill discovery, deployment, validation,
updates, and configuration.

DESIGN DECISIONS:
- Use BaseCommand pattern for consistency with other CLI commands
- Rich output formatting for user-friendly display
- Graceful error handling with informative messages
- Support for verbose output and structured formats
"""

import os
import subprocess
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ...constants import SkillsCommands
from ...skills.skills_service import SkillsService
from ..shared import BaseCommand, CommandResult

console = Console()


class SkillsManagementCommand(BaseCommand):
    """Skills management command for Claude Code skills."""

    def __init__(self):
        super().__init__("skills")
        self._skills_service = None

    @property
    def skills_service(self) -> SkillsService:
        """Get skills service instance (lazy loaded)."""
        if self._skills_service is None:
            self._skills_service = SkillsService()
        return self._skills_service

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Most skills commands are optional, basic validation
        if hasattr(args, "skills_command") and args.skills_command:
            if args.skills_command == SkillsCommands.VALIDATE.value:
                if not hasattr(args, "skill_name") or not args.skill_name:
                    return "Validate command requires a skill name"
            elif args.skills_command == SkillsCommands.INFO.value:
                if not hasattr(args, "skill_name") or not args.skill_name:
                    return "Info command requires a skill name"
        return None

    def run(self, args) -> CommandResult:
        """Execute the skills command."""
        try:
            # Handle default case (no subcommand) - show list
            if not hasattr(args, "skills_command") or not args.skills_command:
                return self._list_skills(args)

            # Route to appropriate subcommand
            command_map = {
                SkillsCommands.LIST.value: self._list_skills,
                SkillsCommands.DEPLOY.value: self._deploy_skills,
                SkillsCommands.VALIDATE.value: self._validate_skill,
                SkillsCommands.UPDATE.value: self._update_skills,
                SkillsCommands.INFO.value: self._show_skill_info,
                SkillsCommands.CONFIG.value: self._manage_config,
            }

            handler = command_map.get(args.skills_command)
            if handler:
                return handler(args)
            return CommandResult(
                success=False,
                message=f"Unknown skills command: {args.skills_command}",
                exit_code=1,
            )

        except Exception as e:
            self.logger.error(f"Skills command failed: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return CommandResult(
                success=False, message=f"Skills command failed: {e}", exit_code=1
            )

    def _list_skills(self, args) -> CommandResult:
        """List available skills."""
        try:
            # Get skills based on filter
            if hasattr(args, "agent") and args.agent:
                skills = self.skills_service.get_skills_for_agent(args.agent)
                console.print(
                    f"\n[bold cyan]Skills for agent '{args.agent}':[/bold cyan]\n"
                )

                if not skills:
                    console.print(
                        f"[yellow]No skills found for agent '{args.agent}'[/yellow]"
                    )
                    return CommandResult(success=True, exit_code=0)

                for skill_name in skills:
                    # Get skill metadata
                    skill_info = self._get_skill_metadata(skill_name)
                    if skill_info:
                        console.print(f"  [green]•[/green] {skill_name}")
                        if (
                            hasattr(args, "verbose")
                            and args.verbose
                            and skill_info.get("description")
                        ):
                            console.print(f"    {skill_info['description']}")
                    else:
                        console.print(f"  [green]•[/green] {skill_name}")

            else:
                # Discover all bundled skills
                skills = self.skills_service.discover_bundled_skills()

                # Filter by category if specified
                if hasattr(args, "category") and args.category:
                    skills = [s for s in skills if s.get("category") == args.category]
                    console.print(
                        f"\n[bold cyan]Skills in category '{args.category}':[/bold cyan]\n"
                    )
                else:
                    console.print("\n[bold cyan]Available Skills:[/bold cyan]\n")

                if not skills:
                    console.print("[yellow]No skills found[/yellow]")
                    return CommandResult(success=True, exit_code=0)

                # Group by category
                by_category = {}
                for skill in skills:
                    category = skill.get("category", "uncategorized")
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(skill)

                # Display by category
                for category, category_skills in sorted(by_category.items()):
                    console.print(f"[bold yellow]{category}[/bold yellow]")
                    for skill in sorted(
                        category_skills, key=lambda s: s.get("name", "")
                    ):
                        name = skill.get("name", "unknown")
                        console.print(f"  [green]•[/green] {name}")

                        if hasattr(args, "verbose") and args.verbose:
                            metadata = skill.get("metadata", {})
                            if desc := metadata.get("description"):
                                console.print(f"    {desc}")
                            if version := metadata.get("version"):
                                console.print(f"    [dim]Version: {version}[/dim]")
                    console.print()

            return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error listing skills: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _deploy_skills(self, args) -> CommandResult:
        """Deploy bundled skills to project."""
        try:
            force = getattr(args, "force", False)
            specific_skills = getattr(args, "skills", None)

            console.print("\n[bold cyan]Deploying skills...[/bold cyan]\n")

            result = self.skills_service.deploy_bundled_skills(
                force=force, skill_names=specific_skills
            )

            # Display results
            if result["deployed"]:
                console.print(
                    f"[green]✓ Deployed {len(result['deployed'])} skill(s):[/green]"
                )
                for skill in result["deployed"]:
                    console.print(f"  • {skill}")
                console.print()

            if result["skipped"]:
                console.print(
                    f"[yellow]⊘ Skipped {len(result['skipped'])} skill(s) (already deployed):[/yellow]"
                )
                for skill in result["skipped"]:
                    console.print(f"  • {skill}")
                console.print("[dim]Use --force to redeploy[/dim]\n")

            if result["errors"]:
                console.print(
                    f"[red]✗ Failed to deploy {len(result['errors'])} skill(s):[/red]"
                )
                for skill, error in result["errors"].items():
                    console.print(f"  • {skill}: {error}")
                console.print()

            # Summary
            total = (
                len(result["deployed"]) + len(result["skipped"]) + len(result["errors"])
            )
            console.print(
                f"[bold]Summary:[/bold] {len(result['deployed'])} deployed, "
                f"{len(result['skipped'])} skipped, {len(result['errors'])} errors "
                f"(Total: {total})\n"
            )

            # Exit with error if any deployments failed
            exit_code = 1 if result["errors"] else 0
            return CommandResult(success=not result["errors"], exit_code=exit_code)

        except Exception as e:
            console.print(f"[red]Error deploying skills: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _validate_skill(self, args) -> CommandResult:
        """Validate skill structure and metadata."""
        try:
            skill_name = args.skill_name
            strict = getattr(args, "strict", False)

            console.print(
                f"\n[bold cyan]Validating skill '{skill_name}'...[/bold cyan]\n"
            )

            result = self.skills_service.validate_skill(skill_name)

            if result["valid"]:
                console.print(f"[green]✓ {skill_name} is valid[/green]\n")

                if result.get("warnings"):
                    console.print(
                        f"[yellow]Warnings ({len(result['warnings'])}):[/yellow]"
                    )
                    for warning in result["warnings"]:
                        console.print(f"  • {warning}")
                    console.print()

                    # Treat warnings as errors in strict mode
                    if strict:
                        console.print(
                            "[red]Strict mode: treating warnings as errors[/red]"
                        )
                        return CommandResult(success=False, exit_code=1)

                return CommandResult(success=True, exit_code=0)
            console.print(f"[red]✗ {skill_name} has validation errors:[/red]")
            for error in result.get("errors", []):
                console.print(f"  • {error}")
            console.print()

            if result.get("warnings"):
                console.print("[yellow]Warnings:[/yellow]")
                for warning in result["warnings"]:
                    console.print(f"  • {warning}")
                console.print()

            return CommandResult(success=False, exit_code=1)

        except Exception as e:
            console.print(f"[red]Error validating skill: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _update_skills(self, args) -> CommandResult:
        """Check for and install skill updates."""
        try:
            skill_names = getattr(args, "skill_names", [])
            check_only = getattr(args, "check_only", False)
            force = getattr(args, "force", False)

            action = "Checking" if check_only else "Updating"
            console.print(f"\n[bold cyan]{action} skills...[/bold cyan]\n")

            result = self.skills_service.check_for_updates(skill_names)

            if not result.get("updates_available"):
                console.print("[green]All skills are up to date[/green]\n")
                return CommandResult(success=True, exit_code=0)

            # Display available updates
            console.print(
                f"[yellow]Updates available for {len(result['updates_available'])} skill(s):[/yellow]"
            )
            for update_info in result["updates_available"]:
                skill_name = update_info["skill"]
                current = update_info["current_version"]
                latest = update_info["latest_version"]
                console.print(f"  • {skill_name}: {current} → {latest}")
            console.print()

            if check_only:
                console.print(
                    "[dim]Run without --check-only to install updates[/dim]\n"
                )
                return CommandResult(success=True, exit_code=0)

            # Install updates
            console.print("[bold cyan]Installing updates...[/bold cyan]\n")
            install_result = self.skills_service.install_updates(
                result["updates_available"], force=force
            )

            if install_result["updated"]:
                console.print(
                    f"[green]✓ Updated {len(install_result['updated'])} skill(s)[/green]\n"
                )

            if install_result.get("errors"):
                console.print(
                    f"[red]✗ Failed to update {len(install_result['errors'])} skill(s)[/red]"
                )
                for skill, error in install_result["errors"].items():
                    console.print(f"  • {skill}: {error}")
                console.print()

            exit_code = 1 if install_result.get("errors") else 0
            return CommandResult(
                success=not install_result.get("errors"), exit_code=exit_code
            )

        except Exception as e:
            console.print(f"[red]Error updating skills: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _show_skill_info(self, args) -> CommandResult:
        """Show detailed skill information."""
        try:
            skill_name = args.skill_name
            show_content = getattr(args, "show_content", False)

            skill_info = self._get_skill_metadata(skill_name)

            if not skill_info:
                console.print(f"[red]Skill '{skill_name}' not found[/red]")
                return CommandResult(success=False, exit_code=1)

            # Display skill info in a panel
            info_text = f"[bold cyan]{skill_name}[/bold cyan]\n\n"

            if desc := skill_info.get("description"):
                info_text += f"{desc}\n\n"

            if category := skill_info.get("category"):
                info_text += f"[bold]Category:[/bold] {category}\n"

            if version := skill_info.get("version"):
                info_text += f"[bold]Version:[/bold] {version}\n"

            if source := skill_info.get("source"):
                info_text += f"[bold]Source:[/bold] {source}\n"

            # Show agents using this skill
            agents_using = self.skills_service.get_agents_for_skill(skill_name)
            if agents_using:
                info_text += (
                    f"\n[bold]Used by agents:[/bold] {', '.join(agents_using)}\n"
                )

            console.print(
                Panel(info_text, title="Skill Information", border_style="cyan")
            )

            # Show content if requested
            if show_content:
                skill_path = self.skills_service.get_skill_path(skill_name)
                skill_md = skill_path / "SKILL.md"

                if skill_md.exists():
                    console.print("\n[bold cyan]Skill Content:[/bold cyan]\n")
                    content = skill_md.read_text()
                    console.print(Markdown(content))
                else:
                    console.print(
                        f"\n[yellow]SKILL.md not found at {skill_md}[/yellow]"
                    )

            return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error showing skill info: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _manage_config(self, args) -> CommandResult:
        """View or edit skills configuration."""
        try:
            scope = getattr(args, "scope", "project")
            edit = getattr(args, "edit", False)
            show_path = getattr(args, "path", False)

            config_path = self.skills_service.get_config_path(scope)

            if show_path:
                console.print(
                    f"\n[cyan]Configuration path ({scope}):[/cyan] {config_path}\n"
                )
                return CommandResult(success=True, exit_code=0)

            if not config_path.exists():
                console.print(
                    f"\n[yellow]Configuration file does not exist: {config_path}[/yellow]"
                )
                console.print("[dim]Would you like to create it? (y/n):[/dim] ", end="")

                if input().lower() == "y":
                    self.skills_service.create_default_config(scope)
                    console.print(
                        f"[green]Created default configuration at {config_path}[/green]\n"
                    )
                else:
                    return CommandResult(success=False, exit_code=1)

            if edit:
                # Open in editor
                editor = os.environ.get("EDITOR", "nano")
                try:
                    subprocess.run([editor, str(config_path)], check=True)
                    console.print(
                        f"\n[green]Configuration saved to {config_path}[/green]\n"
                    )
                    return CommandResult(success=True, exit_code=0)
                except subprocess.CalledProcessError as e:
                    console.print(f"[red]Error opening editor: {e}[/red]")
                    return CommandResult(success=False, exit_code=1)
            else:
                # Display config
                console.print(
                    f"\n[bold cyan]Skills Configuration ({scope}):[/bold cyan]\n"
                )
                console.print(f"[dim]Path: {config_path}[/dim]\n")

                import yaml

                config = yaml.safe_load(config_path.read_text())
                console.print(yaml.dump(config, default_flow_style=False))

                return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error managing configuration: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _get_skill_metadata(self, skill_name: str) -> Optional[dict]:
        """Get skill metadata from SKILL.md file."""
        try:
            skill_path = self.skills_service.get_skill_path(skill_name)
            skill_md = skill_path / "SKILL.md"

            if not skill_md.exists():
                return None

            # Parse SKILL.md metadata
            content = skill_md.read_text()
            return self.skills_service.parse_skill_metadata(content)

        except Exception:
            return None


def manage_skills(args) -> int:
    """
    Main entry point for skills command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    command = SkillsManagementCommand()

    # Validate arguments
    error = command.validate_args(args)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        return 1

    # Run command
    result = command.run(args)
    return result.exit_code
