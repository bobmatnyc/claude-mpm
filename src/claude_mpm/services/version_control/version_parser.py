"""
Enhanced version parsing system with multiple source support and fallback mechanisms.

This module provides a robust version parsing system that can retrieve version information
from multiple sources with intelligent fallback logic:

1. Git tags (primary source - most reliable)
2. CHANGELOG.md (for release notes and history)
3. VERSION file (for current version)
4. package.json (for npm packages)
5. pyproject.toml (for Python packages)

The system includes caching for performance and validation for data integrity.
"""

import contextlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class VersionSource:
    """Enumeration of version sources with priority ordering."""

    GIT_TAGS = "git_tags"
    CHANGELOG = "changelog"
    VERSION_FILE = "version_file"
    PACKAGE_JSON = "package_json"
    PYPROJECT_TOML = "pyproject_toml"
    SETUP_PY = "setup_py"

    # Priority order for fallback mechanism
    PRIORITY_ORDER = [
        GIT_TAGS,
        CHANGELOG,
        VERSION_FILE,
        PACKAGE_JSON,
        PYPROJECT_TOML,
        SETUP_PY,
    ]


class VersionMetadata:
    """Extended metadata for version information."""

    def __init__(
        self,
        version: str,
        source: str,
        release_date: Optional[datetime] = None,
        commit_hash: Optional[str] = None,
        author: Optional[str] = None,
        message: Optional[str] = None,
        changes: Optional[List[str]] = None,
    ):
        self.version = version
        self.source = source
        self.release_date = release_date or datetime.now(timezone.utc)
        self.commit_hash = commit_hash
        self.author = author
        self.message = message
        self.changes = changes or []

    def to_dict(self) -> Dict:
        """Convert metadata to dictionary format."""
        return {
            "version": self.version,
            "source": self.source,
            "release_date": (
                self.release_date.isoformat() if self.release_date else None
            ),
            "commit_hash": self.commit_hash,
            "author": self.author,
            "message": self.message,
            "changes": self.changes,
        }


