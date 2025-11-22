"""Skills Configuration Service - Manage skill collections and settings.

WHY: Skills can come from multiple GitHub repositories (collections). This service
manages collection configurations, priorities, and enables/disables collections.

DESIGN DECISIONS:
- Store config in ~/.claude-mpm/config.json under "skills" key
- Support multiple collections with priority ordering
- Enable/disable collections without removing them
- Default collection for implicit deployments
- Backward compatible with single-collection usage

ARCHITECTURE:
1. Configuration Management: Load/save collection settings
2. Collection CRUD: Add, remove, update collections
3. Default Management: Set default collection for implicit deployments
4. Timestamp Tracking: Track last update time for each collection

Example config structure:
{
    "skills": {
        "collections": {
            "claude-mpm": {
                "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                "enabled": true,
                "priority": 1,
                "last_update": "2025-11-21T15:30:00Z"
            },
            "obra-superpowers": {
                "url": "https://github.com/obra/superpowers",
                "enabled": true,
                "priority": 2,
                "last_update": null
            }
        },
        "default_collection": "claude-mpm"
    }
}
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.mixins import LoggerMixin
from claude_mpm.utils.config_manager import ConfigurationManager


class SkillsConfig(LoggerMixin):
    """Manage skills configuration including collections.

    This service provides:
    - Collection CRUD operations (add, remove, update, list)
    - Enable/disable collections
    - Default collection management
    - Timestamp tracking for updates
    - Priority-based ordering

    Example:
        >>> config = SkillsConfig()
        >>> config.add_collection("custom", "https://github.com/user/skills", priority=3)
        >>> collections = config.get_collections()
        >>> config.set_default_collection("custom")
    """

    DEFAULT_REPO_URL = "https://github.com/bobmatnyc/claude-mpm-skills"

    def __init__(self):
        """Initialize Skills Configuration Service."""
        super().__init__()
        self.config_path = Path.home() / ".claude-mpm" / "config.json"
        self.config_manager = ConfigurationManager()
        self._ensure_config_exists()

    def _ensure_config_exists(self) -> None:
        """Create default config if not exists.

        Creates initial configuration with default claude-mpm collection.
        """
        if not self.config_path.exists():
            self.logger.info(
                f"Creating default skills configuration at {self.config_path}"
            )
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            default_config = {
                "version": "1.0",
                "skills": {
                    "collections": {
                        "claude-mpm": {
                            "url": self.DEFAULT_REPO_URL,
                            "enabled": True,
                            "priority": 1,
                            "last_update": None,
                        }
                    },
                    "default_collection": "claude-mpm",
                },
            }

            self._save_config(default_config)
        else:
            # Ensure skills section exists in existing config
            config = self._load_config()
            if "skills" not in config:
                self.logger.info("Adding skills section to existing config")
                config["skills"] = {
                    "collections": {
                        "claude-mpm": {
                            "url": self.DEFAULT_REPO_URL,
                            "enabled": True,
                            "priority": 1,
                            "last_update": None,
                        }
                    },
                    "default_collection": "claude-mpm",
                }
                self._save_config(config)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from disk.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config is invalid JSON
        """
        return self.config_manager.load_json(self.config_path)

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to disk.

        Args:
            config: Configuration dictionary to save
        """
        self.config_manager.save_json(config, self.config_path, indent=2)
        self.logger.debug(f"Configuration saved to {self.config_path}")

    def get_collections(self) -> Dict[str, Dict[str, Any]]:
        """Get all collections.

        Returns:
            Dict mapping collection names to their configurations

        Example:
            >>> config.get_collections()
            {
                "claude-mpm": {
                    "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                    "enabled": True,
                    "priority": 1,
                    "last_update": "2025-11-21T15:30:00Z"
                },
                "obra-superpowers": {
                    "url": "https://github.com/obra/superpowers",
                    "enabled": True,
                    "priority": 2,
                    "last_update": null
                }
            }
        """
        config = self._load_config()
        return config.get("skills", {}).get("collections", {})

    def get_enabled_collections(self) -> Dict[str, Dict[str, Any]]:
        """Get only enabled collections.

        Returns:
            Dict mapping enabled collection names to their configurations
        """
        all_collections = self.get_collections()
        return {
            name: details
            for name, details in all_collections.items()
            if details.get("enabled", True)
        }

    def get_collections_by_priority(
        self, enabled_only: bool = True
    ) -> List[tuple[str, Dict[str, Any]]]:
        """Get collections sorted by priority (lower number = higher priority).

        Args:
            enabled_only: Only return enabled collections

        Returns:
            List of (name, config) tuples sorted by priority

        Example:
            >>> collections = config.get_collections_by_priority()
            >>> [(name, details['priority']) for name, details in collections]
            [('claude-mpm', 1), ('obra-superpowers', 2), ('custom', 3)]
        """
        collections = (
            self.get_enabled_collections() if enabled_only else self.get_collections()
        )

        # Sort by priority (lower = higher priority)
        return sorted(collections.items(), key=lambda x: x[1].get("priority", 999))

    def get_collection(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific collection.

        Args:
            name: Collection name

        Returns:
            Collection configuration or None if not found

        Example:
            >>> config.get_collection("claude-mpm")
            {
                "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                "enabled": True,
                "priority": 1,
                "last_update": "2025-11-21T15:30:00Z"
            }
        """
        collections = self.get_collections()
        return collections.get(name)

    def add_collection(
        self,
        name: str,
        url: str,
        priority: int = 99,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Add new collection.

        Args:
            name: Collection name (must be unique)
            url: GitHub repository URL
            priority: Collection priority (lower = higher priority, default: 99)
            enabled: Whether collection is enabled (default: True)

        Returns:
            Dict with operation result

        Raises:
            ValueError: If collection already exists

        Example:
            >>> config.add_collection(
            ...     "obra-superpowers",
            ...     "https://github.com/obra/superpowers",
            ...     priority=2
            ... )
            {"status": "success", "message": "Collection 'obra-superpowers' added"}
        """
        config = self._load_config()
        collections = config.get("skills", {}).get("collections", {})

        if name in collections:
            raise ValueError(f"Collection '{name}' already exists")

        # Validate URL format
        if not url.startswith("https://github.com/"):
            raise ValueError(
                f"Invalid GitHub URL: {url}. Must start with 'https://github.com/'"
            )

        collections[name] = {
            "url": url,
            "enabled": enabled,
            "priority": priority,
            "last_update": None,
        }

        config.setdefault("skills", {})["collections"] = collections
        self._save_config(config)

        self.logger.info(
            f"Added collection '{name}' with priority {priority}, enabled={enabled}"
        )
        return {
            "status": "success",
            "message": f"Collection '{name}' added successfully",
            "collection": collections[name],
        }

    def remove_collection(self, name: str) -> Dict[str, Any]:
        """Remove collection.

        Args:
            name: Collection name to remove

        Returns:
            Dict with operation result

        Raises:
            ValueError: If collection doesn't exist or is default collection

        Example:
            >>> config.remove_collection("obra-superpowers")
            {"status": "success", "message": "Collection 'obra-superpowers' removed"}
        """
        config = self._load_config()
        collections = config.get("skills", {}).get("collections", {})

        if name not in collections:
            raise ValueError(f"Collection '{name}' not found")

        # Prevent removing default collection
        default_collection = config.get("skills", {}).get("default_collection")
        if name == default_collection:
            raise ValueError(
                f"Cannot remove default collection '{name}'. "
                f"Set a different default collection first."
            )

        del collections[name]
        config["skills"]["collections"] = collections
        self._save_config(config)

        self.logger.info(f"Removed collection '{name}'")
        return {
            "status": "success",
            "message": f"Collection '{name}' removed successfully",
        }

    def update_collection(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update collection properties.

        Args:
            name: Collection name
            updates: Dict of properties to update (url, enabled, priority)

        Returns:
            Dict with operation result

        Raises:
            ValueError: If collection doesn't exist

        Example:
            >>> config.update_collection("obra-superpowers", {"priority": 1})
            {"status": "success", "message": "Collection 'obra-superpowers' updated"}
        """
        config = self._load_config()
        collections = config.get("skills", {}).get("collections", {})

        if name not in collections:
            raise ValueError(f"Collection '{name}' not found")

        # Update allowed fields only
        allowed_fields = {"url", "enabled", "priority"}
        for key, value in updates.items():
            if key in allowed_fields:
                collections[name][key] = value
            else:
                self.logger.warning(f"Ignoring unknown field '{key}' in update")

        config["skills"]["collections"] = collections
        self._save_config(config)

        self.logger.info(f"Updated collection '{name}': {updates}")
        return {
            "status": "success",
            "message": f"Collection '{name}' updated successfully",
            "collection": collections[name],
        }

    def enable_collection(self, name: str) -> Dict[str, Any]:
        """Enable a disabled collection.

        Args:
            name: Collection name

        Returns:
            Dict with operation result

        Example:
            >>> config.enable_collection("obra-superpowers")
            {"status": "success", "message": "Collection 'obra-superpowers' enabled"}
        """
        return self.update_collection(name, {"enabled": True})

    def disable_collection(self, name: str) -> Dict[str, Any]:
        """Disable a collection without removing it.

        Args:
            name: Collection name

        Returns:
            Dict with operation result

        Raises:
            ValueError: If trying to disable default collection

        Example:
            >>> config.disable_collection("obra-superpowers")
            {"status": "success", "message": "Collection 'obra-superpowers' disabled"}
        """
        config = self._load_config()
        default_collection = config.get("skills", {}).get("default_collection")

        if name == default_collection:
            raise ValueError(
                f"Cannot disable default collection '{name}'. "
                f"Set a different default collection first."
            )

        return self.update_collection(name, {"enabled": False})

    def get_default_collection(self) -> str:
        """Get the default collection name.

        Returns:
            Default collection name

        Example:
            >>> config.get_default_collection()
            "claude-mpm"
        """
        config = self._load_config()
        return config.get("skills", {}).get("default_collection", "claude-mpm")

    def set_default_collection(self, name: str) -> Dict[str, Any]:
        """Set the default collection.

        Args:
            name: Collection name to set as default

        Returns:
            Dict with operation result

        Raises:
            ValueError: If collection doesn't exist or is disabled

        Example:
            >>> config.set_default_collection("obra-superpowers")
            {
                "status": "success",
                "message": "Default collection set to 'obra-superpowers'",
                "previous_default": "claude-mpm"
            }
        """
        config = self._load_config()
        collections = config.get("skills", {}).get("collections", {})

        if name not in collections:
            raise ValueError(f"Collection '{name}' not found")

        if not collections[name].get("enabled", True):
            raise ValueError(
                f"Cannot set disabled collection '{name}' as default. Enable it first."
            )

        previous_default = config.get("skills", {}).get("default_collection")

        config.setdefault("skills", {})["default_collection"] = name
        self._save_config(config)

        self.logger.info(
            f"Set default collection to '{name}' (was: '{previous_default}')"
        )
        return {
            "status": "success",
            "message": f"Default collection set to '{name}'",
            "previous_default": previous_default,
            "new_default": name,
        }

    def update_collection_timestamp(self, name: str) -> Dict[str, Any]:
        """Update the last_update timestamp for a collection.

        Args:
            name: Collection name

        Returns:
            Dict with operation result

        Example:
            >>> config.update_collection_timestamp("claude-mpm")
            {
                "status": "success",
                "message": "Timestamp updated for 'claude-mpm'",
                "timestamp": "2025-11-21T15:30:00Z"
            }
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        result = self.update_collection(name, {"last_update": timestamp})
        result["timestamp"] = timestamp
        result["message"] = f"Timestamp updated for '{name}'"

        return result

    def get_config_path(self) -> Path:
        """Get path to configuration file.

        Returns:
            Path to config file

        Example:
            >>> config.get_config_path()
            PosixPath('/Users/username/.claude-mpm/config.json')
        """
        return self.config_path

    def validate_collection_config(
        self, collection_config: Dict[str, Any]
    ) -> List[str]:
        """Validate a collection configuration.

        Args:
            collection_config: Collection configuration to validate

        Returns:
            List of validation errors (empty if valid)

        Example:
            >>> errors = config.validate_collection_config({
            ...     "url": "https://github.com/user/repo",
            ...     "enabled": True,
            ...     "priority": 1
            ... })
            >>> errors
            []
        """
        errors = []

        # Required fields
        if "url" not in collection_config:
            errors.append("Missing required field: url")
        elif not collection_config["url"].startswith("https://github.com/"):
            errors.append(
                f"Invalid URL: {collection_config['url']}. "
                f"Must be a GitHub repository URL."
            )

        # Optional field validations
        if "enabled" in collection_config and not isinstance(
            collection_config["enabled"], bool
        ):
            errors.append("Field 'enabled' must be a boolean")

        if "priority" in collection_config:
            priority = collection_config["priority"]
            if not isinstance(priority, int):
                errors.append("Field 'priority' must be an integer")
            elif priority < 1:
                errors.append("Field 'priority' must be >= 1")

        return errors
