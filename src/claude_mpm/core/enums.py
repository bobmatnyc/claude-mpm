"""
Centralized enums for type-safe string constants across Claude MPM.

This module provides enumerated types to replace magic strings throughout the codebase,
improving type safety, IDE autocomplete, and preventing typos.

Created: 2025-10-25
Priority: Phase 1 of systematic enum migration (3-4 week plan)
Impact: Replaces 2,050+ magic string occurrences

Usage:
    from claude_mpm.core.enums import OperationResult, OutputFormat, ServiceState

    # Type-safe operation results
    result = OperationResult.SUCCESS
    if result == OperationResult.SUCCESS:
        print("Operation completed successfully")

    # Type-safe output formatting
    format_type = OutputFormat.JSON

    # Type-safe service state management
    state = ServiceState.RUNNING
"""

from enum import StrEnum


class OperationResult(StrEnum):
    """
    Standard result codes for operations throughout Claude MPM.

    Replaces 876+ occurrences of magic strings like "success", "error", "failed".
    Used in: CLI commands, service operations, API responses, hook handlers.

    Migration Priority: HIGH (Week 1)
    Coverage: ~42% of all magic strings
    """

    SUCCESS = "success"
    """Operation completed successfully."""

    ERROR = "error"
    """Operation encountered an error."""

    FAILED = "failed"
    """Operation failed to complete."""

    PENDING = "pending"
    """Operation is waiting to execute."""

    COMPLETED = "completed"
    """Operation has been completed."""

    TIMEOUT = "timeout"
    """Operation exceeded time limit."""

    CANCELLED = "cancelled"
    """Operation was cancelled before completion."""

    CONTEXT_READY = "context_ready"
    """Context is prepared and ready for use."""

    SKIPPED = "skipped"
    """Operation was intentionally skipped."""

    RETRY = "retry"
    """Operation should be retried."""

    PARTIAL = "partial"
    """Operation completed partially."""

    WARNING = "warning"
    """Operation completed with warnings (partial success with issues)."""

    ROLLBACK = "rollback"
    """Operation rolled back due to failure or cancellation."""

    UNKNOWN = "unknown"
    """Operation result is unknown or indeterminate."""


class OutputFormat(StrEnum):
    """
    Output format options for CLI commands and logging.

    Replaces 200+ occurrences of format strings.
    Used in: CLI output, logging, configuration exports, API responses.

    Migration Priority: HIGH (Week 1)
    Coverage: ~10% of all magic strings
    """

    JSON = "json"
    """JavaScript Object Notation format."""

    YAML = "yaml"
    """YAML Ain't Markup Language format."""

    TEXT = "text"
    """Plain text format."""

    MARKDOWN = "markdown"
    """Markdown formatted text."""

    RAW = "raw"
    """Raw unformatted output."""

    TABLE = "table"
    """Tabular format for display."""

    CSV = "csv"
    """Comma-separated values format."""

    HTML = "html"
    """HyperText Markup Language format."""

    XML = "xml"
    """eXtensible Markup Language format."""


class ServiceState(StrEnum):
    """
    Service lifecycle states for all Claude MPM services.

    Replaces 150+ occurrences of service state strings.
    Used in: Hook services, MCP servers, monitoring, health checks, process management.

    Migration Priority: HIGH (Week 1)
    Coverage: ~7% of all magic strings

    Notes:
        - Consolidated with ProcessStatus enum (Phase 3A Batch 24)
        - Process states are semantically equivalent to service states
        - CRASHED processes map to ERROR state
    """

    UNINITIALIZED = "uninitialized"
    """Service has not been initialized yet."""

    INITIALIZING = "initializing"
    """Service is in the process of initializing."""

    INITIALIZED = "initialized"
    """Service has been initialized but not started."""

    STOPPED = "stopped"
    """Service is completely stopped."""

    STARTING = "starting"
    """Service is in the process of starting."""

    RUNNING = "running"
    """Service is actively running."""

    STOPPING = "stopping"
    """Service is in the process of stopping."""

    RESTARTING = "restarting"
    """Service is restarting."""

    ERROR = "error"
    """Service encountered an error."""

    UNKNOWN = "unknown"
    """Service state cannot be determined."""

    DEGRADED = "degraded"
    """Service is running but with reduced functionality."""

    IDLE = "idle"
    """Service is running but not actively processing."""

    def is_active(self) -> bool:
        """
        Check if state represents an active service/process.

        Returns:
            True if state is STARTING or RUNNING
        """
        return self in (ServiceState.STARTING, ServiceState.RUNNING)

    def is_terminal(self) -> bool:
        """
        Check if state represents a terminal/stopped state.

        Returns:
            True if state is STOPPED or ERROR
        """
        return self in (ServiceState.STOPPED, ServiceState.ERROR)


