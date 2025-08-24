"""
Base class for configuration-heavy services to reduce duplication.

UPDATED: Migrated to use shared ConfigLoader pattern (TSK-0141)
"""

from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ...core.config import Config
from ...core.mixins import LoggerMixin
from ...core.shared.config_loader import ConfigLoader


class ConfigServiceBase(LoggerMixin, ABC):
    """
    Base class for services that heavily use configuration.

    Provides common patterns:
    - Configuration loading and validation
    - Environment variable handling
    - Configuration file discovery
    - Default value management
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[Union[Dict[str, Any], Config]] = None,
        config_section: Optional[str] = None,
        config_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize config service.

        Args:
            service_name: Name of the service
            config: Configuration instance or dictionary
            config_section: Optional section name in config
            config_dir: Optional directory to search for config files
        """
        self.service_name = service_name
        self._logger_name = f"service.{service_name}"
        self.config_section = config_section or service_name.lower()
        self._config_loader = ConfigLoader()

        # Initialize configuration
        if isinstance(config, Config):
            self._config = config
        elif isinstance(config, dict):
            self._config = Config(config)
        else:
            # Use ConfigLoader to load service configuration
            self._config = self._config_loader.load_service_config(
                service_name=service_name, config_dir=config_dir
            )

        # Cache for processed config values
        self._config_cache: Dict[str, Any] = {}

    def get_config_value(
        self,
        key: str,
        default: Any = None,
        required: bool = False,
        config_type: Optional[type] = None,
    ) -> Any:
        """
        Get configuration value with validation and caching.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if not found
            required: Whether the value is required
            config_type: Expected type for validation

        Returns:
            Configuration value

        Raises:
            ValueError: If required value is missing or type validation fails
        """
        # Build full key with section prefix
        if self.config_section and not key.startswith(f"{self.config_section}."):
            full_key = f"{self.config_section}.{key}"
        else:
            full_key = key

        # Check cache first
        if full_key in self._config_cache:
            return self._config_cache[full_key]

        # Get value from config
        value = self._config.get(full_key, default)

        # Handle required values
        if required and value is None:
            raise ValueError(f"Required configuration value missing: {full_key}")

        # Type validation
        if config_type is not None and value is not None:
            if not isinstance(value, config_type):
                try:
                    # Try to convert
                    if config_type == bool and isinstance(value, str):
                        value = value.lower() in ("true", "1", "yes", "on")
                    elif config_type == Path:
                        value = Path(value).expanduser()
                    else:
                        value = config_type(value)
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Invalid type for {full_key}: expected {config_type.__name__}, got {type(value).__name__}"
                    ) from e

        # Cache the processed value
        self._config_cache[full_key] = value
        return value

    def get_config_section(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name (defaults to service section)

        Returns:
            Configuration section as dictionary
        """
        section_name = section or self.config_section
        return self._config.get(section_name, {})

    def validate_config(self, schema: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against a schema.

        Args:
            schema: Validation schema

        Returns:
            List of validation errors
        """
        errors = []

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            try:
                self.get_config_value(field, required=True)
            except ValueError as e:
                errors.append(str(e))

        # Check field types
        field_types = schema.get("types", {})
        for field, expected_type in field_types.items():
            try:
                value = self.get_config_value(field)
                if value is not None and not isinstance(value, expected_type):
                    errors.append(
                        f"Invalid type for {field}: expected {expected_type.__name__}"
                    )
            except Exception as e:
                errors.append(f"Error validating {field}: {e}")

        # Check field constraints
        constraints = schema.get("constraints", {})
        for field, constraint in constraints.items():
            try:
                value = self.get_config_value(field)
                if value is not None:
                    if "min" in constraint and value < constraint["min"]:
                        errors.append(f"{field} must be >= {constraint['min']}")
                    if "max" in constraint and value > constraint["max"]:
                        errors.append(f"{field} must be <= {constraint['max']}")
                    if "choices" in constraint and value not in constraint["choices"]:
                        errors.append(f"{field} must be one of {constraint['choices']}")
            except Exception as e:
                errors.append(f"Error validating constraint for {field}: {e}")

        return errors

    def load_config_file(self, config_path: Union[str, Path]) -> bool:
        """
        Load additional configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if loaded successfully
        """
        try:
            self._config.load_file(config_path)
            # Clear cache since config changed
            self._config_cache.clear()
            self.logger.info(f"Loaded configuration from {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {e}")
            return False

    def find_config_file(
        self, filename: str, search_paths: Optional[List[Union[str, Path]]] = None
    ) -> Optional[Path]:
        """
        Find configuration file in standard locations.

        Args:
            filename: Configuration filename
            search_paths: Additional paths to search

        Returns:
            Path to found configuration file or None
        """
        default_paths = [
            Path.cwd() / ".claude-mpm",
            Path.home() / ".claude-mpm",
            Path.cwd(),
        ]

        if search_paths:
            search_paths = [Path(p) for p in search_paths] + default_paths
        else:
            search_paths = default_paths

        for search_path in search_paths:
            config_file = search_path / filename
            if config_file.exists() and config_file.is_file():
                self.logger.debug(f"Found config file: {config_file}")
                return config_file

        return None

    def get_env_config(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration from environment variables.

        Args:
            prefix: Environment variable prefix (defaults to service name)

        Returns:
            Configuration dictionary from environment
        """
        env_prefix = prefix or f"CLAUDE_MPM_{self.service_name.upper()}_"

        # Use shared ConfigLoader for consistent environment variable handling
        return self._config_loader._load_env_config(env_prefix)

    def merge_env_config(self, prefix: Optional[str] = None) -> None:
        """
        Merge environment configuration into main config.

        Args:
            prefix: Environment variable prefix
        """
        env_config = self.get_env_config(prefix)
        if env_config:
            for key, value in env_config.items():
                full_key = f"{self.config_section}.{key}"
                self._config.set(full_key, value)

            # Clear cache since config changed
            self._config_cache.clear()
            self.logger.debug(f"Merged {len(env_config)} environment variables")

    def reload_config(self, config_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Reload configuration using ConfigLoader pattern.

        Args:
            config_dir: Optional directory to search for config files
        """
        self._config = self._config_loader.load_service_config(
            service_name=self.service_name, config_dir=config_dir
        )

        # Clear cache
        self._config_cache.clear()

        self.logger.info(f"Configuration reloaded for service: {self.service_name}")

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get summary of current configuration.

        Returns:
            Configuration summary
        """
        section_config = self.get_config_section()

        return {
            "service": self.service_name,
            "section": self.config_section,
            "keys": list(section_config.keys()),
            "key_count": len(section_config),
            "cached_values": len(self._config_cache),
        }
