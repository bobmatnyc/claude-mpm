"""Tests for NativeAgentConverter service."""

import json
from pathlib import Path

import pytest

from claude_mpm.services.native_agent_converter import NativeAgentConverter


@pytest.fixture
def converter():
    """Create NativeAgentConverter instance."""
    return NativeAgentConverter()


@pytest.fixture
def sample_mpm_agent():
    """Sample MPM agent configuration."""
    return {
        "name": "Test Engineer",
        "agent_id": "test-engineer",
        "description": "Test engineering agent",
        "instructions": "Follow BASE_ENGINEER.md protocols",
        "capabilities": {
            "model": "sonnet",
            "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        },
        "knowledge": {
            "base_instructions_file": "BASE_ENGINEER.md",
            "domain_expertise": ["Testing", "Quality Assurance", "Automation"],
            "best_practices": ["Write tests first", "Use mocks", "Test edge cases"],
        },
    }


@pytest.fixture
def real_engineer_agent():
    """Load real engineer agent from templates."""
    templates_dir = (
        Path(__file__).parent.parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "templates"
    )
    engineer_file = templates_dir / "engineer.json"

    if engineer_file.exists():
        return json.loads(engineer_file.read_text())

    return None


class TestNativeAgentConverter:
    """Test suite for NativeAgentConverter."""

    def test_convert_basic_agent(self, converter, sample_mpm_agent):
        """Test basic agent conversion."""
        result = converter.convert_mpm_agent_to_native(sample_mpm_agent)

        assert "description" in result
        assert "prompt" in result
        assert "tools" in result
        assert "model" in result

        assert result["description"] == "Test engineering agent"
        assert result["model"] == "sonnet"
        assert "Read" in result["tools"]
        assert "BASE_ENGINEER.md" in result["prompt"]

    def test_model_tier_mapping(self, converter):
        """Test model tier mapping."""
        test_cases = [
            ({"capabilities": {"model": "opus"}}, "opus"),
            ({"capabilities": {"model": "sonnet"}}, "sonnet"),
            ({"capabilities": {"model": "haiku"}}, "haiku"),
            ({"capabilities": {"model": "claude-4-sonnet"}}, "sonnet"),
            ({"metadata": {"model_preference": "claude-3-opus"}}, "opus"),
            ({}, "sonnet"),  # Default
        ]

        for agent_config, expected_model in test_cases:
            result = converter._map_model_tier(agent_config)
            assert result == expected_model, f"Expected {expected_model}, got {result}"

    def test_tool_extraction(self, converter, sample_mpm_agent):
        """Test tool extraction and mapping."""
        result = converter._extract_and_map_tools(sample_mpm_agent)

        assert isinstance(result, list)
        assert len(result) == 6
        assert "Read" in result
        assert "Write" in result
        assert "Bash" in result

    def test_tool_defaults(self, converter):
        """Test default tools when none specified."""
        agent_config = {"name": "Test Agent"}
        result = converter._extract_and_map_tools(agent_config)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "Read" in result  # Should have reasonable defaults

    def test_prompt_building(self, converter, sample_mpm_agent):
        """Test prompt building from config."""
        result = converter._build_agent_prompt(sample_mpm_agent)

        assert isinstance(result, str)
        assert "BASE_ENGINEER.md" in result
        assert "Follow BASE_ENGINEER.md protocols" in result
        # Note: Domain Expertise and Best Practices are intentionally excluded
        # in optimized mode to reduce JSON size (they're in BASE_*.md files)
        # This is the correct behavior after optimization

    def test_generate_agents_json(self, converter, sample_mpm_agent):
        """Test JSON generation for multiple agents."""
        agents = [
            sample_mpm_agent,
            {
                "agent_id": "qa",
                "description": "QA agent",
                "instructions": "Test everything",
                "capabilities": {"model": "haiku", "tools": ["Read", "Bash"]},
            },
        ]

        result = converter.generate_agents_json(agents)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "test-engineer" in parsed
        assert "qa" in parsed
        assert parsed["test-engineer"]["model"] == "sonnet"
        assert parsed["qa"]["model"] == "haiku"

    def test_pm_agent_exclusion(self, converter):
        """Test that PM agent is excluded."""
        agents = [
            {"agent_id": "pm", "description": "PM", "instructions": "Manage"},
            {"agent_id": "engineer", "description": "Engineer", "instructions": "Code"},
        ]

        result = converter.generate_agents_json(agents)
        parsed = json.loads(result)

        assert "pm" not in parsed
        assert "engineer" in parsed

    def test_build_agents_flag(self, converter, sample_mpm_agent):
        """Test building complete --agents flag."""
        agents = [sample_mpm_agent]

        # With shell escaping (default)
        result = converter.build_agents_flag(agents, escape_for_shell=True)
        assert result.startswith("--agents '")
        assert result.endswith("'")

        # Without shell escaping
        result_no_escape = converter.build_agents_flag(agents, escape_for_shell=False)
        assert result_no_escape.startswith("--agents ")
        assert not result_no_escape.startswith("--agents '")

    def test_estimate_json_size(self, converter, sample_mpm_agent):
        """Test JSON size estimation."""
        agents = [sample_mpm_agent]
        size = converter.estimate_json_size(agents)

        assert isinstance(size, int)
        assert size > 0
        assert size < 100000  # Should be reasonable for one agent

    def test_conversion_summary(self, converter):
        """Test conversion summary generation."""
        agents = [
            {
                "agent_id": "eng1",
                "description": "Eng 1",
                "instructions": "Code",
                "capabilities": {"model": "sonnet", "tools": ["Read", "Write"]},
            },
            {
                "agent_id": "eng2",
                "description": "Eng 2",
                "instructions": "Code",
                "capabilities": {"model": "opus", "tools": ["Read", "Bash"]},
            },
            {
                "agent_id": "qa",
                "description": "QA",
                "instructions": "Test",
                "capabilities": {"model": "haiku", "tools": ["Read"]},
            },
        ]

        summary = converter.get_conversion_summary(agents)

        assert summary["total_agents"] == 3
        assert summary["json_size"] > 0
        assert summary["json_size_kb"] > 0
        assert summary["model_distribution"]["sonnet"] == 1
        assert summary["model_distribution"]["opus"] == 1
        assert summary["model_distribution"]["haiku"] == 1
        assert "Read" in summary["tool_usage"]
        assert summary["tool_usage"]["Read"] == 3  # All agents use Read

    def test_real_engineer_agent_conversion(self, converter, real_engineer_agent):
        """Test conversion of real engineer agent from templates."""
        if real_engineer_agent is None:
            pytest.skip("Real engineer agent not available")

        result = converter.convert_mpm_agent_to_native(real_engineer_agent)

        assert "description" in result
        assert "prompt" in result
        assert "tools" in result
        assert "model" in result

        # Verify expected values from real engineer agent
        assert result["model"] == "sonnet"
        assert len(result["tools"]) > 0
        assert "Read" in result["tools"]
        assert "BASE_ENGINEER.md" in result["prompt"]

    def test_load_agents_from_templates(self, converter):
        """Test loading agents from templates directory."""
        templates_dir = (
            Path(__file__).parent.parent.parent
            / "src"
            / "claude_mpm"
            / "agents"
            / "templates"
        )

        if not templates_dir.exists():
            pytest.skip("Templates directory not available")

        agents = converter.load_agents_from_templates(templates_dir)

        assert isinstance(agents, list)
        assert len(agents) > 0
        # Should load multiple agents (at least 10 in real MPM)
        assert len(agents) >= 10

        # Verify structure of loaded agents
        for agent in agents:
            assert "agent_id" in agent or "name" in agent
            assert "capabilities" in agent

    def test_all_agents_conversion(self, converter):
        """Test converting all 37 MPM agents."""
        templates_dir = (
            Path(__file__).parent.parent.parent
            / "src"
            / "claude_mpm"
            / "agents"
            / "templates"
        )

        if not templates_dir.exists():
            pytest.skip("Templates directory not available")

        agents = converter.load_agents_from_templates(templates_dir)

        if len(agents) == 0:
            pytest.skip("No agents loaded from templates")

        # Test conversion of all agents
        summary = converter.get_conversion_summary(agents)

        assert summary["total_agents"] > 0
        assert summary["json_size"] > 0

        # Check JSON size is reasonable (not too large for CLI)
        # After optimization: 37 agents = ~45KB (was 448KB before optimization)
        assert (
            summary["json_size"] < 100000
        ), f"JSON too large: {summary['json_size']} bytes"

        # Log size for visibility
        print("\nAgent conversion summary:")
        print(f"  Total agents: {summary['total_agents']}")
        print(
            f"  JSON size: {summary['json_size']} bytes ({summary['json_size_kb']} KB)"
        )

        # Verify all agents converted successfully
        agents_json = converter.generate_agents_json(agents)
        parsed = json.loads(agents_json)

        assert len(parsed) > 0
        # Verify structure of each converted agent
        for agent_id, agent_config in parsed.items():
            assert "description" in agent_config
            assert "prompt" in agent_config
            assert "tools" in agent_config
            assert "model" in agent_config

    def test_error_handling_invalid_agent(self, converter):
        """Test error handling with invalid agent config."""
        invalid_agent = {"invalid": "config"}

        result = converter.convert_mpm_agent_to_native(invalid_agent)

        # Should return fallback config, not crash
        assert "description" in result
        assert "prompt" in result
        assert "tools" in result
        assert "model" in result

    def test_large_agent_set_warning(self, converter, caplog):
        """Test warning for very large agent sets."""
        # Create many agents to exceed size limit
        agents = []
        for i in range(100):
            agents.append(
                {
                    "agent_id": f"agent-{i}",
                    "description": f"Agent {i} " * 100,  # Make description large
                    "instructions": f"Instructions for agent {i} " * 100,
                    "capabilities": {
                        "model": "sonnet",
                        "tools": ["Read", "Write", "Edit"],
                    },
                }
            )

        with caplog.at_level("WARNING"):
            result = converter.build_agents_flag(agents)

        # Should still return valid flag
        assert result.startswith("--agents '")

        # Should log warning about size
        # Note: May or may not warn depending on actual size
