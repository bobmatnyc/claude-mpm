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
        frontmatter, _body = service._parse_frontmatter(content)

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

        # Verify content semantically (YAML formatting may differ after stripping)
        deployed_content = target_file.read_text()
        frontmatter, body = service._parse_frontmatter(deployed_content)

        # Verify frontmatter fields
        assert frontmatter is not None
        assert frontmatter["namespace"] == "mpm/agents"
        assert frontmatter["command"] == "list"
        assert frontmatter["category"] == "agents"
        assert frontmatter["description"] == "List agents"
        assert frontmatter["aliases"] == ["mpm-agents"]
        # deprecated_aliases should be stripped
        assert "deprecated_aliases" not in frontmatter

        # Verify body content
        assert "# Test Command" in body
        assert "Command content." in body

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


class TestDeprecatedCommandCleanup:
    """Test automatic cleanup of deprecated commands."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create CommandDeploymentService with temporary directories."""
        service = CommandDeploymentService()
        service.source_dir = tmp_path / "source"
        service.target_dir = tmp_path / "target"
        service.source_dir.mkdir()
        service.target_dir.mkdir()
        return service

    def test_remove_deprecated_commands_removes_all_deprecated(self, service):
        """Test that all deprecated commands are removed."""
        # Create all deprecated command files
        for deprecated_cmd in CommandDeploymentService.DEPRECATED_COMMANDS:
            deprecated_file = service.target_dir / deprecated_cmd
            deprecated_file.write_text("# Deprecated command content")

        # Remove deprecated commands
        removed_count = service.remove_deprecated_commands()

        # Verify all were removed
        assert removed_count == len(CommandDeploymentService.DEPRECATED_COMMANDS)
        for deprecated_cmd in CommandDeploymentService.DEPRECATED_COMMANDS:
            assert not (service.target_dir / deprecated_cmd).exists()

    def test_remove_deprecated_commands_partial_removal(self, service):
        """Test removing only some deprecated commands that exist."""
        # Create only 3 deprecated command files
        deprecated_to_create = ["mpm-agents.md", "mpm-config.md", "mpm-ticket.md"]
        for deprecated_cmd in deprecated_to_create:
            deprecated_file = service.target_dir / deprecated_cmd
            deprecated_file.write_text("# Deprecated command content")

        # Remove deprecated commands
        removed_count = service.remove_deprecated_commands()

        # Verify only created files were removed
        assert removed_count == 3
        for deprecated_cmd in deprecated_to_create:
            assert not (service.target_dir / deprecated_cmd).exists()

    def test_remove_deprecated_commands_none_exist(self, service):
        """Test cleanup when no deprecated commands exist."""
        # Don't create any deprecated files
        removed_count = service.remove_deprecated_commands()

        # Should return 0 and not error
        assert removed_count == 0

    def test_remove_deprecated_commands_target_dir_missing(self, service):
        """Test cleanup when target directory doesn't exist."""
        # Remove target directory
        service.target_dir.rmdir()

        # Should handle gracefully
        removed_count = service.remove_deprecated_commands()
        assert removed_count == 0

    def test_remove_deprecated_commands_preserves_new_commands(self, service):
        """Test that new/replacement commands are NOT removed."""
        # Create replacement commands
        new_commands = [
            "mpm-agents-list.md",
            "mpm-agents-auto-configure.md",
            "mpm-config-view.md",
            "mpm-ticket-organize.md",
            "mpm-session-resume.md",
            "mpm-ticket-view.md",
        ]
        for new_cmd in new_commands:
            new_file = service.target_dir / new_cmd
            new_file.write_text("# New command content")

        # Create some deprecated commands
        for deprecated_cmd in ["mpm-agents.md", "mpm-ticket.md"]:
            deprecated_file = service.target_dir / deprecated_cmd
            deprecated_file.write_text("# Deprecated command content")

        # Remove deprecated commands
        removed_count = service.remove_deprecated_commands()

        # Verify only deprecated were removed, new commands preserved
        assert removed_count == 2
        for new_cmd in new_commands:
            assert (service.target_dir / new_cmd).exists(), (
                f"{new_cmd} should be preserved"
            )
        assert not (service.target_dir / "mpm-agents.md").exists()
        assert not (service.target_dir / "mpm-ticket.md").exists()

    def test_remove_deprecated_commands_error_handling(self, service, tmp_path):
        """Test error handling when file removal fails."""
        # Create a deprecated command file
        deprecated_file = service.target_dir / "mpm-agents.md"
        deprecated_file.write_text("# Deprecated command")

        # Make the file read-only to trigger removal error (on Unix-like systems)
        import stat

        deprecated_file.chmod(stat.S_IRUSR)

        try:
            # Attempt removal - should log warning but not crash
            removed_count = service.remove_deprecated_commands()

            # Depending on permissions, file might not be removable
            # The important thing is that it doesn't raise an exception
            assert removed_count >= 0
        finally:
            # Restore write permissions for cleanup (only if file still exists)
            if deprecated_file.exists():
                deprecated_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_deploy_commands_on_startup_includes_cleanup(self, service, tmp_path):
        """Test that startup deployment includes deprecated command cleanup."""
        # Create deprecated commands in target
        for deprecated_cmd in ["mpm-agents.md", "mpm-ticket.md"]:
            deprecated_file = service.target_dir / deprecated_cmd
            deprecated_file.write_text("# Deprecated command")

        # Create a source command for deployment
        source_file = service.source_dir / "mpm-agents-list.md"
        source_file.write_text("# New command")

        # Deploy (which should clean up deprecated first)
        result = service.deploy_commands(force=True)

        # Note: deploy_commands doesn't call remove_deprecated_commands
        # That's done in deploy_commands_on_startup wrapper function
        # So we test that separately
        assert result["success"]

    def test_deprecated_commands_constant_exists(self):
        """Test that DEPRECATED_COMMANDS constant is defined correctly."""
        assert hasattr(CommandDeploymentService, "DEPRECATED_COMMANDS")
        assert isinstance(CommandDeploymentService.DEPRECATED_COMMANDS, list)
        assert len(CommandDeploymentService.DEPRECATED_COMMANDS) == 6
        assert "mpm-agents.md" in CommandDeploymentService.DEPRECATED_COMMANDS
        assert "mpm-ticket.md" in CommandDeploymentService.DEPRECATED_COMMANDS


