"""Validation result classes for deployment validation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from claude_mpm.core.enums import ValidationSeverity


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation of the issue."""
        parts = [f"[{self.severity.value.upper()}]"]

        if self.field_name:
            parts.append(f"Field '{self.field_name}':")

        parts.append(self.message)

        if self.line_number:
            parts.append(f"(line {self.line_number})")

        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [
            issue
            for issue in self.issues
            if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
        ]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues."""
        return [
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        ]

    @property
    def infos(self) -> List[ValidationIssue]:
        """Get all info-level issues."""
        return [
            issue for issue in self.issues if issue.severity == ValidationSeverity.INFO
        ]

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def error_count(self) -> int:
        """Get the number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get the number of warnings."""
        return len(self.warnings)

    def add_error(
        self,
        message: str,
        field_name: Optional[str] = None,
        line_number: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add an error to the validation result.

        Args:
            message: Error message
            field_name: Optional field name
            line_number: Optional line number
            suggestion: Optional suggestion for fixing
        """
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=message,
                field_name=field_name,
                line_number=line_number,
                suggestion=suggestion,
            )
        )
        self.is_valid = False

    def add_warning(
        self,
        message: str,
        field_name: Optional[str] = None,
        line_number: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a warning to the validation result.

        Args:
            message: Warning message
            field_name: Optional field name
            line_number: Optional line number
            suggestion: Optional suggestion for improvement
        """
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=message,
                field_name=field_name,
                line_number=line_number,
                suggestion=suggestion,
            )
        )

    def add_info(
        self,
        message: str,
        field_name: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> None:
        """Add an info message to the validation result.

        Args:
            message: Info message
            field_name: Optional field name
            line_number: Optional line number
        """
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                message=message,
                field_name=field_name,
                line_number=line_number,
            )
        )

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one.

        Args:
            other: Another validation result to merge

        Returns:
            New ValidationResult with merged issues
        """
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            issues=self.issues + other.issues,
            metadata={**self.metadata, **other.metadata},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary.

        Returns:
            Dictionary representation of the result
        """
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "field": issue.field_name,
                    "line_number": issue.line_number,
                    "suggestion": issue.suggestion,
                    "metadata": issue.metadata,
                }
                for issue in self.issues
            ],
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of the validation result."""
        status = "VALID" if self.is_valid else "INVALID"

        summary = f"Validation {status}"

        if self.error_count > 0:
            summary += f" ({self.error_count} errors"
            if self.warning_count > 0:
                summary += f", {self.warning_count} warnings"
            summary += ")"
        elif self.warning_count > 0:
            summary += f" ({self.warning_count} warnings)"

        return summary
