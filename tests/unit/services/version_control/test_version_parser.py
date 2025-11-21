"""Comprehensive unit tests for Enhanced Version Parser.

This test suite provides complete coverage of the EnhancedVersionParser class,
testing multi-source version parsing, caching, validation, and fallback mechanisms.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All error paths tested
- All edge cases covered

Based on: tests/unit/services/cli/test_session_resume_helper.py (Gold Standard)
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from claude_mpm.services.version_control.version_parser import (
    EnhancedVersionParser,
    VersionMetadata,
    VersionSource,
    get_version_parser,
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
def version_parser(temp_project_dir):
    """Create EnhancedVersionParser instance."""
    return EnhancedVersionParser(temp_project_dir, cache_ttl=300)


@pytest.fixture
def sample_version_metadata():
    """Create sample version metadata."""
    return VersionMetadata(
        version="1.2.3",
        source=VersionSource.GIT_TAGS,
        release_date=datetime.now(timezone.utc),
        commit_hash="abc123",
        author="Test Author",
        message="Release v1.2.3",
    )


# ============================================================================
# TEST VERSION SOURCE ENUMERATION
# ============================================================================


class TestVersionSource:
    """Tests for VersionSource enumeration."""

    def test_version_source_constants_defined(self):
        """Test that all version sources are defined."""
        # Arrange & Act & Assert
        assert VersionSource.GIT_TAGS == "git_tags"
        assert VersionSource.CHANGELOG == "changelog"
        assert VersionSource.VERSION_FILE == "version_file"
        assert VersionSource.PACKAGE_JSON == "package_json"
        assert VersionSource.PYPROJECT_TOML == "pyproject_toml"
        assert VersionSource.SETUP_PY == "setup_py"

    def test_priority_order_defined(self):
        """Test that priority order is defined."""
        # Arrange & Act & Assert
        assert len(VersionSource.PRIORITY_ORDER) == 6
        assert VersionSource.PRIORITY_ORDER[0] == VersionSource.GIT_TAGS
        assert VersionSource.PRIORITY_ORDER[-1] == VersionSource.SETUP_PY


# ============================================================================
# TEST VERSION METADATA CLASS
# ============================================================================


class TestVersionMetadataClass:
    """Tests for VersionMetadata class."""

    def test_init_with_minimal_data(self):
        """Test initialization with minimal data."""
        # Arrange & Act
        metadata = VersionMetadata(version="1.2.3", source=VersionSource.GIT_TAGS)

        # Assert
        assert metadata.version == "1.2.3"
        assert metadata.source == VersionSource.GIT_TAGS
        assert metadata.release_date is not None
        assert metadata.commit_hash is None
        assert metadata.changes == []

    def test_init_with_full_data(self):
        """Test initialization with complete data."""
        # Arrange
        release_date = datetime.now(timezone.utc)
        changes = ["Added feature", "Fixed bug"]

        # Act
        metadata = VersionMetadata(
            version="1.2.3",
            source=VersionSource.CHANGELOG,
            release_date=release_date,
            commit_hash="abc123",
            author="Test Author",
            message="Release notes",
            changes=changes,
        )

        # Assert
        assert metadata.commit_hash == "abc123"
        assert metadata.author == "Test Author"
        assert metadata.changes == changes

    def test_to_dict_conversion(self, sample_version_metadata):
        """Test converting metadata to dictionary."""
        # Arrange & Act
        result = sample_version_metadata.to_dict()

        # Assert
        assert result["version"] == "1.2.3"
        assert result["source"] == VersionSource.GIT_TAGS
        assert result["commit_hash"] == "abc123"
        assert result["author"] == "Test Author"
        assert isinstance(result["release_date"], str)


# ============================================================================
# TEST ENHANCED VERSION PARSER INITIALIZATION
# ============================================================================


class TestEnhancedVersionParserInitialization:
    """Tests for EnhancedVersionParser initialization."""

    def test_init_with_explicit_path(self, temp_project_dir):
        """Test initialization with explicit project path."""
        # Arrange & Act
        parser = EnhancedVersionParser(temp_project_dir)

        # Assert
        assert parser.project_root == temp_project_dir
        assert parser.cache_ttl == 300

    def test_init_with_default_path(self):
        """Test initialization with default (current) path."""
        # Arrange & Act
        parser = EnhancedVersionParser()

        # Assert
        assert parser.project_root == Path.cwd()

    def test_init_with_custom_cache_ttl(self, temp_project_dir):
        """Test initialization with custom cache TTL."""
        # Arrange & Act
        parser = EnhancedVersionParser(temp_project_dir, cache_ttl=600)

        # Assert
        assert parser.cache_ttl == 600

    def test_init_compiles_regex_patterns(self, version_parser):
        """Test that regex patterns are compiled on initialization."""
        # Arrange & Act & Assert
        assert version_parser._version_pattern is not None
        assert version_parser._changelog_version_pattern is not None


# ============================================================================
# TEST CACHING
# ============================================================================


class TestCaching:
    """Tests for caching functionality."""

    def test_get_cached_returns_none_for_missing_key(self, version_parser):
        """Test getting cached value for non-existent key."""
        # Arrange & Act
        result = version_parser._get_cached("nonexistent")

        # Assert
        assert result is None

    def test_set_and_get_cached_value(self, version_parser):
        """Test setting and getting cached value."""
        # Arrange
        test_value = {"version": "1.2.3"}

        # Act
        version_parser._set_cached("test_key", test_value)
        result = version_parser._get_cached("test_key")

        # Assert
        assert result == test_value

    def test_cached_value_expires_after_ttl(self, version_parser):
        """Test that cached values expire after TTL."""
        # Arrange
        version_parser.cache_ttl = 0  # Instant expiration
        test_value = {"version": "1.2.3"}

        # Act
        version_parser._set_cached("test_key", test_value)
        # Cache should expire immediately
        result = version_parser._get_cached("test_key")

        # Assert
        assert result is None

    def test_set_cached_returns_value(self, version_parser):
        """Test that _set_cached returns the cached value."""
        # Arrange
        test_value = {"version": "1.2.3"}

        # Act
        result = version_parser._set_cached("test_key", test_value)

        # Assert
        assert result == test_value


# ============================================================================
# TEST VERSION PARSING FROM GIT
# ============================================================================


class TestGitVersionParsing:
    """Tests for parsing versions from Git tags."""

    @patch("subprocess.run")
    def test_get_version_from_git_latest(self, mock_run, version_parser):
        """Test getting latest version from git tags."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="v1.2.3\n"),  # git describe --tags
            Mock(returncode=0, stdout="abc123\n"),  # git rev-list
        ]

        # Act
        version = version_parser._get_version_from_git(latest_only=True)

        # Assert
        assert version is not None
        assert version.version == "1.2.3"
        assert version.source == VersionSource.GIT_TAGS

    @patch("subprocess.run")
    def test_parse_git_tag_with_v_prefix(self, mock_run, version_parser):
        """Test parsing git tag with 'v' prefix."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="abc123\n")

        # Act
        metadata = version_parser._parse_git_tag("v1.2.3")

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"

    @patch("subprocess.run")
    def test_parse_git_tag_with_date_and_message(self, mock_run, version_parser):
        """Test parsing git tag with date and message."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="abc123\n")
        date_str = "2023-06-15 10:00:00 +0000"

        # Act
        metadata = version_parser._parse_git_tag("v1.2.3", date_str, "Release v1.2.3")

        # Assert
        assert metadata.version == "1.2.3"
        assert metadata.message == "Release v1.2.3"
        assert metadata.release_date is not None

    @patch("subprocess.run")
    def test_parse_git_tag_invalid_version_returns_none(self, mock_run, version_parser):
        """Test parsing invalid git tag returns None."""
        # Arrange
        mock_run.return_value = Mock(returncode=0, stdout="abc123\n")

        # Act
        metadata = version_parser._parse_git_tag("invalid-tag")

        # Assert
        assert metadata is None

    @patch("subprocess.run")
    def test_get_all_versions_from_git(self, mock_run, version_parser):
        """Test getting all versions from git tags."""
        # Arrange
        git_output = (
            "v1.2.3|2023-06-15 10:00:00 +0000|Release v1.2.3\n"
            "v1.2.2|2023-06-10 10:00:00 +0000|Release v1.2.2\n"
            "v1.2.1|2023-06-05 10:00:00 +0000|Release v1.2.1\n"
        )
        mock_run.return_value = Mock(returncode=0, stdout=git_output)

        # Mock git rev-list for commit hashes
        with patch("subprocess.run") as mock_rev_list:
            mock_rev_list.return_value = Mock(returncode=0, stdout="abc123\n")

            # Act
            versions = version_parser._get_all_versions_from_git()

        # Assert
        assert len(versions) == 3
        assert versions[0].version == "1.2.3"
        assert versions[2].version == "1.2.1"

    @patch("subprocess.run")
    def test_get_version_from_git_handles_no_tags(self, mock_run, version_parser):
        """Test getting version from git when no tags exist."""
        # Arrange
        mock_run.return_value = Mock(returncode=1, stderr="No tags found")

        # Act
        version = version_parser._get_version_from_git()

        # Assert
        assert version is None


