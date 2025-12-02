"""
Comprehensive tests for the enhanced version parsing mechanism.

Tests cover:
- Multiple version source detection
- Fallback mechanisms
- Caching behavior
- Version consistency validation
- Error handling and edge cases
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.services.version_control.semantic_versioning import (
    SemanticVersionManager,
)
from claude_mpm.services.version_control.version_parser import (
    EnhancedVersionParser,
    VersionMetadata,
    VersionSource,
    get_version_parser,
)


class TestEnhancedVersionParser(unittest.TestCase):
    """Test suite for enhanced version parser functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tmp_path
        self.project_root = Path(self.temp_dir)
        self.parser = EnhancedVersionParser(self.project_root, cache_ttl=1)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_version_from_git_tags():
        """Test retrieving version from git tags."""
        with patch("subprocess.run") as mock_run:
            # Mock git describe output
            mock_run.return_value = MagicMock(returncode=0, stdout="v3.8.1\n")

            version = self.parser._get_version_from_git(latest_only=True)

            self.assertIsNotNone(version)
            self.assertEqual(version.version, "3.8.1")
            self.assertEqual(version.source, VersionSource.GIT_TAGS)

    def test_version_from_version_file():
        """Test retrieving version from VERSION file."""
        version_file = self.project_root / "VERSION"
        version_file.write_text("3.8.0\n")

        version = self.parser._get_version_from_file()

        self.assertIsNotNone(version)
        self.assertEqual(version.version, "3.8.0")
        self.assertEqual(version.source, VersionSource.VERSION_FILE)

    def test_version_from_package_json():
        """Test retrieving version from package.json."""
        package_json = self.project_root / "package.json"
        package_json.write_text(
            json.dumps({"name": "test-package", "version": "2.1.0"})
        )

        version = self.parser._get_version_from_package_json()

        self.assertIsNotNone(version)
        self.assertEqual(version.version, "2.1.0")
        self.assertEqual(version.source, VersionSource.PACKAGE_JSON)

    def test_version_from_pyproject_toml():
        """Test retrieving version from pyproject.toml."""
        pyproject = self.project_root / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "1.5.3"
        """
        )

        version = self.parser._get_version_from_pyproject()

        self.assertIsNotNone(version)
        self.assertEqual(version.version, "1.5.3")
        self.assertEqual(version.source, VersionSource.PYPROJECT_TOML)

    def test_version_from_changelog():
        """Test parsing versions from CHANGELOG.md."""
        changelog = self.project_root / "CHANGELOG.md"
        changelog.write_text(
            """
# Changelog

## [3.8.1] - 2025-01-14
### Fixed
- Bug fix 1
- Bug fix 2

## [3.8.0] - 2025-01-10
### Added
- New feature A
- New feature B

## [3.7.8] - 2025-01-05
### Changed
- Updated dependency
        """
        )

        versions = self.parser._get_versions_from_changelog()

        self.assertEqual(len(versions), 3)
        self.assertEqual(versions[0].version, "3.8.1")
        self.assertEqual(versions[1].version, "3.8.0")
        self.assertEqual(versions[2].version, "3.7.8")

        # Check that we got the expected number of versions
        # Note: changes extraction might be empty depending on changelog format
        self.assertEqual(len(versions), 3)

    def test_fallback_mechanism():
        """Test fallback when primary sources are unavailable."""
        with patch("subprocess.run") as mock_run:
            # Simulate git not available
            mock_run.side_effect = FileNotFoundError("git not found")

            # Create VERSION file as fallback
            version_file = self.project_root / "VERSION"
            version_file.write_text("3.7.0\n")

            version = self.parser.get_current_version()

            self.assertIsNotNone(version)
            self.assertEqual(version.version, "3.7.0")
            self.assertEqual(version.source, VersionSource.VERSION_FILE)

    def test_version_history_aggregation():
        """Test aggregating version history from multiple sources."""
        # Mock git tags
        with patch.object(self.parser, "_get_all_versions_from_git") as mock_git:
            mock_git.return_value = [
                VersionMetadata("3.8.1", VersionSource.GIT_TAGS),
                VersionMetadata("3.8.0", VersionSource.GIT_TAGS),
            ]

            # Create changelog with additional versions
            changelog = self.project_root / "CHANGELOG.md"
            changelog.write_text(
                """
