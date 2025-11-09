"""
Agent Configuration Data Models for Claude MPM Framework
========================================================

WHY: These models represent agent capabilities, recommendations, and
configuration results. They provide a standardized way to communicate
agent suitability, deployment plans, and validation outcomes.

DESIGN DECISION: Uses dataclasses with validation to ensure data consistency.
Includes confidence scores and reasoning to enable transparent decision-making.
Supports both successful and error states for robust error handling.

Part of TSK-0054: Auto-Configuration Feature - Phase 1
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ....core.enums import OperationResult, ValidationSeverity

# Backward compatibility alias (consolidated in Phase 3A Batch 25)
ConfigurationStatus = OperationResult


class AgentSpecialization(str, Enum):
    """Agent specialization categories.

    WHY: Agents have different areas of expertise. This enum provides
    a standardized taxonomy for categorizing agent capabilities.
    """

    GENERAL = "general"
    LANGUAGE_SPECIFIC = "language_specific"
    FRAMEWORK_SPECIFIC = "framework_specific"
    DEVOPS = "devops"
    SECURITY = "security"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"


@dataclass(frozen=True)
class AgentCapabilities:
    """Represents the capabilities of an agent.

    WHY: Understanding what an agent can do is essential for matching
    agents to projects. This model captures all relevant capability
    information in a structured format.

    DESIGN DECISION: Frozen to prevent modification of capability definitions.
    Includes both broad categories (specializations) and specific skills
    (languages, frameworks) to enable fine-grained matching.
    """

    agent_id: str
    agent_name: str
    specializations: List[AgentSpecialization] = field(default_factory=list)
    supported_languages: List[str] = field(default_factory=list)
    supported_frameworks: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    optional_tools: List[str] = field(default_factory=list)
    deployment_targets: List[str] = field(default_factory=list)
    description: str = ""
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate agent capabilities."""
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("Agent ID cannot be empty")
        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("Agent name cannot be empty")

    def supports_language(self, language: str) -> bool:
        """Check if agent supports a specific language (case-insensitive)."""
        return any(
            lang.lower() == language.lower() for lang in self.supported_languages
        )

    def supports_framework(self, framework: str) -> bool:
        """Check if agent supports a specific framework (case-insensitive)."""
        return any(fw.lower() == framework.lower() for fw in self.supported_frameworks)

    def has_specialization(self, specialization: AgentSpecialization) -> bool:
        """Check if agent has a specific specialization."""
        return specialization in self.specializations


