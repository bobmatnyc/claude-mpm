"""Tests for automated orphan detection during startup reconciliation.

These tests cover the _detect_and_remove_orphaned_agents() function which:
1. Builds an "expected agents" set from: cache dir, config (enabled/required),
   local templates, user templates
2. Scans .claude/agents/*.md for deployed agents
3. For each deployed agent NOT in expected set:
   - If MPM-managed (via is_mpm_managed_agent) AND not expected -> removes it (orphan)
   - If NOT MPM-managed -> preserves it (user agent)
4. If expected set is empty -> removes nothing (safety guard)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.deployment_reconciler import DeploymentResult

# ---------------------------------------------------------------------------
# Sample agent file content constants
# ---------------------------------------------------------------------------

MPM_AGENT_CONTENT = """\
---
author: claude-mpm
description: Test agent managed by MPM
version: 1.0.0
---

# Test Agent

This agent is managed by claude-mpm.
"""

MPM_ANTHROPIC_AGENT_CONTENT = """\
---
author: anthropic
description: Core agent from Anthropic
version: 2.0.0
---

# Anthropic Agent

This agent is provided by Anthropic.
"""

USER_AGENT_CONTENT = """\
---
author: my-custom-tool
description: User-created agent
---

# User Agent

This is a user-created agent, not managed by MPM.
"""

NO_FRONTMATTER_CONTENT = """\
# Agent without frontmatter

This is a plain markdown file with no YAML frontmatter.
It should always be treated as a user agent.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROVENANCE_MODULE = "claude_mpm.utils.agent_provenance"
GET_PATH_MANAGER_TARGET = "claude_mpm.core.unified_paths.get_path_manager"


def _make_config(
    *,
    enabled: list[str] | None = None,
    required: list[str] | None = None,
    auto_discover: bool = False,
) -> MagicMock:
    """Create a minimal UnifiedConfig mock with agent sub-config."""
    config = MagicMock()
    config.agents.enabled = enabled if enabled is not None else []
    config.agents.required = required if required is not None else []
    config.agents.auto_discover = auto_discover
    return config


def _make_deployment_result(
    *,
    deployed: list[str] | None = None,
    removed: list[str] | None = None,
    unchanged: list[str] | None = None,
    errors: list[str] | None = None,
) -> DeploymentResult:
    """Create a DeploymentResult with default empty lists."""
    return DeploymentResult(
        deployed=deployed or [],
        removed=removed or [],
        unchanged=unchanged or [],
        errors=errors or [],
    )


