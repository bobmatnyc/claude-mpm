"""Version service for determining application version.

This service handles:
1. Version detection from multiple sources
2. Build number tracking
3. Version formatting for different contexts

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.config.paths import paths
from claude_mpm.core.base_service import BaseService
from claude_mpm.services.core.interfaces import VersionServiceInterface


class VersionService(BaseService, VersionServiceInterface):
    """Service for version detection and formatting."""

    def __init__(self):
        """Initialize the version service."""
        super().__init__(name="version_service")

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def get_version(self) -> str:
        """
        Robust version determination with build number tracking.

        WHY: The version display is critical for debugging and user experience.
        This implementation ensures we always show the correct version with build
        number for precise tracking of code changes.

        DESIGN DECISION: We combine semantic version with build number:
        - Semantic version (X.Y.Z) for API compatibility tracking
        - Build number for fine-grained code change tracking
        - Format: vX.Y.Z-BBBBB (5-digit zero-padded build number)

        Returns version string formatted as "vX.Y.Z-BBBBB"
        """
        version = "0.0.0"
        method_used = "default"
        build_number = None

        # Method 1: Try package import (fastest, most common)
        try:
            from claude_mpm import __version__

            version = __version__
            method_used = "package_import"
            self.logger.debug(f"Version obtained via package import: {version}")
            # If version already includes build number (PEP 440 format), extract it
            if "+build." in version:
                parts = version.split("+build.")
                version = parts[0]  # Base version without build
                build_number = int(parts[1]) if len(parts) > 1 else None
                self.logger.debug(
                    f"Extracted base version: {version}, build: {build_number}"
                )
        except ImportError as e:
            self.logger.debug(f"Package import failed: {e}")
        except Exception as e:
            self.logger.warning(f"Unexpected error in package import: {e}")

        # Method 2: Try importlib.metadata (standard for installed packages)
        if version == "0.0.0":
            try:
                import importlib.metadata

                version = importlib.metadata.version("claude-mpm")
                method_used = "importlib_metadata"
                self.logger.debug(f"Version obtained via importlib.metadata: {version}")
            except importlib.metadata.PackageNotFoundError:
                self.logger.debug(
                    "Package not found in importlib.metadata (likely development install)"
                )
            except ImportError:
                self.logger.debug("importlib.metadata not available (Python < 3.8)")
            except Exception as e:
                self.logger.warning(f"Unexpected error in importlib.metadata: {e}")

        # Method 3: Try reading VERSION file directly (development fallback)
        if version == "0.0.0":
            try:
                # Use centralized path management for VERSION file
                if paths.version_file.exists():
                    version = paths.version_file.read_text().strip()
                    method_used = "version_file"
                    self.logger.debug(f"Version obtained via VERSION file: {version}")
                else:
                    self.logger.debug(
                        f"VERSION file not found at: {paths.version_file}"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to read VERSION file: {e}")

        # Try to read build number (only if not already obtained from version string)
        if build_number is None:
            build_number = self._get_build_number()

        # Log final result
        if version == "0.0.0":
            self.logger.error(
                "All version detection methods failed. This indicates a packaging or installation issue."
            )
        else:
            self.logger.debug(f"Final version: {version} (method: {method_used})")

        # Format version with build number if available
        return self._format_version(version, build_number)

    def _get_build_number(self) -> Optional[int]:
        """Get build number from BUILD_NUMBER file.

        Returns:
            Build number as integer or None if not available
        """
        # Try multiple locations for BUILD_NUMBER file
        build_file_locations = [
            paths.project_root / "BUILD_NUMBER",  # Development location
            Path(__file__).parent.parent / "BUILD_NUMBER",  # Package location
        ]

        for build_file in build_file_locations:
            try:
                if build_file.exists():
                    build_content = build_file.read_text().strip()
                    build_number = int(build_content)
                    self.logger.debug(
                        f"Build number obtained from {build_file}: {build_number}"
                    )
                    return build_number
            except (OSError, ValueError) as e:
                self.logger.debug(f"Could not read BUILD_NUMBER from {build_file}: {e}")
            except Exception as e:
                self.logger.debug(
                    f"Unexpected error reading BUILD_NUMBER from {build_file}: {e}"
                )

        return None

    def _format_version(self, version: str, build_number: Optional[int]) -> str:
        """Format version string with optional build number.

        Args:
            version: Base version string
            build_number: Optional build number

        Returns:
            Formatted version string
        """
        # Format version with build number if available
        # For development: Use PEP 440 format (e.g., "3.9.5+build.275")
        # For UI/logging: Use dash format (e.g., "v3.9.5-build.275")
        # For PyPI releases: Use clean version (e.g., "3.9.5")

        # Determine formatting context (default to UI format for claude_runner)
        if build_number is not None:
            # UI/logging format with 'v' prefix and dash separator
            return f"v{version}-build.{build_number}"
        return f"v{version}"

    def get_base_version(self) -> str:
        """Get base version without build number.

        Returns:
            Base version string (e.g., "3.9.5")
        """
        version = "0.0.0"

        # Try package import first
        try:
            from claude_mpm import __version__

            version = __version__
            # If version includes build number, extract base version
            if "+build." in version:
                version = version.split("+build.")[0]
        except ImportError:
            pass

        # Try importlib.metadata
        if version == "0.0.0":
            try:
                import importlib.metadata

                version = importlib.metadata.version("claude-mpm")
            except (importlib.metadata.PackageNotFoundError, ImportError):
                pass

        # Try VERSION file
        if version == "0.0.0":
            try:
                if paths.version_file.exists():
                    version = paths.version_file.read_text().strip()
            except Exception:
                pass

        return version

    def get_build_number(self) -> Optional[int]:
        """Get current build number.

        Returns:
            Build number as integer or None if not available
        """
        return self._get_build_number()

    def get_pep440_version(self) -> str:
        """Get version in PEP 440 format for packaging.

        Returns:
            Version string in PEP 440 format (e.g., "3.9.5+build.275")
        """
        base_version = self.get_base_version()
        build_number = self.get_build_number()

        if build_number is not None:
            return f"{base_version}+build.{build_number}"
        return base_version

    # Implementation of abstract methods from VersionServiceInterface

    def get_version_info(self) -> Dict[str, Any]:
        """Get detailed version information.

        Returns:
            Dictionary with version details and metadata
        """
        base_version = self.get_base_version()
        build_number = self.get_build_number()

        return {
            "version": self.get_version(),
            "base_version": base_version,
            "build_number": build_number,
            "pep440_version": self.get_pep440_version(),
            "has_build_number": build_number is not None,
            "service": "version_service",
        }

    def format_version_display(self, include_build: bool = False) -> str:
        """Format version for display purposes.

        Args:
            include_build: Whether to include build information

        Returns:
            Formatted version string for display
        """
        if include_build:
            return self.get_version()  # Already includes build number
        return self.get_base_version()

    def check_for_updates(self) -> Dict[str, Any]:
        """Check for available updates.

        Returns:
            Dictionary with update information
        """
        # For now, return a placeholder response
        # In a full implementation, this would check against a remote repository
        return {
            "current_version": self.get_version(),
            "latest_version": self.get_version(),
            "update_available": False,
            "update_url": None,
            "message": "Update checking not implemented",
            "checked_at": None,
        }
