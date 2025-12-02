"""Comprehensive unit tests for Semantic Versioning service.

This test suite provides complete coverage of the semantic versioning module,
testing version parsing, bumping, changelog generation, and version management.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All error paths tested
- All edge cases covered

Based on: tests/unit/services/cli/test_session_resume_helper.py (Gold Standard)
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from claude_mpm.services.version_control.semantic_versioning import (
    ChangeAnalysis,
    SemanticVersion,
    SemanticVersionManager,
    VersionBumpType,
    VersionMetadata,
)

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def version_manager(temp_project_dir, mock_logger):
    """Create SemanticVersionManager instance."""
    return SemanticVersionManager(str(temp_project_dir), mock_logger)


@pytest.fixture
def sample_version():
    """Create sample semantic version."""
    return SemanticVersion(1, 2, 3)


@pytest.fixture
def sample_version_with_prerelease():
    """Create sample semantic version with prerelease."""
    return SemanticVersion(1, 2, 3, prerelease="alpha.1")


@pytest.fixture
def sample_version_with_build():
    """Create sample semantic version with build metadata."""
    return SemanticVersion(1, 2, 3, build="20230615")


# ============================================================================
# TEST SEMANTIC VERSION CLASS
# ============================================================================


class TestSemanticVersion:
    """Tests for SemanticVersion class."""

    def test_init_with_basic_version(self):
        """Test initialization with basic version."""
        # Arrange & Act
        version = SemanticVersion(1, 2, 3)

        # Assert
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease is None
        assert version.build is None

    def test_init_with_prerelease(self):
        """Test initialization with prerelease."""
        # Arrange & Act
        version = SemanticVersion(1, 2, 3, prerelease="alpha.1")

        # Assert
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha.1"
        assert version.build is None

    def test_init_with_build_metadata(self):
        """Test initialization with build metadata."""
        # Arrange & Act
        version = SemanticVersion(1, 2, 3, build="20230615")

        # Assert
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease is None
        assert version.build == "20230615"

    def test_str_basic_version(self, sample_version):
        """Test string representation of basic version."""
        # Arrange & Act
        result = str(sample_version)

        # Assert
        assert result == "1.2.3"

    def test_str_version_with_prerelease(self, sample_version_with_prerelease):
        """Test string representation with prerelease."""
        # Arrange & Act
        result = str(sample_version_with_prerelease)

        # Assert
        assert result == "1.2.3-alpha.1"

    def test_str_version_with_build(self, sample_version_with_build):
        """Test string representation with build metadata."""
        # Arrange & Act
        result = str(sample_version_with_build)

        # Assert
        assert result == "1.2.3+20230615"

    def test_str_full_version(self):
        """Test string representation with all components."""
        # Arrange
        version = SemanticVersion(1, 2, 3, prerelease="beta.2", build="build.123")

        # Act
        result = str(version)

        # Assert
        assert result == "1.2.3-beta.2+build.123"

    def test_comparison_major_version_difference(self):
        """Test comparison with different major versions."""
        # Arrange
        version1 = SemanticVersion(1, 0, 0)
        version2 = SemanticVersion(2, 0, 0)

        # Act & Assert
        assert version1 < version2
        assert version2 > version1

    def test_comparison_minor_version_difference(self):
        """Test comparison with different minor versions."""
        # Arrange
        version1 = SemanticVersion(1, 2, 0)
        version2 = SemanticVersion(1, 3, 0)

        # Act & Assert
        assert version1 < version2
        assert version2 > version1

    def test_comparison_patch_version_difference(self):
        """Test comparison with different patch versions."""
        # Arrange
        version1 = SemanticVersion(1, 2, 3)
        version2 = SemanticVersion(1, 2, 4)

        # Act & Assert
        assert version1 < version2
        assert version2 > version1

    def test_comparison_prerelease_lower_than_release(self):
        """Test that prerelease versions are lower than release versions."""
        # Arrange
        prerelease = SemanticVersion(1, 2, 3, prerelease="alpha.1")
        release = SemanticVersion(1, 2, 3)

        # Act & Assert
        assert prerelease < release
        assert release > prerelease

    def test_comparison_prerelease_alphanumeric(self):
        """Test alphanumeric comparison of prerelease versions."""
        # Arrange
        alpha = SemanticVersion(1, 2, 3, prerelease="alpha.1")
        beta = SemanticVersion(1, 2, 3, prerelease="beta.1")

        # Act & Assert
        assert alpha < beta

    def test_comparison_build_metadata_ignored(self):
        """Test that build metadata is ignored in comparison."""
        # Arrange
        version1 = SemanticVersion(1, 2, 3, build="build.1")
        version2 = SemanticVersion(1, 2, 3, build="build.2")

        # Act & Assert
        assert not (version1 < version2)
        assert not (version2 < version1)

    def test_bump_major_version(self, sample_version):
        """Test bumping major version."""
        # Arrange & Act
        new_version = sample_version.bump(VersionBumpType.MAJOR)

        # Assert
        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0
        assert new_version.prerelease is None

    def test_bump_minor_version(self, sample_version):
        """Test bumping minor version."""
        # Arrange & Act
        new_version = sample_version.bump(VersionBumpType.MINOR)

        # Assert
        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0
        assert new_version.prerelease is None

    def test_bump_patch_version(self, sample_version):
        """Test bumping patch version."""
        # Arrange & Act
        new_version = sample_version.bump(VersionBumpType.PATCH)

        # Assert
        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4
        assert new_version.prerelease is None

    def test_bump_prerelease_from_release(self, sample_version):
        """Test bumping to prerelease from release version."""
        # Arrange & Act
        new_version = sample_version.bump(VersionBumpType.PRERELEASE)

        # Assert
        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 3
        assert new_version.prerelease == "alpha.1"

    def test_bump_prerelease_increment_number(self):
        """Test incrementing existing prerelease number."""
        # Arrange
        version = SemanticVersion(1, 2, 3, prerelease="alpha.1")

        # Act
        new_version = version.bump(VersionBumpType.PRERELEASE)

        # Assert
        assert new_version.prerelease == "alpha.2"

    def test_bump_prerelease_add_number_if_missing(self):
        """Test adding number to prerelease without number."""
        # Arrange
        version = SemanticVersion(1, 2, 3, prerelease="alpha")

        # Act
        new_version = version.bump(VersionBumpType.PRERELEASE)

        # Assert
        assert new_version.prerelease == "alpha.1"

    def test_bump_prerelease_with_beta(self):
        """Test bumping beta prerelease."""
        # Arrange
        version = SemanticVersion(1, 2, 3, prerelease="beta.5")

        # Act
        new_version = version.bump(VersionBumpType.PRERELEASE)

        # Assert
        assert new_version.prerelease == "beta.6"


# ============================================================================
# TEST VERSION METADATA
# ============================================================================


class TestVersionMetadata:
    """Tests for VersionMetadata class."""

    def test_init_with_minimal_data(self):
        """Test initialization with minimal data."""
        # Arrange
        version = SemanticVersion(1, 2, 3)
        release_date = datetime.now(timezone.utc)

        # Act
        metadata = VersionMetadata(version=version, release_date=release_date)

        # Assert
        assert metadata.version == version
        assert metadata.release_date == release_date
        assert metadata.commit_hash is None
        assert metadata.tag_name is None
        assert metadata.changes == []
        assert metadata.breaking_changes == []
        assert metadata.contributors == []
        assert metadata.notes is None

    def test_init_with_full_data(self):
        """Test initialization with complete data."""
        # Arrange
        version = SemanticVersion(1, 2, 3)
        release_date = datetime.now(timezone.utc)
        changes = ["Added feature X", "Fixed bug Y"]
        breaking_changes = ["Removed API endpoint Z"]
        contributors = ["John Doe", "Jane Smith"]

        # Act
        metadata = VersionMetadata(
            version=version,
            release_date=release_date,
            commit_hash="abc123",
            tag_name="v1.2.3",
            changes=changes,
            breaking_changes=breaking_changes,
            contributors=contributors,
            notes="Important release notes",
        )

        # Assert
        assert metadata.commit_hash == "abc123"
        assert metadata.tag_name == "v1.2.3"
        assert metadata.changes == changes
        assert metadata.breaking_changes == breaking_changes
        assert metadata.contributors == contributors
        assert metadata.notes == "Important release notes"


# ============================================================================
# TEST CHANGE ANALYSIS
# ============================================================================


class TestChangeAnalysis:
    """Tests for ChangeAnalysis class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        # Arrange & Act
        analysis = ChangeAnalysis()

        # Assert
        assert analysis.has_breaking_changes is False
        assert analysis.has_new_features is False
        assert analysis.has_bug_fixes is False
        assert analysis.change_descriptions == []
        assert analysis.suggested_bump == VersionBumpType.PATCH
        assert analysis.confidence == 0.0


