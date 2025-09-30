"""
Unified Services Module for Phase 2 Service Consolidation
=========================================================

This module implements the strategy pattern framework for consolidating
Claude MPM's 314 service files into approximately 180 more maintainable services.

Architecture:
- Base service interfaces for common service patterns
- Strategy pattern for pluggable behavior
- Backward compatibility layer for existing services
- Feature flags for gradual migration

Components:
- interfaces.py: Core service interfaces (IDeploymentService, IAnalyzerService, etc.)
- strategies.py: Strategy pattern framework with plugin registry
- migration.py: Migration utilities and backward compatibility
- Unified service implementations for major service categories
"""

from .interfaces import (
    IAnalyzerService,
    IConfigurationService,
    IDeploymentService,
    ServiceCapability,
    ServiceMetadata,
)
from .migration import (
    FeatureFlag,
    MigrationStatus,
    ServiceMapper,
    create_compatibility_wrapper,
)
from .strategies import (
    AnalyzerStrategy,
    ConfigStrategy,
    DeploymentStrategy,
    StrategyRegistry,
)
from .unified_analyzer import UnifiedAnalyzer
from .unified_config import UnifiedConfigManager
from .unified_deployment import UnifiedDeploymentService

__all__ = [
    "AnalyzerStrategy",
    "ConfigStrategy",
    # Strategies
    "DeploymentStrategy",
    "FeatureFlag",
    "IAnalyzerService",
    "IConfigurationService",
    # Interfaces
    "IDeploymentService",
    "MigrationStatus",
    "ServiceCapability",
    # Migration
    "ServiceMapper",
    "ServiceMetadata",
    "StrategyRegistry",
    "UnifiedAnalyzer",
    "UnifiedConfigManager",
    # Unified Services
    "UnifiedDeploymentService",
    "create_compatibility_wrapper",
]
