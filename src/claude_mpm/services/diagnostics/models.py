"""
Data models for the diagnostic system.

WHY: Define clear data structures for diagnostic results to ensure
consistency across all checks and reporting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ...core.enums import OperationResult, ValidationSeverity


class DiagnosticStatus(str, Enum):
    """Backward compatibility wrapper for diagnostic status values.

    WHY: Provides backward compatibility for tests and code that use
    DiagnosticStatus instead of the consolidated OperationResult/ValidationSeverity.

    DESIGN DECISION: Maps to the appropriate consolidated enum values:
    - OK → OperationResult.SUCCESS
    - WARNING → ValidationSeverity.WARNING
    - ERROR → ValidationSeverity.ERROR

    Note: This is a compatibility layer. New code should use OperationResult
    and ValidationSeverity directly.
    """

    OK = "success"  # Maps to OperationResult.SUCCESS
    WARNING = "warning"  # Maps to ValidationSeverity.WARNING
    ERROR = "error"  # Maps to ValidationSeverity.ERROR


@dataclass
class DiagnosticResult:
    """Result from a diagnostic check.

    WHY: Standardized result format ensures consistent reporting
    and makes it easy to aggregate and display results.

    Note: status uses Union[OperationResult, ValidationSeverity] to support both
    operation results (SUCCESS, SKIPPED) and validation results (WARNING, ERROR).
    """

    category: str  # e.g., "Installation", "Agents", "MCP Server"
    status: Union[OperationResult, ValidationSeverity]
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
        return self.status in (ValidationSeverity.WARNING, ValidationSeverity.ERROR)

    @property
    def severity_level(self) -> int:
        """Get numeric severity level for sorting."""
        severity_map = {
            OperationResult.SUCCESS: 0,
            OperationResult.SKIPPED: 1,
            ValidationSeverity.WARNING: 2,
            ValidationSeverity.ERROR: 3,
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

        if result.status == OperationResult.SUCCESS:
            self.ok_count += 1
        elif result.status == ValidationSeverity.WARNING:
            self.warning_count += 1
        elif result.status == ValidationSeverity.ERROR:
            self.error_count += 1
        elif result.status == OperationResult.SKIPPED:
            self.skipped_count += 1

    @property
    def has_issues(self) -> bool:
        """Check if there are any warnings or errors."""
        return self.warning_count > 0 or self.error_count > 0

    @property
    def overall_status(self) -> Union[OperationResult, ValidationSeverity]:
        """Get overall system status."""
        if self.error_count > 0:
            return ValidationSeverity.ERROR
        if self.warning_count > 0:
            return ValidationSeverity.WARNING
        return OperationResult.SUCCESS

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