class EnhancedVersionParser:
    """
    Enhanced version parser with multiple source support and intelligent fallback.

    This parser provides:
    - Multiple version source support
    - Intelligent fallback mechanisms
    - Caching for performance
    - Validation and error handling
    - Comprehensive version history retrieval
    """

    def __init__(self, project_root: Optional[Path] = None, cache_ttl: int = 300):
        """
        Initialize the enhanced version parser.

        Args:
            project_root: Root directory of the project (defaults to current directory)
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.project_root = project_root or Path.cwd()
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[datetime, any]] = {}

        # Compile regex patterns once for efficiency
        self._version_pattern = re.compile(
            r"(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?"
        )
        self._changelog_version_pattern = re.compile(
            r"##\s*\[?([0-9]+\.[0-9]+\.[0-9]+[^\]]*)\]?\s*[--]\s*(\d{4}-\d{2}-\d{2})?"
        )

    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached value if still valid."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if datetime.now(timezone.utc) - timestamp < timedelta(
                seconds=self.cache_ttl
            ):
                return value
            del self._cache[key]
        return None

    def _set_cached(self, key: str, value: any) -> any:
        """Set cached value with timestamp."""
        self._cache[key] = (datetime.now(timezone.utc), value)
        return value

    def get_current_version(
        self, prefer_source: Optional[str] = None
    ) -> Optional[VersionMetadata]:
        """
        Get the current version from the most reliable available source.

        Args:
            prefer_source: Preferred source to check first (optional)

        Returns:
            VersionMetadata with current version information, or None if not found
        """
        cache_key = f"current_version_{prefer_source or 'auto'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        sources = VersionSource.PRIORITY_ORDER.copy()
        if prefer_source and prefer_source in sources:
            sources.remove(prefer_source)
            sources.insert(0, prefer_source)

        for source in sources:
            try:
                version = self._get_version_from_source(source, latest_only=True)
                if version:
                    return self._set_cached(cache_key, version)
            except Exception as e:
                self.logger.debug(f"Failed to get version from {source}: {e}")

        return None

    def get_version_history(
        self, include_prereleases: bool = False, limit: Optional[int] = None
    ) -> List[VersionMetadata]:
        """
        Get complete version history from all available sources.

        Args:
            include_prereleases: Include pre-release versions (alpha, beta, rc)
            limit: Maximum number of versions to return

        Returns:
            List of VersionMetadata objects sorted by version (descending)
        """
        cache_key = f"version_history_{include_prereleases}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        all_versions: Dict[str, VersionMetadata] = {}

        # Try each source and merge results
        for source in VersionSource.PRIORITY_ORDER:
            try:
                versions = self._get_versions_from_source(source)
                for version in versions:
                    # Use the first occurrence of each version (highest priority source)
                    if version.version not in all_versions:
                        all_versions[version.version] = version
            except Exception as e:
                self.logger.debug(f"Failed to get versions from {source}: {e}")

        # Filter and sort versions
        result = list(all_versions.values())

        if not include_prereleases:
            result = [v for v in result if not self._is_prerelease(v.version)]

        # Sort by semantic version
        result.sort(key=lambda v: self._parse_semver(v.version), reverse=True)

        if limit:
            result = result[:limit]

        return self._set_cached(cache_key, result)

    def _get_version_from_source(
        self, source: str, latest_only: bool = False
    ) -> Optional[VersionMetadata]:
        """Get version(s) from a specific source."""
        if source == VersionSource.GIT_TAGS:
            return self._get_version_from_git(latest_only)
        if source == VersionSource.VERSION_FILE:
            return self._get_version_from_file()
        if source == VersionSource.PACKAGE_JSON:
            return self._get_version_from_package_json()
        if source == VersionSource.PYPROJECT_TOML:
            return self._get_version_from_pyproject()
        if source == VersionSource.CHANGELOG:
            versions = self._get_versions_from_changelog()
            return versions[0] if versions else None
        return None

    def _get_versions_from_source(self, source: str) -> List[VersionMetadata]:
        """Get all versions from a specific source."""
        if source == VersionSource.GIT_TAGS:
            return self._get_all_versions_from_git()
        if source == VersionSource.CHANGELOG:
            return self._get_versions_from_changelog()
        if source in [
            VersionSource.VERSION_FILE,
            VersionSource.PACKAGE_JSON,
            VersionSource.PYPROJECT_TOML,
        ]:
            # These sources only provide current version
            version = self._get_version_from_source(source, latest_only=True)
            return [version] if version else []
        return []

    def _get_version_from_git(
        self, latest_only: bool = True
    ) -> Optional[VersionMetadata]:
        """Get version information from git tags."""
        try:
            if latest_only:
                # Get the latest tag
                result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    check=False,
                )
                if result.returncode == 0:
                    tag = result.stdout.strip()
                    return self._parse_git_tag(tag)
            else:
                return (
                    self._get_all_versions_from_git()[0]
                    if self._get_all_versions_from_git()
                    else None
                )
        except Exception as e:
            self.logger.debug(f"Failed to get git version: {e}")
        return None

    def _get_all_versions_from_git(self) -> List[VersionMetadata]:
        """Get all versions from git tags with metadata."""
        versions = []
        try:
            # Get all tags with dates and messages
            result = subprocess.run(
                [
                    "git",
                    "for-each-ref",
                    "--sort=-version:refname",
                    "--format=%(refname:short)|%(creatordate:iso)|%(subject)",
                    "refs/tags",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split("|", 2)
                        if len(parts) >= 1:
                            tag = parts[0]
                            date_str = parts[1] if len(parts) > 1 else None
                            message = parts[2] if len(parts) > 2 else None

                            # Parse the tag
                            metadata = self._parse_git_tag(tag, date_str, message)
                            if metadata:
                                versions.append(metadata)
        except Exception as e:
            self.logger.debug(f"Failed to get git versions: {e}")

        return versions

    def _parse_git_tag(
        self, tag: str, date_str: Optional[str] = None, message: Optional[str] = None
    ) -> Optional[VersionMetadata]:
        """Parse a git tag into VersionMetadata."""
        # Remove 'v' prefix if present
        version = tag[1:] if tag.startswith("v") else tag

        # Validate version format
        if not self._version_pattern.match(version):
            return None

        # Parse date if provided
        release_date = None
        if date_str:
            with contextlib.suppress(Exception):
                release_date = datetime.fromisoformat(date_str.replace(" ", "T"))

        # Get commit hash for this tag
        commit_hash = None
        try:
            result = subprocess.run(
                ["git", "rev-list", "-n", "1", tag],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )
            if result.returncode == 0:
                commit_hash = result.stdout.strip()[:7]
        except Exception:
            pass

        return VersionMetadata(
            version=version,
            source=VersionSource.GIT_TAGS,
            release_date=release_date,
            commit_hash=commit_hash,
            message=message,
        )

    def _get_version_from_file(self) -> Optional[VersionMetadata]:
        """Get version from VERSION file."""
        version_file = self.project_root / "VERSION"
        if version_file.exists():
            try:
                version = version_file.read_text().strip()
                if self._version_pattern.match(version):
                    return VersionMetadata(
                        version=version, source=VersionSource.VERSION_FILE
                    )
            except Exception as e:
                self.logger.debug(f"Failed to read VERSION file: {e}")
        return None

    def _get_version_from_package_json(self) -> Optional[VersionMetadata]:
        """Get version from package.json."""
        package_file = self.project_root / "package.json"
        if package_file.exists():
            try:
                with package_file.open() as f:
                    data = json.load(f)
                    version = data.get("version")
                    if version and self._version_pattern.match(version):
                        return VersionMetadata(
                            version=version, source=VersionSource.PACKAGE_JSON
                        )
            except Exception as e:
                self.logger.debug(f"Failed to read package.json: {e}")
        return None

    def _get_version_from_pyproject(self) -> Optional[VersionMetadata]:
        """Get version from pyproject.toml."""
        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            try:
                content = pyproject_file.read_text()
                # Look for version in [tool.poetry] or [project] sections
                patterns = [
                    r'version\s*=\s*["\']([^"\']+)["\']',
                    r"version\s*=\s*\{[^}]*\}",  # Dynamic version
                ]

                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        version = match.group(1) if match.lastindex else None
                        if version and self._version_pattern.match(version):
                            return VersionMetadata(
                                version=version, source=VersionSource.PYPROJECT_TOML
                            )
            except Exception as e:
                self.logger.debug(f"Failed to read pyproject.toml: {e}")
        return None

    def _get_versions_from_changelog(self) -> List[VersionMetadata]:
        """Parse version history from CHANGELOG.md."""
        versions = []
        changelog_paths = [
            self.project_root / "CHANGELOG.md",
            self.project_root / "docs" / "CHANGELOG.md",
            self.project_root / "HISTORY.md",
        ]

        for changelog_path in changelog_paths:
            if changelog_path.exists():
                try:
                    content = changelog_path.read_text()

                    # Find all version entries
                    for match in self._changelog_version_pattern.finditer(content):
                        version = match.group(1).strip()
                        date_str = match.group(2) if match.lastindex >= 2 else None

                        # Parse release date
                        release_date = None
                        if date_str:
                            with contextlib.suppress(Exception):
                                release_date = datetime.strptime(date_str, "%Y-%m-%d")

                        # Extract changes for this version
                        changes = self._extract_changelog_changes(
                            content, match.start()
                        )

                        versions.append(
                            VersionMetadata(
                                version=version,
                                source=VersionSource.CHANGELOG,
                                release_date=release_date,
                                changes=changes,
                            )
                        )

                    if versions:
                        break
                except Exception as e:
                    self.logger.debug(f"Failed to parse changelog: {e}")

        return versions

    def _extract_changelog_changes(self, content: str, start_pos: int) -> List[str]:
        """Extract change entries for a specific version from changelog."""
        changes = []
        lines = content[start_pos:].split("\n")

        in_changes = False
        for line in lines[1:]:  # Skip the version header line
            # Stop at next version header
            if line.startswith("##"):
                break

            # Collect change lines (usually start with -, *, or +)
            if line.strip().startswith(("-", "*", "+")):
                changes.append(line.strip()[1:].strip())
                in_changes = True
            elif in_changes and line.strip() and not line.startswith("#"):
                # Continuation of previous change
                if changes:
                    changes[-1] += " " + line.strip()

        return changes

    def _is_prerelease(self, version: str) -> bool:
        """Check if a version is a pre-release."""
        prerelease_patterns = [
            r"-(?:alpha|beta|rc|dev|pre)",
            r"\.(?:alpha|beta|rc|dev|pre)",
            r"(?:a|b|rc)\d+$",
        ]

        for pattern in prerelease_patterns:
            if re.search(pattern, version, re.IGNORECASE):
                return True
        return False

    def _parse_semver(self, version: str) -> Tuple[int, int, int, str, str]:
        """
        Parse semantic version for sorting.

        Returns tuple of (major, minor, patch, prerelease, build)
        """
        match = self._version_pattern.match(version)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3))
            prerelease = match.group(4) or ""
            build = match.group(5) or ""
            return (major, minor, patch, prerelease, build)
        return (0, 0, 0, "", "")

    def validate_version_consistency(self) -> Dict[str, str]:
        """
        Validate version consistency across all sources.

        Returns:
            Dictionary mapping source names to versions found
        """
        versions = {}

        for source in VersionSource.PRIORITY_ORDER:
            try:
                version = self._get_version_from_source(source, latest_only=True)
                if version:
                    versions[source] = version.version
            except Exception as e:
                self.logger.debug(f"Failed to check {source}: {e}")

        return versions

    def get_version_for_release(self) -> Optional[str]:
        """
        Get the version that should be used for the next release.

        This prioritizes git tags as the source of truth, falling back
        to VERSION file if no git tags exist.

        Returns:
            Version string for release, or None if no version found
        """
        # Try git first
        git_version = self._get_version_from_git(latest_only=True)
        if git_version:
            return git_version.version

        # Fall back to VERSION file
        file_version = self._get_version_from_file()
        if file_version:
            return file_version.version

        return None


# Convenience function for backward compatibility
@lru_cache(maxsize=1)
def get_version_parser(project_root: Optional[Path] = None) -> EnhancedVersionParser:
    """Get a singleton instance of the version parser."""
    return EnhancedVersionParser(project_root)
