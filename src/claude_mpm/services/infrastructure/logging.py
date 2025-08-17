from pathlib import Path

"""
Logging Service for Claude MPM Framework
========================================

This module provides centralized logging services and utilities.

Part of TSK-0046: Service Layer Architecture Reorganization
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.services.core import IStructuredLogger, SyncBaseService


class LoggingService(SyncBaseService, IStructuredLogger):
    """
    Centralized logging service for the Claude MPM framework.

    This service provides:
    - Structured logging with JSON output
    - Log rotation and archival
    - Performance metrics logging
    - Audit trail capabilities
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize logging service.

        Args:
            config: Logging configuration
        """
        super().__init__("LoggingService", config)
        self.log_dir = Path(self.get_config("log_dir", ".claude-mpm/logs"))
        self.log_level = self.get_config("log_level", "INFO")
        self.structured_logging = self.get_config("structured_logging", True)
        self._log_handlers = []

    def initialize(self) -> bool:
        """Initialize the logging service."""
        try:
            # Create log directory if it doesn't exist
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Set up log rotation if configured
            if self.get_config("enable_rotation", True):
                self._setup_rotation()

            # Set up structured logging if enabled
            if self.structured_logging:
                self._setup_structured_logging()

            self._initialized = True
            self.log_info("Logging service initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize logging service: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the logging service."""
        try:
            # Flush all handlers
            for handler in self._log_handlers:
                handler.flush()
                handler.close()

            self._log_handlers.clear()
            self._shutdown = True
            self.log_info("Logging service shutdown successfully")

        except Exception as e:
            self.log_error(f"Error during logging service shutdown: {e}")

    def log(self, level: str, message: str, **context) -> None:
        """
        Log a message with context.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **context: Additional context to include
        """
        logger = get_logger(context.get("component", "default"))

        if self.structured_logging:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message,
                "context": context,
            }
            message = json.dumps(log_entry)

        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message)

    def log_performance(self, operation: str, duration: float, **metrics) -> None:
        """
        Log performance metrics.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
            **metrics: Additional performance metrics
        """
        self.log(
            "INFO",
            f"Performance: {operation}",
            operation=operation,
            duration_ms=duration * 1000,
            **metrics,
        )

    def log_audit(self, action: str, user: str, **details) -> None:
        """
        Log an audit event.

        Args:
            action: Action performed
            user: User who performed the action
            **details: Additional audit details
        """
        self.log(
            "INFO",
            f"Audit: {action} by {user}",
            audit=True,
            action=action,
            user=user,
            **details,
        )

    def get_logs(
        self,
        level: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent logs.

        Args:
            level: Filter by log level
            component: Filter by component
            limit: Maximum number of logs to return

        Returns:
            List of log entries
        """
        # This would typically read from log files or a log aggregation service
        # For now, return empty list as placeholder
        return []

    def _setup_rotation(self) -> None:
        """Set up log rotation."""
        from logging.handlers import RotatingFileHandler

        max_bytes = self.get_config("max_bytes", 10 * 1024 * 1024)  # 10MB
        backup_count = self.get_config("backup_count", 5)

        handler = RotatingFileHandler(
            self.log_dir / "claude_mpm.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        self._log_handlers.append(handler)
        logging.getLogger().addHandler(handler)

    def _setup_structured_logging(self) -> None:
        """Set up structured JSON logging."""
        import logging.config

        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                }
            },
            "handlers": {
                "json_file": {
                    "class": "logging.FileHandler",
                    "filename": str(self.log_dir / "structured.json"),
                    "formatter": "json",
                }
            },
            "root": {"handlers": ["json_file"], "level": self.log_level},
        }

        try:
            logging.config.dictConfig(config)
        except ImportError:
            # If pythonjsonlogger is not available, fall back to regular logging
            self.log_warning("pythonjsonlogger not available, using standard logging")
