#!/usr/bin/env python3
"""
Unit tests for JSON to Markdown migration script.

Tests conversion logic, validation, error handling, and CLI options.
"""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migrate_json_to_markdown import (
    ConversionResult,
    JSONParseError,
    MigrationReport,
    ValidationError,
    build_markdown,
    convert_json_to_markdown,
    extract_frontmatter_fields,
    migrate_templates,
    safe_convert,
)

# Fixtures


@pytest.fixture
def minimal_template():
    """Minimal valid agent template."""
    return {
        "schema_version": "1.3.0",
        "agent_id": "test-agent",
        "agent_version": "1.0.0",
        "agent_type": "engineer",
        "metadata": {
            "name": "Test Agent",
            "description": "Test description for agent",
            "tags": ["test", "example"],
        },
        "capabilities": {
            "model": "sonnet",
            "resource_tier": "standard",
        },
        "instructions": "# Test Instructions\n\nTest content here.",
    }


@pytest.fixture
def full_template():
    """Full-featured agent template with all optional fields."""
    return {
        "schema_version": "1.3.0",
        "agent_id": "full-test-agent",
        "agent_version": "2.5.3",
        "template_version": "1.2.0",
        "template_changelog": [
            {
                "version": "1.2.0",
                "date": "2025-11-29",
                "description": "Added new features",
            }
        ],
        "agent_type": "research",
        "metadata": {
            "name": "Full Test Agent",
            "description": "Complete test agent with all fields populated",
            "tags": ["test", "research", "comprehensive"],
            "category": "research",
            "color": "blue",
            "author": "Test Author",
        },
        "capabilities": {
            "model": "opus",
            "resource_tier": "intensive",
            "temperature": 0.7,
            "max_tokens": 8192,
            "timeout": 3600,
            "memory_limit": 8192,
            "cpu_limit": 90,
            "network_access": True,
        },
        "dependencies": {
            "python": ["pytest>=7.0.0", "mypy>=1.0.0"],
            "system": ["git", "docker"],
        },
        "skills": ["debugging", "testing", "optimization"],
        "instructions": "# Full Test Agent\n\nComprehensive instructions here.",
        "knowledge": {
            "domain_expertise": ["Testing", "Research"],
            "best_practices": ["TDD", "Documentation"],
        },
    }


@pytest.fixture
def invalid_json_template():
    """Template with invalid JSON syntax."""
    return '{ "invalid": json, syntax" }'


@pytest.fixture
def missing_required_fields_template():
    """Template missing required metadata fields."""
    return {
        "schema_version": "1.3.0",
        "agent_id": "incomplete-agent",
        "agent_version": "1.0.0",
        "agent_type": "engineer",
        "metadata": {
            "tags": ["test"]
            # Missing: name, description
        },
        "capabilities": {
            # Missing: model, resource_tier
        },
        "instructions": "Test",
    }


# Unit Tests


class TestExtractFrontmatterFields:
    """Test frontmatter field extraction from JSON templates."""

    def test_minimal_template(self, minimal_template):
        """Test extraction with minimal required fields."""
        frontmatter = extract_frontmatter_fields(minimal_template)

        assert frontmatter["name"] == "Test Agent"
        assert frontmatter["agent_id"] == "test-agent"
        assert frontmatter["model"] == "sonnet"
        assert frontmatter["resource_tier"] == "standard"
        assert frontmatter["version"] == "1.0.0"
        assert frontmatter["schema_version"] == "1.3.0"
        assert frontmatter["agent_type"] == "engineer"
        assert frontmatter["tags"] == ["test", "example"]

    def test_full_template(self, full_template):
        """Test extraction with all optional fields."""
        frontmatter = extract_frontmatter_fields(full_template)

        # Core fields
        assert frontmatter["name"] == "Full Test Agent"
        assert frontmatter["version"] == "2.5.3"

        # Metadata fields
        assert frontmatter["category"] == "research"
        assert frontmatter["color"] == "blue"
        assert frontmatter["author"] == "Test Author"

        # Capability fields
        assert frontmatter["temperature"] == 0.7
        assert frontmatter["max_tokens"] == 8192
        assert frontmatter["timeout"] == 3600

        # Nested capabilities
        assert "capabilities" in frontmatter
        assert frontmatter["capabilities"]["memory_limit"] == 8192
        assert frontmatter["capabilities"]["cpu_limit"] == 90
        assert frontmatter["capabilities"]["network_access"] is True

        # Extended fields
        assert "dependencies" in frontmatter
        assert frontmatter["dependencies"]["python"] == ["pytest>=7.0.0", "mypy>=1.0.0"]

        assert "skills" in frontmatter
        assert frontmatter["skills"] == ["debugging", "testing", "optimization"]

        assert "template_version" in frontmatter
        assert frontmatter["template_version"] == "1.2.0"

        assert "template_changelog" in frontmatter
        assert len(frontmatter["template_changelog"]) == 1

        assert "knowledge" in frontmatter
        assert frontmatter["knowledge"]["domain_expertise"] == ["Testing", "Research"]

    def test_missing_optional_fields(self, minimal_template):
        """Test that missing optional fields are not included."""
        frontmatter = extract_frontmatter_fields(minimal_template)

        # Optional fields should not be present
        assert "category" not in frontmatter
        assert "color" not in frontmatter
        assert "author" not in frontmatter
        assert "temperature" not in frontmatter
        assert "capabilities" not in frontmatter  # No nested caps
        assert "dependencies" not in frontmatter
        assert "skills" not in frontmatter

    def test_missing_required_fields_with_defaults(
        self, missing_required_fields_template
    ):
        """Test that missing required fields get default values."""
        frontmatter = extract_frontmatter_fields(missing_required_fields_template)

        # Should have defaults
        assert (
            frontmatter["name"] == "Agent incomplete-agent"
        )  # Generated from agent_id
        assert frontmatter["description"] == "Agent description not provided"
        assert frontmatter["model"] == "sonnet"  # Default
        assert frontmatter["resource_tier"] == "standard"  # Default


