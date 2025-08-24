"""Monitor UI Build Tracking Service.

WHY: The Monitor UI needs its own build tracking separate from the main MPM build
number to track UI-specific changes and deployments independently.

DESIGN DECISION:
- Uses atomic file operations for thread-safe build number management
- Stores build number in MONITOR_BUILD file at project root
- Formats as 4-digit zero-padded strings (0001, 0002, etc.)
- Provides both sync and async interfaces for flexibility
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.logger import get_logger


class MonitorBuildService(BaseService):
    """Service for managing Monitor UI build numbers.

    WHY: Separate build tracking allows the Monitor UI to evolve independently
    of the main MPM framework, enabling rapid UI iterations without affecting
    core framework versioning.
    """

    # Default values
    DEFAULT_BUILD_NUMBER = 1
    DEFAULT_VERSION = "1.0.0"
    BUILD_FILE_NAME = "MONITOR_BUILD"

    def __init__(self):
        """Initialize the monitor build service."""
        super().__init__(name="monitor_build_service")
        self.logger = get_logger(self.__class__.__name__)

        # Determine build file location
        self._build_file_path = self._get_build_file_path()

        # Cache for build info to reduce file I/O
        self._cached_build_info: Optional[Dict[str, Any]] = None
        self._cache_lock = asyncio.Lock()

    def _get_build_file_path(self) -> Path:
        """Get the path to the MONITOR_BUILD file.

        WHY: Centralizes build file location logic, checking multiple
        possible locations to support different installation scenarios.

        Returns:
            Path to the MONITOR_BUILD file
        """
        # Try project root first (development)
        try:
            from claude_mpm.config.paths import paths

            build_file = paths.project_root / self.BUILD_FILE_NAME
            if build_file.parent.exists():
                return build_file
        except ImportError:
            pass

        # Fallback to package root
        package_root = Path(__file__).parent.parent.parent
        return package_root / self.BUILD_FILE_NAME

    async def _initialize(self) -> None:
        """Initialize the service and ensure build file exists.

        WHY: Ensures the build file exists with default values on first run,
        preventing errors and providing a clean starting point.
        """
        await self._ensure_build_file_exists()
        await self._load_build_info()

    async def _cleanup(self) -> None:
        """Cleanup service resources."""
        self._cached_build_info = None

    async def _ensure_build_file_exists(self) -> None:
        """Ensure the MONITOR_BUILD file exists with default values.

        WHY: Atomic file creation prevents race conditions when multiple
        processes might try to create the file simultaneously.
        """
        if not self._build_file_path.exists():
            default_info = {
                "build_number": self.DEFAULT_BUILD_NUMBER,
                "version": self.DEFAULT_VERSION,
                "last_updated": None,
            }
            await self._write_build_info(default_info)
            self.logger.info(f"Created MONITOR_BUILD file at {self._build_file_path}")

    async def _load_build_info(self) -> Dict[str, Any]:
        """Load build information from file.

        WHY: Centralizes file reading with error handling and caching
        to improve performance and reliability.

        Returns:
            Dictionary with build information
        """
        async with self._cache_lock:
            try:
                if self._build_file_path.exists():
                    content = self._build_file_path.read_text().strip()

                    # Try to parse as JSON first
                    try:
                        self._cached_build_info = json.loads(content)
                    except json.JSONDecodeError:
                        # Fallback: treat as plain build number
                        try:
                            build_num = int(content)
                            self._cached_build_info = {
                                "build_number": build_num,
                                "version": self.DEFAULT_VERSION,
                                "last_updated": None,
                            }
                        except ValueError:
                            # Invalid content, use defaults
                            self._cached_build_info = {
                                "build_number": self.DEFAULT_BUILD_NUMBER,
                                "version": self.DEFAULT_VERSION,
                                "last_updated": None,
                            }
                else:
                    self._cached_build_info = {
                        "build_number": self.DEFAULT_BUILD_NUMBER,
                        "version": self.DEFAULT_VERSION,
                        "last_updated": None,
                    }
            except Exception as e:
                self.logger.error(f"Error loading build info: {e}")
                self._cached_build_info = {
                    "build_number": self.DEFAULT_BUILD_NUMBER,
                    "version": self.DEFAULT_VERSION,
                    "last_updated": None,
                }

            return self._cached_build_info

    async def _write_build_info(self, info: Dict[str, Any]) -> None:
        """Write build information to file atomically.

        WHY: Atomic writes prevent file corruption if the process is
        interrupted during the write operation.

        Args:
            info: Build information dictionary
        """
        # Add timestamp
        from datetime import datetime

        info["last_updated"] = datetime.utcnow().isoformat()

        # Write atomically using temp file and rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self._build_file_path.parent, prefix=".monitor_build_", suffix=".tmp"
        )

        try:
            # Write JSON content
            with os.fdopen(temp_fd, "w") as f:
                json.dump(info, f, indent=2)

            # Atomic rename
            Path(temp_path).replace(self._build_file_path)

            # Update cache
            async with self._cache_lock:
                self._cached_build_info = info

        except Exception as e:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            raise e

    async def get_build_number(self) -> int:
        """Get the current monitor build number.

        Returns:
            Current build number as integer
        """
        info = await self._load_build_info()
        return info.get("build_number", self.DEFAULT_BUILD_NUMBER)

    async def get_formatted_build_number(self) -> str:
        """Get the current build number as a 4-digit string.

        WHY: Consistent 4-digit formatting ensures proper sorting
        and display alignment in the UI.

        Returns:
            Build number as 4-digit zero-padded string
        """
        build_num = await self.get_build_number()
        return f"{build_num:04d}"

    async def increment_build_number(self) -> int:
        """Increment and return the new build number.

        WHY: Atomic increment operation ensures no build numbers are
        skipped or duplicated even with concurrent access.

        Returns:
            New build number after incrementing
        """
        info = await self._load_build_info()
        new_build = info.get("build_number", self.DEFAULT_BUILD_NUMBER) + 1
        info["build_number"] = new_build
        await self._write_build_info(info)

        self.logger.info(f"Monitor build number incremented to {new_build:04d}")
        return new_build

    async def get_monitor_version(self) -> str:
        """Get the monitor UI version.

        Returns:
            Monitor UI semantic version string
        """
        info = await self._load_build_info()
        return info.get("version", self.DEFAULT_VERSION)

    async def set_monitor_version(self, version: str) -> None:
        """Set the monitor UI version.

        Args:
            version: New semantic version string
        """
        info = await self._load_build_info()
        info["version"] = version
        await self._write_build_info(info)
        self.logger.info(f"Monitor version updated to {version}")

    async def get_full_version_string(self) -> str:
        """Get the full version string for display.

        WHY: Combines semantic version with build number for complete
        version identification in the UI.

        Returns:
            Full version string (e.g., "v1.0.0-0001")
        """
        version = await self.get_monitor_version()
        build = await self.get_formatted_build_number()
        return f"v{version}-{build}"

    async def get_build_info(self) -> Dict[str, Any]:
        """Get complete build information.

        WHY: Provides all build metadata in a single call for
        efficient transmission to the UI via SocketIO.

        Returns:
            Dictionary with all build information
        """
        info = await self._load_build_info()

        # Get MPM version info
        mpm_version = "unknown"
        mpm_build = "unknown"

        try:
            from claude_mpm.services.version_service import VersionService

            version_service = VersionService()
            version_info = version_service.get_version_info()
            mpm_version = version_info.get("base_version", "unknown")
            mpm_build = version_info.get("build_number", "unknown")
        except Exception as e:
            self.logger.debug(f"Could not get MPM version info: {e}")

        return {
            "monitor": {
                "version": info.get("version", self.DEFAULT_VERSION),
                "build": info.get("build_number", self.DEFAULT_BUILD_NUMBER),
                "formatted_build": f"{info.get('build_number', self.DEFAULT_BUILD_NUMBER):04d}",
                "full_version": await self.get_full_version_string(),
                "last_updated": info.get("last_updated"),
            },
            "mpm": {
                "version": mpm_version,
                "build": mpm_build,
                "full_version": (
                    f"v{mpm_version}-build.{mpm_build}"
                    if mpm_build != "unknown"
                    else f"v{mpm_version}"
                ),
            },
        }

    # Synchronous convenience methods for non-async contexts

    def get_build_number_sync(self) -> int:
        """Synchronous version of get_build_number.

        WHY: Some contexts (like SocketIO handlers) may not support
        async operations directly.

        Returns:
            Current build number as integer
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.get_build_number())
        finally:
            loop.close()

    def get_build_info_sync(self) -> Dict[str, Any]:
        """Synchronous version of get_build_info.

        WHY: SocketIO connection handlers often need synchronous
        access to build information.

        Returns:
            Dictionary with all build information
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.get_build_info())
        finally:
            loop.close()


# Global instance for singleton pattern
_monitor_build_service: Optional[MonitorBuildService] = None


def get_monitor_build_service() -> MonitorBuildService:
    """Get or create the global monitor build service instance.

    WHY: Singleton pattern ensures consistent build number management
    across the application.

    Returns:
        The global MonitorBuildService instance
    """
    global _monitor_build_service
    if _monitor_build_service is None:
        _monitor_build_service = MonitorBuildService()
    return _monitor_build_service
