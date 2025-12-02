"""
Core Service Interfaces and Base Classes
========================================

This module provides the core service interfaces and base classes for the
Claude MPM framework. All services should inherit from these base classes
and implement the appropriate interfaces.

Part of TSK-0046: Service Layer Architecture Reorganization
"""

from .base import BaseService, SingletonService, SyncBaseService
from .interfaces import (  # Core dependency injection; Configuration management; Agent management; Health monitoring; Caching; Template management; Factory patterns; Event system; Logging; Service lifecycle; Error handling; Performance monitoring; Cache service; Agent deployment; Memory service; Hook service; SocketIO service; Project analyzer; Ticket manager; Interface registry
    AgentDeploymentInterface,
    AgentMetadata,
    CacheEntry,
    HealthStatus,
    HookServiceInterface,
    IAgentRecommender,
    IAgentRegistry,
    IAutoConfigManager,
    ICacheService,
    IConfigurationManager,
    IConfigurationService,
    IErrorHandler,
    IEventBus,
    IHealthMonitor,
    InterfaceRegistry,
    IPerformanceMonitor,
    IPromptCache,
    IServiceContainer,
    IServiceFactory,
    IServiceLifecycle,
    IStructuredLogger,
    ITemplateManager,
    IToolchainAnalyzer,
    MemoryServiceInterface,
    ProjectAnalyzerInterface,
    ServiceType,
    SocketIOServiceInterface,
    TemplateRenderContext,
    TicketManagerInterface,
)
from .models import (  # Data models for services
    AgentCapabilities,
    AgentRecommendation,
    ConfidenceLevel,
    ConfigurationPreview,
    ConfigurationResult,
    DeploymentTarget,
    Framework,
    LanguageDetection,
    ToolchainAnalysis,
    ToolchainComponent,
    ValidationResult,
)

__all__ = [  # noqa: RUF022 - Grouped by category with comments for clarity
    # Service interfaces
    "AgentDeploymentInterface",
    "AgentMetadata",
    # Base classes
    "BaseService",
    "CacheEntry",
    "HealthStatus",
    "HookServiceInterface",
    "IAgentRecommender",
    "IAgentRegistry",
    "IAutoConfigManager",
    "ICacheService",
    "IConfigurationManager",
    "IConfigurationService",
    "IErrorHandler",
    "IEventBus",
    "IHealthMonitor",
    "IPerformanceMonitor",
    "IPromptCache",
    # Core interfaces
    "IServiceContainer",
    "IServiceFactory",
    "IServiceLifecycle",
    "IStructuredLogger",
    "ITemplateManager",
    "IToolchainAnalyzer",
    # Registry
    "InterfaceRegistry",
    "MemoryServiceInterface",
    "ProjectAnalyzerInterface",
    "ServiceType",
    "SingletonService",
    "SocketIOServiceInterface",
    "SyncBaseService",
    "TemplateRenderContext",
    "TicketManagerInterface",
    # Data models - Toolchain
    "ConfidenceLevel",
    "ToolchainComponent",
    "LanguageDetection",
    "Framework",
    "DeploymentTarget",
    "ToolchainAnalysis",
    # Data models - Agent Configuration
    "AgentCapabilities",
    "AgentRecommendation",
    "ConfigurationResult",
    "ValidationResult",
    "ConfigurationPreview",
]
