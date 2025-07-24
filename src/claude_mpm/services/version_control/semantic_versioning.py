"""
Semantic Versioning Manager - Version management logic for Version Control Agent.

This module provides comprehensive semantic versioning management including:
1. Version parsing and validation
2. Automatic version bumping based on changes
3. Changelog generation and management
4. Tag creation and management
5. Version metadata handling
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging


class VersionBumpType(Enum):
    """Types of version bumps."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


@dataclass
class SemanticVersion:
    """Represents a semantic version."""

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """String representation of version."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Compare versions for sorting."""
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch

        # Handle prerelease comparison
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is not None and other.prerelease is not None:
            return self.prerelease < other.prerelease

        return False

    def bump(self, bump_type: VersionBumpType) -> "SemanticVersion":
        """Create a new version with the specified bump applied."""
        if bump_type == VersionBumpType.MAJOR:
            return SemanticVersion(self.major + 1, 0, 0)
        elif bump_type == VersionBumpType.MINOR:
            return SemanticVersion(self.major, self.minor + 1, 0)
        elif bump_type == VersionBumpType.PATCH:
            return SemanticVersion(self.major, self.minor, self.patch + 1)
        elif bump_type == VersionBumpType.PRERELEASE:
            if self.prerelease:
                # Increment prerelease number
                match = re.match(r"(.+?)(\d+)$", self.prerelease)
                if match:
                    prefix, num = match.groups()
                    new_prerelease = f"{prefix}{int(num) + 1}"
                else:
                    new_prerelease = f"{self.prerelease}.1"
            else:
                new_prerelease = "alpha.1"

            return SemanticVersion(self.major, self.minor, self.patch, prerelease=new_prerelease)

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

        Args:
            version_string: Version string to parse

        Returns:
            SemanticVersion object or None if parsing fails
        """
        try:
            # Clean up version string
            version_string = version_string.strip().lstrip("v")

            # Regex pattern for semantic version
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
        Get the current version from project files.

        Returns:
            Current SemanticVersion or None if not found
        """
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
            with open(file_path, "r") as f:
                data = json.load(f)
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
            elif (
                "tool" in data and "poetry" in data["tool"] and "version" in data["tool"]["poetry"]
            ):
                return data["tool"]["poetry"]["version"]

            return None

        except Exception:
            return self._parse_toml_version_regex(file_path)

    def _parse_toml_version_regex(self, file_path: Path) -> Optional[str]:
        """Parse version from TOML file using regex."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Look for version = "x.y.z" pattern
            patterns = [r'version\s*=\s*["\']([^"\']+)["\']', r'version:\s*["\']([^"\']+)["\']']

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
            with open(file_path, "r") as f:
                return f.read().strip()
        except Exception:
            return None

    def _parse_pom_xml_version(self, file_path: Path) -> Optional[str]:
        """Parse version from Maven pom.xml."""
        try:
            with open(file_path, "r") as f:
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

        Args:
            changes: List of change descriptions (e.g., commit messages)

        Returns:
            ChangeAnalysis with suggested version bump
        """
        analysis = ChangeAnalysis()
        analysis.change_descriptions = changes

        # Analyze each change
        for change in changes:
            change_lower = change.lower()

            # Check for breaking changes
            if any(re.search(pattern, change_lower) for pattern in self.breaking_change_patterns):
                analysis.has_breaking_changes = True

            # Check for new features
            elif any(re.search(pattern, change_lower) for pattern in self.feature_patterns):
                analysis.has_new_features = True

            # Check for bug fixes
            elif any(re.search(pattern, change_lower) for pattern in self.bug_fix_patterns):
                analysis.has_bug_fixes = True

        # Determine suggested bump
        if analysis.has_breaking_changes:
            analysis.suggested_bump = VersionBumpType.MAJOR
            analysis.confidence = 0.9
        elif analysis.has_new_features:
            analysis.suggested_bump = VersionBumpType.MINOR
            analysis.confidence = 0.8
        elif analysis.has_bug_fixes:
            analysis.suggested_bump = VersionBumpType.PATCH
            analysis.confidence = 0.7
        else:
            analysis.suggested_bump = VersionBumpType.PATCH
            analysis.confidence = 0.5

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

    def suggest_version_bump(self, commit_messages: List[str]) -> Tuple[VersionBumpType, float]:
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
                        self.logger.info(f"Updated version to {version_string} in {filename}")
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
            elif filename in ["pyproject.toml", "Cargo.toml"]:
                return self._update_toml_version(file_path, new_version)
            elif filename in ["VERSION", "version.txt"]:
                return self._update_simple_version_file(file_path, new_version)
            elif filename == "pom.xml":
                return self._update_pom_xml_version(file_path, new_version)

            return False

        except Exception as e:
            self.logger.error(f"Error updating {filename}: {e}")
            return False

    def _update_package_json_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in package.json."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            data["version"] = new_version

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except Exception:
            return False

    def _update_toml_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in TOML file."""
        try:
            with open(file_path, "r") as f:
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
            with open(file_path, "r") as f:
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

            if any(re.search(pattern, change_lower) for pattern in self.breaking_change_patterns):
                breaking_changes.append(change)
            elif any(re.search(pattern, change_lower) for pattern in self.feature_patterns):
                features.append(change)
            elif any(re.search(pattern, change_lower) for pattern in self.bug_fix_patterns):
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
        self, version: SemanticVersion, changes: List[str], changelog_file: str = "docs/CHANGELOG.md"
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
                with open(changelog_path, "r") as f:
                    existing_content = f.read()

                # Insert new entry after title
                lines = existing_content.split("\n")
                insert_index = 0

                # Find insertion point (after # Changelog title)
                for i, line in enumerate(lines):
                    if line.startswith("# ") or line.startswith("## [Unreleased]"):
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
        Get version history from changelog or Git tags.

        Returns:
            List of versions in descending order
        """
        versions = []

        # Try to get versions from changelog
        changelog_path = self.project_root / "docs" / "CHANGELOG.md"
        if changelog_path.exists():
            versions.extend(self._parse_changelog_versions(changelog_path))

        # TODO: Add Git tag parsing if needed

        # Sort versions in descending order
        versions.sort(reverse=True)
        return versions

    def _parse_changelog_versions(self, changelog_path: Path) -> List[SemanticVersion]:
        """Parse versions from changelog file."""
        versions = []

        try:
            with open(changelog_path, "r") as f:
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
