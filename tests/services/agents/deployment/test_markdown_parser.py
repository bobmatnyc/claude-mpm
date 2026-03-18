#!/usr/bin/env python3
"""
Tests for Markdown Template Parser
===================================

Tests the new Markdown template parsing functionality with YAML frontmatter.
"""

import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_template_builder import (
    AgentTemplateBuilder,
)


class TestMarkdownTemplateParser:
    """Test suite for Markdown template parsing."""

    @pytest.fixture
    def template_builder(self):
        """Create AgentTemplateBuilder instance."""
        return AgentTemplateBuilder()

    @pytest.fixture
    def markdown_template_content(self):
        """Sample Markdown template with YAML frontmatter."""
        return dedent(
            """
            ---
            name: engineer_agent
            description: Clean architecture specialist with code reduction
            version: 3.9.1
            schema_version: 1.3.0
            agent_id: engineer
            agent_type: engineer
            model: sonnet
            resource_tier: intensive
            tags:
            - engineering
            - SOLID-principles
            - clean-architecture
            category: engineering
            color: blue
            author: Claude MPM Team
            temperature: 0.2
            max_tokens: 12288
            timeout: 1200
            capabilities:
              memory_limit: 6144
              cpu_limit: 80
              network_access: true
            dependencies:
              python:
              - rope>=1.11.0
              - black>=23.0.0
            skills:
            - test-driven-development
            - systematic-debugging
            ---
            # Engineer Agent Instructions

            This is the engineer agent with specialized capabilities.

            ## Core Responsibilities
            - Write clean, maintainable code
            - Follow SOLID principles
            - Minimize code duplication

            ## Workflow
            1. Search for existing solutions
            2. Implement with minimal code
            3. Test thoroughly
        """
        ).strip()

    @pytest.fixture
    def json_template_content(self):
        """Sample JSON template for backward compatibility testing."""
        return {
            "name": "test_agent",
            "description": "Test agent for validation",
            "version": "1.0.0",
            "model": "sonnet",
            "agent_type": "general",
            "tools": ["Read", "Write", "Edit"],
            "instructions": "# Test Agent\n\nThis is a test agent.",
        }

    def test_parse_markdown_template_success(
        self, template_builder, markdown_template_content, tmp_path
    ):
        """Test successful parsing of Markdown template."""
        # Create temporary Markdown file
        template_file = tmp_path / "engineer.md"
        template_file.write_text(markdown_template_content)

        # Parse template
        result = template_builder._parse_markdown_template(template_file)

        # Verify metadata extraction
        assert result["name"] == "engineer_agent"
        assert (
            result["description"] == "Clean architecture specialist with code reduction"
        )
        assert result["version"] == "3.9.1"
        assert result["agent_type"] == "engineer"
        assert result["model"] == "sonnet"

        # Verify tags (list format)
        assert "tags" in result
        assert isinstance(result["tags"], list)
        assert "engineering" in result["tags"]
        assert "SOLID-principles" in result["tags"]

        # Verify capabilities
        assert "capabilities" in result
        assert result["capabilities"]["memory_limit"] == 6144
        assert result["capabilities"]["cpu_limit"] == 80
        assert result["capabilities"]["network_access"] is True

        # Verify dependencies
        assert "dependencies" in result
        assert "python" in result["dependencies"]
        assert "rope>=1.11.0" in result["dependencies"]["python"]

        # Verify skills
        assert "skills" in result
        assert "test-driven-development" in result["skills"]

        # Verify instructions were extracted
        assert "instructions" in result
        assert "# Engineer Agent Instructions" in result["instructions"]
        assert "Core Responsibilities" in result["instructions"]

    def test_parse_markdown_template_missing_frontmatter(
        self, template_builder, tmp_path
    ):
        """Test error handling for missing YAML frontmatter."""
        # Create Markdown file without frontmatter
        template_file = tmp_path / "invalid.md"
        template_file.write_text("# Just a regular markdown file")

        # Should raise ValueError
        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            template_builder._parse_markdown_template(template_file)

    def test_parse_markdown_template_malformed_frontmatter(
        self, template_builder, tmp_path
    ):
        """Test error handling for malformed frontmatter."""
        # Create file with only one --- delimiter
        template_file = tmp_path / "malformed.md"
        template_file.write_text("---\nname: test\n# Missing closing delimiter")

        # Should raise ValueError
        with pytest.raises(ValueError, match="Malformed YAML frontmatter"):
            template_builder._parse_markdown_template(template_file)

    def test_parse_markdown_template_invalid_yaml(self, template_builder, tmp_path):
        """Test error handling for invalid YAML syntax."""
        template_file = tmp_path / "invalid_yaml.md"
        template_file.write_text(
            dedent(
                """
            ---
            name: test
            invalid: yaml: syntax: error
            ---
            # Content
        """
            ).strip()
        )

        # Should raise yaml.YAMLError
        with pytest.raises(yaml.YAMLError):
            template_builder._parse_markdown_template(template_file)

    def test_parse_markdown_template_missing_required_fields(
        self, template_builder, tmp_path
    ):
        """Test error handling for missing required fields."""
        template_file = tmp_path / "missing_fields.md"
        template_file.write_text(
            dedent(
                """
            ---
            name: test_agent
            # Missing description and version
            ---
            # Content
        """
            ).strip()
        )

        # Should raise ValueError with missing fields
        with pytest.raises(ValueError, match="Missing required fields"):
            template_builder._parse_markdown_template(template_file)

    def test_normalize_metadata_structure(self, template_builder):
        """Test metadata normalization for consistent structure."""
        metadata = {
            "name": "test",
            "description": "Test agent",
            "version": "1.0.0",
            "model": "sonnet",
            "memory_limit": 4096,
            "cpu_limit": 50,
            "network_access": True,
        }

        template_builder._normalize_metadata_structure(metadata)

        # Verify capabilities dict was created
        assert "capabilities" in metadata
        assert metadata["capabilities"]["memory_limit"] == 4096
        assert metadata["capabilities"]["cpu_limit"] == 50
        assert metadata["capabilities"]["network_access"] is True
        assert metadata["capabilities"]["model"] == "sonnet"

        # Verify fields were moved (not duplicated)
        assert "memory_limit" not in metadata
        assert "cpu_limit" not in metadata
        assert "network_access" not in metadata

    def test_build_agent_markdown_with_markdown_template(
        self, template_builder, markdown_template_content, tmp_path
    ):
        """Test building agent markdown from Markdown template."""
        # Create temporary Markdown file
        template_file = tmp_path / "engineer.md"
        template_file.write_text(markdown_template_content)

        # Build agent markdown
        base_agent_data = {}
        result = template_builder.build_agent_markdown(
            agent_name="engineer",
            template_path=template_file,
            base_agent_data=base_agent_data,
            source_info="test",
        )

        # Verify result is a string
        assert isinstance(result, str)

        # Verify frontmatter exists
        assert result.startswith("---")
        assert "name: engineer-agent" in result or "name: engineer" in result

        # Verify instructions are included
        assert "Engineer Agent Instructions" in result

    def test_build_agent_markdown_with_json_template(
        self, template_builder, json_template_content, tmp_path
    ):
        """Test backward compatibility with JSON templates."""
        # Create temporary JSON file
        template_file = tmp_path / "test.json"
        import json

        template_file.write_text(json.dumps(json_template_content, indent=2))

        # Build agent markdown
        base_agent_data = {}
        result = template_builder.build_agent_markdown(
            agent_name="test",
            template_path=template_file,
            base_agent_data=base_agent_data,
            source_info="test",
        )

        # Verify result is a string
        assert isinstance(result, str)

        # Verify frontmatter exists
        assert result.startswith("---")
        assert "name: test" in result

    def test_build_agent_markdown_unsupported_format(self, template_builder, tmp_path):
        """Test error handling for unsupported file formats."""
        # Create file with unsupported extension
        template_file = tmp_path / "test.txt"
        template_file.write_text("Some content")

        base_agent_data = {}

        # Should raise ValueError
        with pytest.raises(ValueError, match="Unsupported template format"):
            template_builder.build_agent_markdown(
                agent_name="test",
                template_path=template_file,
                base_agent_data=base_agent_data,
            )

    def test_markdown_template_with_minimal_fields(self, template_builder, tmp_path):
        """Test Markdown template with only required fields."""
        minimal_template = dedent(
            """
            ---
            name: minimal_agent
            description: Minimal test agent
            version: 1.0.0
            ---
            # Minimal Agent

            Basic instructions.
        """
        ).strip()

        template_file = tmp_path / "minimal.md"
        template_file.write_text(minimal_template)

        # Should parse successfully
        result = template_builder._parse_markdown_template(template_file)

        assert result["name"] == "minimal_agent"
        assert result["description"] == "Minimal test agent"
        assert result["version"] == "1.0.0"
        assert "# Minimal Agent" in result["instructions"]

    def test_markdown_template_with_complex_dependencies(
        self, template_builder, tmp_path
    ):
        """Test parsing complex dependency structures."""
        template_content = dedent(
            """
            ---
            name: complex_agent
            description: Agent with complex dependencies
            version: 1.0.0
            dependencies:
              python:
              - package1>=1.0.0
              - package2>=2.0.0
              system:
              - git
              - docker
              optional: false
            ---
            # Complex Agent
        """
        ).strip()

        template_file = tmp_path / "complex.md"
        template_file.write_text(template_content)

        result = template_builder._parse_markdown_template(template_file)

        assert "dependencies" in result
        assert "python" in result["dependencies"]
        assert "system" in result["dependencies"]
        assert len(result["dependencies"]["python"]) == 2
        assert len(result["dependencies"]["system"]) == 2
        assert result["dependencies"]["optional"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
