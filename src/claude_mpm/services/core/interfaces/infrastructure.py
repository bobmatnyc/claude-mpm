"""
Core Infrastructure Interfaces for Claude MPM Framework
======================================================

WHY: This module contains the foundational infrastructure interfaces that provide
the basic building blocks for dependency injection, configuration, caching,
health monitoring, and service lifecycle management.

DESIGN DECISION: These interfaces are grouped together because they form the
core infrastructure layer that other services depend on. They are fundamental
to the framework's operation and are used across all other modules.

EXTRACTED FROM: services/core/interfaces.py (lines 35-507)
- Reduced from 1,437 lines to focused modules
- Infrastructure interfaces: ~470 lines
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

# Type variables for generic interfaces
T = TypeVar("T")
ServiceType = TypeVar("ServiceType")


# Core dependency injection interfaces
class IServiceContainer(ABC):
    """Service container interface for dependency injection"""

    @abstractmethod
    def register(
        self, service_type: type, implementation: type, singleton: bool = True
    ) -> None:
        """Register a service implementation"""

    @abstractmethod
    def register_instance(self, service_type: type, instance: Any) -> None:
        """Register a service instance"""

    @abstractmethod
    def resolve(self, service_type: type) -> Any:
        """Resolve a service by type"""

    @abstractmethod
    def resolve_all(self, service_type: type) -> List[Any]:
        """Resolve all implementations of a service type"""

    @abstractmethod
    def is_registered(self, service_type: type) -> bool:
        """Check if a service type is registered"""


# Configuration management interfaces
class IConfigurationService(ABC):
    """Interface for configuration service (legacy compatibility)"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""

    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from source"""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown configuration service"""


class IConfigurationManager(ABC):
    """Interface for configuration management and validation"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration structure and values"""

    @abstractmethod
    def load_from_file(self, config_path: Path) -> None:
        """Load configuration from file"""

    @abstractmethod
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to file"""

    @abstractmethod
    def watch_changes(self, callback: callable) -> None:
        """Watch for configuration changes"""


# Cache service interface
class ICacheService(ABC):
    """Interface for cache service operations"""

    @abstractmethod
    def get(self, key: str) -> Any:
        """Get value from cache"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache"""

    @abstractmethod
    def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching pattern"""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""

    @abstractmethod
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""


# Health monitoring interface
@dataclass
class HealthStatus:
    """Health status data structure"""

    status: str  # healthy, degraded, unhealthy, unknown
    message: str
    timestamp: datetime
    checks: Dict[str, bool]
    metrics: Dict[str, Any]


class IHealthMonitor(ABC):
    """Interface for service health monitoring"""

    @abstractmethod
    async def check_health(self, service_name: str) -> HealthStatus:
        """Check health of a specific service"""

    @abstractmethod
    async def check_all_services(self) -> Dict[str, HealthStatus]:
        """Check health of all registered services"""

    @abstractmethod
    def register_health_check(self, service_name: str, check_func: callable) -> None:
        """Register a health check function for a service"""

    @abstractmethod
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""


# Prompt cache interface
@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: float
    ttl: Optional[float] = None
    access_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IPromptCache(ABC):
    """Interface for high-performance prompt caching"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL"""

    @abstractmethod
    def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""


# Template management interface
@dataclass
class TemplateRenderContext:
    """Context for template rendering"""

    variables: Dict[str, Any]
    metadata: Dict[str, Any]
    target_path: Optional[Path] = None
    template_id: Optional[str] = None


class ITemplateManager(ABC):
    """Interface for template processing and rendering"""

    @abstractmethod
    async def render_template(
        self, template_content: str, context: TemplateRenderContext
    ) -> str:
        """Render template with given context"""

    @abstractmethod
    async def load_template(self, template_path: Path) -> str:
        """Load template from file"""

    @abstractmethod
    def register_function(self, name: str, func: callable) -> None:
        """Register custom template function"""


# Service factory interface
class IServiceFactory(Generic[ServiceType], ABC):
    """Generic interface for service factories"""

    @abstractmethod
    def create(self, **kwargs) -> ServiceType:
        """Create service instance"""

    @abstractmethod
    def get_service_type(self) -> type:
        """Get the service type this factory creates"""

    @abstractmethod
    def supports(self, service_type: type) -> bool:
        """Check if factory supports service type"""


# Logging interface
class IStructuredLogger(ABC):
    """Interface for structured logging"""

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data"""

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data"""

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data"""

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data"""

    @abstractmethod
    def set_context(self, **kwargs) -> None:
        """Set logging context for all subsequent messages"""


# Service lifecycle interface
class IServiceLifecycle(ABC):
    """Interface for service lifecycle management"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service"""

    @abstractmethod
    async def start(self) -> None:
        """Start the service"""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service"""

    @abstractmethod
    async def restart(self) -> None:
        """Restart the service"""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if service is running"""


# Error handling interface
class IErrorHandler(ABC):
    """Interface for centralized error handling"""

    @abstractmethod
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle error with context"""

    @abstractmethod
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""


# Performance monitoring interface
class IPerformanceMonitor(ABC):
    """Interface for performance monitoring"""

    @abstractmethod
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""

    @abstractmethod
    def end_timer(self, timer_id: str) -> float:
        """End timing and return duration"""

    @abstractmethod
    def record_metric(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a performance metric"""

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""


# Event system interface
class IEventBus(ABC):
    """Interface for event-driven communication"""

    @abstractmethod
    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event"""

    @abstractmethod
    def subscribe(self, event_type: str, handler: callable) -> str:
        """Subscribe to an event type"""

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events"""

    @abstractmethod
    async def publish_async(self, event_type: str, data: Any) -> None:
        """Publish an event asynchronously"""
