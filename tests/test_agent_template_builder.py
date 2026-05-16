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
    def temp_dir(self, tmp_path):
        """Create temporary directory for testing."""
        temp_dir = tmp_path
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

    def test_initialization(self, template_builder):
        """Test AgentTemplateBuilder initialization."""
        assert hasattr(template_builder, "logger")
        assert template_builder.logger is not None

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
        """Test markdown building with tools format containing spaces (now handled gracefully)."""
        # Create template with spaces in tools — normalize_tools_input now handles this
        # by splitting on comma and stripping whitespace (no longer raises ValueError)
        template_data = {
            "name": "test-agent",
            "tools": "Read, Write, Edit",  # Spaces in comma-separated string
        }
        template_file = temp_dir / "spaces.json"
        template_file.write_text(json.dumps(template_data))

        # The current implementation normalizes the tools (splits and strips)
        # rather than raising a ValueError. Verify it produces valid output.
        result = template_builder.build_agent_markdown(
            agent_name="test_agent",
            template_path=template_file,
            base_agent_data=base_agent_data,
        )
        assert isinstance(result, str)
        assert "name: test-agent" in result

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

    def test_merge_narrative_fields(self, template_builder):
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

        result = template_builder.merge_narrative_fields(base_data, template_data)

        assert "when_to_use" in result
        assert "specialized_knowledge" in result
        assert "unique_capabilities" in result

        # Check deduplication
        assert (
            len(result["when_to_use"]) == 2
        )  # "General tasks" should appear only once
        assert "General tasks" in result["when_to_use"]
        assert "Testing" in result["when_to_use"]

    def test_merge_configuration_fields(self, template_builder):
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

        result = template_builder.merge_configuration_fields(base_data, template_data)

        assert result["model"] == "sonnet"  # Template overrides base
        assert result["timeout"] == 300  # Base value preserved
        assert result["max_tokens"] == 4000  # Template value added
        assert result["tools"] == ["Read", "Write", "Edit"]  # Direct field overrides

    def test_extract_agent_metadata(self, template_builder):
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

        result = template_builder.extract_agent_metadata(template_content)

        assert "when_to_use" in result
        assert "specialized_knowledge" in result
        assert "unique_capabilities" in result

        assert "Testing applications" in result["when_to_use"]
        assert "Test frameworks" in result["specialized_knowledge"]
        assert "Automated testing" in result["unique_capabilities"]

    def test_format_yaml_list(self, template_builder):
        """Test YAML list formatting."""
        items = ["Read", "Write", "Edit"]
        result = template_builder.format_yaml_list(items, 2)

        expected = "  - Read\n  - Write\n  - Edit"
        assert result == expected

    def test_format_yaml_list_empty(self, template_builder):
        """Test YAML list formatting with empty list."""
        result = template_builder.format_yaml_list([], 2)
        assert result == ""

    def test_model_mapping(self, template_builder, temp_dir, base_agent_data):
        """Test model name mapping."""
        template_data = {
            "name": "test-agent",
            "model": "claude-3-5-sonnet-20241022",  # Should map to 'sonnet'
        }
        template_file = temp_dir / "model_test.json"
        template_file.write_text(json.dumps(template_data))

        result = template_builder.build_agent_markdown(
            agent_name="test_agent",
            template_path=template_file,
            base_agent_data=base_agent_data,
        )

        assert "model: sonnet" in result

    def test_fallback_values(self, template_builder, temp_dir, base_agent_data):
        """Test fallback values when template fields are missing."""
        minimal_template = {"name": "minimal-agent"}
        template_file = temp_dir / "minimal.json"
        template_file.write_text(json.dumps(minimal_template))

        result = template_builder.build_agent_markdown(
            agent_name="minimal_agent",
            template_path=template_file,
            base_agent_data=base_agent_data,
        )

        # Should produce valid markdown with the YAML frontmatter
        assert isinstance(result, str)
        assert "---" in result  # YAML frontmatter
        assert "name: minimal-agent" in result  # Name from template
        # Default tools are not included in YAML when agent has full capabilities
        # This is intentional for Claude Code compatibility
        assert "tools:" not in result  # Tools field omitted for full-capability agents

    def _build_with_resource_tier(
        self, template_builder, temp_dir, base_agent_data, **template_overrides
    ):
        """Helper: build agent markdown from a template with given fields."""
        template_data = {"name": "tier-agent", **template_overrides}
        template_file = temp_dir / "tier_test.json"
        template_file.write_text(json.dumps(template_data))
        return template_builder.build_agent_markdown(
            agent_name="tier_agent",
            template_path=template_file,
            base_agent_data=base_agent_data,
        )

    def test_resource_tier_intensive_injects_opus_thorough(
        self, template_builder, temp_dir, base_agent_data
    ):
        """`intensive` tier should inject model: opus and effort: thorough."""
        result = self._build_with_resource_tier(
            template_builder, temp_dir, base_agent_data, resource_tier="intensive"
        )

        assert "model: opus" in result
        assert "effort: thorough" in result

    def test_resource_tier_lightweight_injects_haiku_balanced(
        self, template_builder, temp_dir, base_agent_data
    ):
        """`lightweight` tier should inject model: haiku and effort: balanced."""
        result = self._build_with_resource_tier(
            template_builder, temp_dir, base_agent_data, resource_tier="lightweight"
        )

        assert "model: haiku" in result
        assert "effort: balanced" in result

    def test_resource_tier_high_injects_sonnet_thorough(
        self, template_builder, temp_dir, base_agent_data
    ):
        """`high` tier should inject model: sonnet and effort: thorough."""
        result = self._build_with_resource_tier(
            template_builder, temp_dir, base_agent_data, resource_tier="high"
        )

        assert "model: sonnet" in result
        assert "effort: thorough" in result

    def test_resource_tier_explicit_model_preserved(
        self, template_builder, temp_dir, base_agent_data
    ):
        """An explicit `model` in the source must NOT be overwritten by tier injection."""
        result = self._build_with_resource_tier(
            template_builder,
            temp_dir,
            base_agent_data,
            resource_tier="lightweight",  # would normally inject haiku
            model="opus",  # explicit override
        )

        assert "model: opus" in result
        assert "model: haiku" not in result
        # effort still injected from tier since not explicitly set
        assert "effort: balanced" in result

    def test_resource_tier_explicit_effort_preserved(
        self, template_builder, temp_dir, base_agent_data
    ):
        """An explicit `effort` in the source must NOT be overwritten by tier injection."""
        result = self._build_with_resource_tier(
            template_builder,
            temp_dir,
            base_agent_data,
            resource_tier="intensive",  # would normally inject thorough
            effort="balanced",  # explicit override
        )

        assert "effort: balanced" in result
        assert "effort: thorough" not in result

    def test_resource_tier_unknown_falls_back_to_sonnet_balanced(
        self, template_builder, temp_dir, base_agent_data
    ):
        """An unrecognized tier should fall back to model: sonnet and effort: balanced."""
        result = self._build_with_resource_tier(
            template_builder, temp_dir, base_agent_data, resource_tier="bogus-tier"
        )

        assert "model: sonnet" in result
        assert "effort: balanced" in result

    def test_resource_tier_missing_falls_back_to_sonnet_balanced(
        self, template_builder, temp_dir, base_agent_data
    ):
        """A template with no resource_tier should fall back to sonnet/balanced."""
        result = self._build_with_resource_tier(
            template_builder, temp_dir, base_agent_data
        )

        assert "model: sonnet" in result
        assert "effort: balanced" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
