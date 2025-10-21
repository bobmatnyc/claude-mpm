"""
Toolchain Data Models for Claude MPM Framework
==============================================

WHY: These models represent the structure of project toolchain analysis results.
They provide a standardized way to represent detected languages, frameworks,
deployment targets, and overall toolchain characteristics.

DESIGN DECISION: Uses dataclasses with field validation and default values
to ensure data consistency. Confidence levels are included to represent
uncertainty in detection. Immutable where possible to prevent accidental
modification of analysis results.

Part of TSK-0054: Auto-Configuration Feature - Phase 1
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfidenceLevel(str, Enum):
    """Confidence level for detection results.

    WHY: Not all detections are equally certain. This enum provides a
    standardized way to communicate confidence levels to users and
    enable threshold-based decision making.
    """

    HIGH = "high"  # >80% confidence, very strong indicators
    MEDIUM = "medium"  # 50-80% confidence, good indicators
    LOW = "low"  # 20-50% confidence, weak indicators
    VERY_LOW = "very_low"  # <20% confidence, speculative


@dataclass(frozen=True)
class ToolchainComponent:
    """Represents a component in the project's toolchain.

    WHY: Toolchain components (languages, frameworks, tools) share common
    attributes like name, version, and confidence. This base model enables
    consistent representation across different component types.

    DESIGN DECISION: Frozen dataclass to prevent modification after creation,
    ensuring analysis results remain consistent. Version is optional as not
    all components have detectable versions.
    """

    name: str
    version: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate component data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Component name cannot be empty")
        if self.version is not None and not self.version.strip():
            raise ValueError("Component version cannot be empty string")


@dataclass(frozen=True)
class LanguageDetection:
    """Result of language detection analysis.

    WHY: Projects often use multiple languages. This model captures both
    primary (main codebase) and secondary (scripts, config) languages
    with their relative proportions and confidence levels.

    DESIGN DECISION: Includes percentage breakdown to help understand
    language distribution. Confidence per language enables threshold-based
    filtering of uncertain detections.
    """

    primary_language: str
    primary_version: Optional[str] = None
    primary_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    secondary_languages: List[ToolchainComponent] = field(default_factory=list)
    language_percentages: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate language detection data."""
        if not self.primary_language or not self.primary_language.strip():
            raise ValueError("Primary language cannot be empty")

        # Validate language percentages sum to ~100% (allow small floating point error)
        if self.language_percentages:
            total = sum(self.language_percentages.values())
            if not (99.0 <= total <= 101.0):
                raise ValueError(f"Language percentages must sum to 100%, got {total}%")

    @property
    def all_languages(self) -> List[str]:
        """Get list of all detected languages (primary + secondary)."""
        languages = [self.primary_language]
        languages.extend(comp.name for comp in self.secondary_languages)
        return languages

    @property
    def high_confidence_languages(self) -> List[str]:
        """Get languages detected with high confidence."""
        languages = []
        if self.primary_confidence == ConfidenceLevel.HIGH:
            languages.append(self.primary_language)
        languages.extend(
            comp.name
            for comp in self.secondary_languages
            if comp.confidence == ConfidenceLevel.HIGH
        )
        return languages


@dataclass(frozen=True)
class Framework:
    """Represents a detected framework or library.

    WHY: Frameworks are critical for agent recommendation as different agents
    specialize in different frameworks. This model captures framework identity,
    version, type, and usage characteristics.

    DESIGN DECISION: Includes framework type (web, testing, ORM, etc.) to
    enable category-based recommendations. Popularity metric helps prioritize
    agent recommendations for commonly-used frameworks.
    """

    name: str
    version: Optional[str] = None
    framework_type: Optional[str] = None  # web, testing, orm, cli, etc.
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    is_dev_dependency: bool = False
    popularity_score: float = 0.0  # 0.0-1.0, higher = more popular/used
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate framework data."""
        if not self.name or not self.name.strip():
            raise ValueError("Framework name cannot be empty")
        if not (0.0 <= self.popularity_score <= 1.0):
            raise ValueError(
                f"Popularity score must be 0.0-1.0, got {self.popularity_score}"
            )

    @property
    def display_name(self) -> str:
        """Get formatted display name with version."""
        if self.version:
            return f"{self.name} {self.version}"
        return self.name


@dataclass(frozen=True)
class DeploymentTarget:
    """Represents the detected deployment target environment.

    WHY: Deployment target affects agent recommendations (e.g., DevOps agents
    for Kubernetes, serverless agents for Lambda). This model captures the
    deployment platform and configuration details.

    DESIGN DECISION: Includes target type (cloud, container, serverless, etc.)
    and platform-specific configuration. Confidence level enables fallback
    to generic recommendations when deployment target is unclear.
    """

    target_type: str  # cloud, container, serverless, on-premise, edge
    platform: Optional[str] = None  # aws, gcp, azure, kubernetes, docker, etc.
    configuration: Dict[str, Any] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    requires_ops_agent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate deployment target data."""
        valid_types = {"cloud", "container", "serverless", "on-premise", "edge"}
        if self.target_type not in valid_types:
            raise ValueError(
                f"Invalid target_type '{self.target_type}'. "
                f"Must be one of: {valid_types}"
            )

    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        if self.platform:
            return f"{self.target_type} ({self.platform})"
        return self.target_type


