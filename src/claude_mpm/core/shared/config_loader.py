"""
Shared configuration loading utilities to reduce duplication.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config import Config
from ..logger import get_logger


@dataclass
class ConfigPattern:
    """Configuration loading pattern definition."""

    # File patterns to search for
    filenames: List[str]

    # Search paths (relative to working directory)
    search_paths: List[str]

    # Environment variable prefix
    env_prefix: Optional[str] = None

    # Default values
    defaults: Optional[Dict[str, Any]] = None

    # Required configuration keys
    required_keys: Optional[List[str]] = None

    # Configuration section name
    section: Optional[str] = None


class ConfigLoader:
    """
    Centralized configuration loading utility.

    Reduces duplication by providing standard patterns for:
    - Configuration file discovery
    - Environment variable loading
    - Default value management
    - Configuration validation
    """

    # Standard configuration patterns
    AGENT_CONFIG = ConfigPattern(
        filenames=[".agent.yaml", ".agent.yml", "agent.yaml", "agent.yml"],
        search_paths=[".", ".claude-mpm", "agents"],
        env_prefix="CLAUDE_MPM_AGENT_",
        defaults={"timeout": 30, "max_retries": 3, "log_level": "INFO"},
        required_keys=["name", "model"],
    )

    MEMORY_CONFIG = ConfigPattern(
        filenames=[".memory.yaml", ".memory.yml", "memory.yaml", "memory.yml"],
        search_paths=[".", ".claude-mpm", "memories"],
        env_prefix="CLAUDE_MPM_MEMORY_",
        defaults={"max_entries": 1000, "cleanup_interval": 3600, "compression": True},
    )

    SERVICE_CONFIG = ConfigPattern(
        filenames=[".service.yaml", ".service.yml", "service.yaml", "service.yml"],
        search_paths=[".", ".claude-mpm", "config"],
        env_prefix="CLAUDE_MPM_SERVICE_",
        defaults={"enabled": True, "auto_start": False, "health_check_interval": 60},
    )

    def __init__(self, working_dir: Optional[Union[str, Path]] = None):
        """
        Initialize config loader.

        Args:
            working_dir: Working directory for relative paths
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.logger = get_logger("config_loader")
        self._cache: Dict[str, Config] = {}

    def load_config(
        self,
        pattern: ConfigPattern,
        cache_key: Optional[str] = None,
        force_reload: bool = False,
    ) -> Config:
        """
        Load configuration using a pattern.

        Args:
            pattern: Configuration pattern to use
            cache_key: Optional cache key (defaults to pattern hash)
            force_reload: Force reload even if cached

        Returns:
            Loaded configuration
        """
        # Generate cache key if not provided
        if cache_key is None:
            cache_key = self._generate_cache_key(pattern)

        # Check cache
        if not force_reload and cache_key in self._cache:
            self.logger.debug(f"Using cached config: {cache_key}")
            return self._cache[cache_key]

        # Start with defaults
        config_data = pattern.defaults.copy() if pattern.defaults else {}

        # Load from files
        config_file = self._find_config_file(pattern)
        if config_file:
            file_config = self._load_config_file(config_file)
            if pattern.section:
                file_config = file_config.get(pattern.section, {})
            config_data.update(file_config)
            self.logger.info(f"Loaded config from: {config_file}")

        # Load from environment
        if pattern.env_prefix:
            env_config = self._load_env_config(pattern.env_prefix)
            config_data.update(env_config)
            if env_config:
                self.logger.debug(
                    f"Loaded {len(env_config)} env vars with prefix {pattern.env_prefix}"
                )

        # Create config instance
        config = Config(config_data)

        # Validate required keys
        if pattern.required_keys:
            self._validate_required_keys(config, pattern.required_keys)

        # Cache the result
        self._cache[cache_key] = config

        return config

    def load_agent_config(self, agent_dir: Optional[Union[str, Path]] = None) -> Config:
        """Load agent configuration."""
        pattern = self.AGENT_CONFIG
        if agent_dir:
            # Override search paths for specific agent directory
            pattern = ConfigPattern(
                filenames=pattern.filenames,
                search_paths=[str(agent_dir)],
                env_prefix=pattern.env_prefix,
                defaults=pattern.defaults,
                required_keys=pattern.required_keys,
            )

        return self.load_config(pattern, cache_key=f"agent_{agent_dir}")

    def load_main_config(self) -> Config:
        """Load main application configuration."""
        pattern = ConfigPattern(
            filenames=[
                "claude-mpm.yaml",
                "claude-mpm.yml",
                ".claude-mpm.yaml",
                ".claude-mpm.yml",
                "config.yaml",
                "config.yml",
            ],
            search_paths=["~/.config/claude-mpm", ".", "./config", "/etc/claude-mpm"],
            env_prefix="CLAUDE_MPM_",
            defaults={},
        )
        return self.load_config(pattern, cache_key="main_config")

    def load_memory_config(
        self, memory_dir: Optional[Union[str, Path]] = None
    ) -> Config:
        """Load memory configuration."""
        pattern = self.MEMORY_CONFIG
        if memory_dir:
            pattern = ConfigPattern(
                filenames=pattern.filenames,
                search_paths=[str(memory_dir)],
                env_prefix=pattern.env_prefix,
                defaults=pattern.defaults,
            )

        return self.load_config(pattern, cache_key=f"memory_{memory_dir}")

    def load_service_config(
        self, service_name: str, config_dir: Optional[Union[str, Path]] = None
    ) -> Config:
        """Load service configuration."""
        pattern = self.SERVICE_CONFIG

        # Add service-specific filenames
        service_filenames = [
            f".{service_name}.yaml",
            f".{service_name}.yml",
            f"{service_name}.yaml",
            f"{service_name}.yml",
        ]

        pattern = ConfigPattern(
            filenames=service_filenames + pattern.filenames,
            search_paths=[str(config_dir)] if config_dir else pattern.search_paths,
            env_prefix=f"CLAUDE_MPM_{service_name.upper()}_",
            defaults=pattern.defaults,
            section=service_name,
        )

        return self.load_config(pattern, cache_key=f"service_{service_name}")

    def _find_config_file(self, pattern: ConfigPattern) -> Optional[Path]:
        """Find configuration file using pattern."""
        for search_path in pattern.search_paths:
            search_dir = self.working_dir / search_path
            if not search_dir.exists():
                continue

            for filename in pattern.filenames:
                config_file = search_dir / filename
                if config_file.exists() and config_file.is_file():
                    return config_file

        return None

    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            import yaml

            with open(config_file) as f:
                if config_file.suffix.lower() in (".yaml", ".yml"):
                    return yaml.safe_load(f) or {}
                # Try JSON as fallback
                import json

                f.seek(0)
                return json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to load config file {config_file}: {e}")
            return {}

    def _load_env_config(self, prefix: str) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert env var name to config key
                config_key = key[len(prefix) :].lower().replace("_", ".")

                # Try to parse value
                parsed_value = self._parse_env_value(value)
                config[config_key] = parsed_value

        return config

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value."""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Try JSON
        try:
            import json

            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass

        # Return as string
        return value

    def _validate_required_keys(self, config: Config, required_keys: List[str]) -> None:
        """Validate that required keys are present."""
        missing_keys = []

        for key in required_keys:
            if config.get(key) is None:
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")

    def _generate_cache_key(self, pattern: ConfigPattern) -> str:
        """Generate cache key for pattern."""
        import hashlib

        # Create a string representation of the pattern
        pattern_str = f"{pattern.filenames}_{pattern.search_paths}_{pattern.env_prefix}"

        # Generate hash
        return hashlib.md5(pattern_str.encode()).hexdigest()[:8]

    def clear_cache(self, cache_key: Optional[str] = None) -> None:
        """Clear configuration cache."""
        if cache_key:
            self._cache.pop(cache_key, None)
            self.logger.debug(f"Cleared cache for: {cache_key}")
        else:
            self._cache.clear()
            self.logger.debug("Cleared all config cache")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            "cached_configs": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "working_dir": str(self.working_dir),
        }
