"""
Update Preferences Manager
===========================

Manages user preferences for package update checking.
Allows users to skip specific versions or disable update checks entirely.
"""

import json
from pathlib import Path
from typing import Any, Dict


class UpdatePreferences:
    """
    Manage update checking preferences.

    WHY: Respect user preferences about update notifications to avoid
    annoying users who want to stay on specific versions or disable checks.

    DESIGN DECISIONS:
    - Store preferences in user's home directory
    - Simple JSON format for easy manual editing
    - Per-package preferences for granular control
    """

    PREFS_FILE = Path.home() / ".claude-mpm" / "mcp_updates.json"

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """
        Load preferences from disk.

        Returns:
            Dictionary of preferences, empty dict if file doesn't exist
        """
        if cls.PREFS_FILE.exists():
            try:
                with cls.PREFS_FILE.open() as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                # Return empty dict if file is corrupted or unreadable
                pass
        return {}

    @classmethod
    def save(cls, prefs: Dict[str, Any]) -> None:
        """
        Save preferences to disk.

        Args:
            prefs: Preferences dictionary to save
        """
        cls.PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with cls.PREFS_FILE.open("w") as f:
                json.dump(prefs, f, indent=2)
        except OSError:
            # Silently fail if we can't write preferences
            pass

    @classmethod
    def should_check_package(cls, package: str) -> bool:
        """
        Check if updates should be checked for a specific package.

        Args:
            package: Package name to check

        Returns:
            True if updates should be checked, False otherwise
        """
        prefs = cls.load()

        # Global preference takes precedence
        if not prefs.get("global_check_enabled", True):
            return False

        # Package-specific preference
        pkg_prefs = prefs.get("packages", {}).get(package, {})
        return pkg_prefs.get("check_enabled", True)

    @classmethod
    def should_skip_version(cls, package: str, version: str) -> bool:
        """
        Check if a specific version should be skipped for a package.

        Args:
            package: Package name
            version: Version to check

        Returns:
            True if this version should be skipped, False otherwise
        """
        prefs = cls.load()
        pkg_prefs = prefs.get("packages", {}).get(package, {})
        skip_version = pkg_prefs.get("skip_version")
        return skip_version == version

    @classmethod
    def set_skip_version(cls, package: str, version: str) -> None:
        """
        Remember to skip a specific version for a package.

        Args:
            package: Package name
            version: Version to skip
        """
        prefs = cls.load()

        # Ensure packages dict exists
        if "packages" not in prefs:
            prefs["packages"] = {}
        if package not in prefs["packages"]:
            prefs["packages"][package] = {}

        prefs["packages"][package]["skip_version"] = version
        cls.save(prefs)

    @classmethod
    def disable_package_checks(cls, package: str) -> None:
        """
        Disable update checks for a specific package.

        Args:
            package: Package name to disable checks for
        """
        prefs = cls.load()

        # Ensure packages dict exists
        if "packages" not in prefs:
            prefs["packages"] = {}
        if package not in prefs["packages"]:
            prefs["packages"][package] = {}

        prefs["packages"][package]["check_enabled"] = False
        cls.save(prefs)

    @classmethod
    def enable_package_checks(cls, package: str) -> None:
        """
        Enable update checks for a specific package.

        Args:
            package: Package name to enable checks for
        """
        prefs = cls.load()

        # Ensure packages dict exists
        if "packages" not in prefs:
            prefs["packages"] = {}
        if package not in prefs["packages"]:
            prefs["packages"][package] = {}

        prefs["packages"][package]["check_enabled"] = True
        cls.save(prefs)

    @classmethod
    def disable_all_checks(cls) -> None:
        """Disable all update checks globally."""
        prefs = cls.load()
        prefs["global_check_enabled"] = False
        cls.save(prefs)

    @classmethod
    def enable_all_checks(cls) -> None:
        """Enable all update checks globally."""
        prefs = cls.load()
        prefs["global_check_enabled"] = True
        cls.save(prefs)
