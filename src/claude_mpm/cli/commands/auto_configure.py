"""
Auto-Configuration CLI Command for Claude MPM Framework
========================================================

WHY: This module provides a user-friendly CLI interface for the auto-configuration
feature, allowing users to automatically configure agents based on detected toolchain.

DESIGN DECISION: Uses rich for beautiful terminal output, implements interactive
confirmation, and provides comprehensive error handling. Supports both interactive
and non-interactive modes for flexibility.

Part of TSK-0054: Auto-Configuration Feature - Phase 5
"""

import json
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ...core.enums import OperationResult
from ...services.agents.auto_config_manager import AutoConfigManagerService
from ...services.agents.observers import NullObserver
from ...services.core.models.agent_config import ConfigurationResult
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
    agents based on detected project toolchain.
    """

    def __init__(self):
        """Initialize the auto-configure command."""
        super().__init__("auto-configure")
        self.console = Console() if RICH_AVAILABLE else None
        self._auto_config_manager = None

    @property
    def auto_config_manager(self) -> AutoConfigManagerService:
        """Get auto-configuration manager (lazy loaded)."""
        if self._auto_config_manager is None:
            from ...services.agents.auto_config_manager import (
                AutoConfigManagerService,
            )
            from ...services.agents.recommender import AgentRecommenderService
            from ...services.agents.registry import AgentRegistry
            from ...services.project.toolchain_analyzer import (
                ToolchainAnalyzerService,
            )

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

            # Run preview or full configuration
            if dry_run or args.preview if hasattr(args, "preview") else False:
                return self._run_preview(project_path, min_confidence, json_output)
            return self._run_full_configuration(
                project_path, min_confidence, skip_confirmation, json_output
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
        self, project_path: Path, min_confidence: float, json_output: bool
    ) -> CommandResult:
        """Run configuration preview without deploying."""
        # Show analysis spinner
        if self.console and not json_output:
            with self.console.status("[bold green]Analyzing project toolchain..."):
                preview = self.auto_config_manager.preview_configuration(
                    project_path, min_confidence
                )
        else:
            preview = self.auto_config_manager.preview_configuration(
                project_path, min_confidence
            )

        # Output results
        if json_output:
            return self._output_preview_json(preview)
        return self._display_preview(preview)

    def _run_full_configuration(
        self,
        project_path: Path,
        min_confidence: float,
        skip_confirmation: bool,
        json_output: bool,
    ) -> CommandResult:
        """Run full auto-configuration with deployment."""
        # Get preview first
        if self.console and not json_output:
            with self.console.status("[bold green]Analyzing project toolchain..."):
                preview = self.auto_config_manager.preview_configuration(
                    project_path, min_confidence
                )
        else:
            preview = self.auto_config_manager.preview_configuration(
                project_path, min_confidence
            )

        # Display preview (unless JSON output)
        if not json_output:
            self._display_preview(preview)

        # Ask for confirmation (unless skipped)
        if not skip_confirmation and not json_output:
            if not self._confirm_deployment(preview):
                if self.console:
                    self.console.print("\n❌ Operation cancelled by user")
                else:
                    print("\nOperation cancelled by user")
                return CommandResult.error_result("Operation cancelled", exit_code=0)

        # Execute configuration
        import asyncio

        observer = RichProgressObserver(self.console) if self.console else None
        result = asyncio.run(
            self.auto_config_manager.auto_configure(
                project_path,
                confirmation_required=False,  # Already confirmed above
                dry_run=False,
                min_confidence=min_confidence,
                observer=observer,
            )
        )

        # Output results
        if json_output:
            return self._output_result_json(result)
        return self._display_result(result)

    def _display_preview(self, preview) -> CommandResult:
        """Display configuration preview with Rich formatting."""
        if not self.console:
            # Fallback to plain text
            return self._display_preview_plain(preview)

        # Display detected toolchain
        self.console.print("\n📊 Detected Toolchain:", style="bold blue")
        if preview.detected_toolchain and preview.detected_toolchain.components:
            toolchain_table = Table(show_header=True, header_style="bold")
            toolchain_table.add_column("Component", style="cyan")
            toolchain_table.add_column("Version", style="yellow")
            toolchain_table.add_column("Confidence", style="green")

            for component in preview.detected_toolchain.components:
                confidence_pct = int(component.confidence * 100)
                bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)
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
        if preview.recommendations:
            for rec in preview.recommendations:
                confidence_pct = int(rec.confidence * 100)
                icon = "✓" if rec.confidence >= 0.8 else "○"
                self.console.print(
                    f"  {icon} [bold]{rec.agent_id}[/bold] ({confidence_pct}% confidence)"
                )
                self.console.print(f"    Reason: {rec.reasoning}", style="dim")
        else:
            self.console.print("  No agents recommended", style="yellow")

        # Display validation issues
        if preview.validation_result and preview.validation_result.issues:
            self.console.print("\n⚠️  Validation Issues:", style="bold yellow")
            for issue in preview.validation_result.issues:
                severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                    (
                        issue.severity.value
                        if hasattr(issue.severity, "value")
                        else str(issue.severity)
                    ),
                    "•",
                )
                self.console.print(f"  {severity_icon} {issue.message}", style="yellow")

        return CommandResult.success_result()

    def _display_preview_plain(self, preview) -> CommandResult:
        """Display preview in plain text (fallback when Rich not available)."""
        print("\nDetected Toolchain:")
        if preview.detected_toolchain and preview.detected_toolchain.components:
            for component in preview.detected_toolchain.components:
                confidence_pct = int(component.confidence * 100)
                print(f"  - {component.type}: {component.version} ({confidence_pct}%)")
        else:
            print("  No toolchain detected")

        print("\nRecommended Agents:")
        if preview.recommendations:
            for rec in preview.recommendations:
                confidence_pct = int(rec.confidence * 100)
                print(f"  - {rec.agent_id} ({confidence_pct}%)")
                print(f"    Reason: {rec.reasoning}")
        else:
            print("  No agents recommended")

        if preview.validation_result and preview.validation_result.issues:
            print("\nValidation Issues:")
            for issue in preview.validation_result.issues:
                print(f"  - {issue.severity}: {issue.message}")

        return CommandResult.success_result()

    def _confirm_deployment(self, preview) -> bool:
        """Ask user to confirm deployment."""
        if not preview.recommendations:
            return False

        if self.console:
            self.console.print("\n" + "=" * 60)
            self.console.print("Deploy these agents?", style="bold yellow")
            self.console.print("=" * 60)
            response = (
                self.console.input("\n[bold]Proceed? (y/n/s for select):[/bold] ")
                .strip()
                .lower()
            )
        else:
            print("\n" + "=" * 60)
            print("Deploy these agents?")
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

    def _display_result(self, result: ConfigurationResult) -> CommandResult:
        """Display configuration result."""
        if not self.console:
            return self._display_result_plain(result)

        # Display summary
        if result.status == OperationResult.SUCCESS:
            panel = Panel(
                f"✅ Auto-configuration completed successfully!\n\n"
                f"Deployed {len(result.deployed_agents)} agent(s)",
                title="Success",
                border_style="green",
            )
            self.console.print(panel)

            # Show deployed agents
            if result.deployed_agents:
                self.console.print("\n📦 Deployed Agents:", style="bold green")
                for agent_id in result.deployed_agents:
                    self.console.print(f"  ✓ {agent_id}")

            return CommandResult.success_result()

        if result.status == OperationResult.WARNING:
            panel = Panel(
                f"⚠️  Auto-configuration partially completed\n\n"
                f"Deployed: {len(result.deployed_agents)}\n"
                f"Failed: {len(result.failed_agents)}",
                title="Partial Success",
                border_style="yellow",
            )
            self.console.print(panel)

            if result.failed_agents:
                self.console.print("\n❌ Failed Agents:", style="bold red")
                for agent_id in result.failed_agents:
                    error = result.errors.get(agent_id, "Unknown error")
                    self.console.print(f"  ✗ {agent_id}: {error}")

            return CommandResult.error_result("Partial configuration", exit_code=1)

        panel = Panel(
            f"❌ Auto-configuration failed\n\n{result.errors.get('general', 'Unknown error')}",
            title="Error",
            border_style="red",
        )
        self.console.print(panel)

        return CommandResult.error_result("Configuration failed", exit_code=1)

    def _display_result_plain(self, result: ConfigurationResult) -> CommandResult:
        """Display result in plain text (fallback)."""
        if result.status == OperationResult.SUCCESS:
            print("\n✅ Auto-configuration completed successfully!")
            print(f"Deployed {len(result.deployed_agents)} agent(s)")

            if result.deployed_agents:
                print("\nDeployed Agents:")
                for agent_id in result.deployed_agents:
                    print(f"  - {agent_id}")

            return CommandResult.success_result()

        if result.status == OperationResult.WARNING:
            print("\n⚠️  Auto-configuration partially completed")
            print(f"Deployed: {len(result.deployed_agents)}")
            print(f"Failed: {len(result.failed_agents)}")

            if result.failed_agents:
                print("\nFailed Agents:")
                for agent_id in result.failed_agents:
                    error = result.errors.get(agent_id, "Unknown error")
                    print(f"  - {agent_id}: {error}")

            return CommandResult.error_result("Partial configuration", exit_code=1)

        print("\n❌ Auto-configuration failed")
        print(result.errors.get("general", "Unknown error"))

        return CommandResult.error_result("Configuration failed", exit_code=1)

    def _output_preview_json(self, preview) -> CommandResult:
        """Output preview as JSON."""
        output = {
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
                        for c in preview.detected_toolchain.components
                    ]
                    if preview.detected_toolchain
                    else []
                )
            },
            "recommendations": [
                {
                    "agent_id": r.agent_id,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                }
                for r in preview.recommendations
            ],
            "validation": {
                "is_valid": (
                    preview.validation_result.is_valid
                    if preview.validation_result
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
                        for i in preview.validation_result.issues
                    ]
                    if preview.validation_result
                    else []
                ),
            },
        }

        print(json.dumps(output, indent=2))
        return CommandResult.success_result(data=output)

    def _output_result_json(self, result: ConfigurationResult) -> CommandResult:
        """Output result as JSON."""
        output = {
            "status": (
                result.status.value
                if hasattr(result.status, "value")
                else str(result.status)
            ),
            "deployed_agents": result.deployed_agents,
            "failed_agents": result.failed_agents,
            "errors": result.errors,
        }

        print(json.dumps(output, indent=2))

        if result.status == OperationResult.SUCCESS:
            return CommandResult.success_result(data=output)
        return CommandResult.error_result(
            "Configuration failed or partial", exit_code=1, data=output
        )
