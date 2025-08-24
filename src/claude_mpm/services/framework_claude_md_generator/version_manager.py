from pathlib import Path

"""
Version management for framework CLAUDE.md templates.

Handles version parsing, incrementing, and comparison operations.
"""

import re
from typing import Optional


class VersionManager:
    """Manages version numbering for framework CLAUDE.md templates."""

    def __init__(self):
        """Initialize version manager."""
        self.framework_version = self._get_framework_version()

    def _get_framework_version(self) -> str:
        """
        Get the current framework version from framework/VERSION file.

        Returns:
            str: Framework version (e.g., "015")
        """
        # Check if we're in a wheel installation
        package_path = Path(__file__).parent.parent.parent
        path_str = str(package_path.resolve())
        if "site-packages" in path_str or "dist-packages" in path_str:
            # For wheel installations, check data directory
            version_path = package_path / "data" / "framework" / "VERSION"
            if not version_path.exists():
                # Try package root as fallback
                version_path = package_path.parent / "framework" / "VERSION"
        else:
            # Source installation
            version_path = package_path.parent / "framework" / "VERSION"

        if version_path.exists():
            with open(version_path) as f:
                version_content = f.read().strip()
                # Framework VERSION file contains just the framework version number
                try:
                    return f"{int(version_content):03d}"
                except ValueError:
                    # If not a plain number, try to extract from version string
                    match = re.match(r"(\d+)", version_content)
                    if match:
                        return f"{int(match.group(1)):03d}"
        return "014"  # Default fallback

    def parse_current_version(self, content: str) -> str:
        """
        Parse the current CLAUDE_MD_VERSION from existing content.

        Args:
            content: Existing CLAUDE.md content

        Returns:
            str: Version number (e.g., "016")
        """
        # First try simple serial format
        match = re.search(r"CLAUDE_MD_VERSION:\s*(\d+)(?!-)", content)
        if match:
            return match.group(1)

        # Handle old format for backward compatibility
        match = re.search(r"CLAUDE_MD_VERSION:\s*(\d+)-(\d+)", content)
        if match:
            return match.group(1)  # Return just the framework part

        return self.framework_version

    def auto_increment_version(self, current_content: Optional[str] = None) -> str:
        """
        Get the current framework version (no auto-increment for simple serial numbers).

        Args:
            current_content: Current CLAUDE.md content (unused with simple serials)

        Returns:
            str: Current framework version (e.g., "016")
        """
        # With simple serial numbers, we just use the framework version
        # Incrementing is done by updating the framework/VERSION file
        return self.framework_version

    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Args:
            version1: First version string (e.g., "016")
            version2: Second version string (e.g., "017")

        Returns:
            int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """

        def parse_version(v: str) -> int:
            # Handle simple serial format
            if "-" not in v:
                try:
                    return int(v)
                except ValueError:
                    return 0

            # Handle old format for backward compatibility
            match = re.match(r"(\d+)-(\d+)", v)
            if match:
                return int(match.group(1))  # Just compare framework part
            return 0

        v1 = parse_version(version1)
        v2 = parse_version(version2)

        if v1 < v2:
            return -1
        if v1 > v2:
            return 1
        return 0
