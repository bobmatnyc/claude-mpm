"""Tests for AgentOutputFormatter service.

WHY: Comprehensive testing ensures the formatter handles all output scenarios
correctly, maintains consistency across formats, and handles edge cases properly.
"""

import json

import pytest
import yaml

from claude_mpm.services.cli.agent_output_formatter import (
    AgentOutputFormatter,
    IAgentOutputFormatter,
)


class TestAgentOutputFormatter:
    """Test suite for AgentOutputFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return AgentOutputFormatter()

    @pytest.fixture
    def sample_agents(self):
        """Sample agent data for testing."""
        return [
            {
                "name": "engineer",
                "file": "engineer.json",
                "version": "1.0.0",
                "description": "Engineering agent for code implementation",
                "path": "/path/to/engineer.json",
                "tier": "system",
                "specializations": ["python", "typescript"],
            },
            {
                "name": "qa",
                "file": "qa.json",
                "version": "1.2.0",
                "description": "Quality assurance agent",
                "path": "/path/to/qa.json",
                "tier": "project",
            },
        ]

    @pytest.fixture
    def sample_dependencies(self):
        """Sample dependency data for testing."""
        return {
            "python": ["requests", "pytest", "mypy"],
            "system": ["git", "docker"],
            "missing": {"python": ["pandas", "numpy"], "system": ["kubectl"]},
        }

    @pytest.fixture
    def sample_deployment_result(self):
        """Sample deployment result for testing."""
        return {
            "deployed_count": 3,
            "deployed": [{"name": "engineer"}, {"name": "qa"}, {"name": "security"}],
            "updated_count": 2,
            "updated": [{"name": "documentation"}, {"name": "research"}],
            "skipped": [{"name": "base"}],
            "errors": [],
            "target_dir": "/home/user/.claude/agents",
        }

    @pytest.fixture
    def sample_cleanup_result(self):
        """Sample cleanup result for testing."""
        return {
            "orphaned": [
                {"name": "old-agent", "version": "0.9.0"},
                {"name": "deprecated", "version": "1.0.0"},
            ],
            "removed": ["old-agent", "deprecated"],
            "errors": [],
        }

    def test_implements_interface(self, formatter):
        """Test that formatter implements the interface."""
        assert isinstance(formatter, IAgentOutputFormatter)

    def test_format_agent_list_text(self, formatter, sample_agents):
        """Test formatting agent list as text."""
        result = formatter.format_agent_list(sample_agents, output_format="text")

        assert "Available Agents:" in result
        assert "engineer" in result
        assert "qa" in result
        assert "Engineering agent for code implementation" in result
        assert "Quality assurance agent" in result

    def test_format_agent_list_text_quiet(self, formatter, sample_agents):
        """Test formatting agent list in quiet mode."""
        result = formatter.format_agent_list(
            sample_agents, output_format="text", quiet=True
        )

        assert "Available Agents:" not in result
        assert "engineer" in result
        assert "qa" in result
        # Descriptions should not be shown in quiet mode
        assert "Engineering agent" not in result

    def test_format_agent_list_text_verbose(self, formatter, sample_agents):
        """Test formatting agent list in verbose mode."""
        result = formatter.format_agent_list(
            sample_agents, output_format="text", verbose=True
        )

        assert "engineer" in result
        assert "qa" in result
        assert "/path/to/engineer.json" in result
        assert "Tier: system" in result
        assert "Tier: project" in result
        assert "Specializations: python, typescript" in result

    def test_format_agent_list_json(self, formatter, sample_agents):
        """Test formatting agent list as JSON."""
        result = formatter.format_agent_list(sample_agents, output_format="json")
        data = json.loads(result)

        assert data["count"] == 2
        assert len(data["agents"]) == 2
        assert data["agents"][0]["name"] == "engineer"
        assert data["agents"][1]["name"] == "qa"

    def test_format_agent_list_yaml(self, formatter, sample_agents):
        """Test formatting agent list as YAML."""
        result = formatter.format_agent_list(sample_agents, output_format="yaml")
        data = yaml.safe_load(result)

        assert data["count"] == 2
        assert len(data["agents"]) == 2
        assert data["agents"][0]["name"] == "engineer"

    def test_format_agent_list_table(self, formatter, sample_agents):
        """Test formatting agent list as table."""
        result = formatter.format_agent_list(sample_agents, output_format="table")

        assert "Name" in result
        assert "Version" in result
        assert "Description" in result
        assert "engineer" in result
        assert "1.0.0" in result
        assert "qa" in result
        assert "1.2.0" in result

    def test_format_agent_list_empty(self, formatter):
        """Test formatting empty agent list."""
        result = formatter.format_agent_list([], output_format="text")
        assert "No agents found" in result

        result_json = formatter.format_agent_list([], output_format="json")
        data = json.loads(result_json)
        assert data["count"] == 0
        assert data["agents"] == []

    def test_format_agent_details_text(self, formatter, sample_agents):
        """Test formatting single agent details as text."""
        agent = sample_agents[0]
        result = formatter.format_agent_details(agent, output_format="text")

        assert "Agent: engineer" in result
        assert "File: engineer.json" in result
        assert "Version: 1.0.0" in result
        assert "Description: Engineering agent" in result
        assert "Tier: system" in result
        assert "Specializations: python, typescript" in result

    def test_format_agent_details_verbose(self, formatter):
        """Test formatting agent details in verbose mode."""
        agent = {
            "name": "test",
            "dependencies": {"python": ["requests", "pytest"], "system": ["git"]},
            "metadata": {"author": "test-author", "created": "2024-01-01"},
        }
        result = formatter.format_agent_details(
            agent, output_format="text", verbose=True
        )

        assert "Dependencies:" in result
        assert "Python: requests, pytest" in result
        assert "System: git" in result
        assert "Metadata:" in result
        assert "author: test-author" in result

    def test_format_dependency_report_text(self, formatter, sample_dependencies):
        """Test formatting dependency report as text."""
        result = formatter.format_dependency_report(
            sample_dependencies, output_format="text"
        )

        assert "Agent Dependencies:" in result
        assert "Python Dependencies (3):" in result
        assert "requests" in result
        assert "pytest" in result
        assert "System Dependencies (2):" in result
        assert "git" in result
        assert "Missing Python: 2" in result
        assert "pandas" in result
        assert "Missing System: 1" in result
        assert "kubectl" in result

    def test_format_dependency_report_with_status(self, formatter):
        """Test formatting dependencies with installation status."""
        deps = {
            "python": [
                {"name": "requests", "installed": True},
                {"name": "pandas", "installed": False},
            ]
        }
        result = formatter.format_dependency_report(
            deps, output_format="text", show_status=True
        )

        assert "✓ requests" in result
        assert "✗ pandas" in result

    def test_format_deployment_result_text(self, formatter, sample_deployment_result):
        """Test formatting deployment result as text."""
        result = formatter.format_deployment_result(
            sample_deployment_result, output_format="text"
        )

        assert "✓ Deployed 3 agents" in result
        assert "✓ Updated 2 agents" in result
        assert "→ Skipped 1 up-to-date agents" in result
        assert "Target directory: /home/user/.claude/agents" in result

    def test_format_deployment_result_verbose(
        self, formatter, sample_deployment_result
    ):
        """Test formatting deployment result in verbose mode."""
        result = formatter.format_deployment_result(
            sample_deployment_result, output_format="text", verbose=True
        )

        assert "- engineer" in result
        assert "- qa" in result
        assert "- security" in result
        assert "- documentation" in result
        assert "- research" in result
        assert "- base" in result

    def test_format_deployment_result_with_errors(self, formatter):
        """Test formatting deployment result with errors."""
        result_data = {
            "deployed_count": 1,
            "errors": ["Failed to deploy agent X", "Permission denied"],
        }
        result = formatter.format_deployment_result(result_data, output_format="text")

        assert "❌ Encountered 2 errors:" in result
        assert "Failed to deploy agent X" in result
        assert "Permission denied" in result

    def test_format_deployment_result_no_changes(self, formatter):
        """Test formatting deployment result with no changes."""
        result_data = {}
        result = formatter.format_deployment_result(result_data, output_format="text")
        assert "No agents were deployed (all up to date)" in result

    def test_format_cleanup_result_dry_run(self, formatter, sample_cleanup_result):
        """Test formatting cleanup result for dry run."""
        result = formatter.format_cleanup_result(
            sample_cleanup_result, output_format="text", dry_run=True
        )

        assert "Found 2 orphaned agent(s):" in result
        assert "old-agent v0.9.0" in result
        assert "deprecated v1.0.0" in result
        assert "This was a dry run" in result
        assert "Use --force to actually remove" in result

    def test_format_cleanup_result_actual(self, formatter, sample_cleanup_result):
        """Test formatting actual cleanup result."""
        result = formatter.format_cleanup_result(
            sample_cleanup_result, output_format="text", dry_run=False
        )

        assert "Successfully removed 2 orphaned agent(s)" in result
        assert "- old-agent" in result
        assert "- deprecated" in result

    def test_format_cleanup_result_no_orphans(self, formatter):
        """Test formatting cleanup with no orphaned agents."""
        result_data = {"orphaned": []}
        result = formatter.format_cleanup_result(
            result_data, output_format="text", dry_run=True
        )
        assert "✅ No orphaned agents found" in result

    def test_format_cleanup_result_with_errors(self, formatter):
        """Test formatting cleanup result with errors."""
        result_data = {
            "removed": ["agent1"],
            "errors": ["Failed to remove agent2", "Permission denied"],
        }
        result = formatter.format_cleanup_result(
            result_data, output_format="text", dry_run=False
        )

        assert "Successfully removed 1 orphaned agent(s)" in result
        assert "❌ Encountered 2 error(s):" in result
        assert "Failed to remove agent2" in result

    def test_format_as_json_pretty(self, formatter):
        """Test JSON formatting with pretty printing."""
        data = {"key": "value", "number": 42}
        result = formatter.format_as_json(data, pretty=True)

        assert '"key": "value"' in result
        assert '"number": 42' in result
        assert "\n" in result  # Pretty printing adds newlines

    def test_format_as_json_compact(self, formatter):
        """Test JSON formatting without pretty printing."""
        data = {"key": "value", "number": 42}
        result = formatter.format_as_json(data, pretty=False)

        assert (
            '{"key": "value", "number": 42}' in result
            or '{"number": 42, "key": "value"}' in result
        )
        assert "\n" not in result  # Compact format has no newlines

    def test_format_as_yaml(self, formatter):
        """Test YAML formatting."""
        data = {"agents": ["engineer", "qa"], "count": 2}
        result = formatter.format_as_yaml(data)

        parsed = yaml.safe_load(result)
        assert parsed["agents"] == ["engineer", "qa"]
        assert parsed["count"] == 2

    def test_format_as_table(self, formatter):
        """Test table formatting."""
        headers = ["Name", "Version", "Status"]
        rows = [
            ["engineer", "1.0.0", "Active"],
            ["qa", "1.2.0", "Active"],
            ["deprecated", "0.9.0", "Inactive"],
        ]

        result = formatter.format_as_table(headers, rows)

        assert "Name" in result
        assert "Version" in result
        assert "Status" in result
        assert "engineer" in result
        assert "1.0.0" in result
        assert "Active" in result
        assert "-" * 10 in result  # Separator line

    def test_format_as_table_empty(self, formatter):
        """Test table formatting with empty data."""
        headers = ["Name", "Value"]
        rows = []

        result = formatter.format_as_table(headers, rows)

        assert "Name" in result
        assert "Value" in result
        # Should have header and separator but no data rows
        lines = result.split("\n")
        assert len(lines) == 2  # Header and separator only

    def test_format_as_table_uneven_rows(self, formatter):
        """Test table formatting with uneven row lengths."""
        headers = ["Col1", "Col2", "Col3"]
        rows = [
            ["A", "B", "C"],
            ["D", "E"],  # Missing third column
            ["F"],  # Missing two columns
        ]

        result = formatter.format_as_table(headers, rows)

        # Should handle missing columns gracefully
        assert "Col1" in result
        assert "Col2" in result
        assert "Col3" in result
        assert "A" in result
        assert "B" in result
        assert "C" in result
        assert "D" in result
        assert "E" in result
        assert "F" in result

    def test_format_as_table_long_content(self, formatter):
        """Test table formatting with long content."""
        headers = ["Short", "Long Content"]
        rows = [
            [
                "A",
                "This is a very long piece of content that should still be displayed",
            ],
            ["B", "Short"],
        ]

        result = formatter.format_as_table(headers, rows, min_column_width=5)

        # Should expand column to fit content
        assert "This is a very long piece of content" in result

    def test_handle_null_values(self, formatter):
        """Test handling of null/None values."""
        agents = [{"name": "test", "version": None, "description": None}]

        # Should handle None values gracefully
        result = formatter.format_agent_list(agents, output_format="text")
        assert "test" in result

        result_json = formatter.format_agent_list(agents, output_format="json")
        data = json.loads(result_json)
        assert data["agents"][0]["version"] is None

    def test_large_dataset_performance(self, formatter):
        """Test performance with large datasets."""
        # Create a large dataset
        large_agents = [
            {
                "name": f"agent_{i}",
                "file": f"agent_{i}.json",
                "version": f"1.0.{i}",
                "description": f"Description for agent {i}" * 10,  # Long description
                "path": f"/very/long/path/to/agent/files/agent_{i}.json",
                "specializations": [f"spec_{j}" for j in range(10)],
            }
            for i in range(100)
        ]

        # Should handle large datasets without issues
        result = formatter.format_agent_list(large_agents, output_format="text")
        assert "agent_0" in result
        assert "agent_99" in result

        result_json = formatter.format_agent_list(large_agents, output_format="json")
        data = json.loads(result_json)
        assert data["count"] == 100

        result_table = formatter.format_agent_list(large_agents, output_format="table")
        assert "agent_0" in result_table
