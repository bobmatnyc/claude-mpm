"""
Configuration management for Claude PM Framework.

Handles loading configuration from files, environment variables,
and default values with proper validation and type conversion.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from ..utils.config_manager import ConfigurationManager
from .exceptions import ConfigurationError, FileOperationError
from .unified_paths import get_path_manager

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for Claude PM services.

    Implements singleton pattern to ensure configuration is loaded only once
    and shared across all services.

    Supports loading from:
    - Python dictionaries
    - JSON files
    - YAML files
    - Environment variables
    """

    _instance = None
    _initialized = False
    _success_logged = (
        False  # Class-level flag to track if success message was already logged
    )
    _lock = threading.Lock()  # Thread safety for singleton initialization

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to ensure single configuration instance.

        WHY: Configuration was being loaded 11 times during startup, once for each service.
        This singleton pattern ensures configuration is loaded only once and reused.
        Thread-safe implementation prevents race conditions during concurrent initialization.
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern for thread safety
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    logger.info("Creating new Config singleton instance")
                else:
                    logger.debug(
                        "Reusing existing Config singleton instance (concurrent init)"
                    )
        else:
            logger.debug("Reusing existing Config singleton instance")
        return cls._instance

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_file: Optional[Union[str, Path]] = None,
        env_prefix: str = "CLAUDE_PM_",
    ):
        """
        Initialize configuration.

        Args:
            config: Base configuration dictionary
            config_file: Path to configuration file (JSON or YAML)
            env_prefix: Prefix for environment variables
        """
        # Skip initialization if already done (singleton pattern)
        # Use thread-safe check to prevent concurrent initialization
        if Config._initialized:
            logger.debug("Config already initialized, skipping re-initialization")
            # If someone tries to load a different config file after initialization,
            # log a debug message but don't reload
            if config_file and str(config_file) != getattr(self, "_loaded_from", None):
                logger.debug(
                    f"Ignoring config_file parameter '{config_file}' - "
                    f"configuration already loaded from '{getattr(self, '_loaded_from', 'defaults')}'"
                )
            return

        # Thread-safe initialization - acquire lock for ENTIRE initialization process
        with Config._lock:
            # Double-check pattern - check again inside the lock
            if Config._initialized:
                logger.debug(
                    "Config already initialized (concurrent), skipping re-initialization"
                )
                return

            Config._initialized = True
            logger.info("Initializing Config singleton for the first time")

            # Initialize instance variables inside the lock to ensure thread safety
            self._config: Dict[str, Any] = {}
            self._env_prefix = env_prefix
            self._config_mgr = ConfigurationManager(cache_enabled=True)

            # Load base configuration
            if config:
                self._config.update(config)

            # Track where configuration was loaded from
            self._loaded_from = None
            # Track the actual file we loaded from to prevent re-loading
            self._actual_loaded_file = None

            # Load from file if provided
            # Note: Only ONE config file should be loaded, and success message shown only once
            if config_file:
                self.load_file(config_file, is_initial_load=True)
                self._loaded_from = str(config_file)
            else:
                # Try to load from standard location: .claude-mpm/configuration.yaml
                default_config = Path.cwd() / ".claude-mpm" / "configuration.yaml"
                if default_config.exists():
                    self.load_file(default_config, is_initial_load=True)
                    self._loaded_from = str(default_config)
                elif (
                    alt_config := Path.cwd() / ".claude-mpm" / "configuration.yml"
                ).exists():
                    # Also try .yml extension (using walrus operator for cleaner code)
                    self.load_file(alt_config, is_initial_load=True)
                    self._loaded_from = str(alt_config)

            # Load from environment variables (new and legacy prefixes)
            self._load_env_vars()
            self._load_legacy_env_vars()

            # Apply defaults
            self._apply_defaults()

    def load_file(
        self, file_path: Union[str, Path], is_initial_load: bool = True
    ) -> None:
        """Load configuration from file with enhanced error handling.

        WHY: Configuration loading failures can cause silent issues. We need
        to provide clear, actionable error messages to help users fix problems.

        Args:
            file_path: Path to the configuration file
            is_initial_load: Whether this is the initial configuration load (for logging control)
        """
        file_path = Path(file_path)

        # Check if we've already loaded from this exact file to prevent duplicate messages
        if hasattr(self, "_actual_loaded_file") and self._actual_loaded_file == str(
            file_path
        ):
            logger.debug(
                f"Configuration already loaded from {file_path}, skipping reload"
            )
            return

        if not file_path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            logger.info(
                f"TIP: Create a configuration file with: mkdir -p {file_path.parent} && touch {file_path}"
            )
            return

        try:
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                logger.error(f"Configuration file is not readable: {file_path}")
                logger.info(f"TIP: Fix permissions with: chmod 644 {file_path}")
                return

            # Check file size (warn if too large)
            file_size = file_path.stat().st_size
            if file_size > 1024 * 1024:  # 1MB
                logger.warning(
                    f"Configuration file is large ({file_size} bytes): {file_path}"
                )

            # Try to load the configuration
            file_config = self._config_mgr.load_auto(file_path)
            if file_config:
                self._config = self._config_mgr.merge_configs(self._config, file_config)
                # Track that we've successfully loaded from this file
                self._actual_loaded_file = str(file_path)

                # Only log success message once using class-level flag to avoid duplicate messages
                # Check if we should log success message (thread-safe for reads after initialization)
                if is_initial_load:
                    if not Config._success_logged:
                        # Set flag IMMEDIATELY before logging to prevent any possibility of duplicate
                        # messages. No lock needed here since we're already inside __init__ lock
                        Config._success_logged = True
                        logger.info(
                            f"✓ Successfully loaded configuration from {file_path}"
                        )
                    else:
                        # Configuration already successfully loaded before, just debug log
                        logger.debug(
                            f"Configuration already loaded, skipping success message for {file_path}"
                        )
                else:
                    # Not initial load (shouldn't happen in normal flow, but handle gracefully)
                    logger.debug(f"Configuration reloaded from {file_path}")

                # Log important configuration values for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    response_logging = file_config.get("response_logging", {})
                    if response_logging:
                        logger.debug(
                            f"Response logging enabled: {response_logging.get('enabled', False)}"
                        )
                        logger.debug(
                            f"Response logging format: {response_logging.get('format', 'json')}"
                        )

        except yaml.YAMLError as e:
            logger.error(f"YAML syntax error in {file_path}: {e}")
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                logger.error(f"Error at line {mark.line + 1}, column {mark.column + 1}")
            logger.info(
                "TIP: Validate your YAML at https://www.yamllint.com/ or run: python scripts/validate_configuration.py"
            )
            logger.info(
                "TIP: Common issue - YAML requires spaces, not tabs. Fix with: sed -i '' 's/\t/    /g' "
                + str(file_path)
            )
            # Store error for later retrieval
            self._config["_load_error"] = str(e)

        except json.JSONDecodeError as e:
            logger.error(f"JSON syntax error in {file_path}: {e}")
            logger.error(f"Error at line {e.lineno}, column {e.colno}")
            logger.info("TIP: Validate your JSON at https://jsonlint.com/")
            self._config["_load_error"] = str(e)

        except (OSError, PermissionError) as e:
            raise FileOperationError(
                f"Failed to read configuration file: {e}",
                context={
                    "file_path": str(file_path),
                    "operation": "read",
                    "error_type": type(e).__name__,
                },
            )
        except Exception as e:
            # Catch any remaining unexpected errors and wrap them as configuration errors
            raise ConfigurationError(
                f"Unexpected error loading configuration from {file_path}: {e}",
                context={
                    "file_path": str(file_path),
                    "error_type": type(e).__name__,
                    "original_error": str(e),
                },
            )

    def _load_env_vars(self) -> None:
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                config_key = key[len(self._env_prefix) :].lower()

                # Convert environment variable value to appropriate type
                converted_value = self._convert_env_value(value)
                self._config[config_key] = converted_value

                logger.debug(f"Loaded env var: {key} -> {config_key}")

    def _load_legacy_env_vars(self) -> None:
        """Load configuration from legacy CLAUDE_PM_ environment variables for backward compatibility."""
        legacy_prefix = "CLAUDE_PM_"
        loaded_legacy_vars = []

        for key, value in os.environ.items():
            if key.startswith(legacy_prefix):
                config_key = key[len(legacy_prefix) :].lower()

                # Only load if not already set by new environment variables
                if config_key not in self._config:
                    converted_value = self._convert_env_value(value)
                    self._config[config_key] = converted_value
                    loaded_legacy_vars.append(key)
                    logger.debug(f"Loaded legacy env var: {key} -> {config_key}")

        # Warn about legacy variables in use
        if loaded_legacy_vars:
            logger.warning(
                f"Using legacy CLAUDE_PM_ environment variables: {', '.join(loaded_legacy_vars)}. "
                "Please migrate to CLAUDE_MULTIAGENT_PM_ prefix for future compatibility."
            )

    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # Numeric conversion
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _apply_defaults(self) -> None:
        """Apply default configuration values."""
        # Get CLAUDE_MULTIAGENT_PM_ROOT (new) or CLAUDE_PM_ROOT (backward compatibility)
        claude_multiagent_pm_root = os.getenv("CLAUDE_MULTIAGENT_PM_ROOT")
        claude_pm_root = os.getenv("CLAUDE_PM_ROOT")  # Backward compatibility

        # Prioritize new variable name, fall back to old for compatibility
        project_root = claude_multiagent_pm_root or claude_pm_root

        if project_root:
            # Use custom root directory
            claude_pm_path = project_root
            base_path = str(Path(project_root).parent)
            managed_path = str(Path(project_root).parent / "managed")

            # Log which environment variable was used
            if claude_multiagent_pm_root:
                logger.debug("Using CLAUDE_MULTIAGENT_PM_ROOT environment variable")
            else:
                logger.warning(
                    "Using deprecated CLAUDE_PM_ROOT environment variable. Please migrate to CLAUDE_MULTIAGENT_PM_ROOT"
                )
        else:
            # Use default paths
            base_path = str(Path.home() / "Projects")
            claude_pm_path = str(Path.home() / "Projects" / "claude-pm")
            managed_path = str(Path.home() / "Projects" / "managed")

        defaults = {
            # Logging
            "log_level": "INFO",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            # Health monitoring
            "enable_health_monitoring": True,
            "health_check_interval": 30,
            "health_history_size": 100,
            "health_aggregation_window": 300,
            # Metrics
            "enable_metrics": True,
            "metrics_interval": 60,
            # Advanced health monitoring thresholds
            "health_thresholds": {
                "cpu_percent": 80.0,
                "memory_mb": 500,
                "file_descriptors": 1000,
                "max_clients": 1000,
                "max_error_rate": 0.1,
                "network_timeout": 2.0,
            },
            # Automatic recovery configuration
            "recovery": {
                "enabled": True,
                "check_interval": 60,
                "max_recovery_attempts": 5,
                "recovery_timeout": 30,
                "circuit_breaker": {
                    "failure_threshold": 5,
                    "timeout_seconds": 300,
                    "success_threshold": 3,
                },
                "strategy": {
                    "warning_threshold": 2,
                    "critical_threshold": 1,
                    "failure_window_seconds": 300,
                    "min_recovery_interval": 60,
                },
            },
            # Service management
            "graceful_shutdown_timeout": 30,
            "startup_timeout": 60,
            # ai-trackdown-tools integration
            "use_ai_trackdown_tools": False,
            "ai_trackdown_tools_timeout": 30,
            "ai_trackdown_tools_fallback_logging": True,
            # Claude PM specific - dynamic path resolution
            "base_path": base_path,
            "claude_pm_path": claude_pm_path,
            "managed_path": managed_path,
            # Alerting
            "enable_alerting": True,
            "alert_threshold": 60,
            # Development
            "debug": False,
            "verbose": False,
            # Task and issue tracking
            "enable_persistent_tracking": True,
            "fallback_tracking_method": "logging",  # Options: "logging", "file", "disabled"
            # Memory management configuration
            "memory_management": {
                "enabled": True,
                "claude_json_warning_threshold_kb": 500,  # Warn at 500KB
                "claude_json_critical_threshold_kb": 1024,  # Critical at 1MB
                "auto_archive_enabled": False,  # Don't auto-archive by default
                "archive_retention_days": 90,  # Keep archives for 90 days
                "session_retention_hours": 24,  # Keep active sessions for 24 hours
                "conversation_retention_days": 30,  # Keep conversations for 30 days
                "monitor_memory_usage": True,  # Monitor memory usage
                "memory_usage_log_interval": 300,  # Log memory usage every 5 minutes
                "max_memory_usage_mb": 2048,  # Warn if memory usage exceeds 2GB
                "cleanup_on_startup": False,  # Don't auto-cleanup on startup
                "compress_archives": True,  # Compress archived files
            },
            # Evaluation system - Phase 2 Mirascope integration
            "enable_evaluation": True,
            "evaluation_storage_path": str(
                get_path_manager().get_user_config_dir() / "training"
            ),
            "correction_capture_enabled": True,
            "correction_storage_rotation_days": 30,
            "evaluation_logging_enabled": True,
            "auto_prompt_improvement": False,  # Disabled by default for Phase 1
            # Mirascope evaluation settings
            "evaluation_provider": "auto",  # auto, openai, anthropic
            "evaluation_criteria": [
                "correctness",
                "relevance",
                "completeness",
                "clarity",
                "helpfulness",
            ],
            "evaluation_caching_enabled": True,
            "evaluation_cache_ttl_hours": 24,
            "evaluation_cache_max_size": 1000,
            "evaluation_cache_memory_limit_mb": 100,
            "evaluation_cache_strategy": "hybrid",  # lru, ttl, hybrid
            "evaluation_async_enabled": True,
            "evaluation_batch_size": 10,
            "evaluation_max_concurrent": 10,
            "evaluation_timeout_seconds": 30,
            "evaluation_model_config": {},
            # Integration settings
            "auto_evaluate_corrections": True,
            "auto_evaluate_responses": True,
            "batch_evaluation_enabled": True,
            "batch_evaluation_interval_minutes": 5,
            # Performance optimization
            "evaluation_performance_enabled": True,
            "evaluation_batch_wait_ms": 100,
            "evaluation_max_concurrent_batches": 5,
            "evaluation_circuit_breaker_threshold": 5,
            "evaluation_circuit_breaker_timeout": 60,
            "evaluation_circuit_breaker_success_threshold": 3,
            # Metrics and monitoring
            "enable_evaluation_metrics": True,
            "evaluation_monitoring_enabled": True,
            # Additional configuration
            "correction_max_file_size_mb": 10,
            "correction_backup_enabled": True,
            "correction_compression_enabled": True,
            # Agent Memory System configuration
            "memory": {
                "enabled": True,  # Master switch for memory system
                "auto_learning": True,  # Automatic learning extraction (changed default to True)
                "limits": {
                    "default_size_kb": 80,  # Default file size limit (80KB ~20k tokens)
                    "max_sections": 10,  # Maximum sections per file
                    "max_items_per_section": 15,  # Maximum items per section
                    "max_line_length": 120,  # Maximum line length
                },
                "agent_overrides": {
                    "research": {  # Research agent override
                        "size_kb": 120,  # Can have larger memory (120KB ~30k tokens)
                        "auto_learning": True,  # Enable auto learning
                    },
                    "qa": {
                        "auto_learning": True
                    },  # QA agent override  # Enable auto learning
                },
            },
            # Socket.IO server health and recovery configuration
            "socketio_server": {
                "host": "localhost",
                "port": 8765,
                "enable_health_monitoring": True,
                "enable_recovery": True,
                "health_monitoring": {
                    "check_interval": 30,
                    "history_size": 100,
                    "aggregation_window": 300,
                    "thresholds": {
                        "cpu_percent": 80.0,
                        "memory_mb": 500,
                        "file_descriptors": 1000,
                        "max_clients": 1000,
                        "max_error_rate": 0.1,
                    },
                },
                "recovery": {
                    "enabled": True,
                    "max_attempts": 5,
                    "timeout": 30,
                    "circuit_breaker": {
                        "failure_threshold": 5,
                        "timeout_seconds": 300,
                        "success_threshold": 3,
                    },
                    "strategy": {
                        "warning_threshold": 2,
                        "critical_threshold": 1,
                        "failure_window_seconds": 300,
                        "min_recovery_interval": 60,
                    },
                    "actions": {
                        "log_warning": True,
                        "clear_connections": True,
                        "restart_service": True,
                        "emergency_stop": True,
                    },
                },
            },
            # Monitor server configuration (decoupled from dashboard)
            "monitor_server": {
                "host": "localhost",
                "port": 8765,  # Default monitor port (shared with dashboard)
                "enable_health_monitoring": True,
                "auto_start": False,  # Don't auto-start with dashboard by default
                "event_buffer_size": 2000,  # Larger buffer for monitor server
                "client_timeout": 60,  # Timeout for inactive clients
            },
            # Dashboard server configuration (connects to monitor)
            "dashboard_server": {
                "host": "localhost",
                "port": 8765,  # Dashboard UI port
                "monitor_host": "localhost",  # Monitor server host to connect to
                "monitor_port": 8765,  # Monitor server port to connect to
                "auto_connect_monitor": True,  # Automatically connect to monitor
                "monitor_reconnect": True,  # Auto-reconnect to monitor if disconnected
                "fallback_standalone": True,  # Run in standalone mode if monitor unavailable
            },
            # Agent deployment configuration
            "agent_deployment": {
                "excluded_agents": [],  # List of agent IDs to exclude from deployment
                "exclude_dependencies": False,  # Whether to exclude agent dependencies too
                "case_sensitive": False,  # Whether agent name matching is case-sensitive
                "filter_non_mpm_agents": True,  # Filter out non-MPM agents by default
                "mpm_author_patterns": [
                    "claude mpm",
                    "claude-mpm",
                    "anthropic",
                ],  # Patterns for MPM agents
            },
            # Instruction reinforcement system configuration
            "instruction_reinforcement": {
                "enabled": True,
                "test_mode": True,
                "injection_interval": 5,
                "test_messages": [
                    "[TEST-REMINDER] This is an injected instruction reminder",
                    "[PM-INSTRUCTION] Remember to delegate all work to agents",
                    "[PM-INSTRUCTION] Do not use Edit, Write, or Bash tools directly",
                    "[PM-INSTRUCTION] Your role is orchestration and coordination",
                ],
                "production_messages": [
                    "[PM-REMINDER] Delegate implementation tasks to specialized agents",
                    "[PM-REMINDER] Use Task tool for all work delegation",
                    "[PM-REMINDER] Focus on orchestration, not implementation",
                    "[PM-REMINDER] Your role is coordination and management",
                ],
            },
        }

        # Apply defaults for missing keys
        for key, default_value in defaults.items():
            if key not in self._config:
                self._config[key] = default_value

        # Validate health and recovery configuration
        self._validate_health_recovery_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        # Support nested keys with dot notation
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        # Support nested keys with dot notation
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def update(self, config: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._config = self._config_mgr.merge_configs(self._config, config)

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self._config.copy()

    def save(self, file_path: Union[str, Path], format: str = "json") -> None:
        """Save configuration to file."""
        file_path = Path(file_path)

        try:
            if format.lower() == "json":
                self._config_mgr.save_json(self._config, file_path)
            elif format.lower() in ["yaml", "yml"]:
                self._config_mgr.save_yaml(self._config, file_path)
            else:
                raise ConfigurationError(
                    f"Unsupported configuration format: {format}",
                    context={
                        "format": format,
                        "supported_formats": ["json", "yaml", "yml"],
                    },
                )

            logger.info(f"Configuration saved to {file_path}")

        except (OSError, PermissionError) as e:
            raise FileOperationError(
                f"Failed to write configuration file: {e}",
                context={
                    "file_path": str(file_path),
                    "operation": "write",
                    "format": format,
                    "error_type": type(e).__name__,
                },
            )
        except Exception as e:
            # Re-raise ConfigurationError as-is, wrap others
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Unexpected error saving configuration: {e}",
                context={
                    "file_path": str(file_path),
                    "format": format,
                    "error_type": type(e).__name__,
                },
            )

    def validate(self, schema: Dict[str, Any]) -> bool:
        """
        Validate configuration against a schema.

        Args:
            schema: Dictionary defining required keys and types

        Returns:
            True if valid, False otherwise
        """
        try:
            for key, expected_type in schema.items():
                if key not in self._config:
                    logger.error(f"Missing required configuration key: {key}")
                    return False

                value = self.get(key)
                if not isinstance(value, expected_type):
                    logger.error(
                        f"Configuration key '{key}' has wrong type. "
                        f"Expected {expected_type}, got {type(value)}"
                    )
                    return False

            return True

        except Exception as e:
            # Validation errors should be logged but not raise exceptions
            # since this method returns a boolean result
            logger.error(f"Unexpected error during configuration validation: {e}")
            logger.debug(f"Validation error details: {type(e).__name__}: {e}")
            return False

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style assignment."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if configuration contains a key."""
        return self.get(key) is not None

    def _validate_health_recovery_config(self) -> None:
        """Validate health monitoring and recovery configuration."""
        try:
            # Validate health thresholds
            thresholds = self.get("health_thresholds", {})
            if (
                thresholds.get("cpu_percent", 0) < 0
                or thresholds.get("cpu_percent", 0) > 100
            ):
                logger.warning(
                    "CPU threshold should be between 0-100, using default 80"
                )
                self.set("health_thresholds.cpu_percent", 80.0)

            if thresholds.get("memory_mb", 0) <= 0:
                logger.warning(
                    "Memory threshold should be positive, using default 500MB"
                )
                self.set("health_thresholds.memory_mb", 500)

            if (
                thresholds.get("max_error_rate", 0) < 0
                or thresholds.get("max_error_rate", 0) > 1
            ):
                logger.warning(
                    "Error rate threshold should be between 0-1, using default 0.1"
                )
                self.set("health_thresholds.max_error_rate", 0.1)

            # Validate recovery configuration
            recovery_config = self.get("recovery", {})
            if recovery_config.get("max_recovery_attempts", 0) <= 0:
                logger.warning(
                    "Max recovery attempts should be positive, using default 5"
                )
                self.set("recovery.max_recovery_attempts", 5)

            # Validate circuit breaker configuration
            cb_config = recovery_config.get("circuit_breaker", {})
            if cb_config.get("failure_threshold", 0) <= 0:
                logger.warning(
                    "Circuit breaker failure threshold should be positive, using default 5"
                )
                self.set("recovery.circuit_breaker.failure_threshold", 5)

            if cb_config.get("timeout_seconds", 0) <= 0:
                logger.warning(
                    "Circuit breaker timeout should be positive, using default 300"
                )
                self.set("recovery.circuit_breaker.timeout_seconds", 300)

        except Exception as e:
            logger.error(f"Error validating health/recovery configuration: {e}")

    def get_health_monitoring_config(self) -> Dict[str, Any]:
        """Get health monitoring configuration with defaults."""
        base_config = {
            "enabled": self.get("enable_health_monitoring", True),
            "check_interval": self.get("health_check_interval", 30),
            "history_size": self.get("health_history_size", 100),
            "aggregation_window": self.get("health_aggregation_window", 300),
            "thresholds": self.get(
                "health_thresholds",
                {
                    "cpu_percent": 80.0,
                    "memory_mb": 500,
                    "file_descriptors": 1000,
                    "max_clients": 1000,
                    "max_error_rate": 0.1,
                    "network_timeout": 2.0,
                },
            ),
        }

        # Merge with socketio-specific config if available
        socketio_config = self.get("socketio_server.health_monitoring", {})
        if socketio_config:
            base_config.update(socketio_config)

        return base_config

    def get_recovery_config(self) -> Dict[str, Any]:
        """Get recovery configuration with defaults."""
        base_config = self.get(
            "recovery",
            {
                "enabled": True,
                "check_interval": 60,
                "max_recovery_attempts": 5,
                "recovery_timeout": 30,
                "circuit_breaker": {
                    "failure_threshold": 5,
                    "timeout_seconds": 300,
                    "success_threshold": 3,
                },
                "strategy": {
                    "warning_threshold": 2,
                    "critical_threshold": 1,
                    "failure_window_seconds": 300,
                    "min_recovery_interval": 60,
                },
            },
        )

        # Merge with socketio-specific config if available
        socketio_config = self.get("socketio_server.recovery", {})
        if socketio_config:
            base_config = self._config_mgr.merge_configs(base_config, socketio_config)

        return base_config

    def validate_configuration(self) -> Tuple[bool, List[str], List[str]]:
        """Validate the loaded configuration programmatically.

        WHY: Provide a programmatic way to validate configuration that can be
        used by other components to check configuration health.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Check if there was a load error
        if "_load_error" in self._config:
            errors.append(f"Configuration load error: {self._config['_load_error']}")

        # Validate response_logging configuration
        response_logging = self.get("response_logging", {})
        if response_logging:
            # Check enabled field
            if "enabled" in response_logging and not isinstance(
                response_logging["enabled"], bool
            ):
                errors.append(
                    f"response_logging.enabled must be boolean, got {type(response_logging['enabled']).__name__}"
                )

            # Check format field
            if "format" in response_logging:
                valid_formats = ["json", "syslog", "journald"]
                if response_logging["format"] not in valid_formats:
                    errors.append(
                        f"response_logging.format must be one of {valid_formats}, "
                        f"got '{response_logging['format']}'"
                    )

            # Check session_directory
            if "session_directory" in response_logging:
                session_dir = Path(response_logging["session_directory"])
                if session_dir.is_absolute() and not session_dir.parent.exists():
                    warnings.append(
                        f"Parent directory for session_directory does not exist: {session_dir.parent}"
                    )

        # Validate memory configuration
        memory_config = self.get("memory", {})
        if memory_config:
            if "enabled" in memory_config and not isinstance(
                memory_config["enabled"], bool
            ):
                errors.append("memory.enabled must be boolean")

            # Check limits
            limits = memory_config.get("limits", {})
            for field in ["default_size_kb", "max_sections", "max_items_per_section"]:
                if field in limits:
                    value = limits[field]
                    if not isinstance(value, int) or value <= 0:
                        errors.append(
                            f"memory.limits.{field} must be positive integer, got {value}"
                        )

        # Validate health thresholds
        health_thresholds = self.get("health_thresholds", {})
        if health_thresholds:
            cpu = health_thresholds.get("cpu_percent")
            if cpu is not None and (
                not isinstance(cpu, (int, float)) or cpu < 0 or cpu > 100
            ):
                errors.append(f"health_thresholds.cpu_percent must be 0-100, got {cpu}")

            mem = health_thresholds.get("memory_mb")
            if mem is not None and (not isinstance(mem, (int, float)) or mem <= 0):
                errors.append(
                    f"health_thresholds.memory_mb must be positive, got {mem}"
                )

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def get_configuration_status(self) -> Dict[str, Any]:
        """Get detailed configuration status for debugging.

        WHY: Provide a comprehensive view of configuration state for
        troubleshooting and health checks.

        Returns:
            Dictionary with configuration status information
        """
        is_valid, errors, warnings = self.validate_configuration()

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "loaded_from": getattr(self, "_loaded_from", "defaults"),
            "key_count": len(self._config),
            "has_response_logging": "response_logging" in self._config,
            "has_memory_config": "memory" in self._config,
            "response_logging_enabled": self.get("response_logging.enabled", False),
            "memory_enabled": self.get("memory.enabled", False),
        }

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"<Config({len(self._config)} keys)>"

    @classmethod
    def reset_singleton(cls):
        """Reset the singleton instance (mainly for testing purposes).

        WHY: During testing, we may need to reset the singleton to test different
        configurations. This method allows controlled reset of the singleton state.
        """
        cls._instance = None
        cls._initialized = False
        cls._success_logged = False
        logger.debug("Config singleton reset")
