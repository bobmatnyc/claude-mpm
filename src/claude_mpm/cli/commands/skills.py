"""
Skills command implementation for claude-mpm.

WHY: This module provides CLI commands for managing Claude Code skills,
exposing SkillsService functionality for skill discovery, deployment, validation,
updates, and configuration. Also provides GitHub skills deployment via SkillsDeployer.

DESIGN DECISIONS:
- Use BaseCommand pattern for consistency with other CLI commands
- Rich output formatting for user-friendly display
- Graceful error handling with informative messages
- Support for verbose output and structured formats
- Dual service approach: SkillsService for bundled, SkillsDeployer for GitHub

ARCHITECTURE:
- SkillsService: Manages bundled skills (in project .claude/skills/)
- SkillsDeployer: Downloads from GitHub to ~/.claude/skills/ for Claude Code
"""

import os
import subprocess
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ...constants import SkillsCommands
from ...services.skills_deployer import SkillsDeployerService
from ...skills.skills_service import SkillsService
from ..shared import BaseCommand, CommandResult

console = Console()


class SkillsManagementCommand(BaseCommand):
    """Skills management command for Claude Code skills."""

    def __init__(self):
        super().__init__("skills")
        self._skills_service = None
        self._skills_deployer = None

    @property
    def skills_service(self) -> SkillsService:
        """Get skills service instance (lazy loaded)."""
        if self._skills_service is None:
            self._skills_service = SkillsService()
        return self._skills_service

    @property
    def skills_deployer(self) -> SkillsDeployerService:
        """Get skills deployer instance (lazy loaded)."""
        if self._skills_deployer is None:
            self._skills_deployer = SkillsDeployerService()
        return self._skills_deployer

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
                SkillsCommands.CONFIGURE.value: self._configure_skills,
                # GitHub deployment commands
                SkillsCommands.DEPLOY_FROM_GITHUB.value: self._deploy_from_github,
                SkillsCommands.LIST_AVAILABLE.value: self._list_available_github_skills,
                SkillsCommands.CHECK_DEPLOYED.value: self._check_deployed_skills,
                SkillsCommands.REMOVE.value: self._remove_skills,
                # Collection management commands
                SkillsCommands.COLLECTION_LIST.value: self._collection_list,
                SkillsCommands.COLLECTION_ADD.value: self._collection_add,
                SkillsCommands.COLLECTION_REMOVE.value: self._collection_remove,
                SkillsCommands.COLLECTION_ENABLE.value: self._collection_enable,
                SkillsCommands.COLLECTION_DISABLE.value: self._collection_disable,
                SkillsCommands.COLLECTION_SET_DEFAULT.value: self._collection_set_default,
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
        """Deploy skills using two-phase sync: cache → deploy.

        Phase 3 Integration (1M-486): Uses Git skill source manager for deployment.
        - Phase 1: Sync skills to ~/.claude-mpm/cache/skills/ (if needed)
        - Phase 2: Deploy from cache to project .claude-mpm/skills/

        This replaces bundled skill deployment with a multi-project
        architecture where one cache serves multiple project deployments.
        """
        try:
            from pathlib import Path

            from ...config.skill_sources import SkillSourceConfiguration
            from ...services.skills.git_skill_source_manager import (
                GitSkillSourceManager,
            )

            force = getattr(args, "force", False)
            specific_skills = getattr(args, "skills", None)

            console.print("\n[bold cyan]Deploying skills...[/bold cyan]\n")

            # Initialize git skill source manager
            config = SkillSourceConfiguration.load()
            git_skill_manager = GitSkillSourceManager(config)
            project_dir = Path.cwd()

            # Phase 1: Sync skills to cache
            console.print("[dim]Phase 1: Syncing skills to cache...[/dim]")
            sync_results = git_skill_manager.sync_all_sources(force=force)

            synced_count = sum(
                1 for result in sync_results.values() if result.get("synced")
            )
            console.print(f"[dim]Synced {synced_count} skill source(s)[/dim]\n")

            # Phase 2: Deploy from cache to project
            console.print("[dim]Phase 2: Deploying from cache to project...[/dim]\n")
            deploy_result = git_skill_manager.deploy_skills_to_project(
                project_dir=project_dir,
                skill_list=specific_skills,
                force=force,
            )

            # Display results
            if deploy_result["deployed"]:
                console.print(
                    f"[green]✓ Deployed {len(deploy_result['deployed'])} skill(s):[/green]"
                )
                for skill in deploy_result["deployed"]:
                    console.print(f"  • {skill}")
                console.print()

            if deploy_result["updated"]:
                console.print(
                    f"[green]⟳ Updated {len(deploy_result['updated'])} skill(s):[/green]"
                )
                for skill in deploy_result["updated"]:
                    console.print(f"  • {skill}")
                console.print()

            if deploy_result["skipped"]:
                console.print(
                    f"[yellow]⊘ Skipped {len(deploy_result['skipped'])} skill(s) (already up-to-date):[/yellow]"
                )
                for skill in deploy_result["skipped"]:
                    console.print(f"  • {skill}")
                console.print("[dim]Use --force to redeploy[/dim]\n")

            if deploy_result["failed"]:
                console.print(
                    f"[red]✗ Failed to deploy {len(deploy_result['failed'])} skill(s):[/red]"
                )
                for skill in deploy_result["failed"]:
                    console.print(f"  • {skill}")
                console.print()

            # Summary
            success_count = len(deploy_result["deployed"]) + len(
                deploy_result["updated"]
            )
            total = (
                success_count
                + len(deploy_result["skipped"])
                + len(deploy_result["failed"])
            )
            console.print(
                f"[bold]Summary:[/bold] {success_count} deployed/updated, "
                f"{len(deploy_result['skipped'])} skipped, "
                f"{len(deploy_result['failed'])} errors (Total: {total})\n"
            )

            console.print(
                f"[dim]Deployment directory: {deploy_result['deployment_dir']}[/dim]\n"
            )

            # Exit with error if any deployments failed
            exit_code = 1 if deploy_result["failed"] else 0
            return CommandResult(
                success=not deploy_result["failed"],
                message=f"Deployed {success_count} skills from cache",
                exit_code=exit_code,
            )

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

    def _deploy_from_github(self, args) -> CommandResult:
        """Deploy skills from GitHub repository."""
        try:
            collection = getattr(args, "collection", None)
            toolchain = getattr(args, "toolchain", None)
            categories = getattr(args, "categories", None)
            force = getattr(args, "force", False)

            if collection:
                console.print(
                    f"\n[bold cyan]Deploying skills from collection '{collection}'...[/bold cyan]\n"
                )
            else:
                console.print(
                    "\n[bold cyan]Deploying skills from default collection...[/bold cyan]\n"
                )

            # Selective deployment is ALWAYS enabled (deploy only agent-referenced skills)
            # This ensures only skills linked to deployed agents are deployed
            result = self.skills_deployer.deploy_skills(
                collection=collection,
                toolchain=toolchain,
                categories=categories,
                force=force,
                selective=True,  # Always use selective deployment
            )

            # Display results
            # Show selective mode summary
            if result.get("selective_mode"):
                total_available = result.get("total_available", 0)
                deployed_count = result["deployed_count"]
                console.print(
                    f"[cyan]📌 Selective deployment: {deployed_count} agent-referenced skills "
                    f"(out of {total_available} available)[/cyan]"
                )
                console.print(
                    "[dim]Use 'claude-mpm skills configure' to manually select skills[/dim]\n"
                )

            if result["deployed_count"] > 0:
                console.print(
                    f"[green]✓ Deployed {result['deployed_count']} skill(s):[/green]"
                )
                for skill in result["deployed_skills"]:
                    console.print(f"  • {skill}")
                console.print()

            if result["skipped_count"] > 0:
                console.print(
                    f"[yellow]⊘ Skipped {result['skipped_count']} skill(s) (already deployed):[/yellow]"
                )
                for skill in result["skipped_skills"]:
                    console.print(f"  • {skill}")
                console.print("[dim]Use --force to redeploy[/dim]\n")

            if result["errors"]:
                console.print(f"[red]✗ {len(result['errors'])} error(s):[/red]")
                for error in result["errors"]:
                    console.print(f"  • {error}")
                console.print()

            # Show cleanup results
            cleanup = result.get("cleanup", {})
            if cleanup.get("removed_count", 0) > 0:
                console.print(
                    f"[yellow]🧹 Removed {cleanup['removed_count']} orphaned skill(s):[/yellow]"
                )
                for skill in cleanup.get("removed_skills", []):
                    console.print(f"  • {skill}")
                console.print()

            # Show restart instructions
            if result["restart_instructions"]:
                console.print(
                    Panel(
                        result["restart_instructions"],
                        title="⚠️  Important",
                        border_style="yellow",
                    )
                )
                console.print()

            exit_code = 1 if result["errors"] else 0
            return CommandResult(success=not result["errors"], exit_code=exit_code)

        except Exception as e:
            console.print(f"[red]Error deploying from GitHub: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _list_available_github_skills(self, args) -> CommandResult:
        """List available skills from GitHub repository."""
        try:
            collection = getattr(args, "collection", None)

            if collection:
                console.print(
                    f"\n[bold cyan]Fetching skills from collection '{collection}'...[/bold cyan]\n"
                )
            else:
                console.print(
                    "\n[bold cyan]Fetching skills from default collection...[/bold cyan]\n"
                )

            result = self.skills_deployer.list_available_skills(collection=collection)

            if result.get("error"):
                console.print(f"[red]Error: {result['error']}[/red]")
                return CommandResult(
                    success=False, message=result["error"], exit_code=1
                )

            console.print(
                f"[green]Found {result['total_skills']} available skills[/green]\n"
            )

            # Display by category
            console.print("[bold yellow]By Category:[/bold yellow]\n")
            for category, skills in sorted(result["by_category"].items()):
                console.print(f"  [cyan]{category}[/cyan] ({len(skills)} skills)")
                if hasattr(args, "verbose") and args.verbose:
                    for skill in sorted(skills, key=lambda s: s.get("name", "")):
                        console.print(f"    • {skill.get('name', 'unknown')}")
            console.print()

            # Display by toolchain
            console.print("[bold yellow]By Toolchain:[/bold yellow]\n")
            for toolchain, skills in sorted(result["by_toolchain"].items()):
                console.print(f"  [cyan]{toolchain}[/cyan] ({len(skills)} skills)")
                if hasattr(args, "verbose") and args.verbose:
                    for skill in sorted(skills, key=lambda s: s.get("name", "")):
                        console.print(f"    • {skill.get('name', 'unknown')}")
            console.print()

            return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error listing available skills: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _check_deployed_skills(self, args) -> CommandResult:
        """Check currently deployed skills in ~/.claude/skills/."""
        try:
            result = self.skills_deployer.check_deployed_skills()

            console.print("\n[bold cyan]Claude Code Skills Status:[/bold cyan]\n")
            console.print(f"[dim]Directory: {result['claude_skills_dir']}[/dim]\n")

            if result["deployed_count"] == 0:
                console.print("[yellow]No skills currently deployed.[/yellow]")
                console.print(
                    "[dim]Use 'claude-mpm skills deploy-github' to deploy skills.[/dim]\n"
                )
                return CommandResult(success=True, exit_code=0)

            console.print(
                f"[green]{result['deployed_count']} skill(s) deployed:[/green]\n"
            )

            # Create table for deployed skills
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Skill Name", style="green")
            table.add_column("Path", style="dim")

            for skill in sorted(result["skills"], key=lambda s: s["name"]):
                table.add_row(skill["name"], skill["path"])

            console.print(table)
            console.print()

            return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error checking deployed skills: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _remove_skills(self, args) -> CommandResult:
        """Remove deployed skills."""
        try:
            skill_names = getattr(args, "skill_names", None)
            remove_all = getattr(args, "all", False)

            if remove_all:
                skill_names = None
                console.print(
                    "\n[bold yellow]Removing ALL deployed skills...[/bold yellow]\n"
                )
            elif skill_names:
                console.print(
                    f"\n[bold cyan]Removing {len(skill_names)} skill(s)...[/bold cyan]\n"
                )
            else:
                console.print("[red]Error: Specify skill names or use --all[/red]")
                return CommandResult(success=False, exit_code=1)

            result = self.skills_deployer.remove_skills(skill_names)

            if result["removed_count"] > 0:
                console.print(
                    f"[green]✓ Removed {result['removed_count']} skill(s):[/green]"
                )
                for skill in result["removed_skills"]:
                    console.print(f"  • {skill}")
                console.print()

            if result["errors"]:
                console.print(f"[red]✗ {len(result['errors'])} error(s):[/red]")
                for error in result["errors"]:
                    console.print(f"  • {error}")
                console.print()

            exit_code = 1 if result["errors"] else 0
            return CommandResult(success=not result["errors"], exit_code=exit_code)

        except Exception as e:
            console.print(f"[red]Error removing skills: {e}[/red]")
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

    # === Collection Management Commands ===

    def _collection_list(self, args) -> CommandResult:
        """List all configured skill collections."""
        try:
            result = self.skills_deployer.list_collections()

            console.print("\n[bold cyan]Skill Collections:[/bold cyan]\n")
            console.print(
                f"[dim]Default collection: {result['default_collection']}[/dim]"
            )
            console.print(
                f"[dim]Enabled: {result['enabled_count']} / {result['total_count']}[/dim]\n"
            )

            if not result["collections"]:
                console.print("[yellow]No collections configured.[/yellow]")
                console.print(
                    "[dim]Use 'claude-mpm skills collection-add' to add a collection.[/dim]\n"
                )
                return CommandResult(success=True, exit_code=0)

            # Create table for collections
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Name", style="green")
            table.add_column("URL", style="white")
            table.add_column("Priority", justify="center")
            table.add_column("Enabled", justify="center")
            table.add_column("Last Update", style="dim")
            table.add_column("Default", justify="center")

            # Sort by priority
            sorted_collections = sorted(
                result["collections"].items(), key=lambda x: x[1].get("priority", 999)
            )

            for name, config in sorted_collections:
                enabled_icon = "✓" if config.get("enabled", True) else "✗"
                default_icon = "⭐" if name == result["default_collection"] else ""
                last_update = config.get("last_update") or "Never"

                table.add_row(
                    name,
                    config["url"],
                    str(config.get("priority", "N/A")),
                    enabled_icon,
                    last_update,
                    default_icon,
                )

            console.print(table)
            console.print()

            return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error listing collections: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _collection_add(self, args) -> CommandResult:
        """Add a new skill collection."""
        try:
            name = getattr(args, "collection_name", None)
            url = getattr(args, "collection_url", None)
            priority = getattr(args, "priority", 99)

            if not name or not url:
                console.print("[red]Error: Collection name and URL are required[/red]")
                console.print(
                    "[dim]Usage: claude-mpm skills collection-add NAME URL [--priority N][/dim]"
                )
                return CommandResult(success=False, exit_code=1)

            console.print(f"\n[bold cyan]Adding collection '{name}'...[/bold cyan]\n")

            result = self.skills_deployer.add_collection(name, url, priority)

            console.print(f"[green]✓ {result['message']}[/green]")
            console.print(f"  [dim]URL: {url}[/dim]")
            console.print(f"  [dim]Priority: {priority}[/dim]\n")

            return CommandResult(success=True, exit_code=0)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _collection_remove(self, args) -> CommandResult:
        """Remove a skill collection."""
        try:
            name = getattr(args, "collection_name", None)

            if not name:
                console.print("[red]Error: Collection name is required[/red]")
                console.print(
                    "[dim]Usage: claude-mpm skills collection-remove NAME[/dim]"
                )
                return CommandResult(success=False, exit_code=1)

            console.print(
                f"\n[bold yellow]Removing collection '{name}'...[/bold yellow]\n"
            )

            result = self.skills_deployer.remove_collection(name)

            console.print(f"[green]✓ {result['message']}[/green]")
            if result.get("directory_removed"):
                console.print("  [dim]Collection directory removed[/dim]")
            elif result.get("directory_error"):
                console.print(
                    f"  [yellow]Warning: {result['directory_error']}[/yellow]"
                )
            console.print()

            return CommandResult(success=True, exit_code=0)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _collection_enable(self, args) -> CommandResult:
        """Enable a disabled collection."""
        try:
            name = getattr(args, "collection_name", None)

            if not name:
                console.print("[red]Error: Collection name is required[/red]")
                console.print(
                    "[dim]Usage: claude-mpm skills collection-enable NAME[/dim]"
                )
                return CommandResult(success=False, exit_code=1)

            result = self.skills_deployer.enable_collection(name)

            console.print(f"\n[green]✓ {result['message']}[/green]\n")

            return CommandResult(success=True, exit_code=0)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _collection_disable(self, args) -> CommandResult:
        """Disable a collection."""
        try:
            name = getattr(args, "collection_name", None)

            if not name:
                console.print("[red]Error: Collection name is required[/red]")
                console.print(
                    "[dim]Usage: claude-mpm skills collection-disable NAME[/dim]"
                )
                return CommandResult(success=False, exit_code=1)

            result = self.skills_deployer.disable_collection(name)

            console.print(f"\n[green]✓ {result['message']}[/green]\n")

            return CommandResult(success=True, exit_code=0)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)

    def _collection_set_default(self, args) -> CommandResult:
        """Set the default collection."""
        try:
            name = getattr(args, "collection_name", None)

            if not name:
                console.print("[red]Error: Collection name is required[/red]")
                console.print(
                    "[dim]Usage: claude-mpm skills collection-set-default NAME[/dim]"
                )
                return CommandResult(success=False, exit_code=1)

            result = self.skills_deployer.set_default_collection(name)

            console.print(f"\n[green]✓ {result['message']}[/green]")
            if result.get("previous_default"):
                console.print(f"  [dim]Previous: {result['previous_default']}[/dim]")
            console.print()

            return CommandResult(success=True, exit_code=0)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return CommandResult(success=False, message=str(e), exit_code=1)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")

    def _configure_skills(self, args) -> CommandResult:
        """Interactive skills configuration using configuration.yaml.

        Provides checkbox-based selection interface matching agents configure UX:
        - Shows current mode (user_defined vs agent_referenced)
        - If agent mode: shows agent-scanned skills
        - Allows switching to user_defined mode and selecting skills
        - Can reset to agent mode (clears user_defined)
        - Saves selections to configuration.yaml

        Configuration structure:
        ```yaml
        skills:
          agent_referenced:  # Auto-populated from agent scan (read-only)
            - systematic-debugging
            - typescript-core
          user_defined:      # User override - if set, ONLY these are deployed
            []               # Empty = use agent_referenced
        ```
        """
        try:
            from pathlib import Path

            import questionary
            import yaml
            from questionary import Choice, Style
            from rich.prompt import Prompt

            from ...services.skills.selective_skill_deployer import (
                get_skills_to_deploy,
            )

            # Questionary style (matching agents configure)
            QUESTIONARY_STYLE = Style(
                [
                    (
                        "selected",
                        "fg:#e0e0e0 bold",
                    ),  # Light gray - excellent readability
                    (
                        "pointer",
                        "fg:#ffd700 bold",
                    ),  # Gold/yellow - highly visible pointer
                    ("highlighted", "fg:#e0e0e0"),  # Light gray - clear hover state
                    (
                        "question",
                        "fg:#e0e0e0 bold",
                    ),  # Light gray bold - prominent questions
                    ("checkbox", "fg:#00ff00"),  # Green - for checked boxes
                    (
                        "checkbox-selected",
                        "fg:#00ff00 bold",
                    ),  # Green bold - for checked selected boxes
                ]
            )

            console.print("\n[bold cyan]Skills Configuration Manager[/bold cyan]\n")

            # Load current configuration
            project_config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"
            skills_to_deploy, current_mode = get_skills_to_deploy(project_config_path)

            # Display current mode and skill count
            console.print(f"[bold]Current Mode:[/bold] [cyan]{current_mode}[/cyan]")
            console.print(
                f"[bold]Active Skills:[/bold] {len(skills_to_deploy)} skills\n"
            )

            if current_mode == "agent_referenced":
                console.print(
                    "[dim]Agent mode: Skills are auto-detected from deployed agents[/dim]"
                )
                console.print(
                    "[dim]Switch to user mode to manually select skills[/dim]\n"
                )
            else:
                console.print(
                    "[dim]User mode: You've manually selected which skills to deploy[/dim]"
                )
                console.print("[dim]Reset to agent mode to use auto-detection[/dim]\n")

            # Offer mode switching
            action_choices = [
                Choice("View current skills", value="view"),
                Choice("Switch to user mode (manual selection)", value="switch_user"),
                Choice("Reset to agent mode (auto-detection)", value="reset_agent"),
                Choice("Cancel", value="cancel"),
            ]

            action = questionary.select(
                "What would you like to do?",
                choices=action_choices,
                style=QUESTIONARY_STYLE,
            ).ask()

            if action == "cancel" or action is None:
                console.print("[yellow]Configuration cancelled[/yellow]")
                return CommandResult(success=True, exit_code=0)

            if action == "view":
                # Display current skills
                console.print("\n[bold]Current Skills:[/bold]\n")
                for skill in sorted(skills_to_deploy):
                    console.print(f"  • {skill}")
                console.print()
                Prompt.ask("\nPress Enter to continue")
                return CommandResult(success=True, exit_code=0)

            if action == "reset_agent":
                # Reset to agent mode by clearing user_defined
                with open(project_config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

                if "skills" not in config:
                    config["skills"] = {}

                config["skills"]["user_defined"] = []

                with open(project_config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                console.print(
                    "\n[green]✓ Reset to agent mode - skills will be auto-detected from agents[/green]\n"
                )
                Prompt.ask("\nPress Enter to continue")
                return CommandResult(success=True, exit_code=0)

            # Switch to user mode - manual skill selection
            if action == "switch_user":
                console.print(
                    "\n[bold cyan]Switching to User Mode - Manual Skill Selection[/bold cyan]\n"
                )
                console.print("[dim]Fetching available skills from GitHub...[/dim]\n")

                # Get available skills
                available_result = self.skills_deployer.list_available_skills()

                if available_result.get("error"):
                    console.print(f"[red]Error: {available_result['error']}[/red]")
                    return CommandResult(
                        success=False, message=available_result["error"], exit_code=1
                    )

                # Flatten skills by category
                all_skills = []
                for category, skills in available_result.get("by_category", {}).items():
                    for skill in skills:
                        skill_name = skill.get("name", "unknown")
                        is_currently_selected = skill_name in skills_to_deploy
                        skill_info = {
                            "name": skill_name,
                            "category": category,
                            "is_selected": is_currently_selected,
                        }
                        all_skills.append(skill_info)

                # Sort by selection status (selected first), then by name
                all_skills.sort(key=lambda s: (not s["is_selected"], s["name"]))

                # Build checkbox choices
                while True:
                    skill_choices = []

                    for skill in all_skills:
                        skill_name = skill["name"]
                        category = skill["category"]
                        is_selected = skill["is_selected"]

                        # Format: "skill-name (category)"
                        choice_text = f"{skill_name} ({category})"

                        # Pre-select if currently in skills_to_deploy
                        choice = Choice(
                            title=choice_text, value=skill_name, checked=is_selected
                        )

                        skill_choices.append(choice)

                    # Display checkbox selection
                    selected_skills = questionary.checkbox(
                        "Select skills (Space to toggle, Enter to confirm):",
                        choices=skill_choices,
                        style=QUESTIONARY_STYLE,
                    ).ask()

                    if selected_skills is None:
                        # User cancelled (Ctrl+C)
                        console.print("[yellow]Skills configuration cancelled[/yellow]")
                        return CommandResult(success=True, exit_code=0)

                    # Show summary
                    console.print("\n[bold]Selected Skills:[/bold]")
                    console.print(f"  {len(selected_skills)} skills selected\n")

                    if selected_skills:
                        for skill in sorted(selected_skills):
                            console.print(f"  • {skill}")
                        console.print()

                    # Ask user to confirm, adjust, or cancel
                    confirm_action = questionary.select(
                        "\nWhat would you like to do?",
                        choices=[
                            Choice("Save to configuration", value="apply"),
                            Choice("Adjust selection", value="adjust"),
                            Choice("Cancel", value="cancel"),
                        ],
                        default="apply",
                        style=QUESTIONARY_STYLE,
                    ).ask()

                    if confirm_action == "cancel":
                        console.print("[yellow]Configuration cancelled[/yellow]")
                        Prompt.ask("\nPress Enter to continue")
                        return CommandResult(success=True, exit_code=0)

                    if confirm_action == "adjust":
                        # Update selection state and loop back
                        for skill in all_skills:
                            skill["is_selected"] = skill["name"] in selected_skills
                        console.print("\n[dim]Adjusting selection...[/dim]\n")
                        continue

                    # Save to configuration.yaml
                    with open(project_config_path, encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}

                    if "skills" not in config:
                        config["skills"] = {}

                    config["skills"]["user_defined"] = sorted(selected_skills)

                    with open(project_config_path, "w", encoding="utf-8") as f:
                        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                    console.print(
                        f"\n[green]✓ Saved {len(selected_skills)} skills to user_defined mode[/green]"
                    )
                    console.print(
                        "[yellow]⚠️  Important:[/yellow] Run [cyan]claude-mpm init[/cyan] to deploy these skills\n"
                    )
                    Prompt.ask("\nPress Enter to continue")

                    # Exit the loop after successful save
                    break

            return CommandResult(success=True, exit_code=0)

        except Exception as e:
            console.print(f"[red]Error in skills configuration: {e}[/red]")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return CommandResult(success=False, message=str(e), exit_code=1)


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