def _make_path_manager_mock(cache_agents_dir: Path) -> MagicMock:
    """Return a mock get_path_manager() return value wired to *cache_agents_dir*."""
    pm = MagicMock()
    # get_cache_dir() returns a parent; / "agents" yields cache_agents_dir
    cache_parent = cache_agents_dir.parent
    pm.get_cache_dir.return_value = cache_parent
    return pm


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestOrphanDetectionStartup:
    """Tests for automated orphan detection during startup reconciliation."""

    # ------------------------------------------------------------------
    # test: MPM agent not in any expected source -> removed
    # ------------------------------------------------------------------

    def test_removes_orphaned_mpm_agent(self, tmp_path: Path) -> None:
        """MPM agent present in deploy dir but absent from cache is removed."""
        # Filesystem layout
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Put an unrelated agent in cache so expected_stems is non-empty
        (cache_dir / "other-agent.md").write_text(MPM_AGENT_CONTENT)

        # The deployed agent is NOT in cache (orphan)
        orphan_file = deploy_dir / "orphan-agent.md"
        orphan_file.write_text(MPM_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert "orphan-agent" in removed
        assert not orphan_file.exists(), "Orphaned MPM agent file should be deleted"

    # ------------------------------------------------------------------
    # test: user agent not in cache -> preserved
    # ------------------------------------------------------------------

    def test_preserves_user_agent_not_in_cache(self, tmp_path: Path) -> None:
        """User-created agent absent from cache is NOT removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Put an unrelated agent in cache so expected_stems is non-empty
        (cache_dir / "other-agent.md").write_text(MPM_AGENT_CONTENT)

        user_file = deploy_dir / "my-custom-agent.md"
        user_file.write_text(USER_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            # is_mpm_managed_agent returns False for user agents
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=False):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert removed == [], "User agent should not be removed"
        assert user_file.exists(), "User agent file must be preserved"

    # ------------------------------------------------------------------
    # test: MPM agent that IS in cache -> preserved
    # ------------------------------------------------------------------

    def test_preserves_agent_in_cache(self, tmp_path: Path) -> None:
        """MPM agent that appears in cache (expected) is NOT removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Same agent name in both deploy_dir and cache -> expected
        agent_file = deploy_dir / "cached-agent.md"
        agent_file.write_text(MPM_AGENT_CONTENT)
        (cache_dir / "cached-agent.md").write_text(MPM_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert removed == [], "Agent present in cache must not be removed"
        assert agent_file.exists(), "Cached agent file must be preserved"

    # ------------------------------------------------------------------
    # test: MPM agent from local template dir -> preserved
    # ------------------------------------------------------------------

    def test_preserves_agent_in_local_templates(self, tmp_path: Path) -> None:
        """MPM agent whose stem matches a local template is NOT removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Local template directory (project-level: .claude-mpm/agents/)
        local_templates = tmp_path / ".claude-mpm" / "agents"
        local_templates.mkdir(parents=True)

        # Agent is deployed but cache is empty; local template exists
        agent_file = deploy_dir / "local-template-agent.md"
        agent_file.write_text(MPM_AGENT_CONTENT)
        (local_templates / "local-template-agent.md").write_text(MPM_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert removed == [], "Agent with local template should not be removed"
        assert agent_file.exists(), "Local-template agent file must be preserved"

    # ------------------------------------------------------------------
    # test: safety guard - empty expected set -> remove nothing
    # ------------------------------------------------------------------

    def test_no_removal_when_cache_empty(self, tmp_path: Path) -> None:
        """When no expected agents exist at all (empty set), no files are removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        # Cache dir does NOT exist -> no expected agents from cache
        cache_dir = tmp_path / "cache" / "agents"
        # Deliberately not created

        # An MPM-managed file is deployed
        mpm_file = deploy_dir / "some-agent.md"
        mpm_file.write_text(MPM_AGENT_CONTENT)

        # config has no enabled/required agents, auto_discover=False
        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert removed == [], "Safety guard: nothing removed when expected set is empty"
        assert mpm_file.exists(), "File must not be deleted under safety guard"

    # ------------------------------------------------------------------
    # test: missing deploy dir -> no-op
    # ------------------------------------------------------------------

    def test_no_removal_when_deploy_dir_missing(self, tmp_path: Path) -> None:
        """When .claude/agents/ does not exist, function returns empty list."""
        # deploy_dir deliberately absent
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)
        (cache_dir / "some-agent.md").write_text(MPM_AGENT_CONTENT)

        config = _make_config(enabled=["some-agent"])
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert removed == [], "Missing deploy dir must yield empty list with no errors"

    # ------------------------------------------------------------------
    # test: provenance check failure -> file skipped (not removed)
    # ------------------------------------------------------------------

    def test_handles_unreadable_file(self, tmp_path: Path) -> None:
        """File where provenance check raises an exception is skipped, not removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Cache has an agent so expected_stems is non-empty
        (cache_dir / "other-agent.md").write_text(MPM_AGENT_CONTENT)

        # Deploy a file whose provenance check will fail
        problem_file = deploy_dir / "unreadable-agent.md"
        problem_file.write_text(MPM_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            # Simulate read/provenance failure for this file
            with patch(
                f"{PROVENANCE_MODULE}.is_mpm_managed_agent",
                side_effect=PermissionError("cannot read file"),
            ):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        # File must NOT be deleted if provenance check raised
        assert "unreadable-agent" not in removed, (
            "Unreadable file must be skipped, not removed"
        )
        assert problem_file.exists(), "Problem file must be preserved"

    # ------------------------------------------------------------------
    # test: auto_discover=True + empty enabled -> cache still forms expected set
    # ------------------------------------------------------------------

    def test_auto_discover_mode_uses_cache(self, tmp_path: Path) -> None:
        """With auto_discover=True and empty enabled list, cache agents are expected."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Cache has "cache-agent", which is also deployed -> not an orphan
        (cache_dir / "cache-agent.md").write_text(MPM_AGENT_CONTENT)
        deployed_cache_agent = deploy_dir / "cache-agent.md"
        deployed_cache_agent.write_text(MPM_AGENT_CONTENT)

        # An additional deployed agent NOT in cache (potential orphan)
        orphan_file = deploy_dir / "stale-agent.md"
        orphan_file.write_text(MPM_AGENT_CONTENT)

        # auto_discover=True with no explicit enabled list
        config = _make_config(auto_discover=True)
        agent_result = _make_deployment_result()

        def provenance_side_effect(content: str) -> bool:
            return "author: claude-mpm" in content

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(
                f"{PROVENANCE_MODULE}.is_mpm_managed_agent",
                side_effect=provenance_side_effect,
            ):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        # cache-agent is in cache -> expected -> not removed
        assert "cache-agent" not in removed
        assert deployed_cache_agent.exists()

        # stale-agent is MPM-managed but not in cache -> orphan -> removed
        assert "stale-agent" in removed
        assert not orphan_file.exists()

    # ------------------------------------------------------------------
    # test: removed names appear in returned list
    # ------------------------------------------------------------------

    def test_integration_with_reconciliation_result(self, tmp_path: Path) -> None:
        """Orphan removals are returned in the list from _detect_and_remove_orphaned_agents."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Put an unrelated agent in cache so expected_stems is non-empty
        (cache_dir / "unrelated-expected.md").write_text(MPM_AGENT_CONTENT)

        # Three orphaned MPM agents in deploy dir, none matching cache
        for name in ("alpha-agent", "beta-agent", "gamma-agent"):
            (deploy_dir / f"{name}.md").write_text(MPM_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert set(removed) == {"alpha-agent", "beta-agent", "gamma-agent"}
        # Verify files are actually gone
        for name in ("alpha-agent", "beta-agent", "gamma-agent"):
            assert not (deploy_dir / f"{name}.md").exists()

    # ------------------------------------------------------------------
    # test: config.agents.enabled contributes to expected set
    # ------------------------------------------------------------------

    def test_agent_in_enabled_config_is_preserved(self, tmp_path: Path) -> None:
        """Agent listed in config.agents.enabled is in the expected set and not removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Deployed MPM agent that is explicitly enabled in config
        enabled_file = deploy_dir / "enabled-agent.md"
        enabled_file.write_text(MPM_AGENT_CONTENT)

        # Deployed MPM agent that is NOT enabled -> orphan
        orphan_file = deploy_dir / "orphan-agent.md"
        orphan_file.write_text(MPM_AGENT_CONTENT)

        config = _make_config(enabled=["enabled-agent"])
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert "enabled-agent" not in removed
        assert enabled_file.exists()
        assert "orphan-agent" in removed
        assert not orphan_file.exists()

    # ------------------------------------------------------------------
    # test: config.agents.required contributes to expected set
    # ------------------------------------------------------------------

    def test_agent_in_required_config_is_preserved(self, tmp_path: Path) -> None:
        """Agent listed in config.agents.required is in the expected set and not removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        required_file = deploy_dir / "required-agent.md"
        required_file.write_text(MPM_AGENT_CONTENT)

        orphan_file = deploy_dir / "obsolete-agent.md"
        orphan_file.write_text(MPM_AGENT_CONTENT)

        config = _make_config(required=["required-agent"])
        agent_result = _make_deployment_result()

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(f"{PROVENANCE_MODULE}.is_mpm_managed_agent", return_value=True):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        assert "required-agent" not in removed
        assert required_file.exists()
        assert "obsolete-agent" in removed
        assert not orphan_file.exists()

    # ------------------------------------------------------------------
    # test: mixed scenario - user agent + mpm orphan + expected mpm agent
    # ------------------------------------------------------------------

    def test_mixed_scenario_correct_classification(self, tmp_path: Path) -> None:
        """Correctly classifies user agents, expected MPM agents, and orphans."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Expected MPM agent (in cache)
        (cache_dir / "expected-mpm.md").write_text(MPM_AGENT_CONTENT)
        expected_file = deploy_dir / "expected-mpm.md"
        expected_file.write_text(MPM_AGENT_CONTENT)

        # Orphaned MPM agent (not in cache)
        orphan_file = deploy_dir / "orphan-mpm.md"
        orphan_file.write_text(MPM_AGENT_CONTENT)

        # User agent (not in cache, not MPM-managed)
        user_file = deploy_dir / "user-custom.md"
        user_file.write_text(USER_AGENT_CONTENT)

        config = _make_config()
        agent_result = _make_deployment_result()

        def provenance_side_effect(content: str) -> bool:
            return "author: claude-mpm" in content

        with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
            mock_gpm.return_value = _make_path_manager_mock(cache_dir)
            with patch(
                f"{PROVENANCE_MODULE}.is_mpm_managed_agent",
                side_effect=provenance_side_effect,
            ):
                from claude_mpm.services.agents.deployment.startup_reconciliation import (
                    _detect_and_remove_orphaned_agents,
                )

                removed = _detect_and_remove_orphaned_agents(
                    tmp_path, config, agent_result
                )

        # Expected MPM agent: preserved
        assert "expected-mpm" not in removed
        assert expected_file.exists()

        # Orphaned MPM agent: removed
        assert "orphan-mpm" in removed
        assert not orphan_file.exists()

        # User agent: preserved regardless
        assert "user-custom" not in removed
        assert user_file.exists()