# ============================================================================
# TEST SEMANTIC VERSION MANAGER - INITIALIZATION
# ============================================================================


class TestSemanticVersionManagerInitialization:
    """Tests for SemanticVersionManager initialization."""

    def test_init_with_valid_path(self, temp_project_dir, mock_logger):
        """Test initialization with valid project path."""
        # Arrange & Act
        manager = SemanticVersionManager(str(temp_project_dir), mock_logger)

        # Assert
        assert manager.project_root == temp_project_dir
        assert manager.logger == mock_logger
        assert manager.config_mgr is not None
        assert len(manager.version_files) > 0

    def test_init_version_files_registered(self, version_manager):
        """Test that all version file parsers are registered."""
        # Arrange & Act & Assert
        assert "package.json" in version_manager.version_files
        assert "pyproject.toml" in version_manager.version_files
        assert "Cargo.toml" in version_manager.version_files
        assert "VERSION" in version_manager.version_files
        assert "version.txt" in version_manager.version_files
        assert "pom.xml" in version_manager.version_files

    def test_init_change_patterns_defined(self, version_manager):
        """Test that change analysis patterns are defined."""
        # Arrange & Act & Assert
        assert len(version_manager.breaking_change_patterns) > 0
        assert len(version_manager.feature_patterns) > 0
        assert len(version_manager.bug_fix_patterns) > 0


