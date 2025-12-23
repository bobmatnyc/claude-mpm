"""
Auto-Configuration CLI Command for Claude MPM Framework
========================================================

WHY: This module provides a user-friendly CLI interface for the auto-configuration
feature, allowing users to automatically configure BOTH agents AND skills based on
detected toolchain.

DESIGN DECISION: Uses rich for beautiful terminal output, implements interactive
confirmation, and provides comprehensive error handling. Supports both interactive
and non-interactive modes for flexibility. Orchestrates both agent auto-config
(via AutoConfigManagerService) and skill recommendations (via SkillsDeployer).

Part of TSK-0054: Auto-Configuration Feature - Phase 5
Unified Auto-Configure: 1M-502 Phase 2
"""

import json
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ...core.enums import OperationResult
from ...services.agents.auto_config_manager import AutoConfigManagerService
from ...services.agents.observers import NullObserver
from ..shared import BaseCommand, CommandResult


class RichProgressObserver(NullObserver):
    """
    Observer that displays deployment progress using Rich.

    WHY: Extends NullObserver to inherit all required abstract method
    implementations while overriding only the methods needed for
    Rich console output.
    """

    def __init__(self, console: "Console"):
        """Initialize the observer.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.progress = None
        self.task_id = None

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """Called when agent deployment starts."""
        if not self.progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
            )
            self.progress.start()

        self.task_id = self.progress.add_task(f"Deploying {agent_name}...", total=100)

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """Called when deployment makes progress."""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, completed=progress)

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: str | None = None
    ) -> None:
        """Called when agent deployment completes."""
        if self.progress and self.task_id is not None:
            if success:
                self.progress.update(self.task_id, completed=100)
                self.console.print(f"✅ {agent_name} deployed successfully")
            else:
                error_msg = f": {error}" if error else ""
                self.console.print(f"❌ {agent_name} deployment failed{error_msg}")

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """Called when all deployments complete."""
        if self.progress:
            self.progress.stop()


class AutoConfigureCommand(BaseCommand):
    """
    Handle auto-configuration CLI commands.

    This command provides a user-friendly interface for automatically configuring
    BOTH agents AND skills based on detected project toolchain.

    Orchestrates:
    1. Agent auto-configuration (via AutoConfigManagerService)
    2. Skills recommendations and deployment (via SkillsDeployer + agent-skill mapping)
    """

    def __init__(self):
        """Initialize the auto-configure command."""
        super().__init__("auto-configure")
        self.console = Console() if RICH_AVAILABLE else None
        self._auto_config_manager = None
        self._skills_deployer = None

    @property
    def auto_config_manager(self) -> AutoConfigManagerService:
        """Get auto-configuration manager (lazy loaded)."""
        if self._auto_config_manager is None:
            from ...services.agents.auto_config_manager import AutoConfigManagerService
            from ...services.agents.recommender import AgentRecommenderService
            from ...services.agents.registry import AgentRegistry
            from ...services.project.toolchain_analyzer import ToolchainAnalyzerService

            # Initialize services with dependency injection
            toolchain_analyzer = ToolchainAnalyzerService()
            agent_registry = AgentRegistry()
            agent_recommender = AgentRecommenderService()

            # Get deployment service
            try:
                from ...services.agents.deployment import AgentDeploymentService

                agent_deployment = AgentDeploymentService()
            except ImportError:
                agent_deployment = None

            self._auto_config_manager = AutoConfigManagerService(
                toolchain_analyzer=toolchain_analyzer,
                agent_recommender=agent_recommender,
                agent_registry=agent_registry,
                agent_deployment=agent_deployment,
            )

        return self._auto_config_manager

    @property
    def skills_deployer(self):
        """Get skills deployer instance (lazy loaded)."""
        if self._skills_deployer is None:
            from ...services.skills_deployer import SkillsDeployerService

            self._skills_deployer = SkillsDeployerService()
        return self._skills_deployer

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Validate project path
        project_path = (
            Path(args.project_path)
            if hasattr(args, "project_path") and args.project_path
            else Path.cwd()
        )
        if not project_path.exists():
            return f"Project path does not exist: {project_path}"

        # Validate min_confidence range
        if hasattr(args, "min_confidence") and args.min_confidence:
            if not 0.0 <= args.min_confidence <= 1.0:
                return "min_confidence must be between 0.0 and 1.0"

        return None

    def run(self, args) -> CommandResult:
        """
        Execute auto-configuration command.

        Returns:
            CommandResult with success status and exit code
        """
        try:
            # Setup logging
            self.setup_logging(args)

            # Validate arguments
            error = self.validate_args(args)
            if error:
                return CommandResult.error_result(error)

            # Get configuration options
            project_path = (
                Path(args.project_path)
                if hasattr(args, "project_path") and args.project_path
                else Path.cwd()
            )
            min_confidence = (
                args.min_confidence
                if hasattr(args, "min_confidence") and args.min_confidence
                else 0.8
            )
            dry_run = (
                args.preview or args.dry_run if hasattr(args, "preview") else False
            )
            skip_confirmation = args.yes if hasattr(args, "yes") and args.yes else False
            json_output = args.json if hasattr(args, "json") and args.json else False

            # Determine what to configure (agents, skills, or both)
            configure_agents = not getattr(args, "skills_only", False)
            configure_skills = not getattr(args, "agents_only", False)

            # Run preview or full configuration
            if dry_run or args.preview if hasattr(args, "preview") else False:
                return self._run_preview(
                    project_path,
                    min_confidence,
                    json_output,
                    configure_agents,
                    configure_skills,
                )
            return self._run_full_configuration(
                project_path,
                min_confidence,
                skip_confirmation,
                json_output,
                configure_agents,
                configure_skills,
            )

        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n\n❌ Operation cancelled by user")
            else:
                print("\n\nOperation cancelled by user")
            return CommandResult.error_result("Operation cancelled", exit_code=130)

        except Exception as e:
            self.logger.exception("Auto-configuration failed")
            error_msg = f"Auto-configuration failed: {e!s}"
            if self.console:
                self.console.print(f"\n❌ {error_msg}")
            else:
                print(f"\n{error_msg}")
            return CommandResult.error_result(error_msg)

    def _run_preview(
        self,
        project_path: Path,
        min_confidence: float,
        json_output: bool,
        configure_agents: bool = True,
        configure_skills: bool = True,
    ) -> CommandResult:
        """Run configuration preview without deploying."""
        # Get agent preview
        agent_preview = None
        if configure_agents:
            if self.console and not json_output:
                with self.console.status("[bold green]Analyzing project toolchain..."):
                    agent_preview = self.auto_config_manager.preview_configuration(
                        project_path, min_confidence
                    )
            else:
                agent_preview = self.auto_config_manager.preview_configuration(
                    project_path, min_confidence
                )

        # Review existing project agents
        agent_review_results = None
        if configure_agents:
            if self.console and not json_output:
                with self.console.status("[bold green]Reviewing existing agents..."):
                    agent_review_results = self._review_project_agents(agent_preview)
            else:
                agent_review_results = self._review_project_agents(agent_preview)

        # Get skills recommendations
        skills_recommendations = None
        if configure_skills:
            if self.console and not json_output:
                with self.console.status("[bold green]Analyzing skill requirements..."):
                    skills_recommendations = self._recommend_skills(agent_preview)
            else:
                skills_recommendations = self._recommend_skills(agent_preview)

        # Output results
        if json_output:
            return self._output_preview_json(
                agent_preview,
                skills_recommendations,
                configure_agents,
                configure_skills,
                agent_review_results,
            )
        return self._display_preview(
            agent_preview,
            skills_recommendations,
            configure_agents,
            configure_skills,
            agent_review_results,
        )

    def _run_full_configuration(
        self,
        project_path: Path,
        min_confidence: float,
        skip_confirmation: bool,
        json_output: bool,
        configure_agents: bool = True,
        configure_skills: bool = True,
    ) -> CommandResult:
        """Run full auto-configuration with deployment."""
        # Get agent preview
        agent_preview = None
        if configure_agents:
            if self.console and not json_output:
                with self.console.status("[bold green]Analyzing project toolchain..."):
                    agent_preview = self.auto_config_manager.preview_configuration(
                        project_path, min_confidence
                    )
            else:
                agent_preview = self.auto_config_manager.preview_configuration(
                    project_path, min_confidence
                )

        # Review existing project agents
        agent_review_results = None
        if configure_agents:
            if self.console and not json_output:
                with self.console.status("[bold green]Reviewing existing agents..."):
                    agent_review_results = self._review_project_agents(agent_preview)
            else:
                agent_review_results = self._review_project_agents(agent_preview)

        # Get skills recommendations
        skills_recommendations = None
        if configure_skills:
            if self.console and not json_output:
                with self.console.status("[bold green]Analyzing skill requirements..."):
                    skills_recommendations = self._recommend_skills(agent_preview)
            else:
                skills_recommendations = self._recommend_skills(agent_preview)

        # Display preview (unless JSON output)
        if not json_output:
            self._display_preview(
                agent_preview,
                skills_recommendations,
                configure_agents,
                configure_skills,
                agent_review_results,
            )

        # Ask for confirmation (unless skipped)
        if not skip_confirmation and not json_output:
            if not self._confirm_deployment(
                agent_preview,
                skills_recommendations,
                configure_agents,
                configure_skills,
                agent_review_results,
            ):
                if self.console:
                    self.console.print("\n❌ Operation cancelled by user")
                else:
                    print("\nOperation cancelled by user")
                return CommandResult.error_result("Operation cancelled", exit_code=0)

        # Archive unused agents (before deploying new ones)
        archive_result = None
        if configure_agents and agent_review_results:
            agents_to_archive = agent_review_results.get("unused", [])
            if agents_to_archive:
                if self.console and not json_output:
                    self.console.print(
                        "\n[bold yellow]Archiving unused agents...[/bold yellow]\n"
                    )
                archive_result = self._archive_agents(agents_to_archive)

        # Execute agent configuration
        agent_result = None
        if configure_agents and agent_preview:
            import asyncio

            observer = RichProgressObserver(self.console) if self.console else None
            agent_result = asyncio.run(
                self.auto_config_manager.auto_configure(
                    project_path,
                    confirmation_required=False,  # Already confirmed above
                    dry_run=False,
                    min_confidence=min_confidence,
                    observer=observer,
                )
            )

        # Deploy skills
        skills_result = None
        if configure_skills and skills_recommendations:
            if self.console and not json_output:
                self.console.print("\n[bold cyan]Deploying skills...[/bold cyan]\n")
            skills_result = self._deploy_skills(skills_recommendations)

        # Output results
        if json_output:
            return self._output_result_json(agent_result, skills_result, archive_result)
        return self._display_result(agent_result, skills_result, archive_result)

    def _display_preview(
        self,
        agent_preview,
        skills_recommendations=None,
        configure_agents=True,
        configure_skills=True,
        agent_review_results=None,
    ) -> CommandResult:
        """Display configuration preview with Rich formatting."""
        if not self.console:
            # Fallback to plain text
            return self._display_preview_plain(
                agent_preview,
                skills_recommendations,
                configure_agents,
                configure_skills,
                agent_review_results,
            )

        # Only show toolchain and agents if configuring agents
        if not configure_agents:
            agent_preview = None

        # Display detected toolchain
        if configure_agents and agent_preview:
            self.console.print("\n📊 Detected Toolchain:", style="bold blue")
            if (
                agent_preview.detected_toolchain
                and agent_preview.detected_toolchain.components
            ):
                toolchain_table = Table(show_header=True, header_style="bold")
                toolchain_table.add_column("Component", style="cyan")
                toolchain_table.add_column("Version", style="yellow")
                toolchain_table.add_column("Confidence", style="green")

                for component in agent_preview.detected_toolchain.components:
                    confidence_pct = int(component.confidence * 100)
                    bar = "█" * (confidence_pct // 10) + "░" * (
                        10 - confidence_pct // 10
                    )
                    confidence_str = f"{bar} {confidence_pct}%"

                    toolchain_table.add_row(
                        (
                            component.type.value
                            if hasattr(component.type, "value")
                            else str(component.type)
                        ),
                        component.version or "Unknown",
                        confidence_str,
                    )

                self.console.print(toolchain_table)
            else:
                self.console.print("  No toolchain detected", style="yellow")

            # Display recommended agents
            self.console.print("\n🤖 Recommended Agents:", style="bold blue")
            if agent_preview.recommendations:
                for rec in agent_preview.recommendations:
                    confidence_pct = int(rec.confidence * 100)
                    icon = "✓" if rec.confidence >= 0.8 else "○"
                    self.console.print(
                        f"  {icon} [bold]{rec.agent_id}[/bold] ({confidence_pct}% confidence)"
                    )
                    self.console.print(f"    Reason: {rec.reasoning}", style="dim")
            else:
                self.console.print("  No agents recommended", style="yellow")

            # Display validation issues
            if (
                agent_preview.validation_result
                and agent_preview.validation_result.issues
            ):
                self.console.print("\n⚠️  Validation Issues:", style="bold yellow")
                for issue in agent_preview.validation_result.issues:
                    severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                        (
                            issue.severity.value
                            if hasattr(issue.severity, "value")
                            else str(issue.severity)
                        ),
                        "•",
                    )
                    self.console.print(
                        f"  {severity_icon} {issue.message}", style="yellow"
                    )

        # Display agent review results
        if configure_agents and agent_review_results:
            self._display_agent_review(agent_review_results)

        # Display recommended skills
        if configure_skills and skills_recommendations:
            self.console.print("\n🎯 Recommended Skills:", style="bold blue")
            for skill in skills_recommendations:
                self.console.print(f"  ✓ [bold]{skill}[/bold]")

        return CommandResult.success_result()

    def _display_preview_plain(
        self,
        agent_preview,
        skills_recommendations=None,
        configure_agents=True,
        configure_skills=True,
        agent_review_results=None,
    ) -> CommandResult:
        """Display preview in plain text (fallback when Rich not available)."""
        if configure_agents and agent_preview:
            print("\nDetected Toolchain:")
            if (
                agent_preview.detected_toolchain
                and agent_preview.detected_toolchain.components
            ):
                for component in agent_preview.detected_toolchain.components:
                    confidence_pct = int(component.confidence * 100)
                    print(
                        f"  - {component.type}: {component.version} ({confidence_pct}%)"
                    )
            else:
                print("  No toolchain detected")

            print("\nRecommended Agents:")
            if agent_preview.recommendations:
                for rec in agent_preview.recommendations:
                    confidence_pct = int(rec.confidence * 100)
                    print(f"  - {rec.agent_id} ({confidence_pct}%)")
                    print(f"    Reason: {rec.reasoning}")
            else:
                print("  No agents recommended")

            if (
                agent_preview.validation_result
                and agent_preview.validation_result.issues
            ):
                print("\nValidation Issues:")
                for issue in agent_preview.validation_result.issues:
                    print(f"  - {issue.severity}: {issue.message}")

        if configure_skills and skills_recommendations:
            print("\nRecommended Skills:")
            for skill in skills_recommendations:
                print(f"  - {skill}")

        return CommandResult.success_result()

    def _confirm_deployment(
        self,
        agent_preview,
        skills_recommendations=None,
        configure_agents=True,
        configure_skills=True,
        agent_review_results=None,
    ) -> bool:
        """Ask user to confirm deployment."""
        has_agents = (
            configure_agents and agent_preview and agent_preview.recommendations
        )
        has_skills = configure_skills and skills_recommendations

        if not has_agents and not has_skills:
            return False

        # Build confirmation message
        items = []
        if has_agents:
            items.append(f"{len(agent_preview.recommendations)} agent(s)")
        if has_skills:
            items.append(f"{len(skills_recommendations)} skill(s)")

        message = f"Deploy {' and '.join(items)}?"

        if self.console:
            self.console.print("\n" + "=" * 60)
            self.console.print(message, style="bold yellow")
            self.console.print("=" * 60)
            response = (
                self.console.input("\n[bold]Proceed? (y/n/s for select):[/bold] ")
                .strip()
                .lower()
            )
        else:
            print("\n" + "=" * 60)
            print(message)
            print("=" * 60)
            response = input("\nProceed? (y/n/s for select): ").strip().lower()

        if response in ["y", "yes"]:
            return True
        if response in ["s", "select"]:
            # TODO: Implement interactive selection
            if self.console:
                self.console.print(
                    "\n⚠️  Interactive selection not yet implemented",
                    style="yellow",
                )
            else:
                print("\nInteractive selection not yet implemented")
            return False
        return False

    def _display_result(
        self,
        agent_result: Optional = None,
        skills_result: Optional[dict] = None,
        archive_result: Optional[dict] = None,
    ) -> CommandResult:
        """Display configuration result."""
        if not self.console:
            return self._display_result_plain(
                agent_result, skills_result, archive_result
            )

        # Determine overall success
        agent_success = (
            (agent_result and agent_result.status == OperationResult.SUCCESS)
            if agent_result
            else True
        )
        skills_success = not skills_result or (
            skills_result and not skills_result.get("errors")
        )
        archive_success = not archive_result or not archive_result.get("errors")
        overall_success = agent_success and skills_success and archive_success

        # Display summary
        if overall_success:
            # Show deployed agents
            if agent_result and agent_result.deployed_agents:
                self.console.print("\n📦 Deployed Agents:", style="bold green")
                for agent_id in agent_result.deployed_agents:
                    self.console.print(f"  ✓ {agent_id}")

            # Show deployed skills
            if skills_result and skills_result.get("deployed"):
                self.console.print("\n🎯 Deployed Skills:", style="bold green")
                for skill in skills_result["deployed"]:
                    self.console.print(f"  ✓ {skill}")

            # Show archived agents
            if archive_result and archive_result.get("archived"):
                self.console.print("\n📁 Archived Agents:", style="bold yellow")
                for archived in archive_result["archived"]:
                    self.console.print(f"  → {archived['name']}")

            # Show restart notification
            self._show_restart_notification(agent_result, skills_result, archive_result)

            return CommandResult.success_result()

        # Partial or complete failure
        has_errors = False
        if agent_result and agent_result.status in [
            OperationResult.WARNING,
            OperationResult.FAILED,
        ]:
            has_errors = True

            if agent_result.status == OperationResult.WARNING:
                self.console.print(
                    "\n⚠️  Agent configuration partially completed", style="yellow"
                )
            else:
                self.console.print("\n❌ Agent configuration failed", style="red")

            if agent_result.failed_agents:
                self.console.print("\n❌ Failed Agents:", style="bold red")
                for agent_id in agent_result.failed_agents:
                    error = agent_result.errors.get(agent_id, "Unknown error")
                    self.console.print(f"  ✗ {agent_id}: {error}")

        if skills_result and skills_result.get("errors"):
            has_errors = True
            self.console.print("\n❌ Skill deployment failed", style="red")
            for error in skills_result["errors"]:
                self.console.print(f"  ✗ {error}")

        return (
            CommandResult.error_result(
                "Configuration partially succeeded"
                if (agent_success or skills_success)
                else "Configuration failed",
                exit_code=1,
            )
            if has_errors
            else CommandResult.success_result()
        )

    def _display_result_plain(
        self,
        agent_result: Optional = None,
        skills_result: Optional[dict] = None,
        archive_result: Optional[dict] = None,
    ) -> CommandResult:
        """Display result in plain text (fallback)."""
        # Determine overall success
        agent_success = (
            (agent_result and agent_result.status == OperationResult.SUCCESS)
            if agent_result
            else True
        )
        skills_success = not skills_result or not skills_result.get("errors")
        overall_success = agent_success and skills_success

        if overall_success:
            print("\n✅ Auto-configuration completed successfully!")

            if agent_result and agent_result.deployed_agents:
                print(f"Deployed {len(agent_result.deployed_agents)} agent(s)")
                print("\nDeployed Agents:")
                for agent_id in agent_result.deployed_agents:
                    print(f"  - {agent_id}")

            if skills_result and skills_result.get("deployed"):
                print(f"\nDeployed {len(skills_result['deployed'])} skill(s)")
                print("\nDeployed Skills:")
                for skill in skills_result["deployed"]:
                    print(f"  - {skill}")

            return CommandResult.success_result()

        # Partial or complete failure
        has_errors = False
        if agent_result and agent_result.status in [
            OperationResult.WARNING,
            OperationResult.FAILED,
        ]:
            has_errors = True
            print(
                "\n⚠️  Agent configuration partially completed"
                if agent_result.status == OperationResult.WARNING
                else "\n❌ Agent configuration failed"
            )

            if agent_result.failed_agents:
                print("\nFailed Agents:")
                for agent_id in agent_result.failed_agents:
                    error = agent_result.errors.get(agent_id, "Unknown error")
                    print(f"  - {agent_id}: {error}")

        if skills_result and skills_result.get("errors"):
            has_errors = True
            print("\n❌ Skill deployment failed")
            for error in skills_result["errors"]:
                print(f"  - {error}")

        return (
            CommandResult.error_result(
                "Configuration partially succeeded"
                if (agent_success or skills_success)
                else "Configuration failed",
                exit_code=1,
            )
            if has_errors
            else CommandResult.success_result()
        )

    def _output_preview_json(
        self,
        agent_preview,
        skills_recommendations=None,
        configure_agents=True,
        configure_skills=True,
        agent_review_results=None,
    ) -> CommandResult:
        """Output preview as JSON."""
        output = {}

        if configure_agents and agent_preview:
            output["agents"] = {
                "detected_toolchain": {
                    "components": (
                        [
                            {
                                "type": (
                                    c.type.value
                                    if hasattr(c.type, "value")
                                    else str(c.type)
                                ),
                                "version": c.version,
                                "confidence": c.confidence,
                            }
                            for c in agent_preview.detected_toolchain.components
                        ]
                        if agent_preview.detected_toolchain
                        else []
                    )
                },
                "recommendations": [
                    {
                        "agent_id": r.agent_id,
                        "confidence": r.confidence,
                        "reasoning": r.reasoning,
                    }
                    for r in agent_preview.recommendations
                ],
                "validation": {
                    "is_valid": (
                        agent_preview.validation_result.is_valid
                        if agent_preview.validation_result
                        else True
                    ),
                    "issues": (
                        [
                            {
                                "severity": (
                                    i.severity.value
                                    if hasattr(i.severity, "value")
                                    else str(i.severity)
                                ),
                                "message": i.message,
                            }
                            for i in agent_preview.validation_result.issues
                        ]
                        if agent_preview.validation_result
                        else []
                    ),
                },
            }

        if configure_skills and skills_recommendations:
            output["skills"] = {
                "recommendations": skills_recommendations,
            }

        print(json.dumps(output, indent=2))
        return CommandResult.success_result(data=output)

    def _output_result_json(
        self,
        agent_result: Optional = None,
        skills_result: Optional[dict] = None,
        archive_result: Optional[dict] = None,
    ) -> CommandResult:
        """Output result as JSON."""
        output = {}

        if agent_result:
            output["agents"] = {
                "status": (
                    agent_result.status.value
                    if hasattr(agent_result.status, "value")
                    else str(agent_result.status)
                ),
                "deployed_agents": agent_result.deployed_agents,
                "failed_agents": agent_result.failed_agents,
                "errors": agent_result.errors,
            }

        if skills_result:
            output["skills"] = skills_result

        print(json.dumps(output, indent=2))

        # Determine overall success
        agent_success = (
            agent_result.status == OperationResult.SUCCESS if agent_result else True
        )
        skills_success = not skills_result or not skills_result.get("errors")
        overall_success = agent_success and skills_success

        if overall_success:
            return CommandResult.success_result(data=output)
        return CommandResult.error_result(
            "Configuration failed or partial", exit_code=1, data=output
        )

    def _recommend_skills(self, agent_preview):
        """Recommend skills based on deployed/recommended agents.

        Args:
            agent_preview: Agent preview result with recommendations

        Returns:
            List of recommended skill names, or None if no agents recommended
        """
        if not agent_preview or not agent_preview.recommendations:
            return None

        # Import agent-skill mapping
        from ...cli.interactive.skills_wizard import AGENT_SKILL_MAPPING

        # Collect recommended skills based on agent types
        recommended_skills = set()
        for rec in agent_preview.recommendations:
            agent_id = rec.agent_id
            # Map agent ID to skill recommendations
            if agent_id in AGENT_SKILL_MAPPING:
                recommended_skills.update(AGENT_SKILL_MAPPING[agent_id])

        return list(recommended_skills) if recommended_skills else None

    def _deploy_skills(self, recommended_skills: list[str]) -> dict:
        """Deploy recommended skills.

        Args:
            recommended_skills: List of skill names to deploy

        Returns:
            Dict with deployment results: {"deployed": [...], "errors": [...]}
        """
        try:
            return self.skills_deployer.deploy_skills(
                skill_names=recommended_skills, force=False
            )
        except Exception as e:
            self.logger.error(f"Failed to deploy skills: {e}")
            return {"deployed": [], "errors": [str(e)]}

    def _review_project_agents(self, agent_preview) -> Optional[dict]:
        """Review existing project agents and categorize them.

        Args:
            agent_preview: Agent preview result with recommendations

        Returns:
            Dictionary with categorized agents or None if no preview
        """
        if not agent_preview:
            return None

        from ...services.agents.agent_review_service import AgentReviewService
        from ...services.agents.deployment.remote_agent_discovery_service import (
            RemoteAgentDiscoveryService,
        )

        # Get managed agents from cache
        agents_cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
        if not agents_cache_dir.exists():
            self.logger.debug("No agents cache found")
            return None

        # Discover managed agents
        discovery_service = RemoteAgentDiscoveryService(agents_cache_dir)
        managed_agents = discovery_service.discover_remote_agents()

        if not managed_agents:
            self.logger.debug("No managed agents found in cache")
            return None

        # Get recommended agent IDs
        recommended_ids = set()
        if agent_preview.recommendations:
            recommended_ids = {rec.agent_id for rec in agent_preview.recommendations}

        # Review project agents
        project_agents_dir = Path.cwd() / ".claude" / "agents"
        review_service = AgentReviewService()
        return review_service.review_project_agents(
            project_agents_dir, managed_agents, recommended_ids
        )

    def _archive_agents(self, agents_to_archive: list[dict]) -> dict:
        """Archive unused agents by moving them to .claude/agents/unused/.

        Args:
            agents_to_archive: List of agent dicts to archive

        Returns:
            Dictionary with archival results
        """
        from ...services.agents.agent_review_service import AgentReviewService

        project_agents_dir = Path.cwd() / ".claude" / "agents"
        review_service = AgentReviewService()
        return review_service.archive_agents(agents_to_archive, project_agents_dir)

    def _display_agent_review(self, review_results: dict) -> None:
        """Display agent review results in the preview.

        Args:
            review_results: Dictionary with categorized agents
        """
        if not self.console:
            return

        # Count agents to archive
        unused_count = len(review_results.get("unused", []))
        outdated_count = len(review_results.get("outdated", []))
        custom_count = len(review_results.get("custom", []))

        if unused_count > 0 or outdated_count > 0 or custom_count > 0:
            self.console.print("\n📋 Existing Agents Review:", style="bold blue")

            # Show custom agents (will be preserved)
            if custom_count > 0:
                self.console.print(
                    "\n  [green]Custom agents (will be preserved):[/green]"
                )
                for agent in review_results["custom"]:
                    self.console.print(f"    ✓ {agent['name']} (v{agent['version']})")

            # Show agents to be archived
            if unused_count > 0:
                self.console.print(
                    "\n  [yellow]Agents to archive (not needed for this toolchain):[/yellow]"
                )
                for agent in review_results["unused"]:
                    reason = (
                        f"outdated (v{agent['current_version']} → v{agent['available_version']})"
                        if "current_version" in agent
                        else "not recommended"
                    )
                    self.console.print(f"    → {agent['name']} ({reason})")
                self.console.print(
                    "    [dim]Will be moved to .claude/agents/unused/[/dim]"
                )

    def _show_restart_notification(
        self, agent_result=None, skills_result=None, archive_result=None
    ) -> None:
        """Show restart notification after configuration is complete.

        Args:
            agent_result: Agent deployment results
            skills_result: Skills deployment results
            archive_result: Agent archival results
        """
        if not self.console:
            return

        # Build summary of changes
        changes = []
        if agent_result and agent_result.deployed_agents:
            changes.append(f"Deployed {len(agent_result.deployed_agents)} agent(s)")
        if skills_result and skills_result.get("deployed"):
            changes.append(f"Deployed {len(skills_result['deployed'])} skill(s)")
        if archive_result and archive_result.get("archived"):
            changes.append(
                f"Archived {len(archive_result['archived'])} unused agent(s) to .claude/agents/unused/"
            )

        if changes:
            self.console.print("\n" + "=" * 70)
            self.console.print("✅ [bold green]Configuration complete![/bold green]")
            self.console.print(
                "\n🔄 [bold yellow]Please restart Claude Code to apply changes:[/bold yellow]"
            )
            self.console.print("   - Quit Claude Code completely")
            self.console.print("   - Relaunch Claude Code")
            self.console.print("\n[bold]Changes applied:[/bold]")
            for change in changes:
                self.console.print(f"  • {change}")
            self.console.print("=" * 70 + "\n")
