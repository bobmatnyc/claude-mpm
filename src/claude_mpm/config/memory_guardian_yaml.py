from pathlib import Path

"""YAML configuration support for Memory Guardian.

This module provides YAML configuration loading and validation for
the Memory Guardian service, allowing users to configure memory monitoring
through configuration files.
"""

import os
from typing import Any, Dict, Optional

import yaml

from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    MonitoringConfig,
    RestartPolicy,
)
from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# Default configuration file locations
DEFAULT_CONFIG_LOCATIONS = [
    Path.home() / ".claude-mpm" / "config" / "memory_guardian.yaml",
    Path.home() / ".claude-mpm" / "memory_guardian.yaml",
    Path.cwd() / ".claude-mpm" / "memory_guardian.yaml",
    Path.cwd() / "memory_guardian.yaml",
]


def find_config_file() -> Optional[Path]:
    """Find memory guardian configuration file in standard locations.

    Returns:
        Path to configuration file or None if not found
    """
    for path in DEFAULT_CONFIG_LOCATIONS:
        if path.exists():
            logger.debug(f"Found memory guardian config at: {path}")
            return path

    return None


def load_yaml_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """Load YAML configuration from file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary of configuration data or None if loading failed
    """
    try:
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return None

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            logger.warning(f"Empty configuration file: {config_path}")
            return {}

        logger.info(f"Loaded configuration from: {config_path}")
        return config_data

    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load configuration file: {e}")
        return None


def create_config_from_yaml(yaml_data: Dict[str, Any]) -> MemoryGuardianConfig:
    """Create MemoryGuardianConfig from YAML data.

    Args:
        yaml_data: Dictionary of configuration data from YAML

    Returns:
        MemoryGuardianConfig instance
    """
    config = MemoryGuardianConfig()

    # General settings
    config.enabled = yaml_data.get("enabled", config.enabled)
    config.auto_start = yaml_data.get("auto_start", config.auto_start)
    config.persist_state = yaml_data.get("persist_state", config.persist_state)
    config.state_file = yaml_data.get("state_file", config.state_file)

    # Memory thresholds
    if "thresholds" in yaml_data:
        thresholds = yaml_data["thresholds"]
        config.thresholds = MemoryThresholds(
            warning=thresholds.get("warning", config.thresholds.warning),
            critical=thresholds.get("critical", config.thresholds.critical),
            emergency=thresholds.get("emergency", config.thresholds.emergency),
        )

    # Monitoring configuration
    if "monitoring" in yaml_data:
        monitoring = yaml_data["monitoring"]
        config.monitoring = MonitoringConfig(
            check_interval=monitoring.get(
                "check_interval", config.monitoring.check_interval
            ),
            check_interval_warning=monitoring.get(
                "check_interval_warning", config.monitoring.check_interval_warning
            ),
            check_interval_critical=monitoring.get(
                "check_interval_critical", config.monitoring.check_interval_critical
            ),
            log_memory_stats=monitoring.get(
                "log_memory_stats", config.monitoring.log_memory_stats
            ),
            log_interval=monitoring.get("log_interval", config.monitoring.log_interval),
        )

    # Restart policy
    if "restart_policy" in yaml_data:
        policy = yaml_data["restart_policy"]
        config.restart_policy = RestartPolicy(
            max_attempts=policy.get("max_attempts", config.restart_policy.max_attempts),
            attempt_window=policy.get(
                "attempt_window", config.restart_policy.attempt_window
            ),
            cooldown_base=policy.get(
                "cooldown_base", config.restart_policy.cooldown_base
            ),
            cooldown_multiplier=policy.get(
                "cooldown_multiplier", config.restart_policy.cooldown_multiplier
            ),
            cooldown_max=policy.get("cooldown_max", config.restart_policy.cooldown_max),
            graceful_timeout=policy.get(
                "graceful_timeout", config.restart_policy.graceful_timeout
            ),
            force_kill_timeout=policy.get(
                "force_kill_timeout", config.restart_policy.force_kill_timeout
            ),
        )

    # Process configuration
    if "process" in yaml_data:
        process = yaml_data["process"]
        config.process_command = process.get("command", config.process_command)
        config.process_args = process.get("args", config.process_args)
        config.process_env = process.get("env", config.process_env)
        config.working_directory = process.get(
            "working_directory", config.working_directory
        )

    return config


