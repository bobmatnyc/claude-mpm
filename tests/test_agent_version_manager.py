#!/usr/bin/env python3
"""
Tests for AgentVersionManager Service
====================================

Comprehensive test suite for the extracted AgentVersionManager service.
Tests all version parsing, comparison, and migration functionality.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_version_manager import (
    AgentVersionManager,
)


class TestAgentVersionManager:
    """Test suite for AgentVersionManager."""

    @pytest.fixture
    def version_manager(self):
        """Create AgentVersionManager instance."""
        return AgentVersionManager()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tmp_path as temp_dir:
            yield Path(temp_dir)

    def test_initialization(version_manager):
        """Test AgentVersionManager initialization."""
        assert hasattr(version_manager, "logger")
        assert version_manager.logger is not None

    def test_parse_version_integer(version_manager):
        """Test parsing integer versions."""
        result = version_manager.parse_version(5)
        assert result == (0, 5, 0)

    def test_parse_version_string_integer(version_manager):
        """Test parsing string integer versions."""
        result = version_manager.parse_version("5")
        assert result == (0, 5, 0)

    def test_parse_version_semantic(version_manager):
        """Test parsing semantic versions."""
        test_cases = [
            ("2.1.0", (2, 1, 0)),
            ("v2.1.0", (2, 1, 0)),
            ("10.5.3", (10, 5, 3)),
            ("1.0.0", (1, 0, 0)),
        ]

        for version_str, expected in test_cases:
            result = version_manager.parse_version(version_str)
            assert result == expected, f"Failed for {version_str}"

    def test_parse_version_invalid(version_manager):
        """Test parsing invalid versions."""
        test_cases = [
            (None, (0, 0, 0)),
            ("", (0, 0, 0)),
            ("invalid", (0, 0, 0)),
            ([], (0, 0, 0)),
            ({}, (0, 0, 0)),
        ]

        for version_value, expected in test_cases:
            result = version_manager.parse_version(version_value)
            assert result == expected, f"Failed for {version_value}"

    def test_parse_version_extract_number(version_manager):
        """Test extracting number from complex strings."""
        result = version_manager.parse_version("version-5-something")
        assert result == (0, 5, 0)

    def test_format_version_display(version_manager):
        """Test version display formatting."""
        test_cases = [
            ((1, 2, 3), "1.2.3"),
            ((0, 5, 0), "0.5.0"),
            ((10, 0, 1), "10.0.1"),
        ]

        for version_tuple, expected in test_cases:
            result = version_manager.format_version_display(version_tuple)
            assert result == expected

    def test_format_version_display_invalid(version_manager):
        """Test version display formatting with invalid input."""
        result = version_manager.format_version_display("invalid")
        assert result == "invalid"

    def test_is_old_version_format(version_manager):
        """Test old version format detection."""
        old_formats = ["", None, "0002-0005", "123-456", "version-5", "invalid"]

        new_formats = ["1.0.0", "v2.1.3", "10.5.0"]

        for version_str in old_formats:
            assert version_manager.is_old_version_format(
                version_str
            ), f"Should be old: {version_str}"

        for version_str in new_formats:
            assert not version_manager.is_old_version_format(
                version_str
            ), f"Should be new: {version_str}"

    def test_compare_versions(version_manager):
        """Test version comparison."""
        test_cases = [
            ((1, 0, 0), (0, 9, 9), 1),  # v1 > v2
            ((1, 0, 0), (1, 0, 0), 0),  # v1 == v2
            ((0, 5, 0), (1, 0, 0), -1),  # v1 < v2
            ((2, 1, 0), (2, 0, 9), 1),  # Minor version comparison
            ((1, 1, 1), (1, 1, 2), -1),  # Patch version comparison
        ]

        for v1, v2, expected in test_cases:
            result = version_manager.compare_versions(v1, v2)
            assert result == expected, f"Failed comparing {v1} vs {v2}"

    def test_extract_version_from_content(version_manager):
        """Test extracting version from content with markers."""
        content = """
        Some content here
        <!-- AGENT_VERSION: 5 -->
        More content
        <!-- BASE_AGENT_VERSION: 3 -->
        """

        agent_version = version_manager.extract_version_from_content(
            content, "AGENT_VERSION:"
        )
        assert agent_version == 5

        base_version = version_manager.extract_version_from_content(
            content, "BASE_AGENT_VERSION:"
        )
        assert base_version == 3

        missing_version = version_manager.extract_version_from_content(
            content, "MISSING:"
        )
        assert missing_version == 0

    def test_extract_version_from_frontmatter_semantic(version_manager):
        """Test extracting semantic version from frontmatter."""
        content = """---
name: test-agent
version: "2.1.0"
description: Test agent
---
Content here"""

        (
            version_tuple,
            is_old,
            version_str,
        ) = version_manager.extract_version_from_frontmatter(content)
        assert version_tuple == (2, 1, 0)
        assert not is_old
        assert version_str == "2.1.0"

    def test_extract_version_from_frontmatter_legacy(version_manager):
        """Test extracting legacy version from frontmatter."""
        content = """---
