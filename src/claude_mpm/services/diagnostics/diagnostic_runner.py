"""
Diagnostic runner service for orchestrating health checks.

WHY: Coordinate execution of all diagnostic checks, handle errors gracefully,
and aggregate results for reporting.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Type

from .checks import (
    AgentCheck,
    BaseDiagnosticCheck,
    ClaudeDesktopCheck,
    CommonIssuesCheck,
    ConfigurationCheck,
    FilesystemCheck,
    InstallationCheck,
    InstructionsCheck,
    MCPCheck,
    MonitorCheck,
    StartupLogCheck,
)
from .models import DiagnosticResult, DiagnosticStatus, DiagnosticSummary


class DiagnosticRunner:
    """Orchestrate diagnostic checks and aggregate results.

    WHY: Provides a single entry point for running all diagnostics with
    proper error handling, parallel execution, and result aggregation.
    """

    def __init__(self, verbose: bool = False, fix: bool = False):
        """Initialize diagnostic runner.

        Args:
            verbose: Include detailed information in results
            fix: Attempt to fix issues automatically (future feature)
        """
        self.verbose = verbose
        self.fix = fix
        self.logger = logging.getLogger(__name__)

        # Define check order (dependencies first)
        self.check_classes: List[Type[BaseDiagnosticCheck]] = [
            InstallationCheck,
            ConfigurationCheck,
            FilesystemCheck,
            InstructionsCheck,  # Check instruction files early
            ClaudeDesktopCheck,
            AgentCheck,
            MCPCheck,
            MonitorCheck,
            StartupLogCheck,  # Check startup logs for recent issues
            CommonIssuesCheck,
        ]

    def run_diagnostics(self) -> DiagnosticSummary:
        """Run all diagnostic checks synchronously.

        Returns:
            DiagnosticSummary with all results
        """
        summary = DiagnosticSummary()

        # Run checks in order
        for check_class in self.check_classes:
            try:
                check = check_class(verbose=self.verbose)

                # Skip if check shouldn't run
                if not check.should_run():
                    self.logger.debug(f"Skipping {check.name}")
                    continue

                self.logger.debug(f"Running {check.name}")
                result = check.run()
                summary.add_result(result)

                # If fix mode is enabled and there's a fix available
                if self.fix and result.has_issues and result.fix_command:
                    self._attempt_fix(result)

            except Exception as e:
                self.logger.error(f"Check {check_class.__name__} failed: {e}")
                error_result = DiagnosticResult(
                    category=check_class.__name__.replace("Check", ""),
                    status=DiagnosticStatus.ERROR,
                    message=f"Check failed: {e!s}",
                    details={"error": str(e)},
                )
                summary.add_result(error_result)

        return summary

    def run_diagnostics_parallel(self) -> DiagnosticSummary:
        """Run diagnostic checks in parallel for faster execution.

        WHY: Some checks may involve I/O or network operations, running them
        in parallel can significantly speed up the overall diagnostic process.

        Returns:
            DiagnosticSummary with all results
        """
        summary = DiagnosticSummary()

        # Group checks by dependency level
        # Level 1: No dependencies
        level1 = [
            InstallationCheck,
            FilesystemCheck,
            ConfigurationCheck,
            InstructionsCheck,
        ]
        # Level 2: May depend on level 1
        level2 = [
            ClaudeDesktopCheck,
            AgentCheck,
            MCPCheck,
            MonitorCheck,
            StartupLogCheck,
        ]
        # Level 3: Depends on others
        level3 = [CommonIssuesCheck]

        for level in [level1, level2, level3]:
            level_results = self._run_level_parallel(level)
            for result in level_results:
                summary.add_result(result)

        return summary

    def _run_level_parallel(
        self, check_classes: List[Type[BaseDiagnosticCheck]]
    ) -> List[DiagnosticResult]:
        """Run a group of checks in parallel.

        Args:
            check_classes: List of check classes to run

        Returns:
            List of DiagnosticResults
        """
        results = []

        with ThreadPoolExecutor(max_workers=len(check_classes)) as executor:
            future_to_check = {}

            for check_class in check_classes:
                try:
                    check = check_class(verbose=self.verbose)
                    if check.should_run():
                        future = executor.submit(check.run)
                        future_to_check[future] = check_class.__name__
                except Exception as e:
                    self.logger.error(
                        f"Failed to create check {check_class.__name__}: {e}"
                    )
                    results.append(
                        DiagnosticResult(
                            category=check_class.__name__.replace("Check", ""),
                            status=DiagnosticStatus.ERROR,
                            message=f"Check initialization failed: {e!s}",
                            details={"error": str(e)},
                        )
                    )

            for future in as_completed(future_to_check):
                check_name = future_to_check[future]
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Check {check_name} failed: {e}")
                    results.append(
                        DiagnosticResult(
                            category=check_name.replace("Check", ""),
                            status=DiagnosticStatus.ERROR,
                            message=f"Check execution failed: {e!s}",
                            details={"error": str(e)},
                        )
                    )

        return results

    def run_specific_checks(self, check_names: List[str]) -> DiagnosticSummary:
        """Run only specific diagnostic checks.

        Args:
            check_names: List of check names to run (e.g., ["installation", "agents"])

        Returns:
            DiagnosticSummary with results from specified checks
        """
        summary = DiagnosticSummary()

        # Map check names to classes
        check_map = {
            "installation": InstallationCheck,
            "configuration": ConfigurationCheck,
            "config": ConfigurationCheck,
            "filesystem": FilesystemCheck,
            "fs": FilesystemCheck,
            "claude": ClaudeDesktopCheck,
            "claude_desktop": ClaudeDesktopCheck,
            "agents": AgentCheck,
            "agent": AgentCheck,
            "mcp": MCPCheck,
            "monitor": MonitorCheck,
            "monitoring": MonitorCheck,
            "common": CommonIssuesCheck,
            "issues": CommonIssuesCheck,
        }

        for name in check_names:
            check_class = check_map.get(name.lower())
            if not check_class:
                self.logger.warning(f"Unknown check: {name}")
                continue

            try:
                check = check_class(verbose=self.verbose)
                if check.should_run():
                    result = check.run()
                    summary.add_result(result)
            except Exception as e:
                self.logger.error(f"Check {name} failed: {e}")
                error_result = DiagnosticResult(
                    category=check_class.__name__.replace("Check", ""),
                    status=DiagnosticStatus.ERROR,
                    message=f"Check failed: {e!s}",
                    details={"error": str(e)},
                )
                summary.add_result(error_result)

        return summary

    def _attempt_fix(self, result: DiagnosticResult):
        """Attempt to fix an issue automatically.

        Args:
            result: DiagnosticResult with fix_command
        """
        if not result.fix_command:
            return

        self.logger.info(f"Attempting to fix: {result.message}")
        self.logger.info(f"Running: {result.fix_command}")

        # In a real implementation, this would execute the fix command
        # For now, we just log it
        # TODO: Implement actual fix execution with proper safeguards

    async def run_diagnostics_async(self) -> DiagnosticSummary:
        """Run diagnostics asynchronously (future enhancement).

        WHY: For integration with async frameworks and better performance
        with I/O-bound checks.

        Returns:
            DiagnosticSummary with all results
        """
        # Convert sync execution to async for now
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run_diagnostics)
