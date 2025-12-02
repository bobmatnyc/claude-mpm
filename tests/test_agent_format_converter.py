#!/usr/bin/env python3
"""
Tests for AgentFormatConverter Service
=====================================

Comprehensive test suite for the extracted AgentFormatConverter service.
Tests all format conversion, migration, and content transformation functionality.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_format_converter import (
    AgentFormatConverter,
)


class TestAgentFormatConverter:
    """Test suite for AgentFormatConverter."""

    @pytest.fixture
    def format_converter(self):
        """Create AgentFormatConverter instance."""
        return AgentFormatConverter()

    @pytest.fixture
    def temp_dir_with_yaml(self):
        """Create temporary directory with YAML files."""
        with tmp_path as temp_dir:
            temp_path = Path(temp_dir)

            # Create test YAML files
            yaml_content = """name: test-agent
description: "Test agent for testing"
version: "1.0.0"
tools: "Read,Write,Edit"
model: "sonnet"
instructions: |
  This is a test agent.
  It performs testing tasks."""

            yaml_file = temp_path / "test-agent.yaml"
            yaml_file.write_text(yaml_content)

            # Create another YAML file
            yaml_content2 = """name: qa-agent
description: "QA agent for quality assurance"
version: "2.0.0"
tools: ["Read", "Write", "Test"]
model: "haiku"
"""

            yaml_file2 = temp_path / "qa-agent.yaml"
            yaml_file2.write_text(yaml_content2)

            yield temp_path

    def test_initialization(self):
        """Test AgentFormatConverter initialization."""
        assert hasattr(self, "logger")
        assert self.logger is not None

    def test_convert_yaml_to_md_success(self, temp_dir_with_yaml):
        """Test successful YAML to MD conversion."""
        results = self.convert_yaml_to_md(temp_dir_with_yaml)

        assert len(results["converted"]) == 2
        assert len(results["errors"]) == 0
        assert len(results["skipped"]) == 0

        # Check that MD files were created
        assert (temp_dir_with_yaml / "test-agent.md").exists()
        assert (temp_dir_with_yaml / "qa-agent.md").exists()

        # Check that YAML files were removed
        assert not (temp_dir_with_yaml / "test-agent.yaml").exists()
        assert not (temp_dir_with_yaml / "qa-agent.yaml").exists()

    def test_convert_yaml_to_md_skip_newer_md(
        self, format_converter, temp_dir_with_yaml
    ):
        """Test skipping conversion when MD file is newer."""
        temp_dir_with_yaml / "test-agent.yaml"
        md_file = temp_dir_with_yaml / "test-agent.md"

        # Create MD file with newer timestamp
        md_file.write_text("# Existing MD file")
        md_file.touch()  # Update timestamp

        results = format_converter.convert_yaml_to_md(temp_dir_with_yaml)

        # Should skip the file with newer MD
        assert "test-agent.yaml" in results["skipped"]
        assert len(results["converted"]) == 1  # Only qa-agent should be converted

    def test_convert_yaml_to_md_nonexistent_directory(self):
        """Test conversion with nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        results = self.convert_yaml_to_md(nonexistent_dir)

        assert results["converted"] == []
        assert results["errors"] == []
        assert results["skipped"] == []

    def test_convert_yaml_content_to_md(self):
        """Test YAML content to MD conversion."""
        yaml_content = """name: test-agent
description: "Test agent for testing"
version: "1.0.0"
tools: "Read,Write,Edit"
model: "sonnet"
author: "test-author"
instructions: |
  This is a test agent.
  It performs testing tasks."""

        md_content = self.convert_yaml_content_to_md(yaml_content, "test-agent")

        # Check that it starts with YAML frontmatter
        assert md_content.startswith("---\n")
        assert "name: test-agent" in md_content
        assert 'description: "Test agent for testing"' in md_content
        assert 'version: "1.0.0"' in md_content
        assert 'author: "test-author"' in md_content

        # Check that instructions are included after frontmatter
        assert "This is a test agent." in md_content
        assert "It performs testing tasks." in md_content

    def test_extract_yaml_field_double_quotes(self):
        """Test extracting field with double quotes."""
        yaml_content = 'name: "test-agent"\ndescription: "Test description"'

        name = self.extract_yaml_field(yaml_content, "name")
        description = self.extract_yaml_field(yaml_content, "description")

        assert name == "test-agent"
        assert description == "Test description"

    def test_extract_yaml_field_single_quotes(self):
        """Test extracting field with single quotes."""
        yaml_content = "name: 'test-agent'\ndescription: 'Test description'"

        name = self.extract_yaml_field(yaml_content, "name")
        description = self.extract_yaml_field(yaml_content, "description")

        assert name == "test-agent"
        assert description == "Test description"

    def test_extract_yaml_field_no_quotes(self):
        """Test extracting field without quotes."""
        yaml_content = "name: test-agent\nversion: 1.0.0"

        name = self.extract_yaml_field(yaml_content, "name")
        version = self.extract_yaml_field(yaml_content, "version")

        assert name == "test-agent"
        assert version == "1.0.0"

    def test_extract_yaml_field_not_found(self):
        """Test extracting non-existent field."""
        yaml_content = "name: test-agent\ndescription: Test description"

        missing_field = self.extract_yaml_field(yaml_content, "missing")

        assert missing_field is None

    def test_convert_md_to_yaml(self):
        """Test converting Markdown with frontmatter to YAML."""
        md_content = """---
name: test-agent
description: "Test agent"
version: "1.0.0"
---

# Test Agent

This is a test agent with instructions."""

        yaml_content = self.convert_md_to_yaml(md_content)

        assert "name: test-agent" in yaml_content
        assert 'description: "Test agent"' in yaml_content
        assert "instructions: |" in yaml_content
        assert "  # Test Agent" in yaml_content
        assert "  This is a test agent with instructions." in yaml_content

    def test_convert_md_to_yaml_no_frontmatter(self):
        """Test converting plain content to YAML."""
        plain_content = "name: test-agent\ndescription: Test description"

        yaml_content = self.convert_md_to_yaml(plain_content)

        # Should return content as-is
        assert yaml_content == plain_content

    def test_detect_format_markdown_yaml(self):
        """Test detecting Markdown with YAML frontmatter format."""
        content = """---
name: test-agent
---

# Test Agent"""

        format_type = self.detect_format(content)
        assert format_type == "markdown_yaml"

    def test_detect_format_json(self):
        """Test detecting JSON format."""
        content = '{"name": "test-agent", "description": "Test"}'

        format_type = self.detect_format(content)
        assert format_type == "json"

    def test_detect_format_yaml(self):
        """Test detecting YAML format."""
        content = "name: test-agent\ndescription: Test description"

        format_type = self.detect_format(content)
        assert format_type == "yaml"

    def test_detect_format_unknown(self):
        """Test detecting unknown format."""
        content = "# This is just a markdown file\n\nWith some content."

        format_type = self.detect_format(content)
        assert format_type == "unknown"

    def test_normalize_agent_content_yaml_to_md(self):
        """Test normalizing YAML content to Markdown."""
        yaml_content = 'name: test-agent\ndescription: "Test agent"'

        normalized = self.normalize_agent_content(
            yaml_content, "test-agent", "markdown_yaml"
        )

        assert normalized.startswith("---\n")
        assert "name: test-agent" in normalized

    def test_normalize_agent_content_same_format(self):
        """Test normalizing content that's already in target format."""
        md_content = """---
name: test-agent
---

# Test Agent"""

        normalized = self.normalize_agent_content(
            md_content, "test-agent", "markdown_yaml"
        )

        # Should return content unchanged
        assert normalized == md_content

    def test_get_conversion_stats(self, temp_dir_with_yaml):
        """Test getting conversion statistics."""
        # Add an MD file to the directory
        md_file = temp_dir_with_yaml / "existing-agent.md"
        md_file.write_text("---\nname: existing\n---\n# Existing Agent")

        stats = self.get_conversion_stats(temp_dir_with_yaml)

        assert stats["total_files"] == 3  # 2 YAML + 1 MD
        assert stats["yaml_files"] == 2
        assert stats["md_files"] == 1
        assert stats["needs_conversion"] == 2  # 2 YAML files without corresponding MD
        assert "yaml" in stats["formats"]
        assert "markdown_yaml" in stats["formats"]

    def test_get_conversion_stats_nonexistent_directory(self):
        """Test getting stats for nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        stats = self.get_conversion_stats(nonexistent_dir)

        assert stats["total_files"] == 0
        assert stats["yaml_files"] == 0
        assert stats["md_files"] == 0
        assert stats["needs_conversion"] == 0

    def test_extract_instructions_from_yaml_with_instructions(self):
        """Test extracting instructions when instructions field exists."""
        yaml_content = """name: test-agent
