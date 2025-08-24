from pathlib import Path

"""
Configuration alias management for Claude PM Framework.

Manages friendly directory aliases for configuration paths, allowing users to
reference configurations using memorable names instead of full paths.

Example:
    claude-pm --config personal  # Resolves to ~/.claude-mpm/configs/personal/
    claude-pm --config work      # Resolves to ~/work/claude-configs/

Aliases are stored in ~/.claude-mpm/config_aliases.json
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from ..utils.config_manager import ConfigurationManager
from .unified_paths import get_path_manager

logger = logging.getLogger(__name__)


class ConfigAliasError(Exception):
    """Base exception for configuration alias errors."""


class AliasNotFoundError(ConfigAliasError):
    """Raised when attempting to resolve a non-existent alias."""


class DuplicateAliasError(ConfigAliasError):
    """Raised when attempting to create an alias that already exists."""


class InvalidDirectoryError(ConfigAliasError):
    """Raised when a directory path is invalid or cannot be created."""


class ConfigAliasManager:
    """
    Manages configuration directory aliases for the Claude PM Framework.

    Provides methods to create, delete, list, and resolve aliases that map
    friendly names to actual directory paths.
    """

    def __init__(self, aliases_file: Optional[Path] = None):
        """
        Initialize the configuration alias manager.

        Args:
            aliases_file: Path to the aliases JSON file. Defaults to
                         ~/.claude-pm/config_aliases.json
        """
        if aliases_file is None:
            self.aliases_file = (
                get_path_manager().get_user_config_dir() / "config_aliases.json"
            )
        else:
            self.aliases_file = Path(aliases_file)

        self.config_mgr = ConfigurationManager(cache_enabled=True)
        self._ensure_aliases_file()
        self._aliases: Dict[str, str] = self._load_aliases()

    def _ensure_aliases_file(self) -> None:
        """Ensure the aliases file and its parent directory exist."""
        self.aliases_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.aliases_file.exists():
            self._save_aliases({})
            logger.info(f"Created new aliases file at {self.aliases_file}")

    def _load_aliases(self) -> Dict[str, str]:
        """Load aliases from the JSON file."""
        try:
            return self.config_mgr.load_json(self.aliases_file)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load aliases: {e}")
            return {}

    def _save_aliases(self, aliases: Dict[str, str]) -> None:
        """Save aliases to the JSON file."""
        try:
            self.config_mgr.save_json(aliases, self.aliases_file, sort_keys=True)
        except Exception as e:
            logger.error(f"Failed to save aliases: {e}")
            raise ConfigAliasError(f"Failed to save aliases: {e}")

    def create_alias(self, alias_name: str, directory_path: str) -> None:
        """
        Create a new configuration alias.

        Args:
            alias_name: The friendly name for the alias
            directory_path: The directory path this alias should resolve to

        Raises:
            DuplicateAliasError: If the alias already exists
            InvalidDirectoryError: If the directory path is invalid
        """
        # Validate alias name
        if not alias_name or not alias_name.strip():
            raise ValueError("Alias name cannot be empty")

        alias_name = alias_name.strip()

        # Check for duplicate
        if alias_name in self._aliases:
            raise DuplicateAliasError(
                f"Alias '{alias_name}' already exists, pointing to: {self._aliases[alias_name]}"
            )

        # Validate and normalize the directory path
        validated_path = self.validate_directory(directory_path)

        # Add the alias
        self._aliases[alias_name] = str(validated_path)
        self._save_aliases(self._aliases)

        logger.info(f"Created alias '{alias_name}' -> {validated_path}")

    def resolve_alias(self, alias_name: str) -> Path:
        """
        Resolve an alias to its directory path.

        Args:
            alias_name: The alias to resolve

        Returns:
            The Path object for the resolved directory

        Raises:
            AliasNotFoundError: If the alias does not exist
        """
        if alias_name not in self._aliases:
            raise AliasNotFoundError(f"Alias '{alias_name}' not found")

        path = Path(self._aliases[alias_name])

        # Ensure the directory still exists or can be created
        try:
            path = self.validate_directory(str(path))
        except InvalidDirectoryError:
            logger.warning(
                f"Directory for alias '{alias_name}' no longer valid: {path}"
            )
            # Still return the path, let the caller handle the missing directory

        return path

    def list_aliases(self) -> List[Tuple[str, str]]:
        """
        List all configured aliases.

        Returns:
            A list of tuples containing (alias_name, directory_path)
        """
        return sorted(self._aliases.items())

    def delete_alias(self, alias_name: str) -> None:
        """
        Delete a configuration alias.

        Args:
            alias_name: The alias to delete

        Raises:
            AliasNotFoundError: If the alias does not exist
        """
        if alias_name not in self._aliases:
            raise AliasNotFoundError(f"Alias '{alias_name}' not found")

        directory_path = self._aliases[alias_name]
        del self._aliases[alias_name]
        self._save_aliases(self._aliases)

        logger.info(f"Deleted alias '{alias_name}' (was pointing to: {directory_path})")

    def validate_directory(self, path: str) -> Path:
        """
        Validate that a directory exists or can be created.

        Args:
            path: The directory path to validate

        Returns:
            The normalized Path object

        Raises:
            InvalidDirectoryError: If the path is invalid or cannot be created
        """
        try:
            # Expand user home directory and environment variables
            directory_path = Path(path).expanduser().resolve()

            # Check if it's a file
            if directory_path.exists() and directory_path.is_file():
                raise InvalidDirectoryError(
                    f"Path exists but is a file, not a directory: {directory_path}"
                )

            # Try to create the directory if it doesn't exist
            if not directory_path.exists():
                try:
                    directory_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created directory: {directory_path}")
                except Exception as e:
                    raise InvalidDirectoryError(
                        f"Cannot create directory '{directory_path}': {e}"
                    )

            # Verify we can write to the directory
            test_file = directory_path / ".claude_pm_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                raise InvalidDirectoryError(
                    f"Directory '{directory_path}' is not writable: {e}"
                )

            return directory_path

        except InvalidDirectoryError:
            raise
        except Exception as e:
            raise InvalidDirectoryError(f"Invalid directory path '{path}': {e}")

    def get_alias(self, alias_name: str) -> Optional[str]:
        """
        Get the directory path for an alias without validation.

        Args:
            alias_name: The alias to look up

        Returns:
            The directory path string if the alias exists, None otherwise
        """
        return self._aliases.get(alias_name)

    def update_alias(self, alias_name: str, new_directory_path: str) -> None:
        """
        Update an existing alias to point to a new directory.

        Args:
            alias_name: The alias to update
            new_directory_path: The new directory path

        Raises:
            AliasNotFoundError: If the alias does not exist
            InvalidDirectoryError: If the new directory path is invalid
        """
        if alias_name not in self._aliases:
            raise AliasNotFoundError(f"Alias '{alias_name}' not found")

        # Validate the new directory path
        validated_path = self.validate_directory(new_directory_path)

        old_path = self._aliases[alias_name]
        self._aliases[alias_name] = str(validated_path)
        self._save_aliases(self._aliases)

        logger.info(f"Updated alias '{alias_name}': {old_path} -> {validated_path}")

    def alias_exists(self, alias_name: str) -> bool:
        """
        Check if an alias exists.

        Args:
            alias_name: The alias to check

        Returns:
            True if the alias exists, False otherwise
        """
        return alias_name in self._aliases

    def get_all_aliases(self) -> Dict[str, str]:
        """
        Get a copy of all aliases.

        Returns:
            A dictionary mapping alias names to directory paths
        """
        return self._aliases.copy()

    def reload_aliases(self) -> None:
        """Reload aliases from the file, discarding any in-memory changes."""
        self._aliases = self._load_aliases()
        logger.debug("Reloaded aliases from file")
