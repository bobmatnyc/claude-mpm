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
    IAgentRegistry,
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
    MemoryServiceInterface,
    ProjectAnalyzerInterface,
    ServiceType,
    SocketIOServiceInterface,
    TemplateRenderContext,
    TicketManagerInterface,
)

__all__ = [
    # Core interfaces
    "IServiceContainer",
    "ServiceType",
    "IConfigurationService",
    "IConfigurationManager",
    "IAgentRegistry",
    "AgentMetadata",
    "IHealthMonitor",
    "HealthStatus",
    "IPromptCache",
    "CacheEntry",
    "ITemplateManager",
    "TemplateRenderContext",
    "IServiceFactory",
    "IEventBus",
    "IStructuredLogger",
    "IServiceLifecycle",
    "IErrorHandler",
    "IPerformanceMonitor",
    "ICacheService",
    # Service interfaces
    "AgentDeploymentInterface",
    "MemoryServiceInterface",
    "HookServiceInterface",
    "SocketIOServiceInterface",
    "ProjectAnalyzerInterface",
    "TicketManagerInterface",
    # Registry
    "InterfaceRegistry",
    # Base classes
    "BaseService",
    "SyncBaseService",
    "SingletonService",
]
