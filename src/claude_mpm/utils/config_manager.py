"""Configuration management utility for Claude MPM.

This module provides a unified interface for loading, saving, and managing
configurations across different file formats (JSON, YAML, TOML).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Handle optional imports
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import toml

    HAS_TOML = True
except ImportError:
    HAS_TOML = False

from ..core.logger import get_logger

logger = get_logger(__name__)


class ConfigurationManager:
    """Unified configuration management with support for multiple formats."""

    def __init__(self, cache_enabled: bool = True):
        """Initialize the configuration manager.

        Args:
            cache_enabled: Whether to enable configuration caching
        """
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}

    def _get_cache_key(self, file_path: Union[str, Path]) -> str:
        """Generate a cache key for a configuration file."""
        path = Path(file_path)
        stat = path.stat()
        return f"{path.absolute()}:{stat.st_mtime}:{stat.st_size}"

    def _check_cache(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Check if configuration is cached and still valid."""
        if not self.cache_enabled:
            return None

        try:
            cache_key = self._get_cache_key(file_path)
            return self._cache.get(cache_key)
        except OSError:
            return None

    def _update_cache(self, file_path: Union[str, Path], config: Dict[str, Any]):
        """Update the configuration cache."""
        if not self.cache_enabled:
            return

        try:
            cache_key = self._get_cache_key(file_path)
            self._cache[cache_key] = config
        except OSError:
            pass

    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()

    def load_json(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load JSON configuration file.

        Args:
            file_path: Path to JSON file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        file_path = Path(file_path)

        # Check cache
        cached = self._check_cache(file_path)
        if cached is not None:
            logger.debug(f"Using cached configuration for {file_path}")
            return cached

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        logger.debug(f"Loading JSON configuration from {file_path}")
        try:
            with open(file_path, encoding="utf-8") as f:
                config = json.load(f)
            self._update_cache(file_path, config)
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading JSON from {file_path}: {e}")
            raise

    def load_yaml(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load YAML configuration file.

        Args:
            file_path: Path to YAML file

        Returns:
            Configuration dictionary

        Raises:
            ImportError: If PyYAML is not installed
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not HAS_YAML:
            raise ImportError(
                "PyYAML is required for YAML support. Install with: pip install pyyaml"
            )

        file_path = Path(file_path)

        # Check cache
        cached = self._check_cache(file_path)
        if cached is not None:
            logger.debug(f"Using cached configuration for {file_path}")
            return cached

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        logger.debug(f"Loading YAML configuration from {file_path}")
        try:
            with open(file_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            self._update_cache(file_path, config)
            return config
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading YAML from {file_path}: {e}")
            raise

    def load_toml(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load TOML configuration file.

        Args:
            file_path: Path to TOML file

        Returns:
            Configuration dictionary

        Raises:
            ImportError: If toml is not installed
            FileNotFoundError: If file doesn't exist
            toml.TomlDecodeError: If TOML is invalid
        """
        if not HAS_TOML:
            raise ImportError(
                "toml is required for TOML support. Install with: pip install toml"
            )

        file_path = Path(file_path)

        # Check cache
        cached = self._check_cache(file_path)
        if cached is not None:
            logger.debug(f"Using cached configuration for {file_path}")
            return cached

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        logger.debug(f"Loading TOML configuration from {file_path}")
        try:
            with open(file_path, encoding="utf-8") as f:
                config = toml.load(f)
            self._update_cache(file_path, config)
            return config
        except toml.TomlDecodeError as e:
            logger.error(f"Invalid TOML in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading TOML from {file_path}: {e}")
            raise

    def load_auto(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Auto-detect format and load configuration file.

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix in [".json"]:
            return self.load_json(file_path)
        if suffix in [".yaml", ".yml"]:
            return self.load_yaml(file_path)
        if suffix in [".toml"]:
            return self.load_toml(file_path)
        raise ValueError(f"Unsupported configuration format: {suffix}")

    def save_json(
        self,
        config: Dict[str, Any],
        file_path: Union[str, Path],
        indent: int = 2,
        sort_keys: bool = True,
    ):
        """Save configuration as JSON.

        Args:
            config: Configuration dictionary
            file_path: Path to save JSON file
            indent: JSON indentation (default: 2)
            sort_keys: Whether to sort keys (default: True)
        """
        file_path = Path(file_path)
        logger.debug(f"Saving JSON configuration to {file_path}")

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=indent, sort_keys=sort_keys)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving JSON to {file_path}: {e}")
            raise

    def save_yaml(
        self,
        config: Dict[str, Any],
        file_path: Union[str, Path],
        default_flow_style: bool = False,
        sort_keys: bool = True,
    ):
        """Save configuration as YAML.

        Args:
            config: Configuration dictionary
            file_path: Path to save YAML file
            default_flow_style: Use flow style (default: False)
            sort_keys: Whether to sort keys (default: True)

        Raises:
            ImportError: If PyYAML is not installed
        """
        if not HAS_YAML:
            raise ImportError(
                "PyYAML is required for YAML support. Install with: pip install pyyaml"
            )

        file_path = Path(file_path)
        logger.debug(f"Saving YAML configuration to {file_path}")

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    config,
                    f,
                    default_flow_style=default_flow_style,
                    sort_keys=sort_keys,
                )
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving YAML to {file_path}: {e}")
            raise

    def save_toml(self, config: Dict[str, Any], file_path: Union[str, Path]):
        """Save configuration as TOML.

        Args:
            config: Configuration dictionary
            file_path: Path to save TOML file

        Raises:
            ImportError: If toml is not installed
        """
        if not HAS_TOML:
            raise ImportError(
                "toml is required for TOML support. Install with: pip install toml"
            )

        file_path = Path(file_path)
        logger.debug(f"Saving TOML configuration to {file_path}")

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                toml.dump(config, f)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving TOML to {file_path}: {e}")
            raise

    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configurations.

        Later configurations override earlier ones. Nested dictionaries
        are merged recursively.

        Args:
            *configs: Configuration dictionaries to merge

        Returns:
            Merged configuration dictionary
        """
        result = {}

        for config in configs:
            self._deep_merge(result, config)

        return result

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep merge source into target dictionary."""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def validate_schema(
        self, config: Dict[str, Any], schema: Dict[str, Any]
    ) -> List[str]:
        """Validate configuration against a schema.

        Args:
            config: Configuration to validate
            schema: Schema dictionary defining required fields and types

        Returns:
            List of validation errors (empty if valid)

        Example schema:
            {
                "required": ["field1", "field2"],
                "types": {
                    "field1": str,
                    "field2": int,
                    "field3": list
                }
            }
        """
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in config:
                errors.append(f"Required field missing: {field}")

        # Check types
        types = schema.get("types", {})
        for field, expected_type in types.items():
            if field in config:
                if not isinstance(config[field], expected_type):
                    actual_type = type(config[field]).__name__
                    expected_name = expected_type.__name__
                    errors.append(
                        f"Invalid type for {field}: expected {expected_name}, got {actual_type}"
                    )

        return errors

    def get_with_default(
        self,
        config: Dict[str, Any],
        key: str,
        default: Any = None,
        separator: str = ".",
    ) -> Any:
        """Get configuration value with default fallback.

        Supports nested keys using dot notation.

        Args:
            config: Configuration dictionary
            key: Key to retrieve (supports dot notation for nested keys)
            default: Default value if key not found
            separator: Key separator for nested access (default: ".")

        Returns:
            Configuration value or default

        Example:
            get_with_default(config, "database.host", "localhost")
        """
        keys = key.split(separator)
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def interpolate_env(
        self, config: Dict[str, Any], pattern: str = "${%s}"
    ) -> Dict[str, Any]:
        """Interpolate environment variables in configuration.

        Args:
            config: Configuration dictionary
            pattern: Pattern for environment variables (default: "${VAR}")

        Returns:
            Configuration with environment variables interpolated

        Example:
            Input: {"host": "${DB_HOST}", "port": "${DB_PORT}"}
            Output: {"host": "localhost", "port": "5432"}
        """
        import re

        def _interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                # Find all environment variable references
                env_pattern = pattern.replace("%s", r"([A-Z_][A-Z0-9_]*)")
                matches = re.findall(env_pattern, value)

                result = value
                for var_name in matches:
                    env_value = os.environ.get(var_name, "")
                    placeholder = pattern % var_name
                    result = result.replace(placeholder, env_value)

                return result
            if isinstance(value, dict):
                return {k: _interpolate_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_interpolate_value(item) for item in value]
            return value

        return _interpolate_value(config)


# Convenience functions
_default_manager = ConfigurationManager()


def load_config(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration file with auto-detection.

    Args:
        file_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    return _default_manager.load_auto(file_path)


def save_config(config: Dict[str, Any], file_path: Union[str, Path]):
    """Save configuration file with auto-detection.

    Args:
        config: Configuration dictionary
        file_path: Path to save configuration
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix in [".json"]:
        _default_manager.save_json(config, file_path)
    elif suffix in [".yaml", ".yml"]:
        _default_manager.save_yaml(config, file_path)
    elif suffix in [".toml"]:
        _default_manager.save_toml(config, file_path)
    else:
        raise ValueError(f"Unsupported configuration format: {suffix}")
