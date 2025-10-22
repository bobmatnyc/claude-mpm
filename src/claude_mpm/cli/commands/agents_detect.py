"""
Agents Detect CLI Command for Claude MPM Framework
===================================================

WHY: This module provides a CLI interface for detecting project toolchain
without making any changes. Useful for debugging and verification of the
toolchain detection system.

DESIGN DECISION: Focused solely on detection and display, with no side effects.
Supports multiple output formats for different use cases (human-readable,
JSON for scripting).

Part of TSK-0054: Auto-Configuration Feature - Phase 5
"""

import json
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ...services.project.toolchain_analyzer import ToolchainAnalyzerService
from ..shared import BaseCommand, CommandResult


class AgentsDetectCommand(BaseCommand):
    """
    Handle agents detect CLI command.

    This command analyzes the project to detect languages, frameworks,
    and deployment targets without making any configuration changes.
    """

    def __init__(self):
        """Initialize the agents detect command."""
        super().__init__("agents-detect")
        self.console = Console() if RICH_AVAILABLE else None
        self._toolchain_analyzer = None

    @property
    def toolchain_analyzer(self) -> ToolchainAnalyzerService:
        """Get toolchain analyzer (lazy loaded)."""
        if self._toolchain_analyzer is None:
            self._toolchain_analyzer = ToolchainAnalyzerService()
        return self._toolchain_analyzer

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

        return None

    def run(self, args) -> CommandResult:
        """
        Execute agents detect command.

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
            json_output = args.json if hasattr(args, "json") and args.json else False
            verbose = (
                args.verbose if hasattr(args, "verbose") and args.verbose else False
            )

            # Analyze toolchain
            if self.console and not json_output:
                with self.console.status("[bold green]Analyzing project toolchain..."):
                    analysis = self.toolchain_analyzer.analyze_project(
                        str(project_path)
                    )
            else:
                analysis = self.toolchain_analyzer.analyze_project(str(project_path))

            # Output results
            if json_output:
                return self._output_json(analysis, verbose)
            return self._display_results(analysis, verbose)

        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n\n❌ Operation cancelled by user")
            else:
                print("\n\nOperation cancelled by user")
            return CommandResult.error_result("Operation cancelled", exit_code=130)

        except Exception as e:
            self.logger.exception("Toolchain detection failed")
            error_msg = f"Toolchain detection failed: {e!s}"
            if self.console:
                self.console.print(f"\n❌ {error_msg}")
            else:
                print(f"\n{error_msg}")
            return CommandResult.error_result(error_msg)

    def _display_results(self, analysis, verbose: bool) -> CommandResult:
        """Display toolchain analysis results with Rich formatting."""
        if not self.console:
            return self._display_results_plain(analysis, verbose)

        # Display header
        self.console.print("\n📊 Project Toolchain Analysis", style="bold blue")
        self.console.print(f"Project: {analysis.project_path}\n")

        # Display detected languages
        if analysis.languages:
            self.console.print("🔤 Detected Languages:", style="bold green")
            lang_table = Table(show_header=True, header_style="bold")
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Version", style="yellow")
            lang_table.add_column("Confidence", style="green")
            if verbose:
                lang_table.add_column("Evidence", style="dim")

            for lang in analysis.languages:
                confidence_pct = int(lang.confidence * 100)
                bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)
                confidence_str = f"{bar} {confidence_pct}%"

                if verbose:
                    evidence = ", ".join(lang.evidence[:3])  # First 3 items
                    if len(lang.evidence) > 3:
                        evidence += f" (+{len(lang.evidence) - 3} more)"
                    lang_table.add_row(
                        lang.language,
                        lang.version or "Unknown",
                        confidence_str,
                        evidence,
                    )
                else:
                    lang_table.add_row(
                        lang.language, lang.version or "Unknown", confidence_str
                    )

            self.console.print(lang_table)
        else:
            self.console.print("  No languages detected", style="yellow")

        # Display detected frameworks
        if analysis.frameworks:
            self.console.print("\n🏗️  Detected Frameworks:", style="bold green")
            fw_table = Table(show_header=True, header_style="bold")
            fw_table.add_column("Framework", style="cyan")
            fw_table.add_column("Version", style="yellow")
            fw_table.add_column("Category", style="magenta")
            fw_table.add_column("Confidence", style="green")

            for fw in analysis.frameworks:
                confidence_pct = int(fw.confidence * 100)
                bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)
                confidence_str = f"{bar} {confidence_pct}%"

                fw_table.add_row(
                    fw.name,
                    fw.version or "Unknown",
                    (
                        fw.category.value
                        if hasattr(fw.category, "value")
                        else str(fw.category)
                    ),
                    confidence_str,
                )

            self.console.print(fw_table)
        else:
            self.console.print("\n  No frameworks detected", style="yellow")

        # Display deployment targets
        if analysis.deployment_targets:
            self.console.print("\n🚀 Deployment Targets:", style="bold green")
            dt_table = Table(show_header=True, header_style="bold")
            dt_table.add_column("Target", style="cyan")
            dt_table.add_column("Confidence", style="green")
            if verbose:
                dt_table.add_column("Evidence", style="dim")

            for target in analysis.deployment_targets:
                confidence_pct = int(target.confidence * 100)
                bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)
                confidence_str = f"{bar} {confidence_pct}%"

                if verbose:
                    evidence = ", ".join(target.evidence[:3])
                    if len(target.evidence) > 3:
                        evidence += f" (+{len(target.evidence) - 3} more)"
                    dt_table.add_row(
                        (
                            target.target_type.value
                            if hasattr(target.target_type, "value")
                            else str(target.target_type)
                        ),
                        confidence_str,
                        evidence,
                    )
                else:
                    dt_table.add_row(
                        (
                            target.target_type.value
                            if hasattr(target.target_type, "value")
                            else str(target.target_type)
                        ),
                        confidence_str,
                    )

            self.console.print(dt_table)
        else:
            self.console.print("\n  No deployment targets detected", style="yellow")

        # Display all components summary
        if analysis.components:
            self.console.print("\n📦 All Components:", style="bold blue")
            comp_table = Table(show_header=True, header_style="bold")
            comp_table.add_column("Type", style="cyan")
            comp_table.add_column("Name", style="yellow")
            comp_table.add_column("Version", style="magenta")
            comp_table.add_column("Confidence", style="green")

            for comp in analysis.components:
                confidence_pct = int(comp.confidence * 100)
                bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)
                confidence_str = f"{bar} {confidence_pct}%"

                comp_table.add_row(
                    comp.type.value if hasattr(comp.type, "value") else str(comp.type),
                    comp.name or "-",
                    comp.version or "Unknown",
                    confidence_str,
                )

            self.console.print(comp_table)

        # Summary
        self.console.print(
            f"\n✅ Analysis complete: {len(analysis.languages)} language(s), "
            f"{len(analysis.frameworks)} framework(s), "
            f"{len(analysis.deployment_targets)} deployment target(s)",
            style="bold green",
        )

        return CommandResult.success_result()

    def _display_results_plain(self, analysis, verbose: bool) -> CommandResult:
        """Display results in plain text (fallback)."""
        print("\n📊 Project Toolchain Analysis")
        print(f"Project: {analysis.project_path}\n")

        # Languages
        if analysis.languages:
            print("Detected Languages:")
            for lang in analysis.languages:
                confidence_pct = int(lang.confidence * 100)
                print(
                    f"  - {lang.language} {lang.version or 'Unknown'} ({confidence_pct}%)"
                )
                if verbose:
                    print(f"    Evidence: {', '.join(lang.evidence[:5])}")
        else:
            print("No languages detected")

        # Frameworks
        if analysis.frameworks:
            print("\nDetected Frameworks:")
            for fw in analysis.frameworks:
                confidence_pct = int(fw.confidence * 100)
                print(
                    f"  - {fw.name} {fw.version or 'Unknown'} ({fw.category}) ({confidence_pct}%)"
                )
        else:
            print("\nNo frameworks detected")

        # Deployment targets
        if analysis.deployment_targets:
            print("\nDeployment Targets:")
            for target in analysis.deployment_targets:
                confidence_pct = int(target.confidence * 100)
                print(f"  - {target.target_type} ({confidence_pct}%)")
                if verbose:
                    print(f"    Evidence: {', '.join(target.evidence[:5])}")
        else:
            print("\nNo deployment targets detected")

        print(
            f"\nAnalysis complete: {len(analysis.languages)} language(s), "
            f"{len(analysis.frameworks)} framework(s), "
            f"{len(analysis.deployment_targets)} deployment target(s)"
        )

        return CommandResult.success_result()

    def _output_json(self, analysis, verbose: bool) -> CommandResult:
        """Output toolchain analysis as JSON."""
        output = {
            "project_path": analysis.project_path,
            "analysis_time": analysis.analysis_time,
            "languages": [
                {
                    "language": lang.language,
                    "version": lang.version,
                    "confidence": lang.confidence,
                    "evidence": lang.evidence if verbose else None,
                }
                for lang in analysis.languages
            ],
            "frameworks": [
                {
                    "name": fw.name,
                    "version": fw.version,
                    "category": (
                        fw.category.value
                        if hasattr(fw.category, "value")
                        else str(fw.category)
                    ),
                    "confidence": fw.confidence,
                    "config_file": fw.config_file,
                }
                for fw in analysis.frameworks
            ],
            "deployment_targets": [
                {
                    "target_type": (
                        target.target_type.value
                        if hasattr(target.target_type, "value")
                        else str(target.target_type)
                    ),
                    "confidence": target.confidence,
                    "evidence": target.evidence if verbose else None,
                }
                for target in analysis.deployment_targets
            ],
            "components": [
                {
                    "type": (
                        comp.type.value
                        if hasattr(comp.type, "value")
                        else str(comp.type)
                    ),
                    "name": comp.name,
                    "version": comp.version,
                    "confidence": comp.confidence,
                }
                for comp in analysis.components
            ],
        }

        # Remove None values if not verbose
        if not verbose:
            for lang in output["languages"]:
                lang.pop("evidence", None)
            for target in output["deployment_targets"]:
                target.pop("evidence", None)

        print(json.dumps(output, indent=2))
        return CommandResult.success_result(data=output)