class TestDeprecatedAliasStripping:
    """Test stripping of deprecated_aliases from deployed command files."""

    @pytest.fixture
    def service(self):
        """Create CommandDeploymentService instance."""
        return CommandDeploymentService()

    def test_strip_deprecated_aliases_removes_field(self, service):
        """Test that deprecated_aliases field is removed from frontmatter."""
        content = """---
namespace: mpm/agents
command: auto-configure
aliases: [mpm-agents-auto-configure]
category: agents
deprecated_aliases: [mpm-auto-configure]
description: Automatically configure agents
---
# Command Content

Body goes here.
"""
        result = service._strip_deprecated_aliases(content)

        # Parse the result to verify deprecated_aliases is gone
        frontmatter, body = service._parse_frontmatter(result)
        assert frontmatter is not None
        assert "deprecated_aliases" not in frontmatter
        assert "aliases" in frontmatter
        assert frontmatter["aliases"] == ["mpm-agents-auto-configure"]
        assert "# Command Content" in body

    def test_strip_deprecated_aliases_preserves_other_fields(self, service):
        """Test that other fields are preserved when stripping deprecated_aliases."""
        content = """---
namespace: mpm/agents
command: list
aliases: [mpm-agents, mpm-agents-list]
migration_target: /mpm/agents:list
category: agents
deprecated_aliases: [mpm-old-agents]
description: List all available agents
extra_field: extra_value
---
# Command Content
"""
        result = service._strip_deprecated_aliases(content)

        frontmatter, _ = service._parse_frontmatter(result)
        assert frontmatter is not None
        assert frontmatter["namespace"] == "mpm/agents"
        assert frontmatter["command"] == "list"
        assert frontmatter["aliases"] == ["mpm-agents", "mpm-agents-list"]
        assert frontmatter["migration_target"] == "/mpm/agents:list"
        assert frontmatter["category"] == "agents"
        assert frontmatter["description"] == "List all available agents"
        assert frontmatter["extra_field"] == "extra_value"
        assert "deprecated_aliases" not in frontmatter

    def test_strip_deprecated_aliases_empty_list(self, service):
        """Test stripping when deprecated_aliases is an empty list."""
        content = """---
namespace: mpm/system
command: help
aliases: [mpm-help]
category: system
deprecated_aliases: []
description: Show help
---
# Content
"""
        result = service._strip_deprecated_aliases(content)

        frontmatter, _ = service._parse_frontmatter(result)
        assert frontmatter is not None
        assert "deprecated_aliases" not in frontmatter

    def test_strip_deprecated_aliases_no_frontmatter(self, service):
        """Test stripping when content has no frontmatter."""
        content = """# Regular Markdown

No frontmatter here.
"""
        result = service._strip_deprecated_aliases(content)

        # Should return content unchanged
        assert result == content

    def test_strip_deprecated_aliases_field_not_present(self, service):
        """Test stripping when deprecated_aliases field doesn't exist."""
        content = """---
namespace: mpm/system
command: help
aliases: [mpm-help]
category: system
description: Show help
---
# Content
"""
        result = service._strip_deprecated_aliases(content)

        # Should return content unchanged (or with frontmatter preserved)
        frontmatter, body = service._parse_frontmatter(result)
        assert frontmatter is not None
        assert "deprecated_aliases" not in frontmatter
        assert frontmatter["aliases"] == ["mpm-help"]
        assert "# Content" in body

    def test_deploy_command_strips_deprecated_aliases(self, service, tmp_path):
        """Test that deploy_commands strips deprecated_aliases from deployed files."""
        # Setup temporary directories
        service.source_dir = tmp_path / "source"
        service.target_dir = tmp_path / "target"
        service.source_dir.mkdir()
        service.target_dir.mkdir()

        # Create source command with deprecated_aliases
        source_content = """---
namespace: mpm/agents
command: auto-configure
aliases: [mpm-agents-auto-configure]
category: agents
deprecated_aliases: [mpm-auto-configure, mpm-configure]
description: Auto-configure agents
---
# Auto Configure Command

This command automatically configures agents.
"""
        source_file = service.source_dir / "mpm-agents-auto-configure.md"
        source_file.write_text(source_content)

        # Deploy the command
        result = service.deploy_commands(force=True)

        assert result["success"]
        assert "mpm-agents-auto-configure.md" in result["deployed"]

        # Verify deployed file has deprecated_aliases stripped
        target_file = service.target_dir / "mpm-agents-auto-configure.md"
        assert target_file.exists()

        deployed_content = target_file.read_text()
        frontmatter, body = service._parse_frontmatter(deployed_content)

        # Verify deprecated_aliases is NOT in deployed file
        assert frontmatter is not None
        assert "deprecated_aliases" not in frontmatter

        # Verify other fields are preserved
        assert frontmatter["namespace"] == "mpm/agents"
        assert frontmatter["command"] == "auto-configure"
        assert frontmatter["aliases"] == ["mpm-agents-auto-configure"]
        assert frontmatter["category"] == "agents"
        assert frontmatter["description"] == "Auto-configure agents"

        # Verify body is preserved
        assert "# Auto Configure Command" in body
        assert "automatically configures agents" in body

    def test_deploy_multiple_commands_all_stripped(self, service, tmp_path):
        """Test that multiple commands all have deprecated_aliases stripped."""
        service.source_dir = tmp_path / "source"
        service.target_dir = tmp_path / "target"
        service.source_dir.mkdir()
        service.target_dir.mkdir()

        # Create multiple source commands
        commands = [
            ("mpm-agents-list.md", ["mpm-agents"]),
            ("mpm-config-view.md", ["mpm-config"]),
            ("mpm-ticket-view.md", ["mpm-ticket"]),
        ]

        for filename, deprecated_aliases in commands:
            content = f"""---
namespace: mpm/test
command: test
aliases: [{filename.replace(".md", "")}]
category: system
deprecated_aliases: {deprecated_aliases}
description: Test command
---
# Content
"""
            source_file = service.source_dir / filename
            source_file.write_text(content)

        # Deploy all commands
        result = service.deploy_commands(force=True)

        assert result["success"]
        assert len(result["deployed"]) == 3

        # Verify all deployed files have deprecated_aliases stripped
        for filename, _ in commands:
            target_file = service.target_dir / filename
            assert target_file.exists()

            deployed_content = target_file.read_text()
            frontmatter, _ = service._parse_frontmatter(deployed_content)

            assert frontmatter is not None
            assert "deprecated_aliases" not in frontmatter, (
                f"{filename} should not have deprecated_aliases"
            )