# ============================================================================
# TEST VERSION PARSING
# ============================================================================


class TestVersionParsing:
    """Tests for version string parsing."""

    def test_parse_basic_version(self, version_manager):
        """Test parsing basic semantic version."""
        # Arrange & Act
        version = version_manager.parse_version("1.2.3")

        # Assert
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_version_with_v_prefix(self, version_manager):
        """Test parsing version with 'v' prefix."""
        # Arrange & Act
        version = version_manager.parse_version("v1.2.3")

        # Assert
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_version_with_prerelease(self, version_manager):
        """Test parsing version with prerelease."""
        # Arrange & Act
        version = version_manager.parse_version("1.2.3-alpha.1")

        # Assert
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha.1"

    def test_parse_version_with_build(self, version_manager):
        """Test parsing version with build metadata."""
        # Arrange & Act
        version = version_manager.parse_version("1.2.3+build.123")

        # Assert
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.build == "build.123"

    def test_parse_full_version(self, version_manager):
        """Test parsing version with all components."""
        # Arrange & Act
        version = version_manager.parse_version("v1.2.3-beta.2+build.456")

        # Assert
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "beta.2"
        assert version.build == "build.456"

    def test_parse_invalid_version_returns_none(self, version_manager):
        """Test parsing invalid version returns None."""
        # Arrange & Act
        version = version_manager.parse_version("invalid")

        # Assert
        assert version is None

    def test_parse_version_with_whitespace(self, version_manager):
        """Test parsing version with whitespace."""
        # Arrange & Act
        version = version_manager.parse_version("  1.2.3  ")

        # Assert
        assert version is not None
        assert version.major == 1

    def test_parse_version_handles_exception(self, version_manager, mock_logger):
        """Test parsing handles exceptions gracefully."""
        # Arrange
        version_manager.logger = mock_logger

        # Act
        version = version_manager.parse_version(None)

        # Assert
        assert version is None
        mock_logger.error.assert_called_once()


# ============================================================================
# TEST CHANGE ANALYSIS
# ============================================================================


