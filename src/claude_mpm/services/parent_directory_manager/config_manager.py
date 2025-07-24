#!/usr/bin/env python3
"""
Configuration Manager - Handles managed directories configuration
================================================================================

This module manages the loading, saving, and tracking of managed directory
configurations for the parent directory manager.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

from .operations import ParentDirectoryContext


@dataclass
class ParentDirectoryConfig:
    """Configuration for parent directory management."""
    target_directory: Path
    context: ParentDirectoryContext
    template_id: str
    template_variables: Dict[str, Any] = field(default_factory=dict)
    backup_enabled: bool = True
    version_control: bool = True
    conflict_resolution: str = "backup_and_replace"
    deployment_metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manages configuration for parent directories."""

    def __init__(
        self,
        configs_dir: Path,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Configuration Manager.

        Args:
            configs_dir: Directory for storing configurations
            logger: Logger instance to use
        """
        self.configs_dir = configs_dir
        self.logger = logger or logging.getLogger(__name__)
        self.managed_directories_file = self.configs_dir / "managed_directories.json"
        self.managed_directories: Dict[str, ParentDirectoryConfig] = {}

    async def load_managed_directories(self) -> None:
        """Load existing managed directories configuration."""
        try:
            if self.managed_directories_file.exists():
                with open(self.managed_directories_file, "r") as f:
                    data = json.load(f)

                # Convert loaded data to ParentDirectoryConfig objects
                for key, config_data in data.items():
                    config = ParentDirectoryConfig(
                        target_directory=Path(config_data["target_directory"]),
                        context=ParentDirectoryContext(config_data["context"]),
                        template_id=config_data["template_id"],
                        template_variables=config_data.get("template_variables", {}),
                        backup_enabled=config_data.get("backup_enabled", True),
                        version_control=config_data.get("version_control", True),
                        conflict_resolution=config_data.get(
                            "conflict_resolution", "backup_and_replace"
                        ),
                        deployment_metadata=config_data.get("deployment_metadata", {}),
                    )
                    self.managed_directories[key] = config

                self.logger.info(f"Loading managed directories...")

        except Exception as e:
            self.logger.error(f"Failed to load managed directories: {e}")

    async def save_managed_directories(self) -> None:
        """Save managed directories configuration."""
        try:
            # Convert ParentDirectoryConfig objects to serializable format
            data = {}
            for key, config in self.managed_directories.items():
                data[key] = {
                    "target_directory": str(config.target_directory),
                    "context": config.context.value,
                    "template_id": config.template_id,
                    "template_variables": config.template_variables,
                    "backup_enabled": config.backup_enabled,
                    "version_control": config.version_control,
                    "conflict_resolution": config.conflict_resolution,
                    "deployment_metadata": config.deployment_metadata,
                }

            with open(self.managed_directories_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug("Managed directories configuration saved")

        except Exception as e:
            self.logger.error(f"Failed to save managed directories: {e}")

    def register_directory(
        self,
        directory_key: str,
        config: ParentDirectoryConfig
    ) -> None:
        """
        Register a directory configuration.

        Args:
            directory_key: Unique key for the directory
            config: Configuration for the directory
        """
        self.managed_directories[directory_key] = config
    
    async def register_parent_directory(
        self,
        target_directory: Path,
        context: ParentDirectoryContext,
        template_id: str,
        template_variables: Dict[str, Any] = None,
        **kwargs
    ) -> bool:
        """
        Register a parent directory for management with validation.

        Args:
            target_directory: Directory to manage
            context: Context type for the directory
            template_id: Template to use for management
            template_variables: Variables for template rendering
            **kwargs: Additional configuration options

        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate inputs
            if not target_directory.exists():
                raise ValueError(f"Target directory does not exist: {target_directory}")

            if not target_directory.is_dir():
                raise ValueError(f"Target path is not a directory: {target_directory}")

            # Create configuration
            config = ParentDirectoryConfig(
                target_directory=target_directory,
                context=context,
                template_id=template_id,
                template_variables=template_variables or {},
                backup_enabled=kwargs.get("backup_enabled", True),
                version_control=kwargs.get("version_control", True),
                conflict_resolution=kwargs.get("conflict_resolution", "backup_and_replace"),
                deployment_metadata=kwargs.get("deployment_metadata", {}),
            )

            # Register the directory
            directory_key = str(target_directory)
            self.register_directory(directory_key, config)

            # Save configuration
            await self.save_managed_directories()

            self.logger.info(
                f"Registered parent directory: {target_directory} with template {template_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to register parent directory {target_directory}: {e}")
            return False

    def get_directory_config(
        self,
        directory_key: str
    ) -> Optional[ParentDirectoryConfig]:
        """
        Get configuration for a directory.

        Args:
            directory_key: Unique key for the directory

        Returns:
            Directory configuration or None if not found
        """
        return self.managed_directories.get(directory_key)

    def is_directory_managed(self, directory_key: str) -> bool:
        """
        Check if a directory is managed.

        Args:
            directory_key: Unique key for the directory

        Returns:
            True if directory is managed, False otherwise
        """
        return directory_key in self.managed_directories

    def get_all_managed_directories(self) -> Dict[str, ParentDirectoryConfig]:
        """
        Get all managed directory configurations.

        Returns:
            Dictionary of all managed directories
        """
        return self.managed_directories.copy()