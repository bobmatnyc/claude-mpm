"""
Directory shortcuts service for Claude MPM messaging system.

WHY: Users need convenient aliases for frequently messaged projects instead of
typing full absolute paths every time.

DESIGN:
- JSON file storage for shortcuts in ~/.claude-mpm/
- Simple key-value mapping of shortcut name -> absolute path
- Path resolution and validation
- CRUD operations for shortcuts management
"""

import json
from pathlib import Path
from typing import Dict, Optional

from ...core.logging_utils import get_logger

logger = get_logger(__name__)


class ShortcutsService:
    """Service for managing directory shortcuts in messaging."""

    def __init__(self, shortcuts_file: Optional[Path] = None):
        """
        Initialize shortcuts service.

        Args:
            shortcuts_file: Override shortcuts file path (for testing)
        """
        self.shortcuts_file = shortcuts_file or (
            Path.home() / ".claude-mpm" / "shortcuts.json"
        )
        self._shortcuts_cache: Optional[Dict[str, str]] = None

        # Ensure shortcuts directory exists
        self.shortcuts_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_shortcuts(self) -> Dict[str, str]:
        """Load shortcuts from disk, with caching."""
        if self._shortcuts_cache is not None:
            return self._shortcuts_cache

        if not self.shortcuts_file.exists():
            self._shortcuts_cache = {}
            return self._shortcuts_cache

        try:
            with open(self.shortcuts_file) as f:
                shortcuts = json.load(f)
                # Validate format
                if not isinstance(shortcuts, dict):
                    logger.warning("Invalid shortcuts format, resetting")
                    shortcuts = {}

                # Ensure all paths are absolute and resolved
                validated_shortcuts = {}
                for name, path_str in shortcuts.items():
                    try:
                        resolved_path = str(Path(path_str).expanduser().resolve())
                        validated_shortcuts[name] = resolved_path
                    except Exception as e:
                        logger.warning(
                            f"Invalid path in shortcut '{name}': {path_str} - {e}"
                        )

                self._shortcuts_cache = validated_shortcuts
                return self._shortcuts_cache

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load shortcuts: {e}")
            self._shortcuts_cache = {}
            return self._shortcuts_cache

    def _save_shortcuts(self) -> None:
        """Save shortcuts to disk."""
        if self._shortcuts_cache is None:
            return

        try:
            with open(self.shortcuts_file, "w") as f:
                json.dump(self._shortcuts_cache, f, indent=2, sort_keys=True)
        except OSError as e:
            logger.error(f"Failed to save shortcuts: {e}")

    def add_shortcut(self, name: str, path: str) -> bool:
        """
        Add or update a shortcut.

        Args:
            name: Shortcut name (alphanumeric with underscores/hyphens)
            path: Directory path to shortcut to

        Returns:
            True if added successfully, False otherwise
        """
        # Validate name
        if not name or not name.replace("_", "").replace("-", "").isalnum():
            logger.error(
                f"Invalid shortcut name: {name}. Use alphanumeric characters, underscores, or hyphens only."
            )
            return False

        # Validate and resolve path
        try:
            resolved_path = Path(path).expanduser().resolve()
            if not resolved_path.exists():
                logger.error(f"Directory does not exist: {resolved_path}")
                return False

            if not resolved_path.is_dir():
                logger.error(f"Path is not a directory: {resolved_path}")
                return False

        except Exception as e:
            logger.error(f"Invalid path: {path} - {e}")
            return False

        # Load current shortcuts
        shortcuts = self._load_shortcuts()

        # Add/update shortcut
        shortcuts[name] = str(resolved_path)
        self._shortcuts_cache = shortcuts
        self._save_shortcuts()

        logger.info(f"Added shortcut '{name}' -> {resolved_path}")
        return True

    def remove_shortcut(self, name: str) -> bool:
        """
        Remove a shortcut.

        Args:
            name: Shortcut name to remove

        Returns:
            True if removed, False if not found
        """
        shortcuts = self._load_shortcuts()

        if name not in shortcuts:
            return False

        del shortcuts[name]
        self._shortcuts_cache = shortcuts
        self._save_shortcuts()

        logger.info(f"Removed shortcut '{name}'")
        return True

    def list_shortcuts(self) -> Dict[str, str]:
        """
        List all shortcuts.

        Returns:
            Dictionary of name -> path mappings
        """
        return self._load_shortcuts().copy()

    def resolve_shortcut(self, name_or_path: str) -> str:
        """
        Resolve a shortcut name to its path, or return the input if not a shortcut.

        Args:
            name_or_path: Either a shortcut name or a direct path

        Returns:
            Resolved absolute path
        """
        shortcuts = self._load_shortcuts()

        # If it's a known shortcut, return the resolved path
        if name_or_path in shortcuts:
            return shortcuts[name_or_path]

        # Otherwise, assume it's a direct path and resolve it
        try:
            return str(Path(name_or_path).expanduser().resolve())
        except Exception as e:
            logger.warning(f"Failed to resolve path: {name_or_path} - {e}")
            return name_or_path

    def is_shortcut(self, name: str) -> bool:
        """
        Check if a name is a known shortcut.

        Args:
            name: Name to check

        Returns:
            True if it's a known shortcut
        """
        shortcuts = self._load_shortcuts()
        return name in shortcuts

    def get_shortcut_path(self, name: str) -> Optional[str]:
        """
        Get the path for a specific shortcut.

        Args:
            name: Shortcut name

        Returns:
            Path if shortcut exists, None otherwise
        """
        shortcuts = self._load_shortcuts()
        return shortcuts.get(name)

    def clear_cache(self) -> None:
        """Clear the shortcuts cache (for testing or forced reload)."""
        self._shortcuts_cache = None
