"""
Core Service Interfaces and Base Classes
========================================

This module provides the core service interfaces and base classes for the
Claude MPM framework. All services should inherit from these base classes
and implement the appropriate interfaces.

Part of TSK-0046: Service Layer Architecture Reorganization
"""

from .interfaces import (
    # Core dependency injection
    IServiceContainer,
    ServiceType,
    
    # Configuration management
    IConfigurationService,
    IConfigurationManager,
    
    # Agent management
    IAgentRegistry,
    AgentMetadata,
    
    # Health monitoring
    IHealthMonitor,
    HealthStatus,
    
    # Caching
    IPromptCache,
    CacheEntry,
    
    # Template management
    ITemplateManager,
    TemplateRenderContext,
    
    # Factory patterns
    IServiceFactory,
    
    # Event system
    IEventBus,
    
    # Logging
    IStructuredLogger,
    
    # Service lifecycle
    IServiceLifecycle,
    
    # Error handling
    IErrorHandler,
    
    # Performance monitoring
    IPerformanceMonitor,
    
    # Cache service
    ICacheService,
    
    # Agent deployment
    AgentDeploymentInterface,
    
    # Memory service
    MemoryServiceInterface,
    
    # Hook service
    HookServiceInterface,
    
    # SocketIO service
    SocketIOServiceInterface,
    
    # Project analyzer
    ProjectAnalyzerInterface,
    
    # Ticket manager
    TicketManagerInterface,
    
    # Interface registry
    InterfaceRegistry,
)

from .base import (
    BaseService,
    SyncBaseService,
    SingletonService,
)

__all__ = [
    # Core interfaces
    'IServiceContainer',
    'ServiceType',
    'IConfigurationService',
    'IConfigurationManager',
    'IAgentRegistry',
    'AgentMetadata',
    'IHealthMonitor',
    'HealthStatus',
    'IPromptCache',
    'CacheEntry',
    'ITemplateManager',
    'TemplateRenderContext',
    'IServiceFactory',
    'IEventBus',
    'IStructuredLogger',
    'IServiceLifecycle',
    'IErrorHandler',
    'IPerformanceMonitor',
    'ICacheService',
    
    # Service interfaces
    'AgentDeploymentInterface',
    'MemoryServiceInterface',
    'HookServiceInterface',
    'SocketIOServiceInterface',
    'ProjectAnalyzerInterface',
    'TicketManagerInterface',
    
    # Registry
    'InterfaceRegistry',
    
    # Base classes
    'BaseService',
    'SyncBaseService',
    'SingletonService',
]