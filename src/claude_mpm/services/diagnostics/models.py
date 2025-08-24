"""
Data models for the diagnostic system.

WHY: Define clear data structures for diagnostic results to ensure
consistency across all checks and reporting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DiagnosticStatus(Enum):
    """Status levels for diagnostic results."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class DiagnosticResult:
    """Result from a diagnostic check.

    WHY: Standardized result format ensures consistent reporting
    and makes it easy to aggregate and display results.
    """

    category: str  # e.g., "Installation", "Agents", "MCP Server"
    status: DiagnosticStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_command: Optional[str] = None
    fix_description: Optional[str] = None
    sub_results: List["DiagnosticResult"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "fix_command": self.fix_command,
            "fix_description": self.fix_description,
            "sub_results": [r.to_dict() for r in self.sub_results],
        }

    @property
    def has_issues(self) -> bool:
        """Check if this result indicates any issues."""
        return self.status in (DiagnosticStatus.WARNING, DiagnosticStatus.ERROR)

    @property
    def severity_level(self) -> int:
        """Get numeric severity level for sorting."""
        severity_map = {
            DiagnosticStatus.OK: 0,
            DiagnosticStatus.SKIPPED: 1,
            DiagnosticStatus.WARNING: 2,
            DiagnosticStatus.ERROR: 3,
        }
        return severity_map.get(self.status, 0)


@dataclass
class DiagnosticSummary:
    """Summary of all diagnostic results.

    WHY: Provides a high-level overview of system health
    and quick access to issues that need attention.
    """

    total_checks: int = 0
    ok_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    results: List[DiagnosticResult] = field(default_factory=list)

    def add_result(self, result: DiagnosticResult):
        """Add a result to the summary."""
        self.results.append(result)
        self.total_checks += 1

        if result.status == DiagnosticStatus.OK:
            self.ok_count += 1
        elif result.status == DiagnosticStatus.WARNING:
            self.warning_count += 1
        elif result.status == DiagnosticStatus.ERROR:
            self.error_count += 1
        elif result.status == DiagnosticStatus.SKIPPED:
            self.skipped_count += 1

    @property
    def has_issues(self) -> bool:
        """Check if there are any warnings or errors."""
        return self.warning_count > 0 or self.error_count > 0

    @property
    def overall_status(self) -> DiagnosticStatus:
        """Get overall system status."""
        if self.error_count > 0:
            return DiagnosticStatus.ERROR
        if self.warning_count > 0:
            return DiagnosticStatus.WARNING
        return DiagnosticStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_checks": self.total_checks,
                "ok": self.ok_count,
                "warnings": self.warning_count,
                "errors": self.error_count,
                "skipped": self.skipped_count,
                "overall_status": self.overall_status.value,
            },
            "results": [r.to_dict() for r in self.results],
        }
