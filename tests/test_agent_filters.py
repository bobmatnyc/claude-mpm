"""
Unit tests for agent filtering utilities (1M-502 Phase 1).

Tests cover:
- BASE_AGENT filtering (case-insensitive)
- Deployed agent detection (new and legacy directories)
- Combined filtering operations
- Edge cases and error handling
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.utils.agent_filters import (
    apply_all_filters,
    filter_base_agents,
    filter_deployed_agents,
    get_deployed_agent_ids,
    is_base_agent,
)


class TestIsBaseAgent:
    """Test BASE_AGENT detection."""

    def test_base_agent_uppercase(self):
        """BASE_AGENT uppercase should be detected."""
        assert is_base_agent("BASE_AGENT") is True

    def test_base_agent_lowercase(self):
        """base_agent lowercase should be detected."""
        assert is_base_agent("base_agent") is True

    def test_base_agent_mixed_case(self):
        """Base_Agent mixed case should be detected."""
        assert is_base_agent("Base_Agent") is True

    def test_base_agent_with_hyphen(self):
        """base-agent with hyphen should be detected."""
        assert is_base_agent("base-agent") is True

    def test_base_agent_uppercase_hyphen(self):
        """BASE-AGENT uppercase hyphen should be detected."""
        assert is_base_agent("BASE-AGENT") is True

    def test_base_agent_no_separator(self):
        """baseagent no separator should be detected."""
        assert is_base_agent("baseagent") is True

    def test_regular_agent_not_detected(self):
        """Regular agents should not be detected as BASE_AGENT."""
        assert is_base_agent("ENGINEER") is False
        assert is_base_agent("PM") is False
        assert is_base_agent("QA") is False

    def test_partial_match_not_detected(self):
        """Partial matches should not be detected."""
        assert is_base_agent("BASE_ENGINEER") is False
        assert is_base_agent("AGENT_BASE") is False

    def test_empty_string(self):
        """Empty string should not be detected."""
        assert is_base_agent("") is False

    def test_none_value(self):
        """None value should not be detected."""
        assert is_base_agent(None) is False

    def test_base_agent_with_path_prefix(self):
        """BASE_AGENT with path prefix should be detected (1M-502 Fix #1)."""
        assert is_base_agent("qa/BASE_AGENT") is True
        assert is_base_agent("qa/BASE-AGENT") is True
        assert is_base_agent("pm/base-agent") is True
        assert is_base_agent("engineer/BASE_AGENT") is True

    def test_regular_agent_with_path_not_detected(self):
        """Regular agents with path prefix should not be BASE_AGENT."""
        assert is_base_agent("qa/QA") is False
        assert is_base_agent("pm/PM") is False
        assert is_base_agent("engineer/ENGINEER") is False


class TestFilterBaseAgents:
    """Test BASE_AGENT filtering from agent lists."""

    def test_filter_single_base_agent(self):
        """Single BASE_AGENT should be filtered out."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"agent_id": "BASE_AGENT", "name": "Base Agent"},
            {"agent_id": "PM", "name": "PM"},
        ]
        filtered = filter_base_agents(agents)
        assert len(filtered) == 2
        assert all(a["agent_id"] != "BASE_AGENT" for a in filtered)

    def test_filter_multiple_base_agent_variants(self):
        """Multiple BASE_AGENT variants should all be filtered."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"agent_id": "BASE_AGENT", "name": "Base Agent"},
            {"agent_id": "base-agent", "name": "Base Agent"},
            {"agent_id": "PM", "name": "PM"},
        ]
        filtered = filter_base_agents(agents)
        assert len(filtered) == 2
        assert "ENGINEER" in [a["agent_id"] for a in filtered]
        assert "PM" in [a["agent_id"] for a in filtered]

    def test_filter_preserves_order(self):
        """Filtering should preserve agent order."""
        agents = [
            {"agent_id": "ALPHA", "name": "Alpha"},
            {"agent_id": "BASE_AGENT", "name": "Base"},
            {"agent_id": "CHARLIE", "name": "Charlie"},
            {"agent_id": "DELTA", "name": "Delta"},
        ]
        filtered = filter_base_agents(agents)
        assert [a["agent_id"] for a in filtered] == ["ALPHA", "CHARLIE", "DELTA"]

    def test_filter_base_agent_with_path_prefix(self):
        """BASE_AGENT with path prefix should be filtered (1M-502 Fix #1)."""
        agents = [
            {"agent_id": "qa/QA", "name": "QA Agent"},
            {"agent_id": "qa/BASE_AGENT", "name": "Base QA Instructions"},
            {"agent_id": "pm/PM", "name": "PM Agent"},
            {"agent_id": "engineer/BASE-AGENT", "name": "Base Engineer"},
        ]
        filtered = filter_base_agents(agents)
        assert len(filtered) == 2
        assert "qa/QA" in [a["agent_id"] for a in filtered]
        assert "pm/PM" in [a["agent_id"] for a in filtered]
        # Verify BASE_AGENT variants are removed
        filtered_ids = [a["agent_id"] for a in filtered]
        assert "qa/BASE_AGENT" not in filtered_ids
        assert "engineer/BASE-AGENT" not in filtered_ids

    def test_filter_empty_list(self):
        """Filtering empty list should return empty list."""
        assert filter_base_agents([]) == []

    def test_filter_no_base_agent(self):
        """List without BASE_AGENT should be unchanged."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"agent_id": "PM", "name": "PM"},
        ]
        filtered = filter_base_agents(agents)
        assert len(filtered) == 2
        assert filtered == agents

    def test_filter_missing_agent_id(self):
        """Agents without agent_id should not crash."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"name": "No ID"},  # Missing agent_id
            {"agent_id": "PM", "name": "PM"},
        ]
        filtered = filter_base_agents(agents)
        assert len(filtered) == 3  # All preserved (no agent_id means not BASE_AGENT)


