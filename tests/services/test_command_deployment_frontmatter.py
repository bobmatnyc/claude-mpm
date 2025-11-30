"""Unit tests for YAML frontmatter parsing and validation in CommandDeploymentService.

Ticket: 1M-400 Phase 1 - Enhanced Flat Naming with Namespace Metadata

Tests:
- YAML frontmatter parsing (valid and invalid cases)
- Frontmatter validation (required fields, data types, categories)
- Error handling for malformed YAML
- Edge cases (missing frontmatter, empty fields, etc.)
"""

from pathlib import Path

import pytest

from claude_mpm.services.command_deployment_service import CommandDeploymentService


class TestFrontmatterParsing:
    """Test YAML frontmatter parsing functionality."""

    @pytest.fixture
    def service(self):
        """Create CommandDeploymentService instance."""
        return CommandDeploymentService()

    def test_parse_valid_frontmatter(self, service):
        """Test parsing valid YAML frontmatter."""
        content = """---
namespace: mpm/agents
command: list
aliases: [mpm-agents, mpm-agents-list]
migration_target: /mpm/agents:list
category: agents
deprecated_aliases: []
description: List all available agents
---
# Command Content

Body of the command goes here.
"""
        frontmatter, body = service._parse_frontmatter(content)

        assert frontmatter is not None
        assert frontmatter["namespace"] == "mpm/agents"
        assert frontmatter["command"] == "list"
        assert frontmatter["category"] == "agents"
        assert isinstance(frontmatter["aliases"], list)
        assert "mpm-agents" in frontmatter["aliases"]
        assert body.strip().startswith("# Command Content")

    def test_parse_no_frontmatter(self, service):
        """Test parsing content without frontmatter."""
        content = """# Regular Markdown

No frontmatter here.
"""
        frontmatter, body = service._parse_frontmatter(content)

        assert frontmatter is None
        assert body == content

    def test_parse_invalid_yaml(self, service):
        """Test parsing malformed YAML frontmatter."""
        content = """---
namespace: mpm/agents
command: list
  this is invalid yaml syntax: [
---
# Content
"""
        frontmatter, body = service._parse_frontmatter(content)

        # Should return None on parse error and log warning
        assert frontmatter is None
        assert body == content

    def test_parse_missing_closing_delimiter(self, service):
        """Test parsing frontmatter without closing delimiter."""
        content = """---
namespace: mpm/agents
command: list

# Content without closing delimiter
"""
        frontmatter, body = service._parse_frontmatter(content)

        # Should return None if closing delimiter missing
        assert frontmatter is None
        assert body == content

    def test_parse_empty_frontmatter(self, service):
        """Test parsing empty frontmatter section."""
        content = """---
---
# Content
"""
        frontmatter, body = service._parse_frontmatter(content)

        # Empty YAML should parse to None or empty dict
        assert frontmatter is None or frontmatter == {}
        assert "# Content" in body

    def test_parse_multiline_values(self, service):
        """Test parsing frontmatter with multiline values."""
        content = """---
namespace: mpm/agents
command: list
description: |
  This is a multiline
  description for testing
aliases: [mpm-agents]
---
# Content
"""
        frontmatter, body = service._parse_frontmatter(content)

        assert frontmatter is not None
        assert "multiline" in frontmatter["description"]
        assert "description" in frontmatter["description"]


class TestFrontmatterValidation:
    """Test YAML frontmatter validation functionality."""

    @pytest.fixture
    def service(self):
        """Create CommandDeploymentService instance."""
        return CommandDeploymentService()

    @pytest.fixture
    def valid_frontmatter(self):
        """Create valid frontmatter dictionary."""
        return {
            "namespace": "mpm/agents",
            "command": "list",
            "category": "agents",
            "description": "List all available agents",
            "aliases": ["mpm-agents"],
            "deprecated_aliases": [],
            "migration_target": "/mpm/agents:list",
        }

    def test_validate_valid_frontmatter(self, service, valid_frontmatter):
        """Test validation of valid frontmatter."""
        errors = service._validate_frontmatter(valid_frontmatter, Path("test.md"))

        assert len(errors) == 0

    def test_validate_missing_required_fields(self, service):
        """Test validation with missing required fields."""
        incomplete_frontmatter = {
            "namespace": "mpm/agents",
            # Missing: command, category, description
        }

        errors = service._validate_frontmatter(incomplete_frontmatter, Path("test.md"))

        assert len(errors) == 3  # Missing 3 required fields
        assert any("command" in err for err in errors)
        assert any("category" in err for err in errors)
        assert any("description" in err for err in errors)

    def test_validate_invalid_category(self, service, valid_frontmatter):
        """Test validation with invalid category value."""
        valid_frontmatter["category"] = "invalid_category"

        errors = service._validate_frontmatter(valid_frontmatter, Path("test.md"))

        assert len(errors) == 1
        assert "Invalid category" in errors[0]
        assert "invalid_category" in errors[0]

    def test_validate_valid_categories(self, service, valid_frontmatter):
        """Test validation with all valid category values."""
        valid_categories = ["agents", "config", "tickets", "session", "system"]

        for category in valid_categories:
            valid_frontmatter["category"] = category
            errors = service._validate_frontmatter(valid_frontmatter, Path("test.md"))
            assert len(errors) == 0, f"Category '{category}' should be valid"

    def test_validate_aliases_not_list(self, service, valid_frontmatter):
        """Test validation when aliases is not a list."""
        valid_frontmatter["aliases"] = "not-a-list"

        errors = service._validate_frontmatter(valid_frontmatter, Path("test.md"))

        assert len(errors) == 1
        assert "aliases" in errors[0]
        assert "must be a list" in errors[0]

    def test_validate_deprecated_aliases_not_list(self, service, valid_frontmatter):
        """Test validation when deprecated_aliases is not a list."""
        valid_frontmatter["deprecated_aliases"] = "not-a-list"

        errors = service._validate_frontmatter(valid_frontmatter, Path("test.md"))

        assert len(errors) == 1
        assert "deprecated_aliases" in errors[0]
        assert "must be a list" in errors[0]

    def test_validate_optional_fields(self, service):
        """Test validation with only required fields (optional fields missing)."""
        minimal_frontmatter = {
            "namespace": "mpm/system",
            "command": "help",
            "category": "system",
            "description": "Show help",
        }

        errors = service._validate_frontmatter(minimal_frontmatter, Path("test.md"))

        assert len(errors) == 0  # Optional fields should not cause errors

    def test_validate_empty_required_fields(self, service):
        """Test validation with empty string required fields."""
        empty_frontmatter = {
            "namespace": "",
            "command": "",
            "category": "",
            "description": "",
        }

        errors = service._validate_frontmatter(empty_frontmatter, Path("test.md"))

        # Empty strings satisfy presence check but invalid category will fail
        assert len(errors) == 1
        assert "Invalid category" in errors[0]


