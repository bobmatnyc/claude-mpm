from pathlib import Path

"""
Semantic Versioning Manager - Version management logic for Version Control Agent.

This module provides comprehensive semantic versioning management including:
1. Version parsing and validation
2. Automatic version bumping based on changes
3. Changelog generation and management
4. Tag creation and management
5. Version metadata handling

Semantic Versioning Strategy:
- Follows semver.org specification 2.0.0
- Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
- MAJOR: Incompatible API changes
- MINOR: Backwards-compatible functionality additions
- PATCH: Backwards-compatible bug fixes
- PRERELEASE: Optional pre-release identifiers (alpha, beta, rc)
- BUILD: Optional build metadata

Agent Version Management:
- Agents use semantic versioning for consistency
- Version stored in agent template JSON files
- Automatic migration from old formats (serial, integer)
- Version comparison for deployment decisions
- Base and agent version tracking

Version Detection:
- Multiple file format support (package.json, pyproject.toml, etc.)
- Git tag integration for version history
- Changelog parsing for version tracking
- Fallback mechanisms for missing version info

Change Analysis:
- Conventional commit pattern matching
- Breaking change detection
- Feature and bug fix classification
- Confidence scoring for version bump suggestions
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ...utils.config_manager import ConfigurationManager


class VersionBumpType(Enum):
    """Types of version bumps."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


