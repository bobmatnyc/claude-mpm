"""
Agents Recommend CLI Command for Claude MPM Framework
======================================================

WHY: This module provides a CLI interface for getting agent recommendations
based on project toolchain without deploying anything. Useful for reviewing
recommendations before committing to deployment.

DESIGN DECISION: Focused on recommendation display with detailed reasoning,
showing users why each agent was recommended. Supports JSON output for
integration with other tools.

Part of TSK-0054: Auto-Configuration Feature - Phase 5
"""

import json
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ...services.agents.recommender import AgentRecommenderService
from ...services.agents.registry import AgentRegistry
from ...services.project.toolchain_analyzer import ToolchainAnalyzerService
from ..shared import BaseCommand, CommandResult


class AgentsRecommendCommand(BaseCommand):
    """
    Handle agents recommend CLI command.

    This command analyzes the project toolchain and recommends appropriate
    agents without deploying them. Shows detailed reasoning for each
    recommendation.
    """

    def __init__(self):
        """Initialize the agents recommend command."""
        super().__init__("agents-recommend")
        self.console = Console() if RICH_AVAILABLE else None
        self._toolchain_analyzer = None
        self._agent_recommender = None

    @property
    def toolchain_analyzer(self) -> ToolchainAnalyzerService:
        """Get toolchain analyzer (lazy loaded)."""
        if self._toolchain_analyzer is None:
            self._toolchain_analyzer = ToolchainAnalyzerService()
        return self._toolchain_analyzer

    @property
    def agent_recommender(self) -> AgentRecommenderService:
        """Get agent recommender (lazy loaded)."""
        if self._agent_recommender is None:
            agent_registry = AgentRegistry()
            self._agent_recommender = AgentRecommenderService(
                agent_registry=agent_registry
            )
        return self._agent_recommender

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
        Execute agents recommend command.

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
            json_output = args.json if hasattr(args, "json") and args.json else False
            show_reasoning = (
                args.show_reasoning
                if hasattr(args, "show_reasoning") and args.show_reasoning
                else True
            )

            # Analyze toolchain
            if self.console and not json_output:
                with self.console.status("[bold green]Analyzing project toolchain..."):
                    analysis = self.toolchain_analyzer.analyze_project(
                        str(project_path)
                    )
            else:
                analysis = self.toolchain_analyzer.analyze_project(str(project_path))

            # Get recommendations
            if self.console and not json_output:
                with self.console.status(
                    "[bold green]Generating agent recommendations..."
                ):
                    recommendations = self.agent_recommender.recommend_agents(
                        analysis, min_confidence
                    )
            else:
                recommendations = self.agent_recommender.recommend_agents(
                    analysis, min_confidence
                )

            # Output results
            if json_output:
                return self._output_json(recommendations, analysis)
            return self._display_results(recommendations, analysis, show_reasoning)

        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n\n❌ Operation cancelled by user")
            else:
                print("\n\nOperation cancelled by user")
            return CommandResult.error_result("Operation cancelled", exit_code=130)

        except Exception as e:
            self.logger.exception("Agent recommendation failed")
            error_msg = f"Agent recommendation failed: {e!s}"
            if self.console:
                self.console.print(f"\n❌ {error_msg}")
            else:
                print(f"\n{error_msg}")
            return CommandResult.error_result(error_msg)

    def _display_results(
        self, recommendations, analysis, show_reasoning: bool
    ) -> CommandResult:
        """Display agent recommendations with Rich formatting."""
        if not self.console:
            return self._display_results_plain(
                recommendations, analysis, show_reasoning
            )

        # Display header
        self.console.print("\n🤖 Agent Recommendations", style="bold blue")
        self.console.print(f"Project: {analysis.project_path}\n")

        # Display quick summary
        if recommendations:
            summary_text = (
                f"Found {len(recommendations)} recommended agent(s) "
                f"for your project based on detected toolchain."
            )
            panel = Panel(summary_text, border_style="green")
            self.console.print(panel)
        else:
            panel = Panel(
                "No agents recommended for this project.\n"
                "Try lowering the confidence threshold with --min-confidence",
                border_style="yellow",
            )
            self.console.print(panel)
            return CommandResult.success_result()

        # Display recommendations table
        self.console.print("\n📋 Recommended Agents:", style="bold green")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Confidence", style="green")
        table.add_column("Priority", style="yellow")
        if show_reasoning:
            table.add_column("Reasoning", style="dim", no_wrap=False)

        for rec in recommendations:
            confidence_pct = int(rec.confidence * 100)
            bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)
            confidence_str = f"{bar} {confidence_pct}%"

            if show_reasoning:
                table.add_row(
                    rec.agent_id,
                    confidence_str,
                    str(rec.priority),
                    rec.reasoning,
                )
            else:
                table.add_row(rec.agent_id, confidence_str, str(rec.priority))

        self.console.print(table)

        # Display match details if reasoning enabled
        if show_reasoning:
            self.console.print("\n🔍 Match Details:", style="bold blue")
            for rec in recommendations:
                self.console.print(f"\n[bold cyan]{rec.agent_id}[/bold cyan]")
                self.console.print(f"  Confidence: {int(rec.confidence * 100)}%")
                self.console.print(f"  Priority: {rec.priority}")
                self.console.print(f"  Reasoning: {rec.reasoning}")

                if rec.matched_capabilities:
                    self.console.print("  Matched capabilities:", style="green")
                    for cap in rec.matched_capabilities[:5]:
                        self.console.print(f"    • {cap}", style="dim")
                    if len(rec.matched_capabilities) > 5:
                        remaining = len(rec.matched_capabilities) - 5
                        self.console.print(f"    ... and {remaining} more", style="dim")

        # Display next steps
        self.console.print("\n💡 Next Steps:", style="bold yellow")
        self.console.print("  1. Review the recommendations and their reasoning")
        self.console.print(
            "  2. Deploy agents with: [bold]claude-mpm auto-configure[/bold]"
        )
        self.console.print(
            "  3. Or preview deployment with: [bold]claude-mpm auto-configure --preview[/bold]"
        )

        return CommandResult.success_result()

    def _display_results_plain(
        self, recommendations, analysis, show_reasoning: bool
    ) -> CommandResult:
        """Display results in plain text (fallback)."""
        print("\n🤖 Agent Recommendations")
        print(f"Project: {analysis.project_path}\n")

        if not recommendations:
            print("No agents recommended for this project.")
            print("Try lowering the confidence threshold with --min-confidence")
            return CommandResult.success_result()

        print(f"Found {len(recommendations)} recommended agent(s) for your project:\n")

        for rec in recommendations:
            confidence_pct = int(rec.confidence * 100)
            print(f"• {rec.agent_id} ({confidence_pct}% confidence)")

            if show_reasoning:
                print(f"  Priority: {rec.priority}")
                print(f"  Reasoning: {rec.reasoning}")

                if rec.matched_capabilities:
                    print("  Matched capabilities:")
                    for cap in rec.matched_capabilities[:5]:
                        print(f"    - {cap}")
                    if len(rec.matched_capabilities) > 5:
                        remaining = len(rec.matched_capabilities) - 5
                        print(f"    ... and {remaining} more")
                print()

        print("\nNext Steps:")
        print("  1. Review the recommendations and their reasoning")
        print("  2. Deploy agents with: claude-mpm auto-configure")
        print("  3. Or preview deployment with: claude-mpm auto-configure --preview")

        return CommandResult.success_result()

    def _output_json(self, recommendations, analysis) -> CommandResult:
        """Output recommendations as JSON."""
        output = {
            "project_path": analysis.project_path,
            "recommendations": [
                {
                    "agent_id": rec.agent_id,
                    "confidence": rec.confidence,
                    "priority": rec.priority,
                    "reasoning": rec.reasoning,
                    "matched_capabilities": rec.matched_capabilities,
                    "requirements": rec.requirements,
                }
                for rec in recommendations
            ],
            "toolchain_summary": {
                "languages": len(analysis.languages),
                "frameworks": len(analysis.frameworks),
                "deployment_targets": len(analysis.deployment_targets),
            },
        }

        print(json.dumps(output, indent=2))
        return CommandResult.success_result(data=output)