# ============================================================================
# TEST VERSION PARSING FROM FILES
# ============================================================================


class TestFileVersionParsing:
    """Tests for parsing versions from files."""

    def test_get_version_from_file(self, version_parser, temp_project_dir):
        """Test getting version from VERSION file."""
        # Arrange
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.2.3\n")

        # Act
        metadata = version_parser._get_version_from_file()

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"
        assert metadata.source == VersionSource.VERSION_FILE

    def test_get_version_from_file_missing_file(self, version_parser):
        """Test getting version when VERSION file doesn't exist."""
        # Arrange & Act
        metadata = version_parser._get_version_from_file()

        # Assert
        assert metadata is None

    def test_get_version_from_package_json(self, version_parser, temp_project_dir):
        """Test getting version from package.json."""
        # Arrange
        package_json = temp_project_dir / "package.json"
        package_json.write_text('{"version": "1.2.3"}')

        # Act
        metadata = version_parser._get_version_from_package_json()

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"
        assert metadata.source == VersionSource.PACKAGE_JSON

    def test_get_version_from_package_json_invalid(
        self, version_parser, temp_project_dir
    ):
        """Test getting version from invalid package.json."""
        # Arrange
        package_json = temp_project_dir / "package.json"
        package_json.write_text("invalid json")

        # Act
        metadata = version_parser._get_version_from_package_json()

        # Assert
        assert metadata is None

    def test_get_version_from_pyproject(self, version_parser, temp_project_dir):
        """Test getting version from pyproject.toml."""
        # Arrange
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.3"\n')

        # Act
        metadata = version_parser._get_version_from_pyproject()

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"
        assert metadata.source == VersionSource.PYPROJECT_TOML

    def test_get_version_from_pyproject_poetry_section(
        self, version_parser, temp_project_dir
    ):
        """Test getting version from pyproject.toml poetry section."""
        # Arrange
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.poetry]\nversion = "1.2.3"\n')

        # Act
        metadata = version_parser._get_version_from_pyproject()

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"