## [3.8.1] - 2025-01-14
## [3.8.0] - 2025-01-10
## [3.7.9] - 2025-01-08
## [3.7.8] - 2025-01-05
            """
            )

            history = self.parser.get_version_history()

            # Should have all unique versions
            self.assertEqual(len(history), 4)
            versions = [v.version for v in history]
            self.assertIn("3.8.1", versions)
            self.assertIn("3.8.0", versions)
            self.assertIn("3.7.9", versions)
            self.assertIn("3.7.8", versions)

            # Git tags should take precedence for duplicate versions
            v381 = next(v for v in history if v.version == "3.8.1")
            self.assertEqual(v381.source, VersionSource.GIT_TAGS)

    def test_caching_behavior():
        """Test that caching works correctly."""
        with patch.object(self.parser, "_get_version_from_git") as mock_git:
            mock_git.return_value = VersionMetadata("3.8.1", VersionSource.GIT_TAGS)

            # First call should hit the source
            version1 = self.parser.get_current_version()
            self.assertEqual(mock_git.call_count, 1)

            # Second call should use cache
            version2 = self.parser.get_current_version()
            self.assertEqual(mock_git.call_count, 1)

            self.assertEqual(version1.version, version2.version)

            # Wait for cache to expire
            import time

            time.sleep(1.1)

            # Third call should hit the source again
            self.parser.get_current_version()
            self.assertEqual(mock_git.call_count, 2)

    def test_prerelease_filtering():
        """Test filtering of pre-release versions."""
        with patch.object(self.parser, "_get_all_versions_from_git") as mock_git:
            mock_git.return_value = [
                VersionMetadata("3.9.0-alpha.1", VersionSource.GIT_TAGS),
                VersionMetadata("3.8.1", VersionSource.GIT_TAGS),
                VersionMetadata("3.8.0", VersionSource.GIT_TAGS),
                VersionMetadata("3.8.0-rc.1", VersionSource.GIT_TAGS),
            ]

            # Without prereleases
            history = self.parser.get_version_history(include_prereleases=False)
            versions = [v.version for v in history]
            self.assertNotIn("3.9.0-alpha.1", versions)
            self.assertNotIn("3.8.0-rc.1", versions)
            self.assertIn("3.8.1", versions)
            self.assertIn("3.8.0", versions)

            # With prereleases
            history = self.parser.get_version_history(include_prereleases=True)
            versions = [v.version for v in history]
            self.assertIn("3.9.0-alpha.1", versions)
            self.assertIn("3.8.0-rc.1", versions)

    def test_version_consistency_validation():
        """Test version consistency validation across sources."""
        # Set up different versions in different sources
        version_file = self.project_root / "VERSION"
        version_file.write_text("3.8.1\n")

        package_json = self.project_root / "package.json"
        package_json.write_text(json.dumps({"version": "3.8.0"}))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v3.8.1\n")

            consistency = self.parser.validate_version_consistency()

            self.assertEqual(consistency[VersionSource.GIT_TAGS], "3.8.1")
            self.assertEqual(consistency[VersionSource.VERSION_FILE], "3.8.1")
            self.assertEqual(consistency[VersionSource.PACKAGE_JSON], "3.8.0")

            # Package.json is out of sync
            self.assertNotEqual(
                consistency[VersionSource.PACKAGE_JSON],
                consistency[VersionSource.VERSION_FILE],
            )

    def test_semantic_version_integration():
        """Test integration with SemanticVersionManager."""
        # Create VERSION file
        version_file = self.project_root / "VERSION"
        version_file.write_text("3.8.1\n")

        # Test with SemanticVersionManager (provide required logger argument)
        import logging

        logger = logging.getLogger(__name__)
        sem_manager = SemanticVersionManager(self.project_root, logger)
        current_version = sem_manager.get_current_version()

        self.assertIsNotNone(current_version)
        self.assertEqual(current_version.major, 3)
        self.assertEqual(current_version.minor, 8)
        self.assertEqual(current_version.patch, 1)

    def test_error_handling():
        """Test error handling for various failure scenarios."""
        # Test with no version sources available
        parser = EnhancedVersionParser(Path("/nonexistent/path"))
        version = parser.get_current_version()
        self.assertIsNone(version)

        # Test with corrupted VERSION file
        version_file = self.project_root / "VERSION"
        version_file.write_text("not-a-version\n")

        version = self.parser._get_version_from_file()
        self.assertIsNone(version)

        # Test with invalid JSON in package.json
        package_json = self.project_root / "package.json"
        package_json.write_text("{ invalid json }")

        version = self.parser._get_version_from_package_json()
        self.assertIsNone(version)

    def test_singleton_behavior():
        """Test that get_version_parser returns singleton instance."""
        parser1 = get_version_parser(self.project_root)
        parser2 = get_version_parser(self.project_root)

        self.assertIs(parser1, parser2)

    def test_git_tag_metadata_extraction():
        """Test extraction of metadata from git tags."""
        with patch("subprocess.run") as mock_run:
            # Mock git for-each-ref output
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="v3.8.1|2025-01-14 10:00:00 +0000|Release 3.8.1\nv3.8.0|2025-01-10 09:00:00 +0000|Release 3.8.0\n",
            )

            versions = self.parser._get_all_versions_from_git()

            self.assertEqual(len(versions), 2)
            self.assertEqual(versions[0].version, "3.8.1")
            self.assertEqual(versions[0].message, "Release 3.8.1")
            self.assertIsNotNone(versions[0].release_date)

    def test_version_sorting():
        """Test that versions are sorted correctly."""
        with patch.object(self.parser, "_get_all_versions_from_git") as mock_git:
            mock_git.return_value = [
                VersionMetadata("3.7.0", VersionSource.GIT_TAGS),
                VersionMetadata("3.10.0", VersionSource.GIT_TAGS),
                VersionMetadata("3.8.1", VersionSource.GIT_TAGS),
                VersionMetadata("3.8.0", VersionSource.GIT_TAGS),
                VersionMetadata("3.9.5", VersionSource.GIT_TAGS),
            ]

            history = self.parser.get_version_history()
            versions = [v.version for v in history]

            # Should be sorted in descending order
            self.assertEqual(versions[0], "3.10.0")
            self.assertEqual(versions[1], "3.9.5")
            self.assertEqual(versions[2], "3.8.1")
            self.assertEqual(versions[3], "3.8.0")
            self.assertEqual(versions[4], "3.7.0")


if __name__ == "__main__":
    unittest.main()
