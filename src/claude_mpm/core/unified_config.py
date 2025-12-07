"""
Unified Configuration Service for Claude MPM.

This module provides a centralized, type-safe configuration management system
using Pydantic models for validation and dependency injection for service access.

Design Principles:
1. Single source of truth for all configuration
2. Type safety with Pydantic models
3. Environment variable support with validation
4. Hierarchical configuration with defaults
5. Injectable service for dependency injection
6. Backward compatibility with existing config systems
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from .exceptions import ConfigurationError


class NetworkConfig(BaseModel):
    """Network and connection configuration."""

    socketio_host: str = Field(default="localhost", description="SocketIO server host")
    socketio_port: int = Field(
        default=8765, ge=1024, le=65535, description="SocketIO server port"
    )
    socketio_port_range: List[int] = Field(
        default=[8765, 8775], description="Port range for SocketIO"
    )
    connection_timeout: int = Field(
        default=30, ge=1, description="Connection timeout in seconds"
    )
    max_retries: int = Field(default=3, ge=0, description="Maximum connection retries")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    max_size_mb: int = Field(
        default=100, ge=1, description="Maximum log file size in MB"
    )
    retention_days: int = Field(
        default=30, ge=1, description="Log retention period in days"
    )
    format: str = Field(default="json", description="Log format (json, text)")
    enable_file_logging: bool = Field(default=True, description="Enable file logging")
    enable_console_logging: bool = Field(
        default=True, description="Enable console logging"
    )

    @validator("level")
    def validate_log_level(self, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()


class AgentConfig(BaseModel):
    """Agent system configuration."""

    auto_discover: bool = Field(
        default=True, description="Enable automatic agent discovery"
    )
    precedence: List[str] = Field(
        default=["project", "user", "system"], description="Agent precedence order"
    )
    enable_hot_reload: bool = Field(
        default=True, description="Enable hot reloading of agents"
    )
    cache_ttl_seconds: int = Field(
        default=3600, ge=0, description="Agent cache TTL in seconds"
    )
    validate_on_load: bool = Field(default=True, description="Validate agents on load")
    strict_validation: bool = Field(
        default=False, description="Enable strict validation"
    )
    max_concurrent_operations: int = Field(
        default=10, ge=1, description="Max concurrent agent operations"
    )


class MemoryConfig(BaseModel):
    """Memory management configuration."""

    enabled: bool = Field(default=True, description="Enable memory system")
    auto_learning: bool = Field(
        default=True, description="Enable automatic learning extraction"
    )
    default_size_kb: int = Field(
        default=80, ge=1, description="Default memory file size limit in KB"
    )
    max_sections: int = Field(
        default=10, ge=1, description="Maximum sections per memory file"
    )
    max_items_per_section: int = Field(
        default=15, ge=1, description="Maximum items per section"
    )
    max_line_length: int = Field(default=120, ge=1, description="Maximum line length")
    claude_json_warning_threshold_kb: int = Field(
        default=500, ge=1, description="Warning threshold for Claude JSON size"
    )


class SecurityConfig(BaseModel):
    """Security and validation configuration."""

    enable_path_validation: bool = Field(
        default=True, description="Enable path traversal protection"
    )
    max_file_size_mb: int = Field(
        default=10, ge=1, description="Maximum file size for operations"
    )
    allowed_file_extensions: List[str] = Field(
        default=[".md", ".txt", ".json", ".yaml", ".yml", ".py"],
        description="Allowed file extensions",
    )
    enable_sandbox_mode: bool = Field(
        default=False, description="Enable sandbox mode for agents"
    )


class PerformanceConfig(BaseModel):
    """Performance and resource configuration."""

    startup_timeout: int = Field(
        default=60, ge=1, description="Service startup timeout in seconds"
    )
    graceful_shutdown_timeout: int = Field(
        default=30, ge=1, description="Graceful shutdown timeout"
    )
    max_memory_usage_mb: int = Field(
        default=1024, ge=128, description="Maximum memory usage in MB"
    )
    enable_metrics: bool = Field(
        default=True, description="Enable performance metrics collection"
    )
    metrics_interval_seconds: int = Field(
        default=60, ge=1, description="Metrics collection interval"
    )

    # Timeout configurations
    hook_timeout_seconds: int = Field(
        default=5, ge=1, description="Hook execution timeout"
    )
    session_timeout_seconds: int = Field(
        default=30, ge=1, description="Session timeout"
    )
    agent_load_timeout_seconds: int = Field(
        default=10, ge=1, description="Agent loading timeout"
    )

    # Retry and recovery settings
    max_restarts: int = Field(default=3, ge=0, description="Maximum service restarts")
    max_recovery_attempts: int = Field(
        default=3, ge=0, description="Maximum recovery attempts"
    )

    # Cache settings
    cache_max_size_mb: float = Field(
        default=100, ge=1, description="Cache maximum size in MB"
    )
    cache_max_entries: int = Field(
        default=10000, ge=1, description="Cache maximum entries"
    )
    cache_default_ttl_seconds: int = Field(
        default=300, ge=1, description="Cache default TTL"
    )

    # Sleep and polling intervals
    health_check_interval_seconds: float = Field(
        default=0.1, ge=0.01, description="Health check interval"
    )
    batch_window_ms: int = Field(
        default=100, ge=1, description="Batch processing window in milliseconds"
    )
    polling_interval_seconds: float = Field(
        default=1.0, ge=0.1, description="General polling interval"
    )


class SessionConfig(BaseModel):
    """Session management configuration."""

    max_age_minutes: int = Field(
        default=30, ge=1, description="Session maximum age in minutes"
    )
    cleanup_max_age_hours: int = Field(
        default=24, ge=1, description="Session cleanup age in hours"
    )
    archive_old_sessions: bool = Field(
        default=True, description="Archive old sessions before cleanup"
    )
    session_timeout_minutes: int = Field(
        default=60, ge=1, description="Session timeout in minutes"
    )


class DevelopmentConfig(BaseModel):
    """Development and debugging configuration."""

    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    enable_profiling: bool = Field(
        default=False, description="Enable performance profiling"
    )
    hot_reload_enabled: bool = Field(
        default=True, description="Enable hot reloading in development"
    )
    mock_external_services: bool = Field(
        default=False, description="Mock external services for testing"
    )


class DocumentationConfig(BaseModel):
    """Documentation routing and management configuration."""

    docs_path: str = Field(
        default="docs/research/",
        description="Default path for session documentation (relative to project root)",
    )
    attach_to_tickets: bool = Field(
        default=True,
        description="Attach work products to tickets when ticket context exists",
    )
    backup_locally: bool = Field(
        default=True,
        description="Always create local backup copies of documentation",
    )
    enable_ticket_detection: bool = Field(
        default=True,
        description="Enable automatic ticket context detection from user messages",
    )


class UnifiedConfig(BaseSettings):
    """
    Unified configuration model for Claude MPM.

    This class combines all configuration sections into a single, type-safe model
    with environment variable support and validation.
    """

    # Configuration metadata
    version: str = Field(default="1.0", description="Configuration version")
    environment: str = Field(
        default="production",
        description="Environment (development, testing, production)",
    )

    # Configuration sections
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    agents: AgentConfig = Field(default_factory=AgentConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    sessions: SessionConfig = Field(default_factory=SessionConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    documentation: DocumentationConfig = Field(default_factory=DocumentationConfig)

    # Path configuration
    base_path: Optional[Path] = Field(
        default=None, description="Base path for Claude MPM"
    )
    config_path: Optional[Path] = Field(
        default=None, description="Configuration file path"
    )

    # Additional settings for backward compatibility
    extra_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Additional settings"
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "CLAUDE_MPM_"
        env_nested_delimiter = "__"
        case_sensitive = False
        validate_assignment = True
        extra = "allow"  # Allow extra fields for backward compatibility

    @validator("environment")
    def validate_environment(self, v):
        valid_envs = ["development", "testing", "production"]
        if v not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of: {valid_envs}")
        return v

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def get_nested(self, key: str, default: Any = None) -> Any:
        """
        Get nested configuration value using dot notation.

        Args:
            key: Dot-separated key (e.g., "network.socketio_port")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            keys = key.split(".")
            value = self
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                elif (
                    hasattr(value, "__getitem__")
                    and hasattr(value, "__contains__")
                    and k in value
                ):
                    value = value[k]
                else:
                    return default
            return value
        except (AttributeError, KeyError, TypeError):
            return default

    def set_nested(self, key: str, value: Any) -> None:
        """
        Set nested configuration value using dot notation.

        Args:
            key: Dot-separated key (e.g., "network.socketio_port")
            value: Value to set
        """
        keys = key.split(".")
        if len(keys) == 1:
            setattr(self, keys[0], value)
            return

        # Navigate to the parent object
        obj = self
        for k in keys[:-1]:
            if hasattr(obj, k):
                obj = getattr(obj, k)
            else:
                raise ConfigurationError(f"Invalid configuration path: {key}")

        # Set the final value
        if hasattr(obj, keys[-1]):
            setattr(obj, keys[-1], value)
        else:
            raise ConfigurationError(f"Invalid configuration key: {keys[-1]}")

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert to legacy dictionary format for backward compatibility.

        Returns:
            Dictionary representation compatible with old Config class
        """
        return {
            # Network settings
            "socketio_host": self.network.socketio_host,
            "socketio_port": self.network.socketio_port,
            "socketio_port_range": self.network.socketio_port_range,
            "connection_timeout": self.network.connection_timeout,
            # Logging settings
            "log_level": self.logging.level,
            "logging": {
                "level": self.logging.level,
                "max_size_mb": self.logging.max_size_mb,
                "retention_days": self.logging.retention_days,
                "format": self.logging.format,
            },
            # Agent settings
            "agents": {
                "auto_discover": self.agents.auto_discover,
                "precedence": self.agents.precedence,
                "enable_hot_reload": self.agents.enable_hot_reload,
                "cache_ttl_seconds": self.agents.cache_ttl_seconds,
            },
            # Memory settings
            "memory": {
                "enabled": self.memory.enabled,
                "auto_learning": self.memory.auto_learning,
                "limits": {
                    "default_size_kb": self.memory.default_size_kb,
                    "max_sections": self.memory.max_sections,
                    "max_items_per_section": self.memory.max_items_per_section,
                    "max_line_length": self.memory.max_line_length,
                },
                "claude_json_warning_threshold_kb": self.memory.claude_json_warning_threshold_kb,
            },
            # Performance settings
            "startup_timeout": self.performance.startup_timeout,
            "graceful_shutdown_timeout": self.performance.graceful_shutdown_timeout,
            "max_concurrent_operations": self.agents.max_concurrent_operations,
            "hook_timeout_seconds": self.performance.hook_timeout_seconds,
            "session_timeout_seconds": self.performance.session_timeout_seconds,
            "agent_load_timeout_seconds": self.performance.agent_load_timeout_seconds,
            "max_restarts": self.performance.max_restarts,
            "max_recovery_attempts": self.performance.max_recovery_attempts,
            # Cache settings
            "cache_max_size_mb": self.performance.cache_max_size_mb,
            "cache_max_entries": self.performance.cache_max_entries,
            "cache_default_ttl_seconds": self.performance.cache_default_ttl_seconds,
            # Session settings
            "session_max_age_minutes": self.sessions.max_age_minutes,
            "session_cleanup_max_age_hours": self.sessions.cleanup_max_age_hours,
            "session_archive_old": self.sessions.archive_old_sessions,
            # Development settings
            "debug": self.development.debug,
            "verbose": self.development.verbose,
            "environment": self.environment,
            # Additional settings
            **self.extra_settings,
        }


class ConfigurationService:
    """
    Injectable configuration service for dependency injection.

    This service provides a centralized way to access configuration throughout
    the application while maintaining backward compatibility with existing code.
    """

    def __init__(self, config: Optional[UnifiedConfig] = None):
        """
        Initialize configuration service.

        Args:
            config: Optional pre-configured UnifiedConfig instance
        """
        self._config = config or self._load_default_config()
        self._legacy_config: Optional[Any] = None

    def _load_default_config(self) -> UnifiedConfig:
        """Load configuration from environment and default files."""
        try:
            # Try to load from standard configuration files
            config_paths = [
                Path.cwd() / ".claude-mpm" / "configuration.yaml",
                Path.cwd() / ".claude-mpm" / "configuration.yml",
                Path.home() / ".claude-mpm" / "configuration.yaml",
                Path.home() / ".claude-mpm" / "configuration.yml",
            ]

            config_data: Dict[str, Any] = {}
            for config_path in config_paths:
                if config_path.exists():
                    import yaml

                    with config_path.open() as f:
                        file_config = yaml.safe_load(f) or {}
                    config_data.update(file_config)
                    break

            # Create unified config with environment variable support
            return UnifiedConfig(**config_data)

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                context={"error_type": type(e).__name__},
            ) from e

    @property
    def config(self) -> UnifiedConfig:
        """Get the unified configuration."""
        return self._config

    def get_legacy_config(self):
        """
        Get legacy Config instance for backward compatibility.

        Returns:
            Legacy Config instance that wraps the unified configuration
        """
        if self._legacy_config is None:
            from .config import Config

            legacy_dict = self._config.to_legacy_dict()
            self._legacy_config = Config(config=legacy_dict)
        return self._legacy_config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get_nested(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        self._config.set_nested(key, value)
        # Invalidate legacy config cache
        self._legacy_config = None

    def reload(self) -> None:
        """Reload configuration from sources."""
        self._config = self._load_default_config()
        self._legacy_config = None

    def validate(self) -> bool:
        """
        Validate the current configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Pydantic validation happens automatically, but we can add custom validation here
            if self._config.network.socketio_port in range(1024, 65536):
                return True
            raise ConfigurationError("Invalid SocketIO port range")
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}") from e

    def export_to_file(self, file_path: Union[str, Path], format: str = "yaml") -> None:
        """
        Export configuration to file.

        Args:
            file_path: Path to export file
            format: Export format (yaml, json)
        """
        file_path = Path(file_path)

        try:
            if format.lower() == "yaml":
                import yaml

                with file_path.open("w") as f:
                    yaml.dump(self._config.dict(), f, default_flow_style=False)
            elif format.lower() == "json":
                import json

                with file_path.open("w") as f:
                    json.dump(self._config.dict(), f, indent=2)
            else:
                raise ConfigurationError(f"Unsupported export format: {format}")

        except Exception as e:
            raise ConfigurationError(
                f"Failed to export configuration: {e}",
                context={"file_path": str(file_path), "format": format},
            ) from e
