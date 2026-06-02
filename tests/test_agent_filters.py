"""
Unit tests for agent filtering utilities (1M-502 Phase 1).

Tests cover:
- BASE_AGENT filtering (case-insensitive)
- Deployed agent detection (new and legacy directories)
- Combined filtering operations
- Edge cases and error handling
- agents.local_only protection (Issue #560)
"""

import logging
import tempfile
from pathlib import Path

import pytest

from claude_mpm.utils.agent_filters import (
    apply_all_filters,
    filter_base_agents,
    filter_deployed_agents,
    get_deployed_agent_ids,
    is_base_agent,
    is_local_only,
    load_local_only_agents,
    warn_missing_local_only_agents,
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
        """baseagent no separator (compound word) — not a BASE template prefix.

        The canonical predicate checks for the ``base-`` / ``base_`` prefix
        (separator required).  A bare ``baseagent`` string does not have a
        separator so it is NOT matched — it could be a real agent named
        ``baseagent``.  This behaviour was changed when ``is_base_agent``
        was updated to delegate to ``is_base_template``.
        """
        assert is_base_agent("baseagent") is False

    def test_regular_agent_not_detected(self):
        """Regular agents should not be detected as BASE_AGENT."""
        assert is_base_agent("ENGINEER") is False
        assert is_base_agent("PM") is False
        assert is_base_agent("QA") is False

    def test_partial_match_not_detected(self):
        """Only genuine suffix-style non-BASE-prefixed strings are not detected.

        ``BASE_ENGINEER`` and ``BASE-ENGINEER`` ARE composition templates —
        they start with ``BASE_`` / ``BASE-`` and therefore match.
        ``AGENT_BASE`` is NOT a template — it does not start with ``base``.
        """
        assert is_base_agent("BASE_ENGINEER") is True  # IS a composition template
        assert is_base_agent("AGENT_BASE") is False  # suffix only, not a template

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
        """Agents in .claude/agents/ should be detected (simplified architecture).

        Note: get_deployed_agent_ids() returns normalized IDs (lowercase, hyphenated).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployed agent files (uppercase filenames → normalized to lowercase)
            (agents_dir / "ENGINEER.md").write_text("# Engineer Agent")
            (agents_dir / "PM.md").write_text("# PM Agent")

            deployed = get_deployed_agent_ids(project_dir)
            assert "engineer" in deployed
            assert "pm" in deployed
            assert len(deployed) == 2

    def test_legacy_architecture_detection(self):
        """Test for legacy .claude/agents/ detection (same as new architecture now)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            # Create deployed agent files (uppercase filenames → normalized to lowercase)
            (agents_dir / "QA.md").write_text("# QA Agent")
            (agents_dir / "DEVOPS.md").write_text("# DevOps Agent")

            deployed = get_deployed_agent_ids(project_dir)
            assert "qa" in deployed
            assert "devops" in deployed
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
            assert "engineer" in deployed
            assert "pm" in deployed
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
            assert "engineer" in deployed
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
            assert "engineer" in deployed
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
            assert "devops" in deployed
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
            assert "engineer" in deployed
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


# ============================================================================
# Issue #560: agents.local_only protection
# ============================================================================


class TestIsLocalOnly:
    """Test is_local_only predicate."""

    def test_exact_match(self):
        assert is_local_only("writer", ["writer", "fact-checker"]) is True

    def test_case_insensitive_match(self):
        assert is_local_only("WRITER", ["writer"]) is True
        assert is_local_only("writer", ["WRITER"]) is True

    def test_md_extension_stripped(self):
        assert is_local_only("writer.md", ["writer"]) is True

    def test_agent_suffix_normalized(self):
        assert is_local_only("writer-agent", ["writer"]) is True
        assert is_local_only("writer", ["writer-agent"]) is True

    def test_underscore_normalized(self):
        assert is_local_only("fact_checker", ["fact-checker"]) is True

    def test_not_in_list(self):
        assert is_local_only("engineer", ["writer", "fact-checker"]) is False

    def test_empty_allow_list(self):
        assert is_local_only("writer", []) is False

    def test_empty_agent_id(self):
        assert is_local_only("", ["writer"]) is False

    def test_none_agent_id(self):
        # type: ignore[arg-type]
        assert is_local_only(None, ["writer"]) is False  # type: ignore[arg-type]


class TestLoadLocalOnlyAgents:
    """Test loading agents.local_only from .claude-mpm/configuration.yaml."""

    def _write_config(self, project_dir: Path, content: str) -> Path:
        config_dir = project_dir / ".claude-mpm"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "configuration.yaml"
        config_path.write_text(content, encoding="utf-8")
        return config_path

    def test_loads_local_only_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            self._write_config(
                project_dir,
                "agents:\n  local_only:\n    - writer\n    - fact-checker\n",
            )
            result = load_local_only_agents(project_dir)
            assert result == ["writer", "fact-checker"]

    def test_missing_config_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            assert load_local_only_agents(project_dir) == []

    def test_missing_agents_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            self._write_config(project_dir, "other:\n  foo: 1\n")
            assert load_local_only_agents(project_dir) == []

    def test_missing_local_only_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            self._write_config(project_dir, "agents:\n  enabled:\n    - engineer\n")
            assert load_local_only_agents(project_dir) == []

    def test_non_list_local_only_returns_empty(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            self._write_config(project_dir, "agents:\n  local_only: not-a-list\n")
            with caplog.at_level(logging.WARNING):
                result = load_local_only_agents(project_dir)
            assert result == []

    def test_malformed_yaml_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            self._write_config(project_dir, "::: not valid yaml :::")
            assert load_local_only_agents(project_dir) == []

    def test_yml_extension_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            config_dir = project_dir / ".claude-mpm"
            config_dir.mkdir(parents=True)
            (config_dir / "configuration.yml").write_text(
                "agents:\n  local_only:\n    - writer\n", encoding="utf-8"
            )
            assert load_local_only_agents(project_dir) == ["writer"]


class TestWarnMissingLocalOnlyAgents:
    """Test missing-agent warnings for local_only entries."""

    def test_all_present_no_warning(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "writer.md").write_text("# Writer")
            (agents_dir / "fact-checker.md").write_text("# Fact Checker")

            with caplog.at_level(logging.WARNING):
                missing = warn_missing_local_only_agents(
                    ["writer", "fact-checker"], project_dir
                )
            assert missing == []

    def test_missing_emits_warning(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            agents_dir = project_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "writer.md").write_text("# Writer")
            # fact-checker is missing

            with caplog.at_level(logging.WARNING):
                missing = warn_missing_local_only_agents(
                    ["writer", "fact-checker"], project_dir
                )
            assert missing == ["fact-checker"]
            assert any(
                "local_only" in record.message.lower() for record in caplog.records
            )

    def test_empty_list_no_warning(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            with caplog.at_level(logging.WARNING):
                missing = warn_missing_local_only_agents([], project_dir)
            assert missing == []
            assert len(caplog.records) == 0


class TestLocalOnlyDeploymentProtection:
    """Integration tests: local_only agents survive cleanup/deploy operations."""

    def test_cleanup_excluded_agents_skips_local_only(self, tmp_path):
        """git_source_sync_service._cleanup_excluded_agents must not delete
        a local_only agent even when its normalized name appears in
        the excluded_set."""
        from claude_mpm.services.agents.sources.git_source_sync_service import (
            GitSourceSyncService,
        )

        deployment_dir = tmp_path / ".claude" / "agents"
        deployment_dir.mkdir(parents=True)
        (deployment_dir / "writer.md").write_text("# Project-local writer")
        (deployment_dir / "engineer.md").write_text("# Engineer")

        service = GitSourceSyncService()
        result = service._cleanup_excluded_agents(
            deployment_dir,
            excluded_set={"writer", "engineer"},
            local_only_list=["writer"],
        )

        # writer protected, engineer removed
        assert (deployment_dir / "writer.md").exists()
        assert not (deployment_dir / "engineer.md").exists()
        assert "writer" not in result["removed"]
        assert "engineer" in result["removed"]

    def test_cleanup_excluded_agents_backward_compat_no_local_only(self, tmp_path):
        """Calling _cleanup_excluded_agents without local_only_list keeps
        the existing behavior (all excluded agents removed)."""
        from claude_mpm.services.agents.sources.git_source_sync_service import (
            GitSourceSyncService,
        )

        deployment_dir = tmp_path / ".claude" / "agents"
        deployment_dir.mkdir(parents=True)
        (deployment_dir / "writer.md").write_text("# Writer")
        (deployment_dir / "engineer.md").write_text("# Engineer")

        service = GitSourceSyncService()
        result = service._cleanup_excluded_agents(
            deployment_dir,
            excluded_set={"writer", "engineer"},
        )

        # Default behavior: both removed
        assert not (deployment_dir / "writer.md").exists()
        assert not (deployment_dir / "engineer.md").exists()
        assert set(result["removed"]) == {"writer", "engineer"}

    def test_deployment_reconciler_skips_local_only_removal(self, tmp_path):
        """DeploymentReconciler.reconcile_agents() must not remove
        agents listed in agents.local_only, even if they are deployed
        but not in agents.enabled."""
        from claude_mpm.core.unified_config import UnifiedConfig
        from claude_mpm.services.agents.deployment.deployment_reconciler import (
            DeploymentReconciler,
        )

        # Stage a deployed-only agent that is not in enabled list
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        (deploy_dir / "writer.md").write_text(
            "---\nname: Writer\n---\n# Hand-crafted project-local writer"
        )

        # Build a config where 'writer' is local_only and NOT enabled
        config = UnifiedConfig(
            agents={
                "enabled": [],
                "required": [],
                "include_universal": False,
                "auto_discover": False,
                "local_only": ["writer"],
            }
        )

        reconciler = DeploymentReconciler(config)
        result = reconciler.reconcile_agents(project_path=tmp_path)

        # writer.md must still exist (was not removed)
        assert (deploy_dir / "writer.md").exists()
        assert "writer" not in result.removed