@dataclass
class SemanticVersion:
    """Represents a semantic version following semver.org specification.

    This class encapsulates a semantic version with support for:
    - Major, minor, and patch version numbers
    - Pre-release identifiers (alpha, beta, rc, etc.)
    - Build metadata
    - Version comparison and sorting
    - Version bumping operations

    The comparison logic follows semver precedence rules:
    1. Compare major, minor, patch numerically
    2. Pre-release versions have lower precedence than normal versions
    3. Pre-release identifiers are compared alphanumerically
    4. Build metadata is ignored in comparisons

    This is used for both project versioning and agent version management.
    """

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """String representation of version in semver format.

        Examples:
        - 1.2.3
        - 1.2.3-alpha.1
        - 1.2.3-beta.2+build.123
        - 1.2.3+20230615
        """
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Compare versions for sorting according to semver precedence.

        Comparison Rules:
        1. Version core (major.minor.patch) compared numerically
        2. Version with pre-release < same version without pre-release
        3. Pre-release versions compared alphanumerically
        4. Build metadata ignored (1.0.0+build1 == 1.0.0+build2)

        This enables proper version sorting for:
        - Determining latest version
        - Agent deployment decisions
        - Version history display
        """
        # Compare version core components
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch

        # Handle prerelease comparison per semver spec
        # No prerelease > with prerelease (1.0.0 > 1.0.0-alpha)
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        # Both have prerelease - compare alphanumerically
        if self.prerelease is not None and other.prerelease is not None:
            return self.prerelease < other.prerelease

        return False

    def bump(self, bump_type: VersionBumpType) -> "SemanticVersion":
        """Create a new version with the specified bump applied.

        Version Bump Rules:
        - MAJOR: Increment major, reset minor and patch to 0
        - MINOR: Increment minor, reset patch to 0
        - PATCH: Increment patch only
        - PRERELEASE: Handle pre-release progression

        Pre-release Progression:
        - No prerelease -> alpha.1
        - alpha.1 -> alpha.2
        - beta.1 -> beta.2
        - rc.1 -> rc.2
        - custom -> custom.1

        Examples:
        - 1.2.3 + MAJOR -> 2.0.0
        - 1.2.3 + MINOR -> 1.3.0
        - 1.2.3 + PATCH -> 1.2.4
        - 1.2.3 + PRERELEASE -> 1.2.3-alpha.1
        - 1.2.3-alpha.1 + PRERELEASE -> 1.2.3-alpha.2

        Args:
            bump_type: Type of version bump to apply

        Returns:
            New SemanticVersion instance with bump applied
        """
        if bump_type == VersionBumpType.MAJOR:
            # Breaking changes - reset minor and patch
            return SemanticVersion(self.major + 1, 0, 0)
        if bump_type == VersionBumpType.MINOR:
            # New features - reset patch only
            return SemanticVersion(self.major, self.minor + 1, 0)
        if bump_type == VersionBumpType.PATCH:
            # Bug fixes - increment patch only
            return SemanticVersion(self.major, self.minor, self.patch + 1)
        if bump_type == VersionBumpType.PRERELEASE:
            if self.prerelease:
                # Increment existing prerelease number
                match = re.match(r"(.+?)(\d+)$", self.prerelease)
                if match:
                    prefix, num = match.groups()
                    new_prerelease = f"{prefix}{int(num) + 1}"
                else:
                    # Add .1 if no number present
                    new_prerelease = f"{self.prerelease}.1"
            else:
                # Start new prerelease series
                new_prerelease = "alpha.1"

            return SemanticVersion(
                self.major, self.minor, self.patch, prerelease=new_prerelease
            )

        return self


@dataclass
class VersionMetadata:
    """Metadata associated with a version."""

    version: SemanticVersion
    release_date: datetime
    commit_hash: Optional[str] = None
    tag_name: Optional[str] = None
    changes: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class ChangeAnalysis:
    """Analysis of changes for version bumping."""

    has_breaking_changes: bool = False
    has_new_features: bool = False
    has_bug_fixes: bool = False
    change_descriptions: List[str] = field(default_factory=list)
    suggested_bump: VersionBumpType = VersionBumpType.PATCH
    confidence: float = 0.0


class SemanticVersionManager:
    """
    Manages semantic versioning for the Version Control Agent.

    Provides comprehensive version management including parsing, bumping,
    changelog generation, and integration with Git tags.
    """

    def __init__(self, project_root: str, logger: logging.Logger):
        """
        Initialize Semantic Version Manager.

        Args:
            project_root: Root directory of the project
            logger: Logger instance
        """
        self.project_root = Path(project_root)
        self.logger = logger
        self.config_mgr = ConfigurationManager(cache_enabled=True)

        # Version file patterns
        self.version_files = {
            "package.json": self._parse_package_json_version,
            "pyproject.toml": self._parse_pyproject_toml_version,
            "Cargo.toml": self._parse_cargo_toml_version,
            "VERSION": self._parse_version_file,
            "version.txt": self._parse_version_file,
            "pom.xml": self._parse_pom_xml_version,
        }

        # Change patterns for analysis
        self.breaking_change_patterns = [
            r"\bbreaking\b",
            r"\bbreaking[-_]change\b",
            r"\bremove\b.*\bapi\b",
            r"\bdelete\b.*\bapi\b",
            r"\bdrop\b.*\bsupport\b",
            r"\bincompatible\b",
            r"\bmajor\b.*\bchange\b",
        ]

        self.feature_patterns = [
            r"\badd\b",
            r"\bnew\b.*\bfeature\b",
            r"\bimplement\b",
            r"\benhance\b",
            r"\bintroduce\b",
            r"\bfeature\b.*\badd\b",
        ]

        self.bug_fix_patterns = [
            r"\bfix\b",
            r"\bbug\b.*\bfix\b",
            r"\bresolve\b",
            r"\bcorrect\b",
            r"\bpatch\b",
            r"\bhotfix\b",
        ]

    def parse_version(self, version_string: str) -> Optional[SemanticVersion]:
        """
        Parse a version string into a SemanticVersion object.

        Version String Formats Supported:
        - 1.2.3 (basic semantic version)
        - v1.2.3 (with 'v' prefix - common in git tags)
        - 1.2.3-alpha (with prerelease)
        - 1.2.3-alpha.1 (with prerelease and number)
        - 1.2.3-beta.2+build.123 (full format)
        - 1.2.3+20230615 (with build metadata only)

        The parser is flexible and handles:
        - Optional 'v' prefix (stripped automatically)
        - Whitespace trimming
        - Full semver specification compliance
        - Graceful failure for invalid formats

        This is used for:
        - Parsing versions from files (package.json, etc.)
        - Converting git tags to versions
        - Agent version parsing and migration
        - User input validation

        Args:
            version_string: Version string to parse

        Returns:
            SemanticVersion object or None if parsing fails
        """
        try:
            # Clean up version string - handle common variations
            version_string = version_string.strip().lstrip("v")

            # Regex pattern for semantic version per semver.org spec
            # Captures: major.minor.patch[-prerelease][+build]
            pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$"
            match = re.match(pattern, version_string)

            if match:
                major, minor, patch, prerelease, build = match.groups()

                return SemanticVersion(
                    major=int(major),
                    minor=int(minor),
                    patch=int(patch),
                    prerelease=prerelease,
                    build=build,
                )

            return None

        except Exception as e:
            self.logger.error(f"Error parsing version '{version_string}': {e}")
            return None

    def get_current_version(self) -> Optional[SemanticVersion]:
        """
        Get the current version from multiple sources with intelligent fallback.

        Uses the enhanced version parser to check:
        1. Git tags (most recent)
        2. VERSION file
        3. package.json
        4. pyproject.toml
        5. Other configured version files

        Returns:
            Current SemanticVersion or None if not found
        """
        try:
            # Import here to avoid circular dependency
            from claude_mpm.services.version_control.version_parser import (
                get_version_parser,
            )

            # Use enhanced parser for current version
            parser = get_version_parser(self.project_root)
            version_meta = parser.get_current_version()

            if version_meta:
                version = self.parse_version(version_meta.version)
                if version:
                    self.logger.info(
                        f"Found version {version} from {version_meta.source}"
                    )
                    # Optionally attach metadata
                    if hasattr(version, "__dict__"):
                        version.source = version_meta.source
                    return version

        except ImportError:
            # Fallback to original implementation
            self.logger.debug("Enhanced version parser not available, using fallback")
        except Exception as e:
            self.logger.error(
                f"Error getting current version with enhanced parser: {e}"
            )

        # Fallback to original implementation
        for filename, parser in self.version_files.items():
            file_path = self.project_root / filename

            if file_path.exists():
                try:
                    version_string = parser(file_path)
                    if version_string:
                        version = self.parse_version(version_string)
                        if version:
                            self.logger.info(f"Found version {version} in {filename}")
                            return version
                except Exception as e:
                    self.logger.error(f"Error parsing version from {filename}: {e}")
                    continue

        self.logger.warning("No version found in project files")
        return None

    def _parse_package_json_version(self, file_path: Path) -> Optional[str]:
        """Parse version from package.json."""
        try:
            data = self.config_mgr.load_json(file_path)
            return data.get("version")
        except Exception:
            return None

    def _parse_pyproject_toml_version(self, file_path: Path) -> Optional[str]:
        """Parse version from pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                # Fallback to simple regex parsing
                return self._parse_toml_version_regex(file_path)

        try:
            with open(file_path, "rb") as f:
                data = tomllib.load(f)

            # Try different locations for version
            if "project" in data and "version" in data["project"]:
                return data["project"]["version"]
            if (
                "tool" in data
                and "poetry" in data["tool"]
                and "version" in data["tool"]["poetry"]
            ):
                return data["tool"]["poetry"]["version"]

            return None

        except Exception:
            return self._parse_toml_version_regex(file_path)

    def _parse_toml_version_regex(self, file_path: Path) -> Optional[str]:
        """Parse version from TOML file using regex."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Look for version = "x.y.z" pattern
            patterns = [
                r'version\s*=\s*["\']([^"\']+)["\']',
                r'version:\s*["\']([^"\']+)["\']',
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)

            return None

        except Exception:
            return None

    def _parse_cargo_toml_version(self, file_path: Path) -> Optional[str]:
        """Parse version from Cargo.toml."""
        return self._parse_toml_version_regex(file_path)

    def _parse_version_file(self, file_path: Path) -> Optional[str]:
        """Parse version from simple version file."""
        try:
            with open(file_path) as f:
                return f.read().strip()
        except Exception:
            return None

    def _parse_pom_xml_version(self, file_path: Path) -> Optional[str]:
        """Parse version from Maven pom.xml."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Simple regex to find version in pom.xml
            pattern = r"<version>([^<]+)</version>"
            match = re.search(pattern, content)

            if match:
                return match.group(1)

            return None

        except Exception:
            return None

    def analyze_changes(self, changes: List[str]) -> ChangeAnalysis:
        """
        Analyze changes to suggest version bump type.

        Change Analysis Process:
        1. Scan each change description for patterns
        2. Categorize changes (breaking, feature, fix)
        3. Determine highest priority change type
        4. Suggest appropriate version bump
        5. Calculate confidence score

        Pattern Matching:
        - Breaking: "breaking", "breaking change", "remove api", etc.
        - Features: "add", "new feature", "implement", "enhance"
        - Fixes: "fix", "bug fix", "resolve", "correct"

        Version Bump Priority:
        1. Breaking changes -> MAJOR (highest priority)
        2. New features -> MINOR
        3. Bug fixes -> PATCH
        4. Other changes -> PATCH (default)

        Confidence Scoring:
        - 0.9: Clear breaking changes detected
        - 0.8: Clear new features detected
        - 0.7: Clear bug fixes detected
        - 0.5: No clear patterns (default to patch)

        This analysis is used for:
        - Conventional commit integration
        - Automated version bumping
        - Release note generation
        - Agent version updates

        Args:
            changes: List of change descriptions (e.g., commit messages)

        Returns:
            ChangeAnalysis with suggested version bump and confidence
        """
        analysis = ChangeAnalysis()
        analysis.change_descriptions = changes

        # Analyze each change against defined patterns
        for change in changes:
            change_lower = change.lower()

            # Check for breaking changes (highest priority)
            if any(
                re.search(pattern, change_lower)
                for pattern in self.breaking_change_patterns
            ):
                analysis.has_breaking_changes = True

            # Check for new features
            elif any(
                re.search(pattern, change_lower) for pattern in self.feature_patterns
            ):
                analysis.has_new_features = True

            # Check for bug fixes
            elif any(
                re.search(pattern, change_lower) for pattern in self.bug_fix_patterns
            ):
                analysis.has_bug_fixes = True

        # Determine suggested bump based on priority
        if analysis.has_breaking_changes:
            analysis.suggested_bump = VersionBumpType.MAJOR
            analysis.confidence = 0.9  # High confidence for breaking changes
        elif analysis.has_new_features:
            analysis.suggested_bump = VersionBumpType.MINOR
            analysis.confidence = 0.8  # Good confidence for features
        elif analysis.has_bug_fixes:
            analysis.suggested_bump = VersionBumpType.PATCH
            analysis.confidence = 0.7  # Moderate confidence for fixes
        else:
            analysis.suggested_bump = VersionBumpType.PATCH
            analysis.confidence = 0.5  # Low confidence, default to safe patch

        return analysis

    def bump_version(
        self, current_version: SemanticVersion, bump_type: VersionBumpType
    ) -> SemanticVersion:
        """
        Bump version according to semantic versioning rules.

        Args:
            current_version: Current version
            bump_type: Type of bump to apply

        Returns:
            New version
        """
        return current_version.bump(bump_type)

    def suggest_version_bump(
        self, commit_messages: List[str]
    ) -> Tuple[VersionBumpType, float]:
        """
        Suggest version bump based on commit messages.

        Args:
            commit_messages: List of commit messages since last version

        Returns:
            Tuple of (suggested_bump_type, confidence_score)
        """
        analysis = self.analyze_changes(commit_messages)
        return analysis.suggested_bump, analysis.confidence

    def update_version_files(
        self, new_version: SemanticVersion, files_to_update: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Update version in project files.

        Args:
            new_version: New version to set
            files_to_update: Specific files to update (defaults to all found)

        Returns:
            Dictionary mapping filenames to success status
        """
        results = {}
        version_string = str(new_version)

        files_to_check = files_to_update or list(self.version_files.keys())

        for filename in files_to_check:
            file_path = self.project_root / filename

            if file_path.exists():
                try:
                    success = self._update_version_file(file_path, version_string)
                    results[filename] = success

                    if success:
                        self.logger.info(
                            f"Updated version to {version_string} in {filename}"
                        )
                    else:
                        self.logger.error(f"Failed to update version in {filename}")

                except Exception as e:
                    self.logger.error(f"Error updating version in {filename}: {e}")
                    results[filename] = False

        return results

    def _update_version_file(self, file_path: Path, new_version: str) -> bool:
        """Update version in a specific file."""
        filename = file_path.name

        try:
            if filename == "package.json":
                return self._update_package_json_version(file_path, new_version)
            if filename in ["pyproject.toml", "Cargo.toml"]:
                return self._update_toml_version(file_path, new_version)
            if filename in ["VERSION", "version.txt"]:
                return self._update_simple_version_file(file_path, new_version)
            if filename == "pom.xml":
                return self._update_pom_xml_version(file_path, new_version)

            return False

        except Exception as e:
            self.logger.error(f"Error updating {filename}: {e}")
            return False

    def _update_package_json_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in package.json."""
        try:
            data = self.config_mgr.load_json(file_path)
            data["version"] = new_version

            self.config_mgr.save_json(data, file_path)

            return True

        except Exception:
            return False

    def _update_toml_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in TOML file."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Replace version field
            patterns = [
                (r'(version\s*=\s*)["\']([^"\']+)["\']', rf'\g<1>"{new_version}"'),
                (r'(version:\s*)["\']([^"\']+)["\']', rf'\g<1>"{new_version}"'),
            ]

            updated = False
            for pattern, replacement in patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    updated = True
                    break

            if updated:
                with open(file_path, "w") as f:
                    f.write(content)
                return True

            return False

        except Exception:
            return False

    def _update_simple_version_file(self, file_path: Path, new_version: str) -> bool:
        """Update version in simple version file."""
        try:
            with open(file_path, "w") as f:
                f.write(new_version + "\n")
            return True
        except Exception:
            return False

    def _update_pom_xml_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in Maven pom.xml."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Replace first version tag (project version)
            pattern = r"(<version>)[^<]+(</version>)"
            replacement = rf"\g<1>{new_version}\g<2>"

            new_content = re.sub(pattern, replacement, content, count=1)

            if new_content != content:
                with open(file_path, "w") as f:
                    f.write(new_content)
                return True

            return False

        except Exception:
            return False

    def generate_changelog_entry(
        self,
        version: SemanticVersion,
        changes: List[str],
        metadata: Optional[VersionMetadata] = None,
    ) -> str:
        """
        Generate changelog entry for a version.

        Args:
            version: Version for the changelog entry
            changes: List of changes
            metadata: Optional version metadata

        Returns:
            Formatted changelog entry
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        if metadata and metadata.release_date:
            date_str = metadata.release_date.strftime("%Y-%m-%d")

        # Build changelog entry
        lines = [f"## [{version}] - {date_str}", ""]

        # Categorize changes
        breaking_changes = []
        features = []
        fixes = []
        other_changes = []

        for change in changes:
            change_lower = change.lower()

            if any(
                re.search(pattern, change_lower)
                for pattern in self.breaking_change_patterns
            ):
                breaking_changes.append(change)
            elif any(
                re.search(pattern, change_lower) for pattern in self.feature_patterns
            ):
                features.append(change)
            elif any(
                re.search(pattern, change_lower) for pattern in self.bug_fix_patterns
            ):
                fixes.append(change)
            else:
                other_changes.append(change)

        # Add sections
        if breaking_changes:
            lines.extend(["### ⚠ BREAKING CHANGES", ""])
            for change in breaking_changes:
                lines.append(f"- {change}")
            lines.append("")

        if features:
            lines.extend(["### ✨ Features", ""])
            for change in features:
                lines.append(f"- {change}")
            lines.append("")

        if fixes:
            lines.extend(["### 🐛 Bug Fixes", ""])
            for change in fixes:
                lines.append(f"- {change}")
            lines.append("")

        if other_changes:
            lines.extend(["### 📝 Other Changes", ""])
            for change in other_changes:
                lines.append(f"- {change}")
            lines.append("")

        # Add metadata
        if metadata:
            if metadata.commit_hash:
                lines.append(f"**Commit:** {metadata.commit_hash}")
            if metadata.contributors:
                lines.append(f"**Contributors:** {', '.join(metadata.contributors)}")
            if metadata.notes:
                lines.extend(["", metadata.notes])

        return "\n".join(lines)

    def update_changelog(
        self,
        version: SemanticVersion,
        changes: List[str],
        changelog_file: str = "docs/CHANGELOG.md",
    ) -> bool:
        """
        Update CHANGELOG.md with new version entry.

        Args:
            version: Version for the changelog entry
            changes: List of changes
            changelog_file: Changelog file name

        Returns:
            True if update was successful
        """
        changelog_path = self.project_root / changelog_file

        try:
            # Generate new entry
            new_entry = self.generate_changelog_entry(version, changes)

            # Read existing changelog or create new one
            if changelog_path.exists():
                with open(changelog_path) as f:
                    existing_content = f.read()

                # Insert new entry after title
                lines = existing_content.split("\n")
                insert_index = 0

                # Find insertion point (after # Changelog title)
                for i, line in enumerate(lines):
                    if line.startswith(("# ", "## [Unreleased]")):
                        insert_index = i + 1
                        break

                # Insert new entry
                lines.insert(insert_index, new_entry)
                lines.insert(insert_index + 1, "")

                content = "\n".join(lines)
            else:
                # Create new changelog
                content = f"# Changelog\n\n{new_entry}\n"

            # Write updated changelog
            with open(changelog_path, "w") as f:
                f.write(content)

            self.logger.info(f"Updated {changelog_file} with version {version}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating changelog: {e}")
            return False

    def get_version_history(self) -> List[SemanticVersion]:
        """
        Get version history from multiple sources with intelligent fallback.

        Uses the enhanced version parser to retrieve version history from:
        1. Git tags (primary source)
        2. CHANGELOG.md (fallback)
        3. VERSION files (current version only)

        Returns:
            List of versions in descending order
        """
        try:
            # Import here to avoid circular dependency
            from claude_mpm.services.version_control.version_parser import (
                get_version_parser,
            )

            # Use enhanced parser for comprehensive version history
            parser = get_version_parser(self.project_root)
            version_metadata = parser.get_version_history(include_prereleases=False)

            # Convert to SemanticVersion objects
            versions = []
            for meta in version_metadata:
                version = self.parse_version(meta.version)
                if version:
                    # Optionally attach metadata to version
                    if hasattr(version, "__dict__"):
                        version.source = meta.source
                        version.release_date = meta.release_date
                        version.commit_hash = meta.commit_hash
                    versions.append(version)

            return versions

        except ImportError:
            # Fallback to original implementation if enhanced parser not available
            self.logger.warning(
                "Enhanced version parser not available, falling back to changelog parsing"
            )
            return self._parse_changelog_versions_fallback()
        except Exception as e:
            self.logger.error(f"Error getting version history: {e}")
            # Fallback to original implementation
            return self._parse_changelog_versions_fallback()

    def _parse_changelog_versions_fallback(self) -> List[SemanticVersion]:
        """Fallback method: Parse versions from changelog file only."""
        versions = []

        # Try to get versions from changelog
        changelog_paths = [
            self.project_root / "CHANGELOG.md",
            self.project_root / "docs" / "CHANGELOG.md",
        ]

        for changelog_path in changelog_paths:
            if changelog_path.exists():
                versions.extend(self._parse_changelog_versions(changelog_path))
                break

        # Sort versions in descending order
        versions.sort(reverse=True)
        return versions

    def _parse_changelog_versions(self, changelog_path: Path) -> List[SemanticVersion]:
        """Parse versions from changelog file."""
        versions = []

        try:
            with open(changelog_path) as f:
                content = f.read()

            # Find version entries
            pattern = r"##\s*\[([^\]]+)\]"
            matches = re.findall(pattern, content)

            for match in matches:
                version = self.parse_version(match)
                if version:
                    versions.append(version)

        except Exception as e:
            self.logger.error(f"Error parsing changelog versions: {e}")

        return versions