# ============================================================================
# TEST VERSION PARSING FROM CHANGELOG
# ============================================================================


class TestChangelogVersionParsing:
    """Tests for parsing versions from changelog."""

    def test_get_versions_from_changelog(self, version_parser, temp_project_dir):
        """Test getting versions from CHANGELOG.md."""
        # Arrange
        changelog = temp_project_dir / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n"
            "## [1.2.3] - 2023-06-15\n"
            "- Added feature X\n"
            "- Fixed bug Y\n\n"
            "## [1.2.2] - 2023-06-10\n"
            "- Fixed bug Z\n"
        )

        # Act
        versions = version_parser._get_versions_from_changelog()

        # Assert
        assert len(versions) == 2
        assert versions[0].version == "1.2.3"
        assert versions[1].version == "1.2.2"

    def test_get_versions_from_changelog_with_changes(
        self, version_parser, temp_project_dir
    ):
        """Test extracting changes from changelog."""
        # Arrange
        changelog = temp_project_dir / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n## [1.2.3] - 2023-06-15\n- Added feature X\n- Fixed bug Y\n"
        )

        # Act
        versions = version_parser._get_versions_from_changelog()

        # Assert
        assert len(versions[0].changes) == 2
        assert "Added feature X" in versions[0].changes[0]
        assert "Fixed bug Y" in versions[0].changes[1]

    def test_get_versions_from_changelog_alternate_path(
        self, version_parser, temp_project_dir
    ):
        """Test getting versions from docs/CHANGELOG.md."""
        # Arrange
        docs_dir = temp_project_dir / "docs"
        docs_dir.mkdir()
        changelog = docs_dir / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## [1.2.3] - 2023-06-15\n- Feature\n")

        # Act
        versions = version_parser._get_versions_from_changelog()

        # Assert
        assert len(versions) == 1
        assert versions[0].version == "1.2.3"

    def test_extract_changelog_changes(self, version_parser):
        """Test extracting change entries from changelog section."""
        # Arrange
        content = (
            "## [1.2.3] - 2023-06-15\n"
            "- Added feature X\n"
            "- Fixed bug Y\n"
            "  with additional details\n"
            "- Updated docs\n"
            "\n"
            "## [1.2.2] - 2023-06-10\n"
        )

        # Act
        changes = version_parser._extract_changelog_changes(content, 0)

        # Assert
        assert len(changes) >= 3
        assert "Added feature X" in changes[0]


