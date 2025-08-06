"""
Configuration management for Claude PM Framework.

Handles loading configuration from files, environment variables,
and default values with proper validation and type conversion.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging

from ..utils.config_manager import ConfigurationManager

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for Claude PM services.

    Supports loading from:
    - Python dictionaries
    - JSON files
    - YAML files
    - Environment variables
    """

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
        self._config: Dict[str, Any] = {}
        self._env_prefix = env_prefix
        self._config_mgr = ConfigurationManager(cache_enabled=True)

        # Load base configuration
        if config:
            self._config.update(config)

        # Load from file if provided
        if config_file:
            self.load_file(config_file)

        # Load from environment variables (new and legacy prefixes)
        self._load_env_vars()
        self._load_legacy_env_vars()

        # Apply defaults
        self._apply_defaults()

    def load_file(self, file_path: Union[str, Path]) -> None:
        """Load configuration from file."""
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return

        try:
            file_config = self._config_mgr.load_auto(file_path)
            if file_config:
                self._config = self._config_mgr.merge_configs(self._config, file_config)
                logger.info(f"Loaded configuration from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")

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
        elif value.lower() in ("false", "no", "0", "off"):
            return False

        # Numeric conversion
        try:
            if "." in value:
                return float(value)
            else:
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
                "network_timeout": 2.0
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
                    "success_threshold": 3
                },
                "strategy": {
                    "warning_threshold": 2,
                    "critical_threshold": 1,
                    "failure_window_seconds": 300,
                    "min_recovery_interval": 60
                }
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
            # Evaluation system - Phase 2 Mirascope integration
            "enable_evaluation": True,
            "evaluation_storage_path": str(Path.home() / ".claude-pm" / "training"),
            "correction_capture_enabled": True,
            "correction_storage_rotation_days": 30,
            "evaluation_logging_enabled": True,
            "auto_prompt_improvement": False,  # Disabled by default for Phase 1
            # Mirascope evaluation settings
            "evaluation_provider": "auto",  # auto, openai, anthropic
            "evaluation_criteria": ["correctness", "relevance", "completeness", "clarity", "helpfulness"],
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
                "enabled": True,                    # Master switch for memory system
                "auto_learning": True,              # Automatic learning extraction (changed default to True)
                "limits": {
                    "default_size_kb": 8,           # Default file size limit
                    "max_sections": 10,             # Maximum sections per file
                    "max_items_per_section": 15,    # Maximum items per section
                    "max_line_length": 120          # Maximum line length
                },
                "agent_overrides": {
                    "research": {                   # Research agent override
                        "size_kb": 16,              # Can have larger memory
                        "auto_learning": True       # Enable auto learning
                    },
                    "qa": {                         # QA agent override
                        "auto_learning": True       # Enable auto learning
                    }
                }
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
                        "max_error_rate": 0.1
                    }
                },
                "recovery": {
                    "enabled": True,
                    "max_attempts": 5,
                    "timeout": 30,
                    "circuit_breaker": {
                        "failure_threshold": 5,
                        "timeout_seconds": 300,
                        "success_threshold": 3
                    },
                    "strategy": {
                        "warning_threshold": 2,
                        "critical_threshold": 1,
                        "failure_window_seconds": 300,
                        "min_recovery_interval": 60
                    },
                    "actions": {
                        "log_warning": True,
                        "clear_connections": True,
                        "restart_service": True,
                        "emergency_stop": True
                    }
                }
            }
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
                raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Configuration saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration to {file_path}: {e}")
            raise

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
            logger.error(f"Configuration validation error: {e}")
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
            thresholds = self.get('health_thresholds', {})
            if thresholds.get('cpu_percent', 0) < 0 or thresholds.get('cpu_percent', 0) > 100:
                logger.warning("CPU threshold should be between 0-100, using default 80")
                self.set('health_thresholds.cpu_percent', 80.0)
            
            if thresholds.get('memory_mb', 0) <= 0:
                logger.warning("Memory threshold should be positive, using default 500MB")
                self.set('health_thresholds.memory_mb', 500)
            
            if thresholds.get('max_error_rate', 0) < 0 or thresholds.get('max_error_rate', 0) > 1:
                logger.warning("Error rate threshold should be between 0-1, using default 0.1")
                self.set('health_thresholds.max_error_rate', 0.1)
            
            # Validate recovery configuration
            recovery_config = self.get('recovery', {})
            if recovery_config.get('max_recovery_attempts', 0) <= 0:
                logger.warning("Max recovery attempts should be positive, using default 5")
                self.set('recovery.max_recovery_attempts', 5)
            
            # Validate circuit breaker configuration
            cb_config = recovery_config.get('circuit_breaker', {})
            if cb_config.get('failure_threshold', 0) <= 0:
                logger.warning("Circuit breaker failure threshold should be positive, using default 5")
                self.set('recovery.circuit_breaker.failure_threshold', 5)
            
            if cb_config.get('timeout_seconds', 0) <= 0:
                logger.warning("Circuit breaker timeout should be positive, using default 300")
                self.set('recovery.circuit_breaker.timeout_seconds', 300)
            
        except Exception as e:
            logger.error(f"Error validating health/recovery configuration: {e}")
    
    def get_health_monitoring_config(self) -> Dict[str, Any]:
        """Get health monitoring configuration with defaults."""
        base_config = {
            'enabled': self.get('enable_health_monitoring', True),
            'check_interval': self.get('health_check_interval', 30),
            'history_size': self.get('health_history_size', 100),
            'aggregation_window': self.get('health_aggregation_window', 300),
            'thresholds': self.get('health_thresholds', {
                'cpu_percent': 80.0,
                'memory_mb': 500,
                'file_descriptors': 1000,
                'max_clients': 1000,
                'max_error_rate': 0.1,
                'network_timeout': 2.0
            })
        }
        
        # Merge with socketio-specific config if available
        socketio_config = self.get('socketio_server.health_monitoring', {})
        if socketio_config:
            base_config.update(socketio_config)
        
        return base_config
    
    def get_recovery_config(self) -> Dict[str, Any]:
        """Get recovery configuration with defaults."""
        base_config = self.get('recovery', {
            'enabled': True,
            'check_interval': 60,
            'max_recovery_attempts': 5,
            'recovery_timeout': 30,
            'circuit_breaker': {
                'failure_threshold': 5,
                'timeout_seconds': 300,
                'success_threshold': 3
            },
            'strategy': {
                'warning_threshold': 2,
                'critical_threshold': 1,
                'failure_window_seconds': 300,
                'min_recovery_interval': 60
            }
        })
        
        # Merge with socketio-specific config if available
        socketio_config = self.get('socketio_server.recovery', {})
        if socketio_config:
            base_config = self._config_mgr.merge_configs(base_config, socketio_config)
        
        return base_config

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"<Config({len(self._config)} keys)>"