def load_config(config_path: Optional[Path] = None) -> Optional[MemoryGuardianConfig]:
    """Load memory guardian configuration from YAML file.

    Args:
        config_path: Optional path to configuration file.
                    If not provided, searches standard locations.

    Returns:
        MemoryGuardianConfig instance or None if loading failed
    """
    # Find configuration file if not specified
    if config_path is None:
        config_path = find_config_file()
        if config_path is None:
            logger.debug("No memory guardian configuration file found")
            return None

    # Load YAML data
    yaml_data = load_yaml_config(config_path)
    if yaml_data is None:
        return None

    # Create configuration
    try:
        config = create_config_from_yaml(yaml_data)

        # Validate configuration
        issues = config.validate()
        if issues:
            for issue in issues:
                logger.warning(f"Configuration validation issue: {issue}")

        return config

    except Exception as e:
        logger.error(f"Failed to create configuration from YAML: {e}")
        return None


def save_config(
    config: MemoryGuardianConfig, config_path: Optional[Path] = None
) -> bool:
    """Save memory guardian configuration to YAML file.

    Args:
        config: MemoryGuardianConfig instance to save
        config_path: Optional path to save configuration.
                    If not provided, uses default location.

    Returns:
        True if save successful, False otherwise
    """
    try:
        # Determine save path
        if config_path is None:
            config_path = (
                Path.home() / ".claude-mpm" / "config" / "memory_guardian.yaml"
            )

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert configuration to dictionary
        config_dict = config.to_dict()

        # Write to file
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved configuration to: {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return False


def create_default_config_file(config_path: Optional[Path] = None) -> bool:
    """Create a default memory guardian configuration file.

    Args:
        config_path: Optional path for configuration file.
                    If not provided, uses default location.

    Returns:
        True if file created successfully, False otherwise
    """
    try:
        # Determine save path
        if config_path is None:
            config_path = (
                Path.home() / ".claude-mpm" / "config" / "memory_guardian.yaml"
            )

        # Check if file already exists
        if config_path.exists():
            logger.warning(f"Configuration file already exists: {config_path}")
            return False

        # Create default configuration
        config = MemoryGuardianConfig()

        # Add helpful comments to YAML
        yaml_content = """# Memory Guardian Configuration
# This file configures memory monitoring and automatic restart for Claude Code

# Enable/disable memory monitoring
enabled: true

# Automatically start monitoring when service initializes
auto_start: true

# Preserve state across restarts
persist_state: true

# Path to state file for persistence
state_file: ~/.claude-mpm/state/memory_guardian.json

# Memory thresholds in MB
thresholds:
  # Warning threshold - logs warnings
  warning: 14400  # 14GB

  # Critical threshold - triggers restart
  critical: 18000  # 18GB

  # Emergency threshold - immediate restart
  emergency: 21600  # 21GB

# Monitoring configuration
monitoring:
  # Default check interval in seconds
  check_interval: 30

  # Check interval when in warning state
  check_interval_warning: 15

  # Check interval when in critical state
  check_interval_critical: 5

  # Enable periodic memory statistics logging
  log_memory_stats: true

  # Statistics logging interval in seconds
  log_interval: 60

# Restart policy configuration
restart_policy:
  # Maximum restart attempts (0 = unlimited)
  max_attempts: 3

  # Time window for counting attempts (seconds)
  attempt_window: 3600  # 1 hour

  # Base cooldown between restarts (seconds)
  cooldown_base: 10

  # Cooldown multiplier for consecutive failures
  cooldown_multiplier: 2.0

  # Maximum cooldown period (seconds)
  cooldown_max: 300  # 5 minutes

  # Timeout for graceful shutdown (seconds)
  graceful_timeout: 30

  # Timeout for force kill if graceful fails (seconds)
  force_kill_timeout: 10

# Process configuration (usually set by runner)
process:
  # Command to execute (set by runner)
  command: ["claude"]

  # Additional arguments
  args: []

  # Environment variables
  env: {}

  # Working directory (defaults to current)
  working_directory: null
"""

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write configuration file
        with open(config_path, "w") as f:
            f.write(yaml_content)

        logger.info(f"Created default configuration file: {config_path}")
        print(f"✓ Created memory guardian configuration at: {config_path}")
        print("  Edit this file to customize memory thresholds and policies")

        return True

    except Exception as e:
        logger.error(f"Failed to create default configuration file: {e}")
        return False