name: test-agent
version: "0002-0005"
description: Test agent
---
Content here"""

        (
            version_tuple,
            is_old,
            version_str,
        ) = version_manager.extract_version_from_frontmatter(content)
        assert version_tuple == (0, 5, 0)
        assert is_old
        assert version_str == "0002-0005"

    def test_extract_version_from_frontmatter_old_separate(version_manager):
        """Test extracting old separate version format."""
        content = """---
name: test-agent
agent_version: 5
description: Test agent
---
Content here"""

        (
            version_tuple,
            is_old,
            version_str,
        ) = version_manager.extract_version_from_frontmatter(content)
        assert version_tuple == (0, 5, 0)
        assert is_old
        assert version_str == "agent_version: 5"

    def test_extract_version_from_frontmatter_missing(version_manager):
        """Test extracting version when missing."""
        content = """---
name: test-agent
description: Test agent
---
Content here"""

        (
            version_tuple,
            is_old,
            version_str,
        ) = version_manager.extract_version_from_frontmatter(content)
        assert version_tuple == (0, 0, 0)
        assert is_old
        assert version_str == "missing"

    def test_check_agent_needs_update_not_system(version_manager, temp_dir):
        """Test update check for non-system agent."""
        # Create deployed file without system marker
        deployed_file = temp_dir / "test.md"
        deployed_file.write_text(
            """---
name: test-agent
version: "1.0.0"
---
User created agent"""
        )

        # Create template file
        template_file = temp_dir / "test.json"
        template_file.write_text(json.dumps({"version": 2}))

        needs_update, reason = version_manager.check_agent_needs_update(
            deployed_file, template_file, (0, 0, 0)
        )

        assert not needs_update
        assert reason == "not a system agent"

    def test_check_agent_needs_update_migration_needed(version_manager, temp_dir):
        """Test update check when migration is needed."""
        # Create deployed file with old format
        deployed_file = temp_dir / "test.md"
        deployed_file.write_text(
            """---
name: test-agent
version: "0002-0005"
author: claude-mpm
---
System agent"""
        )

        # Create template file
        template_file = temp_dir / "test.json"
        template_file.write_text(json.dumps({"version": "2.0.0"}))

        needs_update, reason = version_manager.check_agent_needs_update(
            deployed_file, template_file, (0, 0, 0)
        )

        assert needs_update
        assert "migration needed" in reason

    def test_check_agent_needs_update_template_newer(version_manager, temp_dir):
        """Test update check when template is newer."""
        # Create deployed file with older version
        deployed_file = temp_dir / "test.md"
        deployed_file.write_text(
            """---
name: test-agent
version: "1.0.0"
author: claude-mpm
---
System agent"""
        )

        # Create template file with newer version
        template_file = temp_dir / "test.json"
        template_file.write_text(json.dumps({"version": "2.0.0"}))

        needs_update, reason = version_manager.check_agent_needs_update(
            deployed_file, template_file, (0, 0, 0)
        )

        assert needs_update
        assert "agent template updated" in reason

    def test_check_agent_needs_update_up_to_date(version_manager, temp_dir):
        """Test update check when agent is up to date."""
        # Create deployed file with current version
        deployed_file = temp_dir / "test.md"
        deployed_file.write_text(
            """---
name: test-agent
version: "2.0.0"
author: claude-mpm
---
System agent"""
        )

        # Create template file with same version
        template_file = temp_dir / "test.json"
        template_file.write_text(json.dumps({"version": "2.0.0"}))

        needs_update, reason = version_manager.check_agent_needs_update(
            deployed_file, template_file, (0, 0, 0)
        )

        assert not needs_update
        assert reason == "up to date"

    def test_validate_version_in_content_valid(version_manager):
        """Test version validation for valid content."""
        content = """---
name: test-agent
version: "2.1.0"
description: Test agent
---
Content here"""

        is_valid, errors = version_manager.validate_version_in_content(content)
        assert is_valid
        assert len(errors) == 0

    def test_validate_version_in_content_missing_frontmatter(version_manager):
        """Test version validation for missing frontmatter."""
        content = "Just content without frontmatter"

        is_valid, errors = version_manager.validate_version_in_content(content)
        assert not is_valid
        assert "Missing YAML frontmatter" in errors

    def test_validate_version_in_content_missing_version(version_manager):
        """Test version validation for missing version field."""
        content = """---
name: test-agent
description: Test agent
---
Content here"""

        is_valid, errors = version_manager.validate_version_in_content(content)
        assert not is_valid
        assert "Missing version field in frontmatter" in errors

    def test_validate_version_in_content_old_format(version_manager):
        """Test version validation for old version format."""
        content = """---
name: test-agent
version: "0002-0005"
description: Test agent
---
Content here"""

        is_valid, errors = version_manager.validate_version_in_content(content)
        assert not is_valid
        assert "Old version format detected" in errors[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
