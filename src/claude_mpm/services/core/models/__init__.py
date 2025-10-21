"""
Core Models Package for Claude MPM Framework
============================================

WHY: This package contains data models used across the service layer.
Models are organized by domain to maintain clear boundaries and enable
independent evolution of different model types.

DESIGN DECISION: Models are grouped by domain (toolchain, agent_config)
to create logical cohesion and make it easier to understand dependencies
between different parts of the system.

Part of TSK-0054: Auto-Configuration Feature - Phase 1
"""

from .agent_config import (
    AgentCapabilities,
    AgentRecommendation,
    ConfigurationPreview,
    ConfigurationResult,
    ValidationResult,
)
from .toolchain import (
    ConfidenceLevel,
    DeploymentTarget,
    Framework,
    LanguageDetection,
    ToolchainAnalysis,
    ToolchainComponent,
)

__all__ = [  # noqa: RUF022 - Grouped by category with comments for clarity
    # Toolchain models
    "ConfidenceLevel",
    "ToolchainComponent",
    "LanguageDetection",
    "Framework",
    "DeploymentTarget",
    "ToolchainAnalysis",
    # Agent configuration models
    "AgentCapabilities",
    "AgentRecommendation",
    "ConfigurationResult",
    "ValidationResult",
    "ConfigurationPreview",
]
