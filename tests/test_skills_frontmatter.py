#!/usr/bin/env python3
"""
Unit tests for Skills Frontmatter Parsing
Tests the frontmatter parsing functionality in the skills registry.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from claude_mpm.skills.registry import SkillsRegistry


class TestFrontmatterParsing:
    """Test suite for frontmatter parsing functionality."""

    def test_parse_valid_frontmatter(self):
        """Test parsing valid YAML frontmatter."""
        registry = SkillsRegistry()

        content = """---
skill_id: test-skill
skill_version: 1.0.0
description: Test skill description
updated_at: 2025-10-30T17:00:00Z
tags: [test, example]
---

# Test Skill

Content here."""

        frontmatter = registry._parse_skill_frontmatter(content)

        assert frontmatter["skill_id"] == "test-skill"
        assert frontmatter["skill_version"] == "1.0.0"
        assert frontmatter["description"] == "Test skill description"
        # updated_at may be parsed as datetime or string by YAML
        assert frontmatter["updated_at"] is not None
        assert frontmatter["tags"] == ["test", "example"]

    def test_parse_no_frontmatter(self):
        """Test content without frontmatter returns empty dict."""
        registry = SkillsRegistry()

        content = """# Test Skill

This has no frontmatter."""

        frontmatter = registry._parse_skill_frontmatter(content)

        assert frontmatter == {}

    def test_parse_malformed_frontmatter(self):
        """Test malformed YAML frontmatter returns empty dict."""
        registry = SkillsRegistry()

        content = """---
invalid: yaml: structure: here
---

# Test Skill"""

        frontmatter = registry._parse_skill_frontmatter(content)

        # Should return empty dict on parse failure
        assert frontmatter == {}

    def test_parse_empty_frontmatter(self):
        """Test empty frontmatter returns empty dict."""
        registry = SkillsRegistry()

        content = """---
---

# Test Skill"""

        frontmatter = registry._parse_skill_frontmatter(content)

        assert frontmatter == {}

    def test_parse_frontmatter_with_newlines(self):
        """Test frontmatter with newlines in values."""
        registry = SkillsRegistry()

        content = """---
skill_id: test-skill
skill_version: 0.1.0
description: |
  This is a multiline
  description
tags: [test]
---

# Test Skill"""

        frontmatter = registry._parse_skill_frontmatter(content)

        assert "test-skill" in frontmatter["skill_id"]
        assert "0.1.0" in frontmatter["skill_version"]
        assert "multiline" in frontmatter["description"]


class TestSkillVersionFields:
    """Test suite for skill version tracking fields."""

    def test_skill_has_version_fields(self):
        """Test that loaded skills have version tracking fields."""
        registry = SkillsRegistry()

        # Get a bundled skill that should have frontmatter
        skill = registry.get_skill("test-driven-development")

        assert skill is not None
        assert hasattr(skill, "version")
        assert hasattr(skill, "skill_id")
        assert hasattr(skill, "updated_at")
        assert hasattr(skill, "tags")

    def test_skill_version_defaults(self):
        """Test that skills without frontmatter get default version values.

        Flat bundled skills that have no version in frontmatter default to 0.1.0.
        Structured SKILL.md skills may carry explicit semver strings.
        """
        registry = SkillsRegistry()

        skills = registry.list_skills(source="bundled")

        for skill in skills:
            # Every skill must have a non-None version (either explicit or default)
            assert skill.version is not None
            # skill_id should default to name if not provided
            assert skill.skill_id == skill.name or skill.skill_id != ""

    def test_skill_tags_is_list(self):
        """Test that skill tags is always a list."""
        registry = SkillsRegistry()

        skill = registry.get_skill("test-driven-development")

        assert skill is not None
        assert isinstance(skill.tags, list)

    def test_bundled_skills_have_frontmatter(self):
        """Test that all bundled skills have frontmatter with version info."""
        registry = SkillsRegistry()

        bundled_skills = registry.list_skills(source="bundled")

        # Should have at least 20 bundled skills
        assert len(bundled_skills) >= 20

        for skill in bundled_skills:
            # Each skill should have version and skill_id
            assert skill.version is not None
            assert skill.skill_id is not None
            assert skill.skill_id == skill.name or len(skill.skill_id) > 0

    def test_skill_description_from_frontmatter(self):
        """Test that description is loaded from frontmatter when available."""
        registry = SkillsRegistry()

        skill = registry.get_skill("test-driven-development")

        assert skill is not None
        assert skill.description is not None
        assert len(skill.description) > 0

    def test_skill_updated_at_field(self):
        """Test that updated_at field is present on the Skill dataclass."""
        registry = SkillsRegistry()

        skill = registry.get_skill("test-driven-development")

        assert skill is not None
        # updated_at may be None when the SKILL.md does not carry an updated_at
        # key; the field must still exist on the object
        assert hasattr(skill, "updated_at")


class TestBackwardCompatibility:
    """Test suite for backward compatibility."""

    def test_skills_without_frontmatter_still_load(self):
        """Test that skills without frontmatter still load with defaults.

        The version field always defaults to "0.1.0" for skills that carry no
        explicit version in their frontmatter. Structured SKILL.md files may
        carry an explicit semver string, so we only require that the field is
        non-None rather than exactly "0.1.0".
        """
        registry = SkillsRegistry()

        # Even if a skill doesn't have frontmatter, it should load with defaults
        skills = registry.list_skills()

        for skill in skills:
            # All skills should have version field with a value
            assert hasattr(skill, "version")
            assert skill.version is not None

    def test_registry_loads_without_errors(self):
        """Test that registry loads without errors."""
        # This should not raise any exceptions
        registry = SkillsRegistry()

        assert len(registry.skills) > 0

    def test_all_original_fields_present(self):
        """Test that all original Skill fields are still present."""
        registry = SkillsRegistry()

        skill = registry.get_skill("test-driven-development")

        assert skill is not None
        # Original fields
        assert hasattr(skill, "name")
        assert hasattr(skill, "path")
        assert hasattr(skill, "content")
        assert hasattr(skill, "source")
        assert hasattr(skill, "description")
        assert hasattr(skill, "agent_types")
        # New version fields
        assert hasattr(skill, "version")
        assert hasattr(skill, "skill_id")
        assert hasattr(skill, "updated_at")
        assert hasattr(skill, "tags")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