class TestGetDeployedAgentIds:
    """Test deployed agent detection from filesystem."""

    def test_new_architecture_detection(self):
        """Agents in .claude/agents/ should be detected (simplified architecture)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployed agent files
            (agents_dir / "ENGINEER.md").write_text("# Engineer Agent")
            (agents_dir / "PM.md").write_text("# PM Agent")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert "PM" in deployed
            assert len(deployed) == 2

    def test_legacy_architecture_detection(self):
        """Test for legacy .claude/agents/ detection (same as new architecture now)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployed agent files
            (agents_dir / "QA.md").write_text("# QA Agent")
            (agents_dir / "DEVOPS.md").write_text("# DevOps Agent")

            deployed = get_deployed_agent_ids(project_dir)
            assert "QA" in deployed
            assert "DEVOPS" in deployed
            assert len(deployed) == 2

    def test_both_architectures_detection(self):
        """Multiple agents in single deployment directory should be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Simplified architecture - single deployment location
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "ENGINEER.md").write_text("# Engineer")
            (agents_dir / "PM.md").write_text("# PM")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert "PM" in deployed
            assert len(deployed) == 2

    def test_duplicate_across_architectures(self):
        """Same agent should only be counted once (simplified architecture)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Single deployment location
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "ENGINEER.md").write_text("# Engineer")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert len(deployed) == 1  # Only counted once

    def test_no_deployed_agents(self):
        """Empty directories should return empty set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create directory but no files
            (project_dir / ".claude" / "agents").mkdir(parents=True)

            deployed = get_deployed_agent_ids(project_dir)
            assert len(deployed) == 0

    def test_missing_directories(self):
        """Missing directories should return empty set without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            # Don't create any directories

            deployed = get_deployed_agent_ids(project_dir)
            assert len(deployed) == 0

    def test_default_project_dir(self):
        """Function should work with no project_dir argument."""
        # This uses current working directory
        deployed = get_deployed_agent_ids()
        assert isinstance(deployed, set)

    def test_ignores_non_md_files(self):
        """Only .md files should be counted as agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create files with different extensions
            (agents_dir / "ENGINEER.md").write_text("# Engineer")
            (agents_dir / "README.txt").write_text("Not an agent")
            (agents_dir / "config.json").write_text("{}")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert len(deployed) == 1  # Only .md file

    def test_virtual_deployment_state_detection(self):
        """Agents in .mpm_deployment_state should be detected."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployment state file
            state_file = agents_dir / ".mpm_deployment_state"
            state_data = {
                "deployment_hash": "test-hash",
                "last_check_time": 1234567890.0,
                "last_check_results": {
                    "agents": {
                        "python-engineer": {"python": {"satisfied": [], "missing": []}},
                        "qa": {"python": {"satisfied": [], "missing": []}},
                        "gcp-ops": {"python": {"satisfied": [], "missing": []}},
                    }
                },
                "agent_count": 3,
            }

            with state_file.open("w") as f:
                json.dump(state_data, f)

            deployed = get_deployed_agent_ids(project_dir)
            assert "python-engineer" in deployed
            assert "qa" in deployed
            assert "gcp-ops" in deployed
            assert len(deployed) == 3

    def test_virtual_and_physical_combined(self):
        """Agents from both virtual state and physical files should be detected."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployment state file
            state_file = agents_dir / ".mpm_deployment_state"
            state_data = {
                "last_check_results": {
                    "agents": {
                        "python-engineer": {"python": {"satisfied": [], "missing": []}},
                        "qa": {"python": {"satisfied": [], "missing": []}},
                    }
                },
                "agent_count": 2,
            }

            with state_file.open("w") as f:
                json.dump(state_data, f)

            # Also create physical file
            (agents_dir / "DEVOPS.md").write_text("# DevOps Agent")

            deployed = get_deployed_agent_ids(project_dir)
            assert "python-engineer" in deployed
            assert "qa" in deployed
            assert "DEVOPS" in deployed
            assert len(deployed) == 3  # Combined from both sources

    def test_malformed_deployment_state_graceful(self):
        """Malformed deployment state should not break detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create malformed state file
            state_file = agents_dir / ".mpm_deployment_state"
            state_file.write_text("not valid json{}")

            # Create physical file
            (agents_dir / "ENGINEER.md").write_text("# Engineer")

            # Should still detect physical file even if state is malformed
            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert len(deployed) == 1


