"""Tests for agentskills.io specification compliance.

Tests cover:
- Spec field validation (name, description, license, compatibility, metadata, allowed_tools)
- Backward compatibility with legacy claude-mpm format
- Auto-migration of legacy fields to spec format
- Name format validation per spec
"""

from pathlib import Path

import pytest

from claude_mpm.skills.registry import Skill, SkillsRegistry, validate_agentskills_spec


class TestAgentSkillsSpecCompliance:
    """Test agentskills.io specification compliance."""

    def test_validate_spec_required_fields_present(self):
        """Test that required fields (name, description) are validated."""
        # Valid skill with required fields and metadata properly structured
        skill = Skill(
            name="test-skill",
            description="A test skill for validation",
            path=Path("/tmp/test.md"),
            metadata={"version": "0.1.0"},  # version in metadata, not top-level
            version="0.1.0",  # Derived field matches metadata
        )

        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_spec_missing_name(self):
        """Test validation fails when name is missing."""
        skill = Skill(
            name="",
            description="A test skill",
            path=Path("/tmp/test.md"),
        )

        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is False
        assert any("Missing required field: name" in w for w in warnings)

    def test_validate_spec_missing_description(self):
        """Test validation fails when description is missing."""
        skill = Skill(
            name="test-skill",
            description="",
            path=Path("/tmp/test.md"),
        )

        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is False
        assert any("Missing required field: description" in w for w in warnings)

    def test_validate_spec_name_format_valid(self):
        """Test name format validation with valid names."""
        valid_names = [
            "test-skill",
            "my-awesome-skill-123",
            "skill123",
            "a",
            "test-skill-v2",
        ]

        for name in valid_names:
            skill = Skill(
                name=name,
                description="Test skill",
                path=Path("/tmp/test.md"),
            )
            is_valid, _warnings = validate_agentskills_spec(skill)
            assert is_valid is True, f"Name '{name}' should be valid"

    def test_validate_spec_name_format_invalid(self):
        """Test name format validation with invalid names."""
        invalid_names = [
            "Test-Skill",  # uppercase
            "-test-skill",  # leading hyphen
            "test-skill-",  # trailing hyphen
            "test--skill",  # consecutive hyphens
            "test_skill",  # underscore
            "test skill",  # space
            "test.skill",  # dot
        ]

        for name in invalid_names:
            skill = Skill(
                name=name,
                description="Test skill",
                path=Path("/tmp/test.md"),
            )
            is_valid, warnings = validate_agentskills_spec(skill)
            assert not is_valid, f"Name '{name}' should be invalid"
            assert any("Invalid name format" in w for w in warnings)

    def test_validate_spec_name_length_max_64(self):
        """Test name length validation (max 64 chars)."""
        # Valid: exactly 64 chars
        skill = Skill(
            name="a" * 64,
            description="Test skill",
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is True

        # Invalid: 65 chars
        skill = Skill(
            name="a" * 65,
            description="Test skill",
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert not is_valid
        assert any("Name too long" in w for w in warnings)

    def test_validate_spec_description_length(self):
        """Test description length validation (1-1024 chars)."""
        # Valid: 1 char
        skill = Skill(
            name="test",
            description="A",
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is True

        # Valid: 1024 chars
        skill = Skill(
            name="test",
            description="A" * 1024,
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is True

        # Invalid: 1025 chars
        skill = Skill(
            name="test",
            description="A" * 1025,
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert not is_valid
        assert any("Description length" in w for w in warnings)

    def test_validate_spec_optional_fields(self):
        """Test optional spec fields are validated correctly."""
        skill = Skill(
            name="test-skill",
            description="Test skill for API development",
            license="Apache-2.0",
            compatibility="Requires Python 3.9+, FastAPI",
            metadata={"version": "1.0.0", "author": "testuser"},
            allowed_tools=["Bash", "Read", "Write"],
            path=Path("/tmp/test.md"),
        )

        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_spec_compatibility_max_500_chars(self):
        """Test compatibility field length validation (max 500 chars)."""
        # Valid: 500 chars
        skill = Skill(
            name="test",
            description="Test",
            compatibility="A" * 500,
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert is_valid is True

        # Invalid: 501 chars
        skill = Skill(
            name="test",
            description="Test",
            compatibility="A" * 501,
            path=Path("/tmp/test.md"),
        )
        is_valid, warnings = validate_agentskills_spec(skill)
        assert not is_valid
        assert any("Compatibility field too long" in w for w in warnings)

    def test_validate_spec_metadata_must_be_dict(self):
        """Test metadata must be a dictionary."""
        skill = Skill(
            name="test",
            description="Test",
            metadata="not a dict",  # Invalid type
            path=Path("/tmp/test.md"),
        )

        is_valid, warnings = validate_agentskills_spec(skill)
        assert not is_valid
        assert any("Metadata must be a key-value mapping" in w for w in warnings)


class TestBackwardCompatibility:
    """Test backward compatibility with legacy claude-mpm format."""

    def test_parse_legacy_format_with_auto_migration(self):
        """Test legacy format is auto-migrated to spec format."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "version": "1.0.0",
            "author": "testuser",
            "updated": "2025-01-17",
            "tags": ["python", "api"],
        }

        migrated = registry._apply_backward_compatibility(frontmatter)

        # Check auto-migration to metadata
        assert migrated["metadata"]["version"] == "1.0.0"
        assert migrated["metadata"]["author"] == "testuser"
        assert migrated["metadata"]["updated"] == "2025-01-17"
        assert migrated["metadata"]["tags"] == ["python", "api"]

        # Original fields should still be present for backward compat
        assert migrated["version"] == "1.0.0"

    def test_parse_spec_compliant_format_no_migration(self):
        """Test spec-compliant format is not modified."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "license": "Apache-2.0",
            "metadata": {
                "version": "1.0.0",
                "author": "testuser",
            },
        }

        migrated = registry._apply_backward_compatibility(frontmatter)

        # Metadata should remain unchanged
        assert migrated["metadata"]["version"] == "1.0.0"
        assert migrated["metadata"]["author"] == "testuser"

    def test_parse_allowed_tools_space_delimited_to_list(self):
        """Test allowed-tools is parsed from space-delimited string to list."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "allowed-tools": "Bash Read Write",
        }

        migrated = registry._apply_backward_compatibility(frontmatter)

        # Should be converted to list
        assert migrated["allowed-tools"] == ["Bash", "Read", "Write"]

    def test_parse_allowed_tools_already_list(self):
        """Test allowed-tools that is already a list is not modified."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "allowed-tools": ["Bash", "Read", "Write"],
        }

        migrated = registry._apply_backward_compatibility(frontmatter)

        # Should remain a list
        assert migrated["allowed-tools"] == ["Bash", "Read", "Write"]

    def test_default_compatibility_added(self):
        """Test default compatibility is added if not present."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
        }

        migrated = registry._apply_backward_compatibility(frontmatter)

        # Should add default compatibility
        assert migrated["compatibility"] == "claude-code"

    def test_existing_compatibility_not_overridden(self):
        """Test existing compatibility is not overridden."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "compatibility": "Requires Python 3.9+",
        }

        migrated = registry._apply_backward_compatibility(frontmatter)

        # Should preserve existing compatibility
        assert migrated["compatibility"] == "Requires Python 3.9+"


class TestSkillCreationFromFrontmatter:
    """Test skill creation from frontmatter."""

    def test_create_skill_spec_compliant(self):
        """Test creating skill from spec-compliant frontmatter."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "api-development",
            "description": "Build REST APIs with FastAPI",
            "license": "Apache-2.0",
            "compatibility": "Requires Python 3.9+, FastAPI",
            "metadata": {
                "version": "2.1.0",
                "author": "claude-mpm-skills",
                "updated": "2025-01-17",
                "tags": ["python", "api", "fastapi"],
            },
            "allowed-tools": ["Bash", "Read", "Write"],
        }

        skill = registry._create_skill_from_frontmatter(
            frontmatter,
            Path("/tmp/api-development.md"),
            "# API Development\n\nContent here",
            "bundled",
        )

        assert skill is not None
        assert skill.name == "api-development"
        assert skill.description == "Build REST APIs with FastAPI"
        assert skill.license == "Apache-2.0"
        assert skill.compatibility == "Requires Python 3.9+, FastAPI"
        assert skill.metadata["version"] == "2.1.0"
        assert skill.metadata["author"] == "claude-mpm-skills"
        assert skill.allowed_tools == ["Bash", "Read", "Write"]
        assert skill.version == "2.1.0"  # Derived from metadata
        assert skill.source == "bundled"

    def test_create_skill_legacy_format(self):
        """Test creating skill from legacy claude-mpm format."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "my-skill",
            "description": "My custom skill",
            "version": "1.0.0",
            "author": "myname",
            "updated": "2025-01-17",
            "tags": ["python", "api"],
            "category": "api-development",
            "toolchain": "python",
        }

        # Apply backward compatibility before creating skill
        frontmatter = registry._apply_backward_compatibility(frontmatter)

        skill = registry._create_skill_from_frontmatter(
            frontmatter,
            Path("/tmp/my-skill.md"),
            "# My Skill\n\nContent here",
            "user",
        )

        assert skill is not None
        assert skill.name == "my-skill"
        assert skill.version == "1.0.0"
        assert skill.metadata["version"] == "1.0.0"  # Auto-migrated
        assert skill.metadata["author"] == "myname"
        assert skill.category == "api-development"
        assert skill.toolchain == "python"
        assert skill.compatibility == "claude-code"  # Default added

    def test_create_skill_missing_name_uses_filename(self):
        """Test skill uses filename stem if name not in frontmatter."""
        registry = SkillsRegistry()

        frontmatter = {
            "description": "Test skill without name",
        }

        frontmatter = registry._apply_backward_compatibility(frontmatter)

        skill = registry._create_skill_from_frontmatter(
            frontmatter,
            Path("/tmp/my-skill.md"),
            "# Skill\n\nContent here",
            "user",
        )

        assert skill is not None
        assert skill.name == "my-skill"  # From filename

    def test_create_skill_missing_required_fields_returns_none(self):
        """Test skill creation returns None if required fields missing."""
        registry = SkillsRegistry()

        # Missing both name and description (can't infer description without content)
        frontmatter = {}

        skill = registry._create_skill_from_frontmatter(
            frontmatter, Path("/tmp/test.md"), "", "user"
        )

        assert skill is None


class TestClaudeMpmExtensions:
    """Test claude-mpm specific extensions are preserved."""

    def test_progressive_disclosure_preserved(self):
        """Test progressive_disclosure field is preserved."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test",
            "progressive_disclosure": {
                "entry_point": {
                    "summary": "Quick patterns",
                    "when_to_use": "Building APIs",
                }
            },
        }

        frontmatter = registry._apply_backward_compatibility(frontmatter)

        skill = registry._create_skill_from_frontmatter(
            frontmatter,
            Path("/tmp/test.md"),
            "# Test\n\nContent",
            "bundled",
        )

        assert skill is not None
        assert skill.progressive_disclosure is not None
        assert "entry_point" in skill.progressive_disclosure

    def test_user_invocable_preserved(self):
        """Test user-invocable field is preserved."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test",
            "user-invocable": True,
        }

        frontmatter = registry._apply_backward_compatibility(frontmatter)

        skill = registry._create_skill_from_frontmatter(
            frontmatter,
            Path("/tmp/test.md"),
            "# Test\n\nContent",
            "bundled",
        )

        assert skill is not None
        assert skill.user_invocable is True

    def test_category_and_toolchain_preserved(self):
        """Test category and toolchain fields are preserved."""
        registry = SkillsRegistry()

        frontmatter = {
            "name": "test-skill",
            "description": "Test",
            "category": "backend-development",
            "toolchain": "python",
        }

        frontmatter = registry._apply_backward_compatibility(frontmatter)

        skill = registry._create_skill_from_frontmatter(
            frontmatter,
            Path("/tmp/test.md"),
            "# Test\n\nContent",
            "bundled",
        )

        assert skill is not None
        assert skill.category == "backend-development"
        assert skill.toolchain == "python"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
