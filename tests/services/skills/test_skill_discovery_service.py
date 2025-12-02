"""Tests for skill discovery service.

Test Coverage:
- Skill file discovery and parsing
- YAML frontmatter extraction and validation
- Skill ID generation
- Bundled resource detection
- Error handling for malformed files
"""

import tempfile
from pathlib import Path

import pytest

from src.claude_mpm.services.skills.skill_discovery_service import (
    SkillDiscoveryService, SkillMetadata)


class TestSkillDiscoveryService:
    """Tests for SkillDiscoveryService class."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary directory for skill files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def service(self, temp_skills_dir):
        """Create a SkillDiscoveryService instance for testing."""
        return SkillDiscoveryService(temp_skills_dir)

    def test_initialization(self, temp_skills_dir):
        """Test service initialization."""
        service = SkillDiscoveryService(temp_skills_dir)
        assert service.skills_dir == temp_skills_dir

    def test_discover_skills_empty_directory(self, service):
        """Test discover_skills() returns empty list for empty directory."""
        skills = service.discover_skills()
        assert skills == []

    def test_discover_skills_nonexistent_directory(self):
        """Test discover_skills() handles non-existent directory."""
        service = SkillDiscoveryService(Path("/nonexistent/path"))
        skills = service.discover_skills()
        assert skills == []

    def test_discover_skills_valid_skill_file(self, service, temp_skills_dir):
        """Test discover_skills() parses valid skill file."""
        # Create valid skill file
        skill_content = """---
name: Code Review
description: Comprehensive code review skill
skill_version: 1.0.0
tags: [review, quality]
agent_types: [engineer, qa]
---

# Code Review Skill

This skill provides comprehensive code review capabilities.
"""
        skill_file = temp_skills_dir / "code-review.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        skills = service.discover_skills()

        assert len(skills) == 1
        skill = skills[0]
        assert skill["skill_id"] == "code-review"
        assert skill["name"] == "Code Review"
        assert skill["description"] == "Comprehensive code review skill"
        assert skill["skill_version"] == "1.0.0"
        assert skill["tags"] == ["review", "quality"]
        assert skill["agent_types"] == ["engineer", "qa"]
        assert "Code Review Skill" in skill["content"]

    def test_discover_skills_multiple_files(self, service, temp_skills_dir):
        """Test discover_skills() finds multiple skill files."""
        # Create multiple skill files
        for i in range(3):
            skill_content = f"""---
name: Skill {i}
description: Test skill {i}
---

Content {i}
"""
            skill_file = temp_skills_dir / f"skill-{i}.md"
            skill_file.write_text(skill_content, encoding="utf-8")

        skills = service.discover_skills()

        assert len(skills) == 3
        skill_names = [s["name"] for s in skills]
        assert "Skill 0" in skill_names
        assert "Skill 1" in skill_names
        assert "Skill 2" in skill_names

    def test_discover_skills_skips_invalid_files(self, service, temp_skills_dir):
        """Test discover_skills() skips files with invalid frontmatter."""
        # Create valid skill
        valid_content = """---
name: Valid Skill
description: This is valid
---

Content
"""
        (temp_skills_dir / "valid.md").write_text(valid_content, encoding="utf-8")

        # Create invalid skill (no frontmatter)
        invalid_content = "Just plain text without frontmatter"
        (temp_skills_dir / "invalid.md").write_text(invalid_content, encoding="utf-8")

        skills = service.discover_skills()

        # Should only find valid skill
        assert len(skills) == 1
        assert skills[0]["name"] == "Valid Skill"

    def test_parse_skill_file_missing_name(self, service, temp_skills_dir):
        """Test parsing fails when 'name' field is missing."""
        skill_content = """---
description: Missing name field
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)
        assert result is None

    def test_parse_skill_file_missing_description(self, service, temp_skills_dir):
        """Test parsing fails when 'description' field is missing."""
        skill_content = """---
name: Test Skill
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)
        assert result is None

    def test_parse_skill_file_optional_fields_defaults(self, service, temp_skills_dir):
        """Test parsing uses defaults for optional fields."""
        skill_content = """---
name: Test Skill
description: Minimal skill
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)

        assert result is not None
        assert result["skill_version"] == "1.0.0"  # Default version
        assert result["tags"] == []  # Default empty tags
        assert "agent_types" not in result  # Optional field

    def test_parse_skill_file_tags_as_string(self, service, temp_skills_dir):
        """Test parsing converts string tag to list."""
        skill_content = """---
name: Test Skill
description: Test
tags: single-tag
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)

        assert result["tags"] == ["single-tag"]

    def test_parse_skill_file_agent_types_as_string(self, service, temp_skills_dir):
        """Test parsing converts string agent_types to list."""
        skill_content = """---