# ============================================================================
# TEST CURRENT VERSION DETECTION
# ============================================================================


class TestCurrentVersionDetection:
    """Tests for current version detection."""

    @patch("subprocess.run")
    def test_get_current_version_from_git(self, mock_run, version_parser):
        """Test getting current version from git tags."""
        # Arrange
        mock_run.side_effect = [
            Mock(returncode=0, stdout="v1.2.3\n"),  # git describe
            Mock(returncode=0, stdout="abc123\n"),  # git rev-list
        ]

        # Act
        metadata = version_parser.get_current_version()

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"
        assert metadata.source == VersionSource.GIT_TAGS

    def test_get_current_version_from_file_fallback(
        self, version_parser, temp_project_dir
    ):
        """Test getting current version falls back to VERSION file."""
        # Arrange
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.2.3\n")

        # Act
        metadata = version_parser.get_current_version()

        # Assert
        assert metadata is not None
        assert metadata.version == "1.2.3"

    def test_get_current_version_with_preferred_source(
        self, version_parser, temp_project_dir
    ):
        """Test getting current version with preferred source."""
        # Arrange
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.2.3\n")

        # Act
        metadata = version_parser.get_current_version(
            prefer_source=VersionSource.VERSION_FILE
        )

        # Assert
        assert metadata is not None
        assert metadata.source == VersionSource.VERSION_FILE

    def test_get_current_version_uses_cache(self, version_parser, temp_project_dir):
        """Test that get_current_version uses cache."""
        # Arrange
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.2.3\n")

        # Act
        metadata1 = version_parser.get_current_version()
        metadata2 = version_parser.get_current_version()

        # Assert
        assert metadata1 is metadata2  # Same object from cache


# ============================================================================
# TEST VERSION HISTORY
# ============================================================================


class TestVersionHistory:
    """Tests for version history retrieval."""

    @patch("subprocess.run")
    def test_get_version_history(self, mock_run, version_parser):
        """Test getting version history from git tags."""
        # Arrange
        git_output = (
            "v1.2.3|2023-06-15 10:00:00 +0000|Release v1.2.3\n"
            "v1.2.2|2023-06-10 10:00:00 +0000|Release v1.2.2\n"
        )
        mock_run.return_value = Mock(returncode=0, stdout=git_output)

        with patch("subprocess.run") as mock_rev_list:
            mock_rev_list.return_value = Mock(returncode=0, stdout="abc123\n")

            # Act
            versions = version_parser.get_version_history()

        # Assert
        assert len(versions) == 2
        assert versions[0].version == "1.2.3"
        assert versions[1].version == "1.2.2"

    def test_get_version_history_excludes_prereleases(
        self, version_parser, temp_project_dir
    ):
        """Test version history excludes prereleases by default."""
        # Arrange
        changelog = temp_project_dir / "CHANGELOG.md"
        changelog.write_text(
            "## [1.2.3] - 2023-06-15\n- Release\n\n"
            "## [1.2.3-alpha.1] - 2023-06-10\n- Prerelease\n"
        )

        # Act
        versions = version_parser.get_version_history(include_prereleases=False)

        # Assert
        assert len(versions) == 1
        assert versions[0].version == "1.2.3"

    def test_get_version_history_includes_prereleases(
        self, version_parser, temp_project_dir
    ):
        """Test version history includes prereleases when requested."""
        # Arrange
        changelog = temp_project_dir / "CHANGELOG.md"
        changelog.write_text(
            "## [1.2.3] - 2023-06-15\n- Release\n\n"
            "## [1.2.3-alpha.1] - 2023-06-10\n- Prerelease\n"
        )

        # Act
        versions = version_parser.get_version_history(include_prereleases=True)

        # Assert
        assert len(versions) == 2

    def test_get_version_history_with_limit(self, version_parser, temp_project_dir):
        """Test version history respects limit."""
        # Arrange
        changelog = temp_project_dir / "CHANGELOG.md"
        changelog.write_text(
            "## [1.2.3] - 2023-06-15\n- Release\n\n"
            "## [1.2.2] - 2023-06-10\n- Release\n\n"
            "## [1.2.1] - 2023-06-05\n- Release\n"
        )

        # Act
        versions = version_parser.get_version_history(limit=2)

        # Assert
        assert len(versions) == 2


