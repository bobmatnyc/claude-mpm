"""
Configuration constants for Claude MPM.

This module provides centralized access to configuration values that were
previously hardcoded throughout the codebase. It serves as a bridge between
the old hardcoded values and the new unified configuration system.

Usage:
    from claude_mpm.core.config_constants import ConfigConstants

    # Get timeout value
    timeout = ConfigConstants.get_timeout('hook_execution')

    # Get port value
    port = ConfigConstants.get_port('socketio')

    # Get cache setting
    cache_size = ConfigConstants.get_cache_setting('max_size_mb')
"""

from typing import Any, Optional

from .unified_config import ConfigurationService


class ConfigConstants:
    """
    Centralized access to configuration constants.

    This class provides a convenient way to access configuration values
    that were previously hardcoded, while maintaining backward compatibility.
    """

    _config_service: Optional[ConfigurationService] = None

    # Default values for backward compatibility
    DEFAULT_VALUES = {
        # Timeouts (in seconds)
        "timeouts": {
            "hook_execution": 5,
            "session_default": 30,
            "session_extended": 60,
            "agent_loading": 10,
            "startup": 60,
            "graceful_shutdown": 30,
        },
        # Ports
        "ports": {
            "socketio_default": 8765,
            "socketio_range_start": 8765,
            "socketio_range_end": 8775,
        },
        # Cache settings
        "cache": {
            "max_size_mb": 100,
            "max_entries": 10000,
            "default_ttl_seconds": 300,
        },
        # Session settings
        "sessions": {
            "max_age_minutes": 30,
            "cleanup_max_age_hours": 24,
            "timeout_minutes": 60,
        },
        # Retry and recovery
        "recovery": {
            "max_restarts": 3,
            "max_recovery_attempts": 3,
        },
        # Sleep and polling intervals (in seconds)
        "intervals": {
            "health_check": 0.1,
            "batch_window_ms": 100,
            "polling": 1.0,
            "brief_pause": 0.1,
        },
        # File and memory limits
        "limits": {
            "max_file_size_mb": 10,
            "max_memory_usage_mb": 1024,
        },
        # Logging configuration
        "logging": {
            "startup_logs_retention_count": 10,
            "mpm_logs_retention_count": 10,
        },
    }

    @classmethod
    def _get_config_service(cls) -> ConfigurationService:
        """Get or create the configuration service."""
        if cls._config_service is None:
            cls._config_service = ConfigurationService()
        return cls._config_service

    @classmethod
    def set_config_service(cls, config_service: ConfigurationService) -> None:
        """Set the configuration service (for dependency injection)."""
        cls._config_service = config_service

    @classmethod
    def get_timeout(cls, timeout_type: str) -> int:
        """
        Get timeout value by type.

        Args:
            timeout_type: Type of timeout (e.g., 'hook_execution', 'session_default')

        Returns:
            Timeout value in seconds
        """
        try:
            config = cls._get_config_service().config

            if timeout_type == "hook_execution":
                return config.performance.hook_timeout_seconds
            if timeout_type == "session_default":
                return config.performance.session_timeout_seconds
            if timeout_type == "session_extended":
                return config.sessions.session_timeout_minutes * 60
            if timeout_type == "agent_loading":
                return config.performance.agent_load_timeout_seconds
            if timeout_type == "startup":
                return config.performance.startup_timeout
            if timeout_type == "graceful_shutdown":
                return config.performance.graceful_shutdown_timeout
            return cls.DEFAULT_VALUES["timeouts"].get(timeout_type, 30)
        except Exception:
            return cls.DEFAULT_VALUES["timeouts"].get(timeout_type, 30)

    @classmethod
    def get_port(cls, port_type: str) -> int:
        """
        Get port value by type.

        Args:
            port_type: Type of port (e.g., 'socketio_default')

        Returns:
            Port number
        """
        try:
            config = cls._get_config_service().config

            if port_type == "socketio_default":
                return config.network.socketio_port
            if port_type == "socketio_range_start":
                return config.network.socketio_port_range[0]
            if port_type == "socketio_range_end":
                return config.network.socketio_port_range[1]
            return cls.DEFAULT_VALUES["ports"].get(port_type, 8765)
        except Exception:
            return cls.DEFAULT_VALUES["ports"].get(port_type, 8765)

    @classmethod
    def get_cache_setting(cls, setting_name: str) -> Any:
        """
        Get cache setting by name.

        Args:
            setting_name: Name of cache setting

        Returns:
            Cache setting value
        """
        try:
            config = cls._get_config_service().config

            if setting_name == "max_size_mb":
                return config.performance.cache_max_size_mb
            if setting_name == "max_entries":
                return config.performance.cache_max_entries
            if setting_name == "default_ttl_seconds":
                return config.performance.cache_default_ttl_seconds
            return cls.DEFAULT_VALUES["cache"].get(setting_name)
        except Exception:
            return cls.DEFAULT_VALUES["cache"].get(setting_name)

    @classmethod
    def get_logging_setting(cls, setting_name: str) -> Any:
        """
        Get logging setting by name.

        Args:
            setting_name: Name of logging setting

        Returns:
            Logging setting value
        """
        try:
            # For now, just return from DEFAULT_VALUES
            # Can be extended to read from unified config later
            return cls.DEFAULT_VALUES["logging"].get(setting_name)
        except Exception:
            # Fallback to default values
            if setting_name in {
                "startup_logs_retention_count",
                "mpm_logs_retention_count",
            }:
                return 10
            return None

    @classmethod
    def get_session_setting(cls, setting_name: str) -> Any:
        """
        Get session setting by name.

        Args:
            setting_name: Name of session setting

        Returns:
            Session setting value
        """
        try:
            config = cls._get_config_service().config

            if setting_name == "max_age_minutes":
                return config.sessions.max_age_minutes
            if setting_name == "cleanup_max_age_hours":
                return config.sessions.cleanup_max_age_hours
            if setting_name == "timeout_minutes":
                return config.sessions.session_timeout_minutes
            return cls.DEFAULT_VALUES["sessions"].get(setting_name)
        except Exception:
            return cls.DEFAULT_VALUES["sessions"].get(setting_name)

    @classmethod
    def get_recovery_setting(cls, setting_name: str) -> int:
        """
        Get recovery setting by name.

        Args:
            setting_name: Name of recovery setting

        Returns:
            Recovery setting value
        """
        try:
            config = cls._get_config_service().config

            if setting_name == "max_restarts":
                return config.performance.max_restarts
            if setting_name == "max_recovery_attempts":
                return config.performance.max_recovery_attempts
            return cls.DEFAULT_VALUES["recovery"].get(setting_name, 3)
        except Exception:
            return cls.DEFAULT_VALUES["recovery"].get(setting_name, 3)

    @classmethod
    def get_interval(cls, interval_type: str) -> float:
        """
        Get interval value by type.

        Args:
            interval_type: Type of interval

        Returns:
            Interval value in seconds
        """
        try:
            config = cls._get_config_service().config

            if interval_type == "health_check":
                return config.performance.health_check_interval_seconds
            if interval_type == "polling":
                return config.performance.polling_interval_seconds
            if interval_type == "batch_window_ms":
                return config.performance.batch_window_ms / 1000.0
            return cls.DEFAULT_VALUES["intervals"].get(interval_type, 1.0)
        except Exception:
            return cls.DEFAULT_VALUES["intervals"].get(interval_type, 1.0)

    @classmethod
    def get_limit(cls, limit_type: str) -> int:
        """
        Get limit value by type.

        Args:
            limit_type: Type of limit

        Returns:
            Limit value
        """
        try:
            config = cls._get_config_service().config

            if limit_type == "max_file_size_mb":
                return config.security.max_file_size_mb
            if limit_type == "max_memory_usage_mb":
                return config.performance.max_memory_usage_mb
            return cls.DEFAULT_VALUES["limits"].get(limit_type, 100)
        except Exception:
            return cls.DEFAULT_VALUES["limits"].get(limit_type, 100)


# Convenience functions for common values
def get_default_timeout() -> int:
    """Get default timeout value."""
    return ConfigConstants.get_timeout("session_default")


def get_socketio_port() -> int:
    """Get default SocketIO port."""
    return ConfigConstants.get_port("socketio_default")


def get_cache_size() -> float:
    """Get default cache size in MB."""
    return ConfigConstants.get_cache_setting("max_size_mb")


def get_max_restarts() -> int:
    """Get maximum restart attempts."""
    return ConfigConstants.get_recovery_setting("max_restarts")