class ValidationSeverity(StrEnum):
    """
    Severity levels for validation and error reporting.

    Replaces validation severity strings across validators and error handlers.
    Used in: Frontmatter validation, API validation, config validation.

    Migration Priority: MEDIUM (Week 2)
    Coverage: ~5% of all magic strings
    """

    INFO = "info"
    """Informational message, no action required."""

    WARNING = "warning"
    """Warning that should be addressed but not critical."""

    ERROR = "error"
    """Error that prevents operation completion."""

    CRITICAL = "critical"
    """Critical error requiring immediate attention."""

    DEBUG = "debug"
    """Debug-level information for troubleshooting."""


class HealthStatus(StrEnum):
    """
    Health check status codes for services and components.

    Replaces health check status strings throughout monitoring and diagnostics.
    Used in: Health checks, monitoring, service diagnostics, uptime tracking.

    Migration Priority: MEDIUM (Week 3)
    Coverage: ~2% of all magic strings

    Notes:
        - Added in Phase 3C for comprehensive service health monitoring
        - Distinct from ServiceState (operational) and OperationResult (transactional)
        - Maps to standard health check patterns (healthy/unhealthy/degraded)
    """

    HEALTHY = "healthy"
    """Component is functioning normally."""

    UNHEALTHY = "unhealthy"
    """Component is not functioning correctly."""

    DEGRADED = "degraded"
    """Component is functioning with reduced capability."""

    UNKNOWN = "unknown"
    """Health status cannot be determined."""

    CHECKING = "checking"
    """Health check is currently in progress."""

    TIMEOUT = "timeout"
    """Health check exceeded time limit."""

    def is_operational(self) -> bool:
        """
        Check if health status indicates operational state.

        Returns:
            True if status is HEALTHY or DEGRADED
        """
        return self in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    def is_critical(self) -> bool:
        """
        Check if health status indicates critical failure.

        Returns:
            True if status is UNHEALTHY
        """
        return self == HealthStatus.UNHEALTHY


