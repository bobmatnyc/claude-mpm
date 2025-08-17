"""Core mixins for Claude MPM.

This module provides reusable mixins that add common functionality
to classes throughout the framework.
"""

import logging
from typing import Optional


class LoggerMixin:
    """Mixin that provides automatic logger initialization.

    This mixin eliminates duplicate logger initialization code by automatically
    creating a logger instance based on the class name or a custom name.

    Usage:
        class MyService(LoggerMixin):
            def __init__(self):
                # Logger is automatically available as self.logger
                self.logger.info("Service initialized")

        class CustomLogger(LoggerMixin):
            def __init__(self):
                # Use custom logger name
                self._logger_name = "my.custom.logger"
                self.logger.info("Using custom logger")

    The logger is lazily initialized on first access, using either:
    1. A custom name set via self._logger_name
    2. The module and class name (e.g., 'claude_mpm.services.MyService')
    3. The module name if class name is not available

    Attributes:
        logger: The logging.Logger instance for this class
        _logger_name: Optional custom logger name to use instead of class name
        _logger_instance: Cached logger instance (internal use)
    """

    _logger_instance: Optional[logging.Logger] = None
    _logger_name: Optional[str] = None

    @property
    def logger(self) -> logging.Logger:
        """Get or create the logger instance.

        Returns:
            logging.Logger: The logger instance for this class

        Examples:
            >>> class MyService(LoggerMixin):
            ...     def process(self):
            ...         self.logger.info("Processing...")
            >>>
            >>> service = MyService()
            >>> service.process()  # Logs with 'claude_mpm.module.MyService'

            >>> class CustomService(LoggerMixin):
            ...     def __init__(self):
            ...         self._logger_name = "custom.service"
            ...         self.logger.debug("Initialized")
            >>>
            >>> custom = CustomService()  # Logs with 'custom.service'
        """
        if self._logger_instance is None:
            if self._logger_name:
                # Use custom logger name if provided
                logger_name = self._logger_name
            else:
                # Build logger name from module and class
                module = self.__class__.__module__
                class_name = self.__class__.__name__

                if module and module != "__main__":
                    logger_name = f"{module}.{class_name}"
                else:
                    # Fallback to just class name if no proper module
                    logger_name = class_name

            self._logger_instance = logging.getLogger(logger_name)

        return self._logger_instance

    def set_logger(
        self, logger: Optional[logging.Logger] = None, name: Optional[str] = None
    ) -> None:
        """Set a custom logger instance or name.

        This method allows overriding the automatic logger creation with either
        a pre-configured logger instance or a custom logger name.

        Args:
            logger: A pre-configured Logger instance to use
            name: A custom name for creating a new logger

        Raises:
            ValueError: If both logger and name are provided

        Examples:
            >>> service = MyService()
            >>> service.set_logger(name="my.custom.logger")
            >>> service.logger.info("Using custom logger")

            >>> import logging
            >>> custom_logger = logging.getLogger("preconfigured")
            >>> service.set_logger(logger=custom_logger)
        """
        if logger and name:
            raise ValueError("Cannot specify both logger instance and name")

        if logger:
            self._logger_instance = logger
            self._logger_name = logger.name
        elif name:
            self._logger_name = name
            self._logger_instance = None  # Reset to force recreation
        else:
            # Reset to defaults
            self._logger_name = None
            self._logger_instance = None


# Example usage patterns for reference
if __name__ == "__main__":
    # Example 1: Basic usage with automatic logger naming
    class ExampleService(LoggerMixin):
        def do_work(self):
            self.logger.info("Doing work...")
            self.logger.debug("Debug details")

    # Example 2: Custom logger name
    class CustomService(LoggerMixin):
        def __init__(self):
            self._logger_name = "custom.service"
            self.logger.info("Service initialized with custom logger")

    # Example 3: Setting logger after initialization
    class ConfigurableService(LoggerMixin):
        def configure(self, logger_name: str):
            self.set_logger(name=logger_name)
            self.logger.info(f"Reconfigured with logger: {logger_name}")

    # Example 4: Multiple inheritance friendly
    class BaseService:
        def __init__(self, config=None):
            self.config = config

    class AdvancedService(BaseService, LoggerMixin):
        def __init__(self, config=None):
            super().__init__(config)
            self.logger.info("Advanced service ready")