class TestChangeAnalysisLogic:
    """Tests for change analysis logic."""

    def test_analyze_breaking_changes(self, version_manager):
        """Test analysis detects breaking changes."""
        # Arrange
        changes = [
            "BREAKING CHANGE: removed old API",
            "Added new feature",
        ]

        # Act
        analysis = version_manager.analyze_changes(changes)

        # Assert
        assert analysis.has_breaking_changes is True
        assert analysis.suggested_bump == VersionBumpType.MAJOR
        assert analysis.confidence == 0.9

    def test_analyze_new_features(self, version_manager):
        """Test analysis detects new features."""
        # Arrange
        changes = [
            "Add user authentication",
            "Implement new dashboard",
        ]

        # Act
        analysis = version_manager.analyze_changes(changes)

        # Assert
        assert analysis.has_new_features is True
        assert analysis.suggested_bump == VersionBumpType.MINOR
        assert analysis.confidence == 0.8

    def test_analyze_bug_fixes(self, version_manager):
        """Test analysis detects bug fixes."""
        # Arrange
        changes = [
            "Fix login issue",
            "Resolve memory leak",
        ]

        # Act
        analysis = version_manager.analyze_changes(changes)

        # Assert
        assert analysis.has_bug_fixes is True
        assert analysis.suggested_bump == VersionBumpType.PATCH
        assert analysis.confidence == 0.7

    def test_analyze_mixed_changes_prioritizes_breaking(self, version_manager):
        """Test analysis prioritizes breaking changes."""
        # Arrange
        changes = [
            "breaking: remove API",
            "add: new feature",
            "fix: bug",
        ]

        # Act
        analysis = version_manager.analyze_changes(changes)

        # Assert
        assert analysis.suggested_bump == VersionBumpType.MAJOR

    def test_analyze_mixed_changes_features_over_fixes(self, version_manager):
        """Test analysis prioritizes features over fixes."""
        # Arrange
        changes = [
            "add new dashboard",
            "fix typo",
        ]

        # Act
        analysis = version_manager.analyze_changes(changes)

        # Assert
        assert analysis.suggested_bump == VersionBumpType.MINOR

    def test_analyze_no_clear_pattern_defaults_to_patch(self, version_manager):
        """Test analysis defaults to patch for unclear changes."""
        # Arrange
        changes = [
            "Update documentation",
            "Refactor code",
        ]

        # Act
        analysis = version_manager.analyze_changes(changes)

        # Assert
        assert analysis.suggested_bump == VersionBumpType.PATCH
        assert analysis.confidence == 0.5

    def test_analyze_empty_changes(self, version_manager):
        """Test analysis with empty changes list."""
        # Arrange & Act
        analysis = version_manager.analyze_changes([])

        # Assert
        assert analysis.suggested_bump == VersionBumpType.PATCH
        assert analysis.confidence == 0.5


# ============================================================================
# TEST VERSION BUMPING
# ============================================================================


class TestVersionBumping:
    """Tests for version bumping operations."""

    def test_bump_version_major(self, version_manager, sample_version):
        """Test bumping major version."""
        # Arrange & Act
        new_version = version_manager.bump_version(
            sample_version, VersionBumpType.MAJOR
        )

        # Assert
        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0

    def test_bump_version_minor(self, version_manager, sample_version):
        """Test bumping minor version."""
        # Arrange & Act
        new_version = version_manager.bump_version(
            sample_version, VersionBumpType.MINOR
        )

        # Assert
        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_bump_version_patch(self, version_manager, sample_version):
        """Test bumping patch version."""
        # Arrange & Act
        new_version = version_manager.bump_version(
            sample_version, VersionBumpType.PATCH
        )

        # Assert
        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4

    def test_suggest_version_bump_from_commits(self, version_manager):
        """Test suggesting version bump from commit messages."""
        # Arrange
        commits = [
            "feat: add authentication",
            "fix: resolve login bug",
        ]

        # Act
        bump_type, confidence = version_manager.suggest_version_bump(commits)

        # Assert
        assert bump_type == VersionBumpType.MINOR
        assert confidence == 0.8


# ============================================================================
# TEST CHANGELOG GENERATION
# ============================================================================


