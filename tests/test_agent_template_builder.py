#!/usr/bin/env python3
"""
Tests for AgentTemplateBuilder Service
=====================================

Comprehensive test suite for the extracted AgentTemplateBuilder service.
Tests all template building, merging, and formatting functionality.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_template_builder import (
    AgentTemplateBuilder,
)


class TestAgentTemplateBuilder:
    """Test suite for AgentTemplateBuilder."""

    @pytest.fixture
    def template_builder(self):
        """Create AgentTemplateBuilder instance."""
        return AgentTemplateBuilder()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tmp_path as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_template_data(self):
        """Sample template data for testing."""
        return {
            "name": "test-agent",
            "description": "Test agent for validation",
            "model": "sonnet",
            "tools": ["Read", "Write", "Edit"],
            "when_to_use": ["Testing", "Validation"],
            "specialized_knowledge": ["Test frameworks"],
            "unique_capabilities": ["Test execution"],
            "configuration_fields": {"timeout": 300, "max_tokens": 4000},
        }

    @pytest.fixture
    def sample_template_file(self, temp_dir, sample_template_data):
        """Create sample template file."""
        template_file = temp_dir / "test_agent.json"
        template_file.write_text(json.dumps(sample_template_data, indent=2))
        return template_file

    @pytest.fixture
    def base_agent_data(self):
        """Sample base agent data."""
        return {
            "content": "# Base Agent Instructions\n\nCore functionality for all agents.",
            "when_to_use": ["General tasks"],
            "specialized_knowledge": ["Basic operations"],
            "configuration_fields": {"model": "haiku", "tools": ["Read", "Write"]},
        }

    def test_initialization(self):
        """Test AgentTemplateBuilder initialization."""
        assert hasattr(self, "logger")
        assert self.logger is not None

    def test_build_agent_markdown_basic(
        self, template_builder, sample_template_file, base_agent_data
    ):
        """Test basic markdown building."""
        result = template_builder.build_agent_markdown(
            agent_name="test_agent",
            template_path=sample_template_file,
            base_agent_data=base_agent_data,
        )

        assert isinstance(result, str)
        assert "---" in result  # YAML frontmatter
        assert "name: test-agent" in result
        assert "model: sonnet" in result
        assert "tools: Read,Write,Edit" in result
        assert "# Base Agent Instructions" in result

    def test_build_agent_markdown_invalid_name(
        self, template_builder, sample_template_file, base_agent_data
    ):
        """Test markdown building with invalid agent name."""
        with pytest.raises(ValueError, match="does not meet Claude Code requirements"):
            template_builder.build_agent_markdown(
                agent_name="Invalid@Name!",  # Contains invalid characters
                template_path=sample_template_file,
                base_agent_data=base_agent_data,
            )

    def test_build_agent_markdown_tools_with_spaces(
        self, template_builder, temp_dir, base_agent_data
    ):
        """Test markdown building with invalid tools format."""
        # Create template with spaces in tools
        invalid_template_data = {
            "name": "test-agent",
            "tools": "Read, Write, Edit",  # Invalid: contains spaces
        }
        template_file = temp_dir / "invalid.json"
        template_file.write_text(json.dumps(invalid_template_data))

        with pytest.raises(
            ValueError, match="Tools must be comma-separated WITHOUT spaces"
        ):
            template_builder.build_agent_markdown(
                agent_name="test_agent",
                template_path=template_file,
                base_agent_data=base_agent_data,
            )

    def test_build_agent_markdown_missing_file(
        self, template_builder, temp_dir, base_agent_data
    ):
        """Test markdown building with missing template file."""
        missing_file = temp_dir / "missing.json"

        with pytest.raises(FileNotFoundError):
            template_builder.build_agent_markdown(
                agent_name="test_agent",
                template_path=missing_file,
                base_agent_data=base_agent_data,
            )

    def test_build_agent_markdown_invalid_json(
        self, template_builder, temp_dir, base_agent_data
    ):
        """Test markdown building with invalid JSON."""
        invalid_file = temp_dir / "invalid.json"
        invalid_file.write_text("{ invalid json")

        with pytest.raises(json.JSONDecodeError):
            template_builder.build_agent_markdown(
                agent_name="test_agent",
                template_path=invalid_file,
                base_agent_data=base_agent_data,
            )

    def test_build_agent_yaml_basic(
        self, template_builder, sample_template_file, base_agent_data
    ):
        """Test basic YAML building."""
        result = template_builder.build_agent_yaml(
            agent_name="test_agent",
            template_path=sample_template_file,
            base_agent_data=base_agent_data,
        )

        assert isinstance(result, str)
        assert "name: test-agent" in result
        assert "description:" in result
        assert "model:" in result
        assert "tools:" in result
        assert "- Read" in result

    def test_merge_narrative_fields(self):
        """Test merging narrative fields."""
        base_data = {
            "when_to_use": ["General tasks"],
            "specialized_knowledge": ["Basic operations"],
        }
        template_data = {
            "when_to_use": [
                "Testing",
                "General tasks",
            ],  # Overlap should be deduplicated
            "specialized_knowledge": ["Test frameworks"],
            "unique_capabilities": ["Test execution"],
        }

        result = self.merge_narrative_fields(base_data, template_data)

        assert "when_to_use" in result
        assert "specialized_knowledge" in result
        assert "unique_capabilities" in result

        # Check deduplication
        assert (
            len(result["when_to_use"]) == 2
        )  # "General tasks" should appear only once
        assert "General tasks" in result["when_to_use"]
        assert "Testing" in result["when_to_use"]

    def test_merge_configuration_fields(self):
        """Test merging configuration fields."""
        base_data = {
            "configuration_fields": {
                "model": "haiku",
                "timeout": 300,
                "tools": ["Read", "Write"],
            }
        }
        template_data = {
            "configuration_fields": {
                "model": "sonnet",  # Should override base
                "max_tokens": 4000,  # Should be added
            },
            "tools": ["Read", "Write", "Edit"],  # Direct field should override
        }

        result = self.merge_configuration_fields(base_data, template_data)

        assert result["model"] == "sonnet"  # Template overrides base
        assert result["timeout"] == 300  # Base value preserved
        assert result["max_tokens"] == 4000  # Template value added
        assert result["tools"] == ["Read", "Write", "Edit"]  # Direct field overrides

    def test_extract_agent_metadata(self):
        """Test extracting metadata from template content."""
        template_content = """# Agent Template