@dataclass
class ToolchainAnalysis:
    """Complete toolchain analysis result.

    WHY: This is the primary output of toolchain analysis, aggregating all
    detected components into a single structure. It provides a complete
    picture of the project's technical stack.

    DESIGN DECISION: Not frozen to allow caching and updating of analysis
    results. Includes project_path for reference and validation. Provides
    convenience methods for common queries (e.g., has framework, get languages).
    """

    project_path: Path
    language_detection: LanguageDetection
    frameworks: List[Framework] = field(default_factory=list)
    deployment_target: Optional[DeploymentTarget] = None
    build_tools: List[ToolchainComponent] = field(default_factory=list)
    package_managers: List[ToolchainComponent] = field(default_factory=list)
    development_tools: List[ToolchainComponent] = field(default_factory=list)
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    analysis_timestamp: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate toolchain analysis data."""
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {self.project_path}")
        if not self.project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {self.project_path}")

    def has_framework(self, framework_name: str) -> bool:
        """Check if a specific framework is detected."""
        return any(fw.name.lower() == framework_name.lower() for fw in self.frameworks)

    def get_framework(self, framework_name: str) -> Optional[Framework]:
        """Get framework by name (case-insensitive)."""
        for fw in self.frameworks:
            if fw.name.lower() == framework_name.lower():
                return fw
        return None

    def get_frameworks_by_type(self, framework_type: str) -> List[Framework]:
        """Get all frameworks of a specific type."""
        return [
            fw
            for fw in self.frameworks
            if fw.framework_type and fw.framework_type.lower() == framework_type.lower()
        ]

    @property
    def primary_language(self) -> str:
        """Get the primary language detected."""
        return self.language_detection.primary_language

    @property
    def all_languages(self) -> List[str]:
        """Get all detected languages."""
        return self.language_detection.all_languages

    @property
    def web_frameworks(self) -> List[Framework]:
        """Get all web frameworks."""
        return self.get_frameworks_by_type("web")

    @property
    def is_web_project(self) -> bool:
        """Check if this appears to be a web project."""
        return len(self.web_frameworks) > 0

    @property
    def requires_devops_agent(self) -> bool:
        """Check if project likely needs DevOps agent."""
        if self.deployment_target and self.deployment_target.requires_ops_agent:
            return True
        # Check for containerization
        return any(
            tool.name.lower() in {"docker", "kubernetes", "terraform"}
            for tool in self.development_tools
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for serialization."""
        return {
            "project_path": str(self.project_path),
            "language_detection": {
                "primary_language": self.language_detection.primary_language,
                "primary_version": self.language_detection.primary_version,
                "primary_confidence": self.language_detection.primary_confidence.value,
                "secondary_languages": [
                    {"name": lang.name, "version": lang.version}
                    for lang in self.language_detection.secondary_languages
                ],
                "language_percentages": self.language_detection.language_percentages,
            },
            "frameworks": [
                {
                    "name": fw.name,
                    "version": fw.version,
                    "type": fw.framework_type,
                    "confidence": fw.confidence.value,
                }
                for fw in self.frameworks
            ],
            "deployment_target": (
                {
                    "type": self.deployment_target.target_type,
                    "platform": self.deployment_target.platform,
                    "confidence": self.deployment_target.confidence.value,
                }
                if self.deployment_target
                else None
            ),
            "build_tools": [tool.name for tool in self.build_tools],
            "package_managers": [pm.name for pm in self.package_managers],
            "overall_confidence": self.overall_confidence.value,
            "metadata": self.metadata,
        }
