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
        """Agents in .claude-mpm/agents/ should be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude-mpm" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployed agent files
            (agents_dir / "ENGINEER.md").write_text("# Engineer Agent")
            (agents_dir / "PM.md").write_text("# PM Agent")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert "PM" in deployed
            assert len(deployed) == 2

    def test_legacy_architecture_detection(self):
        """Agents in .claude/agents/ should be detected."""
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
        """Agents in both directories should be detected (union)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # New architecture
            new_agents_dir = project_dir / ".claude-mpm" / "agents"
            new_agents_dir.mkdir(parents=True)
            (new_agents_dir / "ENGINEER.md").write_text("# Engineer")

            # Legacy architecture
            legacy_agents_dir = project_dir / ".claude" / "agents"
            legacy_agents_dir.mkdir(parents=True)
            (legacy_agents_dir / "PM.md").write_text("# PM")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert "PM" in deployed
            assert len(deployed) == 2

    def test_duplicate_across_architectures(self):
        """Same agent in both directories should only appear once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # New architecture
            new_agents_dir = project_dir / ".claude-mpm" / "agents"
            new_agents_dir.mkdir(parents=True)
            (new_agents_dir / "ENGINEER.md").write_text("# Engineer")

            # Legacy architecture (same agent)
            legacy_agents_dir = project_dir / ".claude" / "agents"
            legacy_agents_dir.mkdir(parents=True)
            (legacy_agents_dir / "ENGINEER.md").write_text("# Engineer")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert len(deployed) == 1  # Only counted once

    def test_no_deployed_agents(self):
        """Empty directories should return empty set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create directories but no files
            (project_dir / ".claude-mpm" / "agents").mkdir(parents=True)
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
            agents_dir = project_dir / ".claude-mpm" / "agents"
            agents_dir.mkdir(parents=True)

            # Create files with different extensions
            (agents_dir / "ENGINEER.md").write_text("# Engineer")
            (agents_dir / "README.txt").write_text("Not an agent")
            (agents_dir / "config.json").write_text("{}")

            deployed = get_deployed_agent_ids(project_dir)
            assert "ENGINEER" in deployed
            assert len(deployed) == 1  # Only .md file


class TestFilterDeployedAgents:
    """Test filtering of deployed agents from lists."""

    def test_filter_deployed_agents(self):
        """Deployed agents should be filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude-mpm" / "agents"
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
            agents_dir = project_dir / ".claude-mpm" / "agents"
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
            agents_dir = project_dir / ".claude-mpm" / "agents"
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
            agents_dir = project_dir / ".claude-mpm" / "agents"
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
            agents_dir = project_dir / ".claude-mpm" / "agents"
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