@dataclass
class AgentRecommendation:
    """Represents a recommended agent with reasoning.

    WHY: Users need to understand why agents are recommended. This model
    captures the recommendation along with confidence score, match reasoning,
    and any warnings or considerations.

    DESIGN DECISION: Includes detailed reasoning to support transparency
    and enable users to make informed decisions. Confidence score enables
    filtering and ranking of recommendations.
    """

    agent_id: str
    agent_name: str
    confidence_score: float  # 0.0-1.0
    match_reasons: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    capabilities: Optional[AgentCapabilities] = None
    deployment_priority: int = 1  # Lower = higher priority
    configuration_hints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate agent recommendation."""
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("Agent ID cannot be empty")
        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(
                f"Confidence score must be 0.0-1.0, got {self.confidence_score}"
            )
        if self.deployment_priority < 1:
            raise ValueError(
                f"Deployment priority must be >= 1, got {self.deployment_priority}"
            )

    @property
    def is_high_confidence(self) -> bool:
        """Check if recommendation has high confidence (>= 0.8)."""
        return self.confidence_score >= 0.8

    @property
    def is_medium_confidence(self) -> bool:
        """Check if recommendation has medium confidence (0.5-0.8)."""
        return 0.5 <= self.confidence_score < 0.8

    @property
    def is_low_confidence(self) -> bool:
        """Check if recommendation has low confidence (< 0.5)."""
        return self.confidence_score < 0.5

    @property
    def has_concerns(self) -> bool:
        """Check if recommendation has any concerns."""
        return len(self.concerns) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "confidence_score": self.confidence_score,
            "match_reasons": self.match_reasons,
            "concerns": self.concerns,
            "deployment_priority": self.deployment_priority,
            "configuration_hints": self.configuration_hints,
        }


@dataclass
class ConfigurationResult:
    """Result of automated configuration operation.

    WHY: Configuration operations need to return comprehensive results
    including what was deployed, what failed, and any warnings. This model
    provides a complete picture of the configuration outcome.

    DESIGN DECISION: Separates successful and failed deployments to enable
    proper error handling. Includes validation results and user-facing
    messages for transparency.

    NOTE: Uses core OperationResult enum (consolidated from ConfigurationStatus
    in Phase 3A Batch 25). Mappings:
    - SUCCESS → OperationResult.SUCCESS
    - PARTIAL_SUCCESS → OperationResult.WARNING (partial success with issues)
    - FAILURE → OperationResult.FAILED
    - VALIDATION_ERROR → OperationResult.ERROR
    - USER_CANCELLED → OperationResult.CANCELLED
    """

    status: OperationResult
    deployed_agents: List[str] = field(default_factory=list)
    failed_agents: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    recommendations: List[AgentRecommendation] = field(default_factory=list)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        """Check if configuration was completely successful."""
        return self.status == OperationResult.SUCCESS

    @property
    def has_failures(self) -> bool:
        """Check if any agents failed to deploy."""
        return len(self.failed_agents) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.validation_warnings) > 0

    @property
    def deployment_count(self) -> int:
        """Get number of successfully deployed agents."""
        return len(self.deployed_agents)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "deployed_agents": self.deployed_agents,
            "failed_agents": self.failed_agents,
            "validation_warnings": self.validation_warnings,
            "validation_errors": self.validation_errors,
            "message": self.message,
            "deployment_count": self.deployment_count,
        }


@dataclass
class ValidationIssue:
    """Represents a validation issue.

    WHY: Validation can identify multiple types of issues. This model
    provides structured representation of issues with context and
    suggested resolutions.
    """

    severity: ValidationSeverity
    message: str
    agent_id: Optional[str] = None
    field: Optional[str] = None
    suggested_fix: Optional[str] = None

    def __post_init__(self):
        """Validate issue data."""
        if not self.message or not self.message.strip():
            raise ValueError("Validation issue message cannot be empty")


@dataclass
class ValidationResult:
    """Result of configuration validation.

    WHY: Validation produces multiple types of findings (errors, warnings, info).
    This model aggregates all validation results and provides summary properties.

    DESIGN DECISION: Separates issues by severity to enable appropriate handling.
    Provides convenience properties for common checks (is_valid, has_errors).
    """

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validated_agents: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [
            issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR
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
        """Check if validation has any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation has any warnings."""
        return len(self.warnings) > 0

    @property
    def error_count(self) -> int:
        """Get number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get number of warnings."""
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "validated_agents": self.validated_agents,
            "errors": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "agent_id": issue.agent_id,
                }
                for issue in self.errors
            ],
            "warnings": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "agent_id": issue.agent_id,
                }
                for issue in self.warnings
            ],
        }


@dataclass
class ConfigurationPreview:
    """Preview of what would be configured.

    WHY: Users need to see what would change before committing. This model
    provides a complete preview including recommendations, validation results,
    and estimated impact.

    DESIGN DECISION: Includes validation results to show potential issues
    before deployment. Provides summary statistics for quick assessment.
    """

    recommendations: List[AgentRecommendation] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    estimated_deployment_time: float = 0.0  # seconds
    would_deploy: List[str] = field(default_factory=list)
    would_skip: List[str] = field(default_factory=list)
    requires_confirmation: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def deployment_count(self) -> int:
        """Get number of agents that would be deployed."""
        return len(self.would_deploy)

    @property
    def skip_count(self) -> int:
        """Get number of agents that would be skipped."""
        return len(self.would_skip)

    @property
    def is_valid(self) -> bool:
        """Check if preview represents a valid configuration."""
        if self.validation_result is None:
            return True
        return self.validation_result.is_valid

    @property
    def high_confidence_count(self) -> int:
        """Get number of high-confidence recommendations."""
        return sum(1 for rec in self.recommendations if rec.is_high_confidence)

    def to_dict(self) -> Dict[str, Any]:
        """Convert preview to dictionary."""
        return {
            "deployment_count": self.deployment_count,
            "skip_count": self.skip_count,
            "high_confidence_count": self.high_confidence_count,
            "estimated_deployment_time": self.estimated_deployment_time,
            "is_valid": self.is_valid,
            "would_deploy": self.would_deploy,
            "would_skip": self.would_skip,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
        }
