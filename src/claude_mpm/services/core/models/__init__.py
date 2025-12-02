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
from .process import (
    PROTECTED_PORT_RANGES,
    DeploymentState,
    ProcessInfo,
    StartConfig,
    is_port_protected,
)
from .restart import CircuitBreakerState, RestartAttempt, RestartConfig, RestartHistory
from .stability import LogPatternMatch, MemoryTrend, ResourceUsage
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
    # Process management models
    "DeploymentState",
    "ProcessInfo",
    "StartConfig",
    "PROTECTED_PORT_RANGES",
    "is_port_protected",
    # Restart management models
    "CircuitBreakerState",
    "RestartAttempt",
    "RestartHistory",
    "RestartConfig",
    # Stability monitoring models
    "MemoryTrend",
    "LogPatternMatch",
    "ResourceUsage",
]