name: Test Skill
description: Test
agent_types: engineer
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)

        assert result["agent_types"] == ["engineer"]

    def test_extract_frontmatter_valid(self, service):
        """Test YAML frontmatter extraction."""
        content = """---
name: Test
description: Test skill
tags: [tag1, tag2]
---

# Skill Body

This is the skill content.
"""
        frontmatter, body = service._extract_frontmatter(content)

        assert frontmatter["name"] == "Test"
        assert frontmatter["description"] == "Test skill"
        assert frontmatter["tags"] == ["tag1", "tag2"]
        assert "# Skill Body" in body
        assert "skill content" in body

    def test_extract_frontmatter_missing_raises_error(self, service):
        """Test extraction raises error when frontmatter is missing."""
        content = "Just content without frontmatter"

        with pytest.raises(ValueError, match="No valid YAML frontmatter"):
            service._extract_frontmatter(content)

    def test_extract_frontmatter_invalid_yaml_raises_error(self, service):
        """Test extraction raises error for invalid YAML."""
        content = """---
invalid: yaml: content:
---

Content
"""
        with pytest.raises(ValueError, match="Invalid YAML in frontmatter"):
            service._extract_frontmatter(content)

    def test_extract_frontmatter_non_dict_raises_error(self, service):
        """Test extraction raises error when frontmatter is not a dict."""
        content = """---
- list
- item
---

Content
"""
        with pytest.raises(ValueError, match="must be a YAML dictionary"):
            service._extract_frontmatter(content)

    def test_generate_skill_id_basic(self, service):
        """Test skill ID generation from name."""
        assert service._generate_skill_id("Code Review") == "code-review"
        assert service._generate_skill_id("Python Style") == "python-style"

    def test_generate_skill_id_underscores(self, service):
        """Test skill ID generation replaces underscores."""
        assert service._generate_skill_id("test_skill_name") == "test-skill-name"

    def test_generate_skill_id_special_characters(self, service):
        """Test skill ID generation removes special characters."""
        assert service._generate_skill_id("Test!@#$Skill") == "testskill"
        assert service._generate_skill_id("Code-Review!") == "code-review"

    def test_generate_skill_id_multiple_hyphens(self, service):
        """Test skill ID generation collapses multiple hyphens."""
        assert service._generate_skill_id("test---skill") == "test-skill"
        assert service._generate_skill_id("a  b  c") == "a-b-c"

    def test_generate_skill_id_leading_trailing_hyphens(self, service):
        """Test skill ID generation removes leading/trailing hyphens."""
        assert service._generate_skill_id("-test-") == "test"
        assert service._generate_skill_id("--test--") == "test"

    def test_find_bundled_resources_none(self, service, temp_skills_dir):
        """Test resource detection when no resources exist."""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text("content", encoding="utf-8")

        resources = service._find_bundled_resources(skill_file)
        assert resources == []

    def test_find_bundled_resources_scripts(self, service, temp_skills_dir):
        """Test resource detection finds scripts."""
        # Create skill file
        skill_file = temp_skills_dir / "test-skill.md"
        skill_file.write_text("content", encoding="utf-8")

        # Create scripts directory with resources
        scripts_dir = temp_skills_dir / "scripts" / "test-skill"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "helper.sh").write_text("#!/bin/bash", encoding="utf-8")
        (scripts_dir / "setup.py").write_text("# setup", encoding="utf-8")

        resources = service._find_bundled_resources(skill_file)

        assert len(resources) == 2
        resource_names = [r.name for r in resources]
        assert "helper.sh" in resource_names
        assert "setup.py" in resource_names

    def test_find_bundled_resources_references(self, service, temp_skills_dir):
        """Test resource detection finds references."""
        skill_file = temp_skills_dir / "test-skill.md"
        skill_file.write_text("content", encoding="utf-8")

        # Create references directory
        refs_dir = temp_skills_dir / "references" / "test-skill"
        refs_dir.mkdir(parents=True)
        (refs_dir / "docs.md").write_text("# Docs", encoding="utf-8")

        resources = service._find_bundled_resources(skill_file)

        assert len(resources) == 1
        assert resources[0].name == "docs.md"

    def test_find_bundled_resources_assets(self, service, temp_skills_dir):
        """Test resource detection finds assets."""
        skill_file = temp_skills_dir / "test-skill.md"
        skill_file.write_text("content", encoding="utf-8")

        # Create assets directory
        assets_dir = temp_skills_dir / "assets" / "test-skill"
        assets_dir.mkdir(parents=True)
        (assets_dir / "image.png").write_text("fake image", encoding="utf-8")

        resources = service._find_bundled_resources(skill_file)

        assert len(resources) == 1
        assert resources[0].name == "image.png"

    def test_find_bundled_resources_multiple_types(self, service, temp_skills_dir):
        """Test resource detection finds resources from multiple directories."""
        skill_file = temp_skills_dir / "test-skill.md"
        skill_file.write_text("content", encoding="utf-8")

        # Create all resource types
        for resource_type in ["scripts", "references", "assets"]:
            resource_dir = temp_skills_dir / resource_type / "test-skill"
            resource_dir.mkdir(parents=True)
            (resource_dir / f"file.{resource_type}").write_text(
                "content", encoding="utf-8"
            )

        resources = service._find_bundled_resources(skill_file)

        assert len(resources) == 3

    def test_find_bundled_resources_nested_files(self, service, temp_skills_dir):
        """Test resource detection finds files in nested directories."""
        skill_file = temp_skills_dir / "test-skill.md"
        skill_file.write_text("content", encoding="utf-8")

        # Create nested structure
        scripts_dir = temp_skills_dir / "scripts" / "test-skill" / "subdir"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "nested.sh").write_text("#!/bin/bash", encoding="utf-8")

        resources = service._find_bundled_resources(skill_file)

        assert len(resources) == 1
        assert resources[0].name == "nested.sh"

    def test_get_skill_metadata_existing(self, service, temp_skills_dir):
        """Test get_skill_metadata() returns metadata for existing skill."""
        skill_content = """---
name: Test Skill
description: Test description
skill_version: 2.0.0
tags: [test]
agent_types: [engineer]
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        metadata = service.get_skill_metadata("Test Skill")

        assert metadata is not None
        assert isinstance(metadata, SkillMetadata)
        assert metadata.name == "Test Skill"
        assert metadata.description == "Test description"
        assert metadata.skill_version == "2.0.0"
        assert metadata.tags == ["test"]
        assert metadata.agent_types == ["engineer"]

    def test_get_skill_metadata_nonexistent(self, service):
        """Test get_skill_metadata() returns None for non-existent skill."""
        metadata = service.get_skill_metadata("Nonexistent Skill")
        assert metadata is None

    def test_get_skill_metadata_with_resources(self, service, temp_skills_dir):
        """Test get_skill_metadata() includes bundled resources."""
        skill_content = """---
