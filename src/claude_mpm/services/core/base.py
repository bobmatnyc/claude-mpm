"""
Base Service Classes for Claude MPM Framework
============================================

This module provides the base service classes that all services should inherit from.
These base classes provide common functionality like logging, configuration access,
and lifecycle management.

Part of TSK-0046: Service Layer Architecture Reorganization
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from claude_mpm.core.logger import get_logger


class BaseService(ABC):
    """
    Base class for all services in the Claude MPM framework.

    Provides:
    - Logging setup
    - Configuration access
    - Lifecycle management
    - Common error handling patterns
    """

    def __init__(
        self,
        service_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base service.

        Args:
            service_name: Name of the service for logging
            config: Service-specific configuration
        """
        self.service_name = service_name or self.__class__.__name__
        self.logger = get_logger(self.service_name)
        self._config = config or {}
        self._initialized = False
        self._shutdown = False

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the service.

        This method should be called before the service is used.
        Implementations should set up any required resources.

        Returns:
            True if initialization successful, False otherwise
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the service gracefully.

        This method should clean up any resources held by the service.
        """

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    @property
    def is_shutdown(self) -> bool:
        """Check if service is shutdown."""
        return self._shutdown

    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(f"[{self.service_name}] {message}", **kwargs)

    def log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(f"[{self.service_name}] {message}", **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(f"[{self.service_name}] {message}", **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(f"[{self.service_name}] {message}", **kwargs)

    def log_critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(f"[{self.service_name}] {message}", **kwargs)


class SyncBaseService(ABC):
    """
    Base class for synchronous services in the Claude MPM framework.

    Similar to BaseService but for services that don't require async operations.
    """

    def __init__(
        self,
        service_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base service.

        Args:
            service_name: Name of the service for logging
            config: Service-specific configuration
        """
        self.service_name = service_name or self.__class__.__name__
        self.logger = get_logger(self.service_name)
        self._config = config or {}
        self._initialized = False
        self._shutdown = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the service.

        This method should be called before the service is used.
        Implementations should set up any required resources.

        Returns:
            True if initialization successful, False otherwise
        """

    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown the service gracefully.

        This method should clean up any resources held by the service.
        """

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    @property
    def is_shutdown(self) -> bool:
        """Check if service is shutdown."""
        return self._shutdown

    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(f"[{self.service_name}] {message}", **kwargs)

    def log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(f"[{self.service_name}] {message}", **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(f"[{self.service_name}] {message}", **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(f"[{self.service_name}] {message}", **kwargs)

    def log_critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(f"[{self.service_name}] {message}", **kwargs)


class SingletonService(SyncBaseService):
    """
    Base class for singleton services.

    Ensures only one instance of the service exists.
    """

    _instances: Dict[type, "SingletonService"] = {}

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance exists."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    @classmethod
    def get_instance(cls) -> "SingletonService":
        """Get the singleton instance."""
        if cls not in cls._instances:
            cls._instances[cls] = cls()
        return cls._instances[cls]

    @classmethod
    def clear_instance(cls) -> None:
        """Clear the singleton instance (useful for testing)."""
        if cls in cls._instances:
            instance = cls._instances[cls]
            if hasattr(instance, "shutdown") and not instance.is_shutdown:
                instance.shutdown()
            del cls._instances[cls]
