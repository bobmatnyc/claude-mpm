"""
Package Version Checker
=======================

Checks PyPI packages for updates with caching and timeout support.
Provides non-blocking version checking for MCP tools like kuzu-memory.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from packaging import version

from ....core.logger import get_logger


class PackageVersionChecker:
    """
    Check PyPI packages for updates with caching and timeout.

    WHY: Automatically detect when newer versions of critical packages
    (like kuzu-memory) are available to help users stay up-to-date.

    DESIGN DECISIONS:
    - Cache results to avoid excessive PyPI API calls
    - Non-blocking with timeout to prevent startup delays
    - Graceful failure handling (never block system operation)
    """

    CACHE_DIR = Path.home() / ".cache" / "claude-mpm" / "version-checks"
    DEFAULT_CACHE_TTL = 86400  # 24 hours
    PYPI_TIMEOUT = 5  # seconds

    def __init__(self):
        """Initialize the version checker with cache directory."""
        self.logger = get_logger("PackageVersionChecker")
        self.cache_dir = self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def check_for_update(
        self, package_name: str, current_version: str, cache_ttl: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a package has updates available.

        Args:
            package_name: Name of the package on PyPI
            current_version: Currently installed version
            cache_ttl: Cache time-to-live in seconds (optional)

        Returns:
            Dict with update information or None if check fails:
            {
                "current": "1.0.0",
                "latest": "1.1.0",
                "update_available": True,
                "checked_at": "2025-01-29T12:00:00"
            }
        """
        cache_ttl = cache_ttl or self.DEFAULT_CACHE_TTL

        # Check cache first
        cache_file = self.cache_dir / f"{package_name}.json"
        cached = self._read_cache(cache_file, cache_ttl)
        if cached:
            # Update current version in cached data
            cached["current"] = current_version
            cached["update_available"] = version.parse(
                cached["latest"]
            ) > version.parse(current_version)
            return cached

        # Fetch from PyPI with timeout
        try:
            latest = await self._fetch_pypi_version(package_name)
            if latest:
                result = {
                    "current": current_version,
                    "latest": latest,
                    "update_available": version.parse(latest)
                    > version.parse(current_version),
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
                self._write_cache(cache_file, result)
                return result
        except Exception as e:
            self.logger.debug(f"Version check failed for {package_name}: {e}")

        return None

    async def _fetch_pypi_version(self, package_name: str) -> Optional[str]:
        """
        Fetch the latest version from PyPI.

        Args:
            package_name: Package name to query

        Returns:
            Latest version string or None if fetch fails
        """
        url = f"https://pypi.org/pypi/{package_name}/json"

        try:
            timeout = aiohttp.ClientTimeout(total=self.PYPI_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["info"]["version"]
        except asyncio.TimeoutError:
            self.logger.debug(f"PyPI request timed out for {package_name}")
        except Exception as e:
            self.logger.debug(f"PyPI request failed: {e}")

        return None

    def _read_cache(self, cache_file: Path, ttl: int) -> Optional[Dict[str, Any]]:
        """
        Read from cache if valid.

        Args:
            cache_file: Path to cache file
            ttl: Time-to-live in seconds

        Returns:
            Cached data if valid, None otherwise
        """
        if not cache_file.exists():
            return None

        try:
            with cache_file.open() as f:
                data = json.load(f)

            # Check TTL
            checked_at = datetime.fromisoformat(data["checked_at"])
            if datetime.now(timezone.utc) - checked_at < timedelta(seconds=ttl):
                return data
        except Exception as e:
            self.logger.debug(f"Cache read error: {e}")

        return None

    def _write_cache(self, cache_file: Path, data: Dict[str, Any]) -> None:
        """
        Write data to cache file.

        Args:
            cache_file: Path to cache file
            data: Data to cache
        """
        try:
            with cache_file.open("w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.debug(f"Cache write failed: {e}")