class ModelTier(StrEnum):
    """
    Claude model tier classifications and identifiers.

    Replaces model name strings and enables model normalization.
    Used in: Agent configuration, API calls, capability detection.

    Migration Priority: MEDIUM (Week 2)
    Coverage: ~4% of all magic strings

    Notes:
        - Replaces manual model normalization code
        - Enables type-safe model selection
        - Provides both tier names and full model identifiers
    """

    # Tier names (simplified)
    OPUS = "opus"
    """Claude Opus tier (highest capability)."""

    SONNET = "sonnet"
    """Claude Sonnet tier (balanced)."""

    HAIKU = "haiku"
    """Claude Haiku tier (fastest)."""

    # Full model identifiers (Claude 4.x)
    OPUS_4 = "claude-opus-4-20250514"
    """Claude 4 Opus - May 2025 release."""

    SONNET_4 = "claude-sonnet-4-20250514"
    """Claude 4 Sonnet - May 2025 release."""

    SONNET_4_5 = "claude-sonnet-4-5-20250929"
    """Claude 4.5 Sonnet - September 2025 release."""

    # Legacy model identifiers (Claude 3.x)
    OPUS_3 = "claude-3-opus-20240229"
    """Claude 3 Opus - February 2024 release."""

    SONNET_3_5 = "claude-3-5-sonnet-20241022"
    """Claude 3.5 Sonnet - October 2024 release."""

    HAIKU_3 = "claude-3-haiku-20240307"
    """Claude 3 Haiku - March 2024 release."""

    @classmethod
    def normalize(cls, model_name: str) -> "ModelTier":
        """
        Normalize a model name to its canonical tier.

        Args:
            model_name: Any model name variant (e.g., "opus", "claude-opus-4", "OPUS")

        Returns:
            Normalized ModelTier enum value

        Examples:
            >>> ModelTier.normalize("OPUS")
            ModelTier.OPUS
            >>> ModelTier.normalize("claude-sonnet-4-20250514")
            ModelTier.SONNET_4
            >>> ModelTier.normalize("sonnet")
            ModelTier.SONNET
        """
        normalized = model_name.lower().strip()

        # Direct enum value match
        for tier in cls:
            if tier.value == normalized:
                return tier

        # Tier name extraction
        if "opus" in normalized:
            return cls.OPUS
        if "sonnet" in normalized:
            return cls.SONNET
        if "haiku" in normalized:
            return cls.HAIKU

        # Default to sonnet for unknown models
        return cls.SONNET


class AgentCategory(StrEnum):
    """
    Agent specialization categories for classification and routing.

    Replaces category strings in agent configurations and routing logic.
    Used in: Agent templates, capability detection, routing decisions.

    Migration Priority: MEDIUM (Week 3)
    Coverage: ~3% of all magic strings

    Notes:
        - Expanded in Phase 3C to include all template categories
        - Maps to actual usage in agent JSON templates
        - Supports both legacy and new category schemes
    """

    # Core Engineering Categories
    ENGINEERING = "engineering"
    """Software engineering and implementation agents."""

    # Research and Analysis
    RESEARCH = "research"
    """Research and analysis agents."""

    ANALYSIS = "analysis"
    """Code analysis and architectural review agents."""

    # Quality and Testing
    QUALITY = "quality"
    """Quality assurance and testing agents (replaces QA)."""

    QA = "qa"
    """Legacy quality assurance category (use QUALITY for new agents)."""

    SECURITY = "security"
    """Security analysis and vulnerability assessment agents."""

    # Operations and Infrastructure
    OPERATIONS = "operations"
    """DevOps and infrastructure management agents."""

    INFRASTRUCTURE = "infrastructure"
    """Infrastructure provisioning and cloud management agents."""

    # Documentation and Content
    DOCUMENTATION = "documentation"
    """Documentation and technical writing agents."""

    CONTENT = "content"
    """Content creation, optimization, and management agents."""

    # Data and Analytics
    DATA = "data"
    """Data engineering and analytics agents."""

    # Specialized Functions
    OPTIMIZATION = "optimization"
    """Performance and resource optimization agents."""

    SPECIALIZED = "specialized"
    """Specialized single-purpose agents."""

    SYSTEM = "system"
    """System-level framework agents."""

    # Management and Coordination
    PROJECT_MANAGEMENT = "project-management"
    """Project management and coordination agents."""

    PRODUCT = "product"
    """Product ownership and strategy agents."""

    # Legacy and General
    VERSION_CONTROL = "version_control"
    """Version control and release management agents."""

    DESIGN = "design"
    """UI/UX design and frontend agents."""

    GENERAL = "general"
    """General-purpose agents without specific specialization."""

    CUSTOM = "custom"
    """User-defined custom agent categories."""


# Export all enums for convenient access
__all__ = [
    "AgentCategory",
    "HealthStatus",
    "ModelTier",
    "OperationResult",
    "OutputFormat",
    "ServiceState",
    "ValidationSeverity",
]