class TestFilterDeployedAgents:
    """Test filtering of deployed agents from lists."""

    def test_filter_deployed_agents(self):
        """Deployed agents should be filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "ENGINEER.md").write_text("# Engineer")

            agents = [
                {"agent_id": "ENGINEER", "name": "Engineer"},
                {"agent_id": "PM", "name": "PM"},
                {"agent_id": "QA", "name": "QA"},
            ]

            filtered = filter_deployed_agents(agents, project_dir)
            assert len(filtered) == 2
            assert "ENGINEER" not in [a["agent_id"] for a in filtered]
            assert "PM" in [a["agent_id"] for a in filtered]
            assert "QA" in [a["agent_id"] for a in filtered]

    def test_filter_preserves_non_deployed(self):
        """Non-deployed agents should be preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            # No agents deployed

            agents = [
                {"agent_id": "ENGINEER", "name": "Engineer"},
                {"agent_id": "PM", "name": "PM"},
            ]

            filtered = filter_deployed_agents(agents, project_dir)
            assert len(filtered) == 2
            assert filtered == agents

    def test_filter_all_deployed(self):
        """All deployed agents should return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "ENGINEER.md").write_text("# Engineer")
            (agents_dir / "PM.md").write_text("# PM")

            agents = [
                {"agent_id": "ENGINEER", "name": "Engineer"},
                {"agent_id": "PM", "name": "PM"},
            ]

            filtered = filter_deployed_agents(agents, project_dir)
            assert len(filtered) == 0


class TestApplyAllFilters:
    """Test combined filtering operations."""

    def test_filter_base_only(self):
        """BASE_AGENT filtering alone should work."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"agent_id": "BASE_AGENT", "name": "Base"},
            {"agent_id": "PM", "name": "PM"},
        ]

        filtered = apply_all_filters(agents, filter_base=True, filter_deployed=False)
        assert len(filtered) == 2
        assert "BASE_AGENT" not in [a["agent_id"] for a in filtered]

    def test_filter_deployed_only(self):
        """Deployed filtering alone should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "ENGINEER.md").write_text("# Engineer")

            agents = [
                {"agent_id": "ENGINEER", "name": "Engineer"},
                {"agent_id": "PM", "name": "PM"},
            ]

            filtered = apply_all_filters(
                agents, project_dir, filter_base=False, filter_deployed=True
            )
            assert len(filtered) == 1
            assert "PM" in [a["agent_id"] for a in filtered]

    def test_filter_both(self):
        """Both filters should work together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "ENGINEER.md").write_text("# Engineer")

            agents = [
                {"agent_id": "ENGINEER", "name": "Engineer"},  # Deployed
                {"agent_id": "BASE_AGENT", "name": "Base"},  # BASE_AGENT
                {"agent_id": "PM", "name": "PM"},  # Available
                {"agent_id": "QA", "name": "QA"},  # Available
            ]

            filtered = apply_all_filters(
                agents, project_dir, filter_base=True, filter_deployed=True
            )
            assert len(filtered) == 2
            assert "PM" in [a["agent_id"] for a in filtered]
            assert "QA" in [a["agent_id"] for a in filtered]

    def test_no_filters(self):
        """No filtering should return original list."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"agent_id": "BASE_AGENT", "name": "Base"},
        ]

        filtered = apply_all_filters(agents, filter_base=False, filter_deployed=False)
        assert len(filtered) == 2
        assert filtered == agents

    def test_default_behavior(self):
        """Default should filter BASE_AGENT but not deployed."""
        agents = [
            {"agent_id": "ENGINEER", "name": "Engineer"},
            {"agent_id": "BASE_AGENT", "name": "Base"},
            {"agent_id": "PM", "name": "PM"},
        ]

        filtered = apply_all_filters(agents)
        assert len(filtered) == 2
        assert "BASE_AGENT" not in [a["agent_id"] for a in filtered]