name: Test Skill
description: Test
---

Content
"""
        skill_file = temp_skills_dir / "test-skill.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        # Add resource
        scripts_dir = temp_skills_dir / "scripts" / "test-skill"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "helper.sh").write_text("#!/bin/bash", encoding="utf-8")

        metadata = service.get_skill_metadata("Test Skill")

        assert metadata is not None
        assert len(metadata.resources) == 1
        assert metadata.resources[0].name == "helper.sh"

    def test_repr(self, service, temp_skills_dir):
        """Test string representation."""
        repr_str = repr(service)

        assert "SkillDiscoveryService" in repr_str
        assert str(temp_skills_dir) in repr_str

    def test_parse_skill_file_preserves_content(self, service, temp_skills_dir):
        """Test that skill content is preserved exactly."""
        skill_content = """---
name: Test
description: Test
---

# Important Content

This is **markdown** with `code` blocks:

```python
def test():
    pass
```

And lists:
- Item 1
- Item 2
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)

        assert "# Important Content" in result["content"]
        assert "**markdown**" in result["content"]
        assert "```python" in result["content"]
        assert "def test():" in result["content"]

    def test_parse_skill_file_multiline_description(self, service, temp_skills_dir):
        """Test parsing multiline description in frontmatter."""
        skill_content = """---
name: Test
description: >
  This is a multi-line
  description that spans
  multiple lines.
---

Content
"""
        skill_file = temp_skills_dir / "test.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        result = service._parse_skill_file(skill_file)

        assert "multi-line" in result["description"]
        assert "description" in result["description"]

    def test_discover_skills_ignores_non_markdown_files(self, service, temp_skills_dir):
        """Test that discovery ignores non-.md files."""
        # Create valid skill
        skill_content = """---
name: Test
description: Test
---

Content
"""
        (temp_skills_dir / "skill.md").write_text(skill_content, encoding="utf-8")

        # Create non-markdown files
        (temp_skills_dir / "README.txt").write_text("readme", encoding="utf-8")
        (temp_skills_dir / "config.yaml").write_text("config", encoding="utf-8")

        skills = service.discover_skills()

        # Should only find .md file
        assert len(skills) == 1
        assert skills[0]["name"] == "Test"