class TestChangelogGeneration:
    """Tests for changelog generation."""

    def test_generate_changelog_entry_basic(self, version_manager, sample_version):
        """Test generating basic changelog entry."""
        # Arrange
        changes = ["Add feature X", "Fix bug Y"]

        # Act
        entry = version_manager.generate_changelog_entry(sample_version, changes)

        # Assert
        assert "## [1.2.3]" in entry
        assert "Add feature X" in entry
        assert "Fix bug Y" in entry

    def test_generate_changelog_entry_categorizes_changes(
        self, version_manager, sample_version
    ):
        """Test changelog categorizes changes."""
        # Arrange
        changes = [
            "breaking: remove API",
            "add: new feature",
            "fix: bug",
        ]

        # Act
        entry = version_manager.generate_changelog_entry(sample_version, changes)

        # Assert
        assert "BREAKING CHANGES" in entry
        assert "Features" in entry
        assert "Bug Fixes" in entry

    def test_generate_changelog_entry_with_metadata(
        self, version_manager, sample_version
    ):
        """Test generating changelog with metadata."""
        # Arrange
        changes = ["Add feature"]
        metadata = VersionMetadata(
            version=sample_version,
            release_date=datetime.now(timezone.utc),
            commit_hash="abc123",
            contributors=["John Doe"],
        )

        # Act
        entry = version_manager.generate_changelog_entry(
            sample_version, changes, metadata
        )

        # Assert
        assert "abc123" in entry
        assert "John Doe" in entry

    def test_update_changelog_creates_new_file(
        self, version_manager, sample_version, temp_project_dir
    ):
        """Test updating changelog creates new file if it doesn't exist."""
        # Arrange
        changes = ["Add feature X"]
        changelog_path = "CHANGELOG.md"

        # Act
        result = version_manager.update_changelog(
            sample_version, changes, changelog_path
        )

        # Assert
        assert result is True
        changelog_file = temp_project_dir / changelog_path
        assert changelog_file.exists()

    def test_update_changelog_appends_to_existing(
        self, version_manager, sample_version, temp_project_dir
    ):
        """Test updating changelog appends to existing file."""
        # Arrange
        changelog_path = "CHANGELOG.md"
        changelog_file = temp_project_dir / changelog_path
        changelog_file.write_text(
            "# Changelog\n\n## [1.0.0] - 2023-01-01\n- Initial release\n"
        )
        changes = ["Add feature X"]

        # Act
        result = version_manager.update_changelog(
            sample_version, changes, changelog_path
        )

        # Assert
        assert result is True
        content = changelog_file.read_text()
        assert "## [1.2.3]" in content
        assert "## [1.0.0]" in content


# ============================================================================
# TEST FILE PARSING
# ============================================================================


class TestVersionFileParsing:
    """Tests for version file parsing."""

    def test_parse_package_json(self, version_manager, temp_project_dir):
        """Test parsing version from package.json."""
        # Arrange
        package_json = temp_project_dir / "package.json"
        package_json.write_text('{"version": "1.2.3"}')

        # Act
        version_string = version_manager._parse_package_json_version(package_json)

        # Assert
        assert version_string == "1.2.3"

    def test_parse_version_file(self, version_manager, temp_project_dir):
        """Test parsing version from VERSION file."""
        # Arrange
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.2.3\n")

        # Act
        version_string = version_manager._parse_version_file(version_file)

        # Assert
        assert version_string == "1.2.3"

    def test_parse_pyproject_toml_regex(self, version_manager, temp_project_dir):
        """Test parsing version from pyproject.toml using regex."""
        # Arrange
        pyproject_file = temp_project_dir / "pyproject.toml"
        pyproject_file.write_text('[project]\nversion = "1.2.3"\n')

        # Act
        version_string = version_manager._parse_toml_version_regex(pyproject_file)

        # Assert
        assert version_string == "1.2.3"


# ============================================================================
# TEST FILE UPDATING
# ============================================================================


class TestVersionFileUpdating:
    """Tests for version file updating."""

    def test_update_package_json_version(self, version_manager, temp_project_dir):
        """Test updating version in package.json."""
        # Arrange
        package_json = temp_project_dir / "package.json"
        package_json.write_text('{"version": "1.0.0"}')

        # Act
        result = version_manager._update_package_json_version(package_json, "1.2.3")

        # Assert
        assert result is True
        assert '"version": "1.2.3"' in package_json.read_text()

    def test_update_simple_version_file(self, version_manager, temp_project_dir):
        """Test updating simple VERSION file."""
        # Arrange
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.0.0\n")

        # Act
        result = version_manager._update_simple_version_file(version_file, "1.2.3")

        # Assert
        assert result is True
        assert version_file.read_text() == "1.2.3\n"

    def test_update_toml_version(self, version_manager, temp_project_dir):
        """Test updating version in TOML file."""
        # Arrange
        toml_file = temp_project_dir / "pyproject.toml"
        toml_file.write_text('[project]\nversion = "1.0.0"\n')

        # Act
        result = version_manager._update_toml_version(toml_file, "1.2.3")

        # Assert
        assert result is True
        assert 'version = "1.2.3"' in toml_file.read_text()

    def test_update_version_files_multiple(self, version_manager, temp_project_dir):
        """Test updating multiple version files."""
        # Arrange
        (temp_project_dir / "VERSION").write_text("1.0.0\n")
        (temp_project_dir / "package.json").write_text('{"version": "1.0.0"}')
        new_version = SemanticVersion(1, 2, 3)

        # Act
        results = version_manager.update_version_files(new_version)

        # Assert
        assert results["VERSION"] is True
        assert results["package.json"] is True