instructions: |
  This is the instruction text.
  It has multiple lines."""

        instructions = self._extract_instructions_from_yaml(yaml_content, "test-agent")

        assert "This is the instruction text." in instructions
        assert "It has multiple lines." in instructions

    def test_extract_instructions_from_yaml_with_long_description(
        self, format_converter
    ):
        """Test extracting instructions from long description."""
        yaml_content = """name: test-agent
description: "This is a very long description that could serve as instructions for the agent to follow when performing tasks."
"""

        instructions = format_converter._extract_instructions_from_yaml(
            yaml_content, "test-agent"
        )

        assert "Test-Agent Agent" in instructions
        assert "very long description" in instructions

    def test_extract_instructions_from_yaml_default(self):
        """Test extracting default instructions."""
        yaml_content = """name: test-agent
description: "Short desc"
"""

        instructions = self._extract_instructions_from_yaml(yaml_content, "test-agent")

        assert "Test-Agent Agent" in instructions
        assert "specialized functionality" in instructions

    def test_convert_json_to_md(self):
        """Test converting JSON content to Markdown."""
        json_content = json.dumps(
            {
                "name": "test-agent",
                "description": "Test agent",
                "version": "1.0.0",
                "tools": ["Read", "Write"],
            }
        )

        md_content = self._convert_json_to_md(json_content, "test-agent")

        assert md_content.startswith("---\n")
        assert "name: test-agent" in md_content
        assert 'description: "Test agent"' in md_content

    def test_convert_json_to_md_invalid_json(self):
        """Test converting invalid JSON."""
        invalid_json = '{"name": "test-agent", invalid}'

        md_content = self._convert_json_to_md(invalid_json, "test-agent")

        assert "Test-Agent Agent" in md_content
        assert "Conversion failed" in md_content

    def test_convert_md_to_json(self):
        """Test converting Markdown to JSON."""
        md_content = """---
name: test-agent
description: "Test agent"
version: "1.0.0"
---

# Test Agent

Instructions here."""

        with patch("yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "name": "test-agent",
                "description": "Test agent",
                "version": "1.0.0",
            }

            json_content = self._convert_md_to_json(md_content)

            data = json.loads(json_content)
            assert data["name"] == "test-agent"
            assert data["description"] == "Test agent"
            assert "instructions" in data
            assert "Instructions here." in data["instructions"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
