"""CT-1: Characterization tests for perform_startup_reconciliation().

These tests capture the CURRENT behavior of the startup reconciliation pipeline
as a safety net before refactoring. They are NOT correctness tests -- they
document what the code does today so regressions can be detected during the
agent-pipelines-unification work.

Key behaviors captured:
- perform_startup_reconciliation returns a tuple of two DeploymentResult objects
- Required agents are deployed from cache when present
- Missing cache entries produce errors (not exceptions)
- Frontmatter injection (agent_id) is applied during deploy
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.core.unified_config import UnifiedConfig
from claude_mpm.services.agents.deployment.deployment_reconciler import (
    DeploymentResult as ReconcilerDeploymentResult,
)
from claude_mpm.services.agents.deployment.startup_reconciliation import (
    perform_startup_reconciliation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_config(
    enabled: list[str] | None = None,
    required: list[str] | None = None,
    include_universal: bool = False,
    auto_discover: bool = False,
) -> UnifiedConfig:
    """Build a UnifiedConfig with custom agent settings.

    Defaults disable auto_discover and include_universal to keep tests focused
    on explicit lists.
    """
    config = UnifiedConfig()
    config.agents.enabled = enabled or []
    config.agents.required = required or []
    config.agents.include_universal = include_universal
    config.agents.auto_discover = auto_discover
    return config


def _populate_cache(cache_dir: Path, agent_names: list[str]) -> None:
    """Write stub agent .md files into a fake cache directory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for name in agent_names:
        agent_file = cache_dir / f"{name}.md"
        agent_file.write_text(
            f"---\nname: {name.replace('-', ' ').title()}\n---\n# {name}\nAgent content.\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CT-1 Tests
# ---------------------------------------------------------------------------


class TestCharacterizationStartupReconciliation:
    """CT-1: Characterize perform_startup_reconciliation() current behavior."""

    # We need to mock three things that the DeploymentReconciler __init__
    # touches:
    #   1. get_path_manager() -- so it returns a tmp_path-based cache dir
    #   2. ManifestCache -- it opens a real SQLite DB; we don't want that
    #   3. DeploymentVersionGate -- depends on ManifestCache
    # We also mock _detect_and_remove_orphaned_agents to isolate
    # reconciliation from orphan cleanup.

    _RECONCILER_MOD = "claude_mpm.services.agents.deployment.deployment_reconciler"
    _STARTUP_MOD = "claude_mpm.services.agents.deployment.startup_reconciliation"

    def _mock_path_manager(self, cache_dir: Path) -> MagicMock:
        """Create a mock path manager returning *cache_dir* as the cache root."""
        pm = MagicMock()
        pm.get_cache_dir.return_value = cache_dir
        return pm

    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_deploys_required_agents_from_cache(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """When required agents exist in cache, they are deployed to
        .claude/agents/ in the project directory."""
        cache_dir = tmp_path / "cache"
        _populate_cache(cache_dir / "agents", ["engineer", "research"])

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        config = _build_config(required=["engineer", "research"])
        project_path = tmp_path / "project"
        project_path.mkdir()

        agent_result, _skill_result = perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        # The reconciler should report both agents as deployed
        assert set(agent_result.deployed) == {"engineer", "research"}
        assert agent_result.errors == []

        # Files should exist on disk
        deploy_dir = project_path / ".claude" / "agents"
        assert (deploy_dir / "engineer.md").exists()
        assert (deploy_dir / "research.md").exists()

    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_empty_cache_produces_errors_not_exception(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """When required agents are NOT in cache, errors are recorded but
        perform_startup_reconciliation does NOT raise."""
        cache_dir = tmp_path / "cache"
        # Create the agents dir but leave it empty
        (cache_dir / "agents").mkdir(parents=True)

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        config = _build_config(required=["engineer", "research"])
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Must NOT raise
        agent_result, _skill_result = perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        # Both agents should appear in errors (not found in cache)
        assert len(agent_result.errors) == 2
        assert agent_result.deployed == []
        for error in agent_result.errors:
            assert "not found in cache" in error

    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_frontmatter_is_injected(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """Deployed files have agent_id injected into their YAML frontmatter.

        This captures the current behavior where deploy_agent_file() calls
        ensure_agent_id_in_frontmatter() during deployment.
        """
        cache_dir = tmp_path / "cache"
        # Create a cache file WITHOUT agent_id in frontmatter
        agents_cache = cache_dir / "agents"
        agents_cache.mkdir(parents=True)
        (agents_cache / "engineer.md").write_text(
            "---\nname: Engineer\n---\n# Engineer\nContent.\n",
            encoding="utf-8",
        )

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        config = _build_config(required=["engineer"])
        project_path = tmp_path / "project"
        project_path.mkdir()

        perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        deployed_file = project_path / ".claude" / "agents" / "engineer.md"
        assert deployed_file.exists()

        content = deployed_file.read_text(encoding="utf-8")
        # agent_id should have been injected
        assert "agent_id: engineer" in content

    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_returns_tuple_of_two_deployment_results(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """perform_startup_reconciliation() returns a 2-tuple of
        (agent_result, skill_result), both of type DeploymentResult
        from the deployment_reconciler module."""
        cache_dir = tmp_path / "cache"
        (cache_dir / "agents").mkdir(parents=True)

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        config = _build_config()
        project_path = tmp_path / "project"
        project_path.mkdir()

        result = perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        # Must be a tuple of length 2
        assert isinstance(result, tuple)
        assert len(result) == 2

        agent_result, skill_result = result
        assert isinstance(agent_result, ReconcilerDeploymentResult)
        assert isinstance(skill_result, ReconcilerDeploymentResult)

        # Both results should have the expected attributes
        assert hasattr(agent_result, "deployed")
        assert hasattr(agent_result, "removed")
        assert hasattr(agent_result, "unchanged")
        assert hasattr(agent_result, "errors")
        assert hasattr(agent_result, "success")

    # ------------------------------------------------------------------
    # CRITICAL FIX 1: auto_discover early-return path (lines 146-155)
    # ------------------------------------------------------------------
    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_auto_discover_returns_unchanged_without_deploying(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """When enabled=[] and auto_discover=True, the reconciler hits the
        early-return path (deployment_reconciler.py:146-155) and returns
        already-deployed agents as 'unchanged' without deploying new ones.

        This covers the backward-compatibility code path for projects that
        rely on auto-discovery rather than explicit agent lists.
        """
        cache_dir = tmp_path / "cache"
        (cache_dir / "agents").mkdir(parents=True)

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        # Override default required=[] to ensure enabled=[] triggers auto_discover path
        config = _build_config(
            enabled=[],
            required=[],
            include_universal=False,
            auto_discover=True,
        )
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Pre-populate the deploy directory (simulating already-deployed agents)
        deploy_dir = project_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        (deploy_dir / "engineer.md").write_text(
            "---\nagent_id: engineer\n---\n# Engineer\n",
            encoding="utf-8",
        )

        agent_result, _skill_result = perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        # The auto_discover early-return should NOT deploy new agents
        assert agent_result.deployed == []
        # Should NOT remove anything
        assert agent_result.removed == []
        # The already-deployed agent should appear in unchanged
        assert "engineer" in agent_result.unchanged

    # ------------------------------------------------------------------
    # CRITICAL FIX 2: production-default UnifiedConfig deploys required
    # ------------------------------------------------------------------
    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_production_defaults_deploy_required_agents(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """With production-default UnifiedConfig() (7 required agents,
        include_universal=True), all required agents are deployed from cache.

        This validates the real production path where UnifiedConfig() is
        instantiated without overrides, ensuring the standard 7 core agents
        (engineer, research, qa, web-qa, documentation, ops, ticketing)
        are deployed as expected.
        """
        cache_dir = tmp_path / "cache"
        required_agents = [
            "engineer",
            "research",
            "qa",
            "web-qa",
            "documentation",
            "ops",
            "ticketing",
        ]
        _populate_cache(cache_dir / "agents", required_agents)

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        # Use production-default config (NOT _build_config which zeroes out defaults)
        config = UnifiedConfig()

        project_path = tmp_path / "project"
        project_path.mkdir()

        agent_result, _skill_result = perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        # All 7 required agents should be deployed (or already present = unchanged)
        all_handled = set(agent_result.deployed) | set(agent_result.unchanged)
        for agent in required_agents:
            assert agent in all_handled, (
                f"Required agent '{agent}' not in deployed or unchanged. "
                f"deployed={agent_result.deployed}, unchanged={agent_result.unchanged}, "
                f"errors={agent_result.errors}"
            )
        assert agent_result.errors == []

    # ------------------------------------------------------------------
    # MEDIUM FIX 7: xfail - configure selections not respected at startup
    # ------------------------------------------------------------------
    @pytest.mark.xfail(
        reason=(
            "Known bug: startup reads UnifiedConfig.agents.enabled (defaults to []) "
            "instead of agent_states.json written by 'claude-mpm configure'. "
            "Configure selections are therefore lost on restart."
        ),
        strict=True,
    )
    @patch(f"{_STARTUP_MOD}._detect_and_remove_orphaned_agents", return_value=[])
    @patch(f"{_RECONCILER_MOD}.DeploymentVersionGate")
    @patch(f"{_RECONCILER_MOD}.ManifestCache")
    @patch(f"{_RECONCILER_MOD}.get_path_manager")
    def test_ct1_configure_selections_not_respected_at_startup(
        self,
        mock_get_pm,
        mock_manifest_cache,
        mock_deploy_gate,
        mock_orphan_detect,
        tmp_path,
    ):
        """Documents the known disconnect between 'claude-mpm configure'
        and startup reconciliation.

        The configure command writes selections to agent_states.json, but
        startup reconciliation reads from UnifiedConfig.agents.enabled
        which defaults to []. This means user selections made via configure
        are NOT reflected at startup -- agents that were enabled via
        configure will NOT be deployed.

        This test uses xfail(strict=True) to document the bug: we expect
        the assertion to FAIL because the qa agent will NOT be deployed
        when enabled=[] (the startup default).
        """
        cache_dir = tmp_path / "cache"
        _populate_cache(cache_dir / "agents", ["qa"])

        mock_get_pm.return_value = self._mock_path_manager(cache_dir)

        # Simulate startup default: enabled=[], required=[], include_universal=False
        # Even though configure may have written qa to agent_states.json,
        # startup only looks at UnifiedConfig which has enabled=[]
        config = _build_config(
            enabled=[],
            required=[],
            include_universal=False,
        )
        project_path = tmp_path / "project"
        project_path.mkdir()

        perform_startup_reconciliation(
            project_path=project_path, config=config, silent=True
        )

        deploy_dir = project_path / ".claude" / "agents"
        # This assertion WILL FAIL because qa is not deployed (not in enabled or required)
        # xfail(strict=True) expects this failure, documenting the bug
        assert (deploy_dir / "qa.md").exists()