class TestCommandDeploymentWithFrontmatter:
    """Test command deployment with frontmatter validation."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create CommandDeploymentService with temporary directories."""
        service = CommandDeploymentService()
        service.source_dir = tmp_path / "source"
        service.target_dir = tmp_path / "target"
        service.source_dir.mkdir()
        service.target_dir.mkdir()
        return service

    def test_deploy_command_with_valid_frontmatter(self, service):
        """Test deploying command file with valid frontmatter."""
        command_content = """---
namespace: mpm/agents
command: list
category: agents
description: List agents
aliases: [mpm-agents]
deprecated_aliases: []
---
# Test Command

Command content.
"""
        source_file = service.source_dir / "test-command.md"
        source_file.write_text(command_content)

        result = service.deploy_commands(force=True)

        assert result["success"]
        assert "test-command.md" in result["deployed"]
        assert len(result["errors"]) == 0

        # Verify file was deployed
        target_file = service.target_dir / "test-command.md"
        assert target_file.exists()
        assert target_file.read_text() == command_content

    def test_deploy_command_with_invalid_frontmatter(self, service):
        """Test deploying command with invalid frontmatter logs warnings."""
        command_content = """---
namespace: mpm/agents
# Missing required: command, category, description
---
# Test Command
"""
        source_file = service.source_dir / "invalid-command.md"
        source_file.write_text(command_content)

        result = service.deploy_commands(force=True)

        # Should still deploy but log warnings
        assert result["success"]
        assert "invalid-command.md" in result["deployed"]

    def test_deploy_command_without_frontmatter(self, service):
        """Test deploying command without frontmatter."""
        command_content = """# Regular Command

No frontmatter.
"""
        source_file = service.source_dir / "no-frontmatter.md"
        source_file.write_text(command_content)

        result = service.deploy_commands(force=True)

        # Should deploy successfully (frontmatter is optional)
        assert result["success"]
        assert "no-frontmatter.md" in result["deployed"]


class TestEdgeCases:
    """Test edge cases for frontmatter parsing and validation."""

    @pytest.fixture
    def service(self):
        """Create CommandDeploymentService instance."""
        return CommandDeploymentService()

    def test_parse_frontmatter_with_special_characters(self, service):
        """Test parsing frontmatter with special characters in values."""
        content = """---
namespace: mpm/agents
command: list
description: "Command with special chars: @#$%^&*()"
aliases: ["mpm-agents", "mpm:agents"]
---
# Content
"""
        frontmatter, _ = service._parse_frontmatter(content)

        assert frontmatter is not None
        assert "@#$%^&*()" in frontmatter["description"]

    def test_parse_frontmatter_with_unicode(self, service):
        """Test parsing frontmatter with Unicode characters."""
        content = """---
namespace: mpm/agents
command: list
description: "Command with Unicode: 你好 🚀"
category: agents
---
# Content
"""
        frontmatter, _ = service._parse_frontmatter(content)

        assert frontmatter is not None
        assert "你好" in frontmatter["description"]
        assert "🚀" in frontmatter["description"]

    def test_validate_extra_fields(self, service):
        """Test validation doesn't fail on extra (unknown) fields."""
        frontmatter_with_extras = {
            "namespace": "mpm/agents",
            "command": "list",
            "category": "agents",
            "description": "Test",
            "extra_field": "extra_value",
            "another_extra": 123,
        }

        errors = service._validate_frontmatter(frontmatter_with_extras, Path("test.md"))

        # Should not fail on extra fields
        assert len(errors) == 0

    def test_parse_frontmatter_with_nested_structures(self, service):
        """Test parsing frontmatter with nested YAML structures."""
        content = """---
namespace: mpm/agents
command: list
category: agents
description: Test
metadata:
  author: Test Author
  version: 1.0.0
  tags: [tag1, tag2]
---
# Content
"""
        frontmatter, _ = service._parse_frontmatter(content)

        assert frontmatter is not None
        assert isinstance(frontmatter["metadata"], dict)
        assert frontmatter["metadata"]["author"] == "Test Author"
        assert isinstance(frontmatter["metadata"]["tags"], list)