# ============================================================================
# TEST PRERELEASE DETECTION
# ============================================================================


class TestPrereleaseDetection:
    """Tests for prerelease version detection."""

    def test_is_prerelease_alpha(self, version_parser):
        """Test detecting alpha prerelease."""
        # Arrange & Act & Assert
        assert version_parser._is_prerelease("1.2.3-alpha.1") is True

    def test_is_prerelease_beta(self, version_parser):
        """Test detecting beta prerelease."""
        # Arrange & Act & Assert
        assert version_parser._is_prerelease("1.2.3-beta.2") is True

    def test_is_prerelease_rc(self, version_parser):
        """Test detecting release candidate."""
        # Arrange & Act & Assert
        assert version_parser._is_prerelease("1.2.3-rc.1") is True

    def test_is_prerelease_false_for_release(self, version_parser):
        """Test release version is not prerelease."""
        # Arrange & Act & Assert
        assert version_parser._is_prerelease("1.2.3") is False


# ============================================================================
# TEST SEMANTIC VERSION PARSING
# ============================================================================


class TestSemanticVersionParsing:
    """Tests for semantic version parsing."""

    def test_parse_semver_basic(self, version_parser):
        """Test parsing basic semantic version."""
        # Arrange & Act
        result = version_parser._parse_semver("1.2.3")

        # Assert
        assert result == (1, 2, 3, "", "")

    def test_parse_semver_with_prerelease(self, version_parser):
        """Test parsing version with prerelease."""
        # Arrange & Act
        result = version_parser._parse_semver("1.2.3-alpha.1")

        # Assert
        assert result == (1, 2, 3, "alpha.1", "")

    def test_parse_semver_with_build(self, version_parser):
        """Test parsing version with build metadata."""
        # Arrange & Act
        result = version_parser._parse_semver("1.2.3+build.123")

        # Assert
        assert result == (1, 2, 3, "", "build.123")

    def test_parse_semver_invalid_returns_zeros(self, version_parser):
        """Test parsing invalid version returns zeros."""
        # Arrange & Act
        result = version_parser._parse_semver("invalid")

        # Assert
        assert result == (0, 0, 0, "", "")


# ============================================================================
# TEST VERSION VALIDATION
# ============================================================================


class TestVersionValidation:
    """Tests for version validation."""

    def test_validate_version_consistency(self, version_parser, temp_project_dir):
        """Test validating version consistency across sources."""
        # Arrange
        (temp_project_dir / "VERSION").write_text("1.2.3\n")
        (temp_project_dir / "package.json").write_text('{"version": "1.2.3"}')

        # Act
        versions = version_parser.validate_version_consistency()

        # Assert
        assert versions[VersionSource.VERSION_FILE] == "1.2.3"
        assert versions[VersionSource.PACKAGE_JSON] == "1.2.3"


# ============================================================================
# TEST CONVENIENCE FUNCTIONS
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_version_parser_singleton(self, temp_project_dir):
        """Test that get_version_parser returns singleton."""
        # Arrange & Act
        parser1 = get_version_parser(temp_project_dir)
        parser2 = get_version_parser(temp_project_dir)

        # Assert
        assert parser1 is parser2

    def test_get_version_for_release_prefers_git(
        self, version_parser, temp_project_dir
    ):
        """Test get_version_for_release prefers git tags."""
        # Arrange
        (temp_project_dir / "VERSION").write_text("1.0.0\n")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="v1.2.3\n"),  # git describe
                Mock(returncode=0, stdout="abc123\n"),  # git rev-list
            ]

            # Act
            version = version_parser.get_version_for_release()

        # Assert
        assert version == "1.2.3"

    def test_get_version_for_release_falls_back_to_file(
        self, version_parser, temp_project_dir
    ):
        """Test get_version_for_release falls back to VERSION file."""
        # Arrange
        (temp_project_dir / "VERSION").write_text("1.2.3\n")

        # Act
        version = version_parser.get_version_for_release()

        # Assert
        assert version == "1.2.3"