class TestBuildMarkdown:
    """Test markdown generation with YAML frontmatter."""

    def test_valid_yaml_generation(self, minimal_template):
        """Test that generated YAML is valid and parseable."""
        frontmatter = extract_frontmatter_fields(minimal_template)
        instructions = minimal_template["instructions"]

        markdown = build_markdown(frontmatter, instructions)

        # Check structure
        assert markdown.startswith("---\n")
        assert "\n---\n\n" in markdown
        assert "# Test Instructions" in markdown

        # Parse YAML to verify validity
        parts = markdown.split("---\n")
        yaml_content = parts[1]
        parsed = yaml.safe_load(yaml_content)

        assert parsed["name"] == "Test Agent"
        assert parsed["model"] == "sonnet"

    def test_nested_structures_preserved(self, full_template):
        """Test that nested structures are preserved in YAML."""
        frontmatter = extract_frontmatter_fields(full_template)
        instructions = full_template["instructions"]

        markdown = build_markdown(frontmatter, instructions)

        # Parse and verify nested structures
        parts = markdown.split("---\n")
        yaml_content = parts[1]
        parsed = yaml.safe_load(yaml_content)

        assert "capabilities" in parsed
        assert parsed["capabilities"]["memory_limit"] == 8192

        assert "dependencies" in parsed
        assert "python" in parsed["dependencies"]
        assert "pytest>=7.0.0" in parsed["dependencies"]["python"]

    def test_unicode_handling(self):
        """Test that unicode characters are handled correctly."""
        frontmatter = {
            "name": "Test Agent 🚀",
            "description": "Agent with émojis and spëcial chàrs",
            "version": "1.0.0",
            "model": "sonnet",
        }
        instructions = "# Instructions\n\nWith unicode: 中文, العربية, 日本語"

        markdown = build_markdown(frontmatter, instructions)

        assert "🚀" in markdown
        assert "émojis" in markdown
        assert "中文" in markdown

        # Verify YAML can be parsed
        parts = markdown.split("---\n")
        yaml_content = parts[1]
        parsed = yaml.safe_load(yaml_content)
        assert parsed["name"] == "Test Agent 🚀"


