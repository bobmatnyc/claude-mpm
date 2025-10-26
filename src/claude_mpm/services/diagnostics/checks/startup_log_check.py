"""
Check startup log health and analyze for common issues.

WHY: Startup logs contain valuable diagnostic information about agent deployment,
MCP configuration, memory loading, and other startup issues that may not be
immediately visible to users.

DESIGN DECISIONS:
- Parse the most recent startup log file
- Identify common error patterns and provide fixes
- Count errors, warnings, and info messages
- Provide actionable recommendations based on log content
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class StartupLogCheck(BaseDiagnosticCheck):
    """Analyze startup logs for errors and issues."""

    # Common error patterns and their fixes
    ERROR_PATTERNS: ClassVar[dict[str, dict[str, Any]]] = {
        r"Agent deployment.*failed": (
            "Agent deployment failure",
            "Check agent configuration in .claude/agents/ and run 'claude-mpm deploy'",
        ),
        r"MCP.*not found": (
            "MCP server not found",
            "Install MCP server: npm install -g @modelcontextprotocol/server",
        ),
        r"Port \d+ .*in use": (
            "Port binding conflict",
            "Kill the process using the port or use --websocket-port to specify a different port",
        ),
        r"Memory loading.*error": (
            "Memory loading failure",
            "Check .claude-mpm/memory/ permissions and run 'claude-mpm memory validate'",
        ),
        r"Permission denied": (
            "Permission error",
            "Check file permissions in project directory and .claude-mpm/",
        ),
        r"ModuleNotFoundError|ImportError": (
            "Missing Python dependency",
            "Install missing dependencies: pip install -e . or pip install claude-mpm[agents]",
        ),
        r"Socket\.IO.*failed|socketio.*error": (
            "Socket.IO initialization failure",
            "Install monitor dependencies: pip install claude-mpm[monitor]",
        ),
        r"Configuration.*invalid|yaml.*error": (
            "Configuration file error",
            "Validate configuration: claude-mpm config validate",
        ),
        r"claude\.json.*large|memory.*issue": (
            "Large .claude.json file",
            "Run 'claude-mpm cleanup-memory' to archive old conversations",
        ),
        r"Failed to start.*daemon": (
            "Daemon startup failure",
            "Check system resources and try: claude-mpm monitor stop && claude-mpm monitor start",
        ),
    }

    # Warning patterns that should be noted
    WARNING_PATTERNS = {
        r"agent.*source.*tracking": "Agent source tracking warning",
        r"dependency.*missing": "Missing optional dependency",
        r"deprecated": "Deprecation warning",
        r"Socket\.IO.*not available": "Monitor mode unavailable",
        r"Response logging.*disabled": "Response logging is disabled",
    }

    @property
    def name(self) -> str:
        return "startup_log_check"

    @property
    def category(self) -> str:
        return "Startup Log"

    def run(self) -> DiagnosticResult:
        """Run startup log diagnostics."""
        try:
            # Find the latest startup log
            log_file = self._find_latest_log()

            if not log_file:
                return DiagnosticResult(
                    category=self.category,
                    status=ValidationSeverity.WARNING,
                    message="No startup logs found",
                    details={
                        "recommendation": "Startup logging will be created on next run"
                    },
                )

            # Parse the log file
            analysis = self._analyze_log_file(log_file)

            # Determine status based on findings
            status = self._determine_status(analysis)
            message = self._create_message(analysis)

            # Build details
            details = {
                "log_file": str(log_file),
                "last_startup": analysis["timestamp"],
                "errors": analysis["error_count"],
                "warnings": analysis["warning_count"],
                "info_messages": analysis["info_count"],
            }

            # Add specific issues found
            if analysis["errors_found"]:
                details["errors_found"] = analysis["errors_found"]

            if analysis["warnings_found"]:
                details["warnings_found"] = analysis["warnings_found"]

            # Add recommendations
            if analysis["recommendations"]:
                details["recommendations"] = analysis["recommendations"]

            # Create sub-results if verbose
            sub_results = []
            if self.verbose and analysis["errors_found"]:
                for error_type, fix in analysis["errors_found"]:
                    sub_results.append(
                        DiagnosticResult(
                            category="Error",
                            status=ValidationSeverity.ERROR,
                            message=error_type,
                            details={"fix": fix},
                        )
                    )

            return DiagnosticResult(
                category=self.category,
                status=status,
                message=message,
                details=details,
                sub_results=sub_results if self.verbose else [],
                fix_command=self._get_fix_command(analysis),
            )

        except Exception as e:
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.ERROR,
                message=f"Startup log check failed: {e!s}",
                details={"error": str(e)},
            )

    def _find_latest_log(self) -> Optional[Path]:
        """Find the most recent startup log file."""
        log_dir = Path.cwd() / ".claude-mpm" / "logs" / "startup"

        if not log_dir.exists():
            return None

        log_files = sorted(
            log_dir.glob("startup-*.log"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        return log_files[0] if log_files else None

    def _analyze_log_file(self, log_file: Path) -> Dict[str, Any]:
        """Analyze the contents of a startup log file."""
        analysis = {
            "timestamp": None,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "debug_count": 0,
            "errors_found": [],
            "warnings_found": [],
            "recommendations": [],
            "startup_successful": False,
        }

        try:
            with Path(log_file).open(
                encoding="utf-8",
            ) as f:
                lines = f.readlines()

            # Extract timestamp from filename or first line
            match = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", log_file.name)
            if match:
                timestamp_str = match.group(1)
                # Convert to readable format
                dt = datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M-%S")
                analysis["timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S")

            # Process each line
            for line in lines:
                # Count log levels
                if " - ERROR - " in line:
                    analysis["error_count"] += 1
                    self._check_error_patterns(line, analysis)
                elif " - WARNING - " in line:
                    analysis["warning_count"] += 1
                    self._check_warning_patterns(line, analysis)
                elif " - INFO - " in line:
                    analysis["info_count"] += 1
                elif " - DEBUG - " in line:
                    analysis["debug_count"] += 1

                # Check for successful startup indicators
                if "Claude session completed successfully" in line:
                    analysis["startup_successful"] = True
                elif "Starting Claude MPM session" in line:
                    analysis["startup_successful"] = True  # At least startup began

            # Generate recommendations based on findings
            self._generate_recommendations(analysis)

        except Exception as e:
            analysis["error_count"] += 1
            analysis["errors_found"].append(("Failed to parse log", str(e)))

        return analysis

    def _check_error_patterns(self, line: str, analysis: Dict[str, Any]) -> None:
        """Check line for known error patterns."""
        for pattern, (error_type, fix) in self.ERROR_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                # Avoid duplicates
                if (error_type, fix) not in analysis["errors_found"]:
                    analysis["errors_found"].append((error_type, fix))
                break

    def _check_warning_patterns(self, line: str, analysis: Dict[str, Any]) -> None:
        """Check line for known warning patterns."""
        for pattern, warning_type in self.WARNING_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                # Avoid duplicates
                if warning_type not in analysis["warnings_found"]:
                    analysis["warnings_found"].append(warning_type)
                break

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> None:
        """Generate recommendations based on analysis."""
        recommendations = []

        # High error count
        if analysis["error_count"] > 5:
            recommendations.append(
                "High error count detected. Review full log for systematic issues."
            )

        # No successful startup
        if not analysis["startup_successful"] and analysis["error_count"] > 0:
            recommendations.append(
                "Startup may have failed. Check error messages above."
            )

        # Specific error recommendations
        if any("MCP" in error[0] for error in analysis["errors_found"]):
            recommendations.append(
                "MCP issues detected. Run 'claude-mpm doctor' for full diagnostics."
            )

        if any("Agent" in error[0] for error in analysis["errors_found"]):
            recommendations.append(
                "Agent issues detected. Run 'claude-mpm agents validate' to check agents."
            )

        if any("memory" in error[0].lower() for error in analysis["errors_found"]):
            recommendations.append(
                "Memory issues detected. Run 'claude-mpm cleanup-memory' to free space."
            )

        analysis["recommendations"] = recommendations

    def _determine_status(self, analysis: Dict[str, Any]):
        """Determine overall status based on analysis."""
        if analysis["error_count"] > 0:
            return ValidationSeverity.ERROR
        if analysis["warning_count"] > 3 or analysis["warning_count"] > 0:
            return ValidationSeverity.WARNING
        return OperationResult.SUCCESS

    def _create_message(self, analysis: Dict[str, Any]) -> str:
        """Create summary message based on analysis."""
        if analysis["error_count"] > 0:
            return f"Startup has {analysis['error_count']} error(s)"
        if analysis["warning_count"] > 0:
            return f"Startup successful with {analysis['warning_count']} warning(s)"
        if analysis["startup_successful"]:
            return "Last startup was successful"
        return "Startup log is clean"

    def _get_fix_command(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Get the most relevant fix command based on errors found."""
        if not analysis["errors_found"]:
            return None

        # Priority order for fix commands
        for _error_type, fix in analysis["errors_found"]:
            if "claude-mpm" in fix:
                # Extract claude-mpm command from fix suggestion
                match = re.search(r'(claude-mpm [^\'"\n]+)', fix)
                if match:
                    return match.group(1)
            elif "pip install" in fix:
                match = re.search(r'(pip install [^\'"\n]+)', fix)
                if match:
                    return match.group(1)

        return None