## When to Use
- Testing applications
- Validating functionality

## Specialized Knowledge
- Test frameworks
- Quality assurance

## Unique Capabilities
- Automated testing
- Bug detection
"""

        result = self.extract_agent_metadata(template_content)

        assert "when_to_use" in result
        assert "specialized_knowledge" in result
        assert "unique_capabilities" in result

        assert "Testing applications" in result["when_to_use"]
        assert "Test frameworks" in result["specialized_knowledge"]
        assert "Automated testing" in result["unique_capabilities"]

    def test_format_yaml_list(self):
        """Test YAML list formatting."""
        items = ["Read", "Write", "Edit"]
        result = self.format_yaml_list(items, 2)

        expected = "  - Read\n  - Write\n  - Edit"
        assert result == expected

    def test_format_yaml_list_empty(self):
        """Test YAML list formatting with empty list."""
        result = self.format_yaml_list([], 2)
        assert result == ""

    def test_model_mapping(self, temp_dir, base_agent_data):
        """Test model name mapping."""
        template_data = {
            "name": "test-agent",
            "model": "claude-3-5-sonnet-20241022",  # Should map to 'sonnet'
        }
        template_file = temp_dir / "model_test.json"
        template_file.write_text(json.dumps(template_data))

        result = self.build_agent_markdown(
            agent_name="test_agent",
            template_path=template_file,
            base_agent_data=base_agent_data,
        )

        assert "model: sonnet" in result

    def test_fallback_values(self, temp_dir, base_agent_data):
        """Test fallback values when template fields are missing."""
        minimal_template = {"name": "minimal-agent"}
        template_file = temp_dir / "minimal.json"
        template_file.write_text(json.dumps(minimal_template))

        result = self.build_agent_markdown(
            agent_name="minimal_agent",
            template_path=template_file,
            base_agent_data=base_agent_data,
        )

        # Should use fallback values
        assert "model: sonnet" in result  # Default model
        # Default tools are not included in YAML when agent has full capabilities
        # This is intentional for Claude Code compatibility
        assert "tools:" not in result  # Tools field omitted for full-capability agents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