class TestConvertJsonToMarkdown:
    """Test full JSON to Markdown conversion."""

    def test_successful_conversion(self, tmp_path, minimal_template):
        """Test successful conversion of valid template."""
        # Write JSON template
        json_path = tmp_path / "test_agent.json"
        json_path.write_text(json.dumps(minimal_template), encoding="utf-8")

        # Convert
        markdown, validation = convert_json_to_markdown(json_path)

        # Verify output
        assert markdown.startswith("---\n")
        assert "name:" in markdown  # Name may be normalized by validator
        assert "agent_id: test-agent" in markdown
        assert "# Test Instructions" in markdown

        # Validation should pass
        assert validation.is_valid or len(validation.errors) == 0

    def test_invalid_json_raises_error(self, tmp_path):
        """Test that invalid JSON raises JSONParseError."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(JSONParseError):
            convert_json_to_markdown(json_path)

    def test_validation_warnings_reported(self, tmp_path):
        """Test that validation warnings are captured."""
        template = {
            "schema_version": "1.3.0",
            "agent_id": "test",
            "agent_version": "1.0.0",
            "agent_type": "engineer",
            "metadata": {
                "name": "Test",
                "description": "Test agent",
                "tags": ["TEST", "Invalid_Tag"],  # Uppercase and underscore
            },
            "capabilities": {
                "model": "sonnet",
                "resource_tier": "standard",
            },
            "instructions": "Test",
        }

        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(template), encoding="utf-8")

        _markdown, validation = convert_json_to_markdown(json_path)

        # Should have warnings about tag format
        assert len(validation.warnings) > 0


class TestSafeConvert:
    """Test safe conversion with error handling."""

    def test_successful_conversion_writes_file(self, tmp_path, minimal_template):
        """Test that successful conversion writes markdown file."""
        json_path = tmp_path / "test_agent.json"
        json_path.write_text(json.dumps(minimal_template), encoding="utf-8")

        result = safe_convert(json_path, dry_run=False)

        assert result.status == "success"
        assert result.md_path is not None

        # Verify file was written
        md_path = Path(result.md_path)
        assert md_path.exists()
        assert md_path.read_text().startswith("---\n")

    def test_dry_run_does_not_write(self, tmp_path, minimal_template):
        """Test that dry-run mode doesn't write files."""
        json_path = tmp_path / "test_agent.json"
        json_path.write_text(json.dumps(minimal_template), encoding="utf-8")

        result = safe_convert(json_path, dry_run=True)

        assert result.status == "preview"

        # Verify file was NOT written
        md_path = tmp_path / "test_agent.md"
        assert not md_path.exists()

    def test_archive_mode_moves_json(self, tmp_path, minimal_template):
        """Test that archive mode moves JSON to archive directory."""
        json_path = tmp_path / "test_agent.json"
        json_path.write_text(json.dumps(minimal_template), encoding="utf-8")

        result = safe_convert(json_path, archive_mode=True, dry_run=False)

        assert result.status == "success"

        # JSON should be moved to archive
        assert not json_path.exists()
        archive_path = tmp_path / "archive" / "test_agent.json"
        assert archive_path.exists()

    def test_error_handling_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("{ invalid }", encoding="utf-8")

        result = safe_convert(json_path, dry_run=False)

        assert result.status == "error"
        assert "JSON parse error" in result.error_message

    def test_rollback_on_error(self, tmp_path):
        """Test that partial files are cleaned up on error."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("{ invalid }", encoding="utf-8")

        result = safe_convert(json_path, dry_run=False)

        # Ensure no markdown file was left behind
        md_path = tmp_path / "invalid.md"
        assert not md_path.exists()


class TestMigrateTemplates:
    """Test batch migration functionality."""

    def test_migrate_all_templates(self, tmp_path, minimal_template, full_template):
        """Test migration of multiple templates."""
        # Create multiple templates
        templates = {
            "agent1.json": minimal_template,
            "agent2.json": full_template,
        }

        for filename, template in templates.items():
            (tmp_path / filename).write_text(json.dumps(template), encoding="utf-8")

        # Migrate all
        report = migrate_templates(tmp_path, dry_run=False)

        assert report.total_templates == 2
        assert report.converted == 2
        assert report.errors == 0

        # Verify markdown files created
        assert (tmp_path / "agent1.md").exists()
        assert (tmp_path / "agent2.md").exists()

    def test_migrate_single_agent(self, tmp_path, minimal_template, full_template):
        """Test migration of specific agent."""
        (tmp_path / "agent1.json").write_text(
            json.dumps(minimal_template), encoding="utf-8"
        )
        (tmp_path / "agent2.json").write_text(
            json.dumps(full_template), encoding="utf-8"
        )

        # Migrate only agent1
        report = migrate_templates(tmp_path, agent_name="agent1", dry_run=False)

        assert report.total_templates == 1
        assert report.converted == 1

        # Only agent1 should be converted
        assert (tmp_path / "agent1.md").exists()
        assert not (tmp_path / "agent2.md").exists()

    def test_migrate_with_errors(self, tmp_path, minimal_template):
        """Test migration with some failing templates."""
        # Valid template
        (tmp_path / "valid.json").write_text(
            json.dumps(minimal_template), encoding="utf-8"
        )

        # Invalid template
        (tmp_path / "invalid.json").write_text("{ invalid }", encoding="utf-8")

        report = migrate_templates(tmp_path, dry_run=False)

        assert report.total_templates == 2
        assert report.converted == 1
        assert report.errors == 1

    def test_dry_run_no_changes(self, tmp_path, minimal_template):
        """Test that dry-run doesn't modify filesystem."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(minimal_template), encoding="utf-8")

        report = migrate_templates(tmp_path, dry_run=True)

        # JSON should still exist
        assert json_path.exists()

        # Markdown should not exist
        assert not (tmp_path / "test.md").exists()

        # Report should show preview
        assert report.converted == 1


# Integration Tests


class TestRealTemplates:
    """Test conversion of actual agent templates from the repository."""

    def test_research_template_conversion(self):
        """Test conversion of research.json template."""
        templates_dir = PROJECT_ROOT / "src" / "claude_mpm" / "agents" / "templates"
        json_path = templates_dir / "research.json"

        if not json_path.exists():
            pytest.skip("research.json not found in templates directory")

        markdown, validation = convert_json_to_markdown(json_path)

        # Verify structure
        assert markdown.startswith("---\n")
        assert "research" in markdown.lower()

        # Should be valid or have only warnings
        assert validation.is_valid or len(validation.errors) == 0

    def test_engineer_template_conversion(self):
        """Test conversion of engineer.json template."""
        templates_dir = PROJECT_ROOT / "src" / "claude_mpm" / "agents" / "templates"
        json_path = templates_dir / "engineer.json"

        if not json_path.exists():
            pytest.skip("engineer.json not found in templates directory")

        markdown, validation = convert_json_to_markdown(json_path)

        assert markdown.startswith("---\n")
        assert "engineer" in markdown.lower()
        assert validation.is_valid or len(validation.errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
