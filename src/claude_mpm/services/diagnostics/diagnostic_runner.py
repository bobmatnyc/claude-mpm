"""
Diagnostic runner service for orchestrating health checks.

WHY: Coordinate execution of all diagnostic checks, handle errors gracefully,
and aggregate results for reporting.
"""

import asyncio
import os
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from claude_mpm.core.enums import ValidationSeverity
from claude_mpm.core.logging_utils import get_logger

from .checks import (
    AgentCheck,
    AgentSourcesCheck,
    BaseDiagnosticCheck,
    ClaudeCodeCheck,
    CommonIssuesCheck,
    ConfigurationCheck,
    FilesystemCheck,
    InstallationCheck,
    InstructionsCheck,
    MCPCheck,
    MCPServicesCheck,
    MonitorCheck,
    SkillSourcesCheck,
    StartupLogCheck,
)
from .models import DiagnosticResult, DiagnosticSummary

logger = get_logger(__name__)


class DiagnosticRunner:
    """Orchestrate diagnostic checks and aggregate results.

    WHY: Provides a single entry point for running all diagnostics with
    proper error handling, parallel execution, and result aggregation.
    """

    def __init__(self, verbose: bool = False, fix: bool = False):
        """Initialize diagnostic runner.

        Args:
            verbose: Include detailed information in results
            fix: Attempt to fix issues automatically when a check provides
                a recognized ``fix_command``. Safe operations
                (``mkdir``, ``chmod``, scoped ``rm``, and ``claude-mpm``
                subcommands) are executed; package installs and
                placeholder commands are surfaced as actionable log
                messages instead of being run.
        """
        self.verbose = verbose
        self.fix = fix
        self.logger = logger  # Add logger initialization
        # Define check order (dependencies first)
        self.check_classes: list[type[BaseDiagnosticCheck]] = [
            InstallationCheck,
            ConfigurationCheck,
            FilesystemCheck,
            InstructionsCheck,  # Check instruction files early
            ClaudeCodeCheck,
            AgentCheck,
            AgentSourcesCheck,  # Check agent sources configuration
            SkillSourcesCheck,  # Check skill sources configuration
            MCPCheck,
            MCPServicesCheck,  # Check external MCP services
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
                    status=ValidationSeverity.ERROR,
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
            ClaudeCodeCheck,
            AgentCheck,
            AgentSourcesCheck,
            SkillSourcesCheck,
            MCPCheck,
            MCPServicesCheck,
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
        self, check_classes: list[type[BaseDiagnosticCheck]]
    ) -> list[DiagnosticResult]:
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
                            status=ValidationSeverity.ERROR,
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
                            status=ValidationSeverity.ERROR,
                            message=f"Check execution failed: {e!s}",
                            details={"error": str(e)},
                        )
                    )

        return results

    def run_specific_checks(self, check_names: list[str]) -> DiagnosticSummary:
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
            "claude": ClaudeCodeCheck,
            "claude_code": ClaudeCodeCheck,
            "agents": AgentCheck,
            "agent": AgentCheck,
            "agent-sources": AgentSourcesCheck,
            "agent_sources": AgentSourcesCheck,
            "sources": AgentSourcesCheck,
            "mcp": MCPCheck,
            "mcp_services": MCPServicesCheck,
            "mcp-services": MCPServicesCheck,
            "external": MCPServicesCheck,
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
                    status=ValidationSeverity.ERROR,
                    message=f"Check failed: {e!s}",
                    details={"error": str(e)},
                )
                summary.add_result(error_result)

        return summary

    def _attempt_fix(self, result: DiagnosticResult) -> bool:
        """Attempt to fix an issue automatically.

        WHY: Many diagnostic checks suggest concrete remediations (create a
        missing directory, fix file permissions, deploy agents, etc.). When the
        user opts in via --fix, we execute the safe subset of these
        suggestions and report success/failure for each. Anything we don't
        recognize as safe is logged with a clear actionable message instead
        of being executed blindly.

        Args:
            result: DiagnosticResult with fix_command

        Returns:
            True if a fix was applied successfully, False otherwise
            (including when the suggestion is informational only).
        """
        if not self.fix:
            return False
        if not result.fix_command:
            return False

        fix_command = result.fix_command.strip()
        self.logger.info(f"Attempting to fix: {result.message}")
        self.logger.info(f"Suggested fix: {fix_command}")

        # Skip pure informational/placeholder suggestions. We refuse to
        # execute commands that contain unfilled placeholders like
        # "<source-id>" because they would either fail or do the wrong
        # thing without user input.
        if fix_command.startswith("#"):
            self.logger.info(
                "Fix is informational only; no action taken: %s", fix_command
            )
            return False
        if "<" in fix_command and ">" in fix_command:
            self.logger.warning(
                "Fix command contains a placeholder and requires user input. "
                "Run manually: %s",
                fix_command,
            )
            return False

        try:
            tokens = shlex.split(fix_command)
        except ValueError as exc:
            self.logger.error("Could not parse fix command %r: %s", fix_command, exc)
            return False

        if not tokens:
            return False

        head = tokens[0]

        try:
            # Directory / permission helpers (executed in-process so we
            # don't depend on a particular shell being available).
            if head == "mkdir":
                return self._fix_mkdir(tokens, fix_command)
            if head == "chmod":
                return self._fix_chmod(tokens, fix_command)
            if head == "rm":
                return self._fix_rm(tokens, fix_command)
            if head == "cat":
                # `cat <file>` is purely diagnostic. Don't execute - just
                # tell the user what to look at.
                self.logger.info("Manual inspection required. Run: %s", fix_command)
                return False

            # Package installation suggestions: don't auto-install, just
            # surface a clear actionable message. Auto-installing system
            # packages is too invasive for a doctor command.
            if head in {"pip", "pip3", "pipx"}:
                self.logger.warning(
                    "Dependency fix requires manual approval. Run: %s",
                    fix_command,
                )
                return False

            # claude-mpm subcommands: run via the same Python interpreter
            # to avoid PATH issues when invoked from `claude-mpm doctor
            # --fix`.
            if head == "claude-mpm":
                return self._fix_claude_mpm(tokens[1:], fix_command)

            self.logger.warning(
                "No automatic handler for fix command. Run manually: %s",
                fix_command,
            )
            return False
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("Fix attempt failed for %r: %s", fix_command, exc)
            return False

    def _fix_mkdir(self, tokens: list[str], fix_command: str) -> bool:
        """Create directories for `mkdir [-p] PATH...` style fix commands.

        Supports brace expansion (e.g. `.claude/{agents,responses}`) by
        expanding manually since we don't go through a shell.
        """
        paths: list[str] = []
        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            paths.extend(self._expand_braces(token))

        if not paths:
            self.logger.warning("No paths to create in: %s", fix_command)
            return False

        success = True
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            try:
                path.mkdir(parents=True, exist_ok=True)
                self.logger.info("Created directory: %s", path)
            except OSError as exc:
                self.logger.error("Failed to create %s: %s", path, exc)
                success = False
        return success

    def _fix_chmod(self, tokens: list[str], fix_command: str) -> bool:
        """Apply `chmod [-R] MODE PATH...` style fix commands.

        Only numeric/octal modes and a small set of symbolic shortcuts
        (e.g. `u+w`) are supported. Anything else is left to the user.
        """
        recursive = False
        positional: list[str] = []
        for token in tokens[1:]:
            if token in {"-R", "-r"}:
                recursive = True
                continue
            if token.startswith("-"):
                # Unknown flag; bail out rather than misinterpret.
                self.logger.warning(
                    "Unsupported chmod flag in %r; run manually.", fix_command
                )
                return False
            positional.append(token)

        if len(positional) < 2:
            self.logger.warning("Malformed chmod command: %s", fix_command)
            return False

        mode_token, *raw_paths = positional

        try:
            mode = int(mode_token, 8)
        except ValueError:
            # Symbolic mode (e.g. u+w). Fall back to invoking /bin/chmod
            # so we don't have to reimplement symbolic mode parsing.
            return self._run_chmod_subprocess(tokens, fix_command)

        success = True
        for raw_path in raw_paths:
            path = Path(raw_path).expanduser()
            if not path.exists():
                self.logger.warning("Path does not exist: %s", path)
                success = False
                continue
            try:
                if recursive and path.is_dir():
                    for entry in path.rglob("*"):
                        os.chmod(entry, mode)
                os.chmod(path, mode)
                self.logger.info("Set mode %s on %s", oct(mode), path)
            except OSError as exc:
                self.logger.error("chmod failed on %s: %s", path, exc)
                success = False
        return success

    def _run_chmod_subprocess(self, tokens: list[str], fix_command: str) -> bool:
        """Fallback for chmod with symbolic modes."""
        chmod_path = shutil.which("chmod")
        if chmod_path is None:
            self.logger.warning("chmod binary not found; run manually: %s", fix_command)
            return False
        try:
            completed = subprocess.run(
                [chmod_path, *tokens[1:]],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            self.logger.error("Failed to invoke chmod: %s", exc)
            return False
        if completed.returncode != 0:
            self.logger.error(
                "chmod failed (%s): %s",
                completed.returncode,
                completed.stderr.strip() or completed.stdout.strip(),
            )
            return False
        self.logger.info("Applied: %s", fix_command)
        return True

    def _fix_rm(self, tokens: list[str], fix_command: str) -> bool:
        """Remove files/directories suggested by checks.

        Only handles paths inside the user's home directory or current
        working directory to avoid catastrophic deletions if a check
        produces a malformed command.
        """
        recursive = False
        force = False
        positional: list[str] = []
        for token in tokens[1:]:
            if token.startswith("-"):
                if "r" in token or "R" in token:
                    recursive = True
                if "f" in token:
                    force = True
                continue
            positional.append(token)

        if not positional:
            self.logger.warning("rm command has no paths: %s", fix_command)
            return False

        home = Path.home().resolve()
        cwd = Path.cwd().resolve()
        success = True

        for raw_path in positional:
            path = Path(raw_path).expanduser().resolve()
            try:
                path.relative_to(home)
            except ValueError:
                try:
                    path.relative_to(cwd)
                except ValueError:
                    self.logger.warning(
                        "Refusing to remove path outside home/cwd: %s", path
                    )
                    success = False
                    continue

            if not path.exists():
                if not force:
                    self.logger.warning("Path does not exist: %s", path)
                    success = False
                continue

            try:
                if path.is_dir():
                    if not recursive:
                        self.logger.warning(
                            "Refusing to remove directory without -r: %s",
                            path,
                        )
                        success = False
                        continue
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self.logger.info("Removed: %s", path)
            except OSError as exc:
                self.logger.error("Failed to remove %s: %s", path, exc)
                success = False
        return success

    def _fix_claude_mpm(self, args: list[str], fix_command: str) -> bool:
        """Run a `claude-mpm <subcommand> ...` fix via the current Python.

        Using `sys.executable -m claude_mpm.cli` ensures the fix runs
        against the same installation that is hosting the doctor command.
        """
        if not args:
            self.logger.warning("Empty claude-mpm fix command: %s", fix_command)
            return False

        try:
            completed = subprocess.run(
                [sys.executable, "-m", "claude_mpm.cli", *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.logger.error("Failed to run %r: %s", fix_command, exc)
            return False

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode == 0:
            if stdout:
                self.logger.info("%s", stdout)
            self.logger.info("Fix succeeded: %s", fix_command)
            return True

        self.logger.error(
            "Fix failed (%s): %s",
            completed.returncode,
            stderr or stdout or "no output",
        )
        return False

    @staticmethod
    def _expand_braces(token: str) -> list[str]:
        """Expand a single-level brace expression like `a/{b,c}` -> [a/b, a/c].

        Only supports one set of braces with a comma list; anything more
        complex is returned unchanged so callers can still attempt a
        best-effort fix.
        """
        start = token.find("{")
        end = token.find("}")
        if start == -1 or end == -1 or end < start:
            return [token]
        prefix = token[:start]
        suffix = token[end + 1 :]
        body = token[start + 1 : end]
        parts = [p.strip() for p in body.split(",") if p.strip()]
        if not parts:
            return [token]
        return [f"{prefix}{part}{suffix}" for part in parts]

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
