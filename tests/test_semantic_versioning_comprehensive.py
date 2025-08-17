#!/usr/bin/env python3
"""
Comprehensive unit tests for Semantic Versioning module.

This test suite provides complete coverage for the semantic versioning
functionality including:
- SemanticVersion class and comparison logic
- Version parsing and validation
- Version bumping operations
- Change analysis and version suggestion
- File-based version management
- Error handling and edge cases
"""

import pytest
import tempfile
import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

# Import the classes we're testing
from claude_mpm.services.version_control.semantic_versioning import (
    SemanticVersion,
    SemanticVersionManager,
    VersionBumpType,
    VersionMetadata,
    ChangeAnalysis
)


class TestSemanticVersion:
    """Test SemanticVersion class functionality."""
    
    def test_semantic_version_creation(self):
        """Test creating SemanticVersion instances."""
        # Basic version
        version = SemanticVersion(1, 2, 3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease is None
        assert version.build is None
        
        # Version with prerelease
        version_pre = SemanticVersion(1, 2, 3, prerelease="alpha.1")
        assert version_pre.prerelease == "alpha.1"
        
        # Version with build
        version_build = SemanticVersion(1, 2, 3, build="build.123")
        assert version_build.build == "build.123"
        
        # Full version
        version_full = SemanticVersion(1, 2, 3, prerelease="beta.2", build="build.456")
        assert version_full.prerelease == "beta.2"
        assert version_full.build == "build.456"
    
    def test_semantic_version_string_representation(self):
        """Test string representation of SemanticVersion."""
        # Basic version
        version = SemanticVersion(1, 2, 3)
        assert str(version) == "1.2.3"
        
        # Version with prerelease
        version_pre = SemanticVersion(1, 2, 3, prerelease="alpha.1")
        assert str(version_pre) == "1.2.3-alpha.1"
        
        # Version with build
        version_build = SemanticVersion(1, 2, 3, build="build.123")
        assert str(version_build) == "1.2.3+build.123"
        
        # Full version
        version_full = SemanticVersion(1, 2, 3, prerelease="beta.2", build="build.456")
        assert str(version_full) == "1.2.3-beta.2+build.456"
    
    def test_semantic_version_comparison(self):
        """Test version comparison logic."""
        v1_0_0 = SemanticVersion(1, 0, 0)
        v1_0_1 = SemanticVersion(1, 0, 1)
        v1_1_0 = SemanticVersion(1, 1, 0)
        v2_0_0 = SemanticVersion(2, 0, 0)
        
        # Basic comparisons
        assert v1_0_0 < v1_0_1
        assert v1_0_1 < v1_1_0
        assert v1_1_0 < v2_0_0
        
        # Equality
        v1_0_0_copy = SemanticVersion(1, 0, 0)
        assert not (v1_0_0 < v1_0_0_copy)
        assert not (v1_0_0_copy < v1_0_0)
    
    def test_semantic_version_prerelease_comparison(self):
        """Test prerelease version comparison."""
        v1_0_0 = SemanticVersion(1, 0, 0)
        v1_0_0_alpha = SemanticVersion(1, 0, 0, prerelease="alpha")
        v1_0_0_alpha1 = SemanticVersion(1, 0, 0, prerelease="alpha.1")
        v1_0_0_alpha2 = SemanticVersion(1, 0, 0, prerelease="alpha.2")
        v1_0_0_beta = SemanticVersion(1, 0, 0, prerelease="beta")
        
        # Prerelease < release
        assert v1_0_0_alpha < v1_0_0
        assert v1_0_0_beta < v1_0_0
        
        # Prerelease comparisons
        assert v1_0_0_alpha < v1_0_0_beta
        assert v1_0_0_alpha1 < v1_0_0_alpha2
    
    def test_semantic_version_build_metadata_ignored(self):
        """Test that build metadata is ignored in comparisons."""
        v1_build1 = SemanticVersion(1, 0, 0, build="build.1")
        v1_build2 = SemanticVersion(1, 0, 0, build="build.2")
        v1_no_build = SemanticVersion(1, 0, 0)
        
        # Build metadata should not affect comparison
        assert not (v1_build1 < v1_build2)
        assert not (v1_build2 < v1_build1)
        assert not (v1_build1 < v1_no_build)
        assert not (v1_no_build < v1_build1)
    
    def test_version_bump_major(self):
        """Test major version bumping."""
        version = SemanticVersion(1, 2, 3)
        bumped = version.bump(VersionBumpType.MAJOR)
        
        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0
        assert bumped.prerelease is None
        assert bumped.build is None
    
    def test_version_bump_minor(self):
        """Test minor version bumping."""
        version = SemanticVersion(1, 2, 3)
        bumped = version.bump(VersionBumpType.MINOR)
        
        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0
        assert bumped.prerelease is None
        assert bumped.build is None
    
    def test_version_bump_patch(self):
        """Test patch version bumping."""
        version = SemanticVersion(1, 2, 3)
        bumped = version.bump(VersionBumpType.PATCH)
        
        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4
        assert bumped.prerelease is None
        assert bumped.build is None
    
    def test_version_bump_prerelease_new(self):
        """Test creating new prerelease version."""
        version = SemanticVersion(1, 2, 3)
        bumped = version.bump(VersionBumpType.PRERELEASE)
        
        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 3
        assert bumped.prerelease == "alpha.1"
    
    def test_version_bump_prerelease_increment(self):
        """Test incrementing existing prerelease version."""
        version = SemanticVersion(1, 2, 3, prerelease="alpha.1")
        bumped = version.bump(VersionBumpType.PRERELEASE)
        
        assert bumped.prerelease == "alpha.2"
        
        # Test with beta
        version_beta = SemanticVersion(1, 2, 3, prerelease="beta.5")
        bumped_beta = version_beta.bump(VersionBumpType.PRERELEASE)
        
        assert bumped_beta.prerelease == "beta.6"
    
    def test_version_bump_prerelease_no_number(self):
        """Test incrementing prerelease without number."""
        version = SemanticVersion(1, 2, 3, prerelease="alpha")
        bumped = version.bump(VersionBumpType.PRERELEASE)
        
        assert bumped.prerelease == "alpha.1"


class TestSemanticVersionManager:
    """Test SemanticVersionManager functionality."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def version_manager(self, temp_project_dir):
        """Create a SemanticVersionManager instance."""
        logger = logging.getLogger(__name__)
        return SemanticVersionManager(str(temp_project_dir), logger)
    
    def test_parse_version_basic(self, version_manager):
        """Test parsing basic version strings."""
        # Basic version
        version = version_manager.parse_version("1.2.3")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        
        # Version with v prefix
        version_v = version_manager.parse_version("v1.2.3")
        assert version_v is not None
        assert version_v.major == 1
        assert version_v.minor == 2
        assert version_v.patch == 3
    
    def test_parse_version_with_prerelease(self, version_manager):
        """Test parsing versions with prerelease."""
        version = version_manager.parse_version("1.2.3-alpha.1")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha.1"
    
    def test_parse_version_with_build(self, version_manager):
        """Test parsing versions with build metadata."""
        version = version_manager.parse_version("1.2.3+build.123")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.build == "build.123"
    
    def test_parse_version_full(self, version_manager):
        """Test parsing full version string."""
        version = version_manager.parse_version("1.2.3-beta.2+build.456")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "beta.2"
        assert version.build == "build.456"
    
    def test_parse_version_invalid(self, version_manager):
        """Test parsing invalid version strings."""
        # Invalid formats
        assert version_manager.parse_version("1.2") is None
        assert version_manager.parse_version("1.2.3.4") is None
        assert version_manager.parse_version("invalid") is None
        assert version_manager.parse_version("") is None
        assert version_manager.parse_version("1.2.a") is None
    
    def test_parse_version_file(self, version_manager, temp_project_dir):
        """Test parsing version from VERSION file."""
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.2.3\n")
        
        version_string = version_manager._parse_version_file(version_file)
        assert version_string == "1.2.3"
    
    def test_parse_package_json_version(self, version_manager, temp_project_dir):
        """Test parsing version from package.json."""
        package_json = temp_project_dir / "package.json"
        package_data = {
            "name": "test-package",
            "version": "1.2.3",
            "description": "Test package"
        }
        package_json.write_text(json.dumps(package_data, indent=2))
        
        version_string = version_manager._parse_package_json_version(package_json)
        assert version_string == "1.2.3"
    
    def test_parse_package_json_invalid(self, version_manager, temp_project_dir):
        """Test parsing invalid package.json."""
        package_json = temp_project_dir / "package.json"
        package_json.write_text("invalid json")
        
        version_string = version_manager._parse_package_json_version(package_json)
        assert version_string is None

    def test_get_current_version_from_version_file(self, version_manager, temp_project_dir):
        """Test getting current version from VERSION file."""
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("2.1.0")

        current_version = version_manager.get_current_version()
        assert current_version is not None
        assert current_version.major == 2
        assert current_version.minor == 1
        assert current_version.patch == 0

    def test_get_current_version_from_package_json(self, version_manager, temp_project_dir):
        """Test getting current version from package.json."""
        package_json = temp_project_dir / "package.json"
        package_data = {"name": "test", "version": "3.2.1"}
        package_json.write_text(json.dumps(package_data))

        current_version = version_manager.get_current_version()
        assert current_version is not None
        assert current_version.major == 3
        assert current_version.minor == 2
        assert current_version.patch == 1

    def test_get_current_version_no_files(self, version_manager):
        """Test getting current version when no version files exist."""
        current_version = version_manager.get_current_version()
        assert current_version is None


class TestChangeAnalysis:
    """Test change analysis and version bump suggestions."""

    @pytest.fixture
    def version_manager(self):
        """Create a SemanticVersionManager instance."""
        logger = logging.getLogger(__name__)
        return SemanticVersionManager("/tmp", logger)

    def test_analyze_changes_breaking(self, version_manager):
        """Test analyzing breaking changes."""
        changes = [
            "breaking: remove deprecated API",
            "feat: add new feature",
            "fix: resolve bug"
        ]

        analysis = version_manager.analyze_changes(changes)

        assert analysis.has_breaking_changes is True
        assert analysis.has_new_features is True
        assert analysis.has_bug_fixes is True
        assert analysis.suggested_bump == VersionBumpType.MAJOR
        assert analysis.confidence > 0.5

    def test_analyze_changes_features(self, version_manager):
        """Test analyzing feature changes."""
        changes = [
            "feat: add user authentication",
            "add: new dashboard component",
            "fix: minor styling issue"
        ]

        analysis = version_manager.analyze_changes(changes)

        assert analysis.has_breaking_changes is False
        assert analysis.has_new_features is True
        assert analysis.has_bug_fixes is True
        assert analysis.suggested_bump == VersionBumpType.MINOR
        assert analysis.confidence > 0.5

    def test_analyze_changes_fixes_only(self, version_manager):
        """Test analyzing bug fix changes only."""
        changes = [
            "fix: resolve memory leak",
            "bugfix: correct calculation error",
            "resolve: issue with file handling"
        ]

        analysis = version_manager.analyze_changes(changes)

        assert analysis.has_breaking_changes is False
        assert analysis.has_new_features is False
        assert analysis.has_bug_fixes is True
        assert analysis.suggested_bump == VersionBumpType.PATCH
        assert analysis.confidence > 0.5

    def test_analyze_changes_mixed_priority(self, version_manager):
        """Test analyzing mixed changes with priority."""
        changes = [
            "docs: update README",
            "style: format code",
            "feat: add new API endpoint"
        ]

        analysis = version_manager.analyze_changes(changes)

        # Should prioritize feature over docs/style
        assert analysis.suggested_bump == VersionBumpType.MINOR

    def test_analyze_changes_empty(self, version_manager):
        """Test analyzing empty changes list."""
        analysis = version_manager.analyze_changes([])

        assert analysis.has_breaking_changes is False
        assert analysis.has_new_features is False
        assert analysis.has_bug_fixes is False
        assert analysis.suggested_bump == VersionBumpType.PATCH  # Default
        assert analysis.confidence == 0.0

    def test_suggest_version_bump(self, version_manager):
        """Test version bump suggestion from commit messages."""
        commit_messages = [
            "feat: add user management",
            "fix: resolve login issue",
            "docs: update API documentation"
        ]

        bump_type, confidence = version_manager.suggest_version_bump(commit_messages)

        assert bump_type == VersionBumpType.MINOR
        assert confidence > 0.0


class TestVersionBumping:
    """Test version bumping functionality."""

    @pytest.fixture
    def version_manager(self):
        """Create a SemanticVersionManager instance."""
        logger = logging.getLogger(__name__)
        return SemanticVersionManager("/tmp", logger)

    def test_bump_version_major(self, version_manager):
        """Test major version bump."""
        current = SemanticVersion(1, 2, 3)
        bumped = version_manager.bump_version(current, VersionBumpType.MAJOR)

        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_bump_version_minor(self, version_manager):
        """Test minor version bump."""
        current = SemanticVersion(1, 2, 3)
        bumped = version_manager.bump_version(current, VersionBumpType.MINOR)

        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0

    def test_bump_version_patch(self, version_manager):
        """Test patch version bump."""
        current = SemanticVersion(1, 2, 3)
        bumped = version_manager.bump_version(current, VersionBumpType.PATCH)

        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4


class TestVersionFileUpdates:
    """Test updating version files."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def version_manager(self, temp_project_dir):
        """Create a SemanticVersionManager instance."""
        logger = logging.getLogger(__name__)
        return SemanticVersionManager(str(temp_project_dir), logger)

    def test_update_version_file_simple(self, version_manager, temp_project_dir):
        """Test updating simple VERSION file."""
        version_file = temp_project_dir / "VERSION"
        version_file.write_text("1.0.0")

        new_version = SemanticVersion(1, 1, 0)
        results = version_manager.update_version_files(new_version, ["VERSION"])

        assert results["VERSION"] is True
        assert version_file.read_text().strip() == "1.1.0"

    def test_update_package_json_version(self, version_manager, temp_project_dir):
        """Test updating package.json version."""
        package_json = temp_project_dir / "package.json"
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "description": "Test package"
        }
        package_json.write_text(json.dumps(package_data, indent=2))

        new_version = SemanticVersion(1, 1, 0)
        results = version_manager.update_version_files(new_version, ["package.json"])

        assert results["package.json"] is True

        # Verify the file was updated correctly
        updated_data = json.loads(package_json.read_text())
        assert updated_data["version"] == "1.1.0"
        assert updated_data["name"] == "test-package"  # Other fields preserved

    def test_update_version_files_nonexistent(self, version_manager):
        """Test updating non-existent version files."""
        new_version = SemanticVersion(2, 0, 0)
        results = version_manager.update_version_files(new_version, ["nonexistent.json"])

        # Should not include non-existent files in results
        assert "nonexistent.json" not in results

    def test_update_version_files_error_handling(self, version_manager, temp_project_dir):
        """Test error handling during version file updates."""
        # Create a file with invalid JSON
        package_json = temp_project_dir / "package.json"
        package_json.write_text("invalid json content")

        new_version = SemanticVersion(2, 0, 0)
        results = version_manager.update_version_files(new_version, ["package.json"])

        assert results["package.json"] is False


class TestVersionMetadata:
    """Test VersionMetadata functionality."""

    def test_version_metadata_creation(self):
        """Test creating VersionMetadata instances."""
        version = SemanticVersion(1, 2, 3)
        release_date = datetime.now()

        metadata = VersionMetadata(
            version=version,
            release_date=release_date,
            commit_hash="abc123",
            tag_name="v1.2.3",
            changes=["feat: new feature", "fix: bug fix"],
            breaking_changes=["breaking: remove API"],
            contributors=["developer1", "developer2"],
            notes="Release notes"
        )

        assert metadata.version == version
        assert metadata.release_date == release_date
        assert metadata.commit_hash == "abc123"
        assert metadata.tag_name == "v1.2.3"
        assert len(metadata.changes) == 2
        assert len(metadata.breaking_changes) == 1
        assert len(metadata.contributors) == 2
        assert metadata.notes == "Release notes"
