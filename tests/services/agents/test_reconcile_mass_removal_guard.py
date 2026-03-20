"""Regression test: sparse agent_states.json must NOT trigger mass-removal.

When agent_states.json contains only a handful of entries (e.g., 2 agents
marked enabled), the reconcile guard in AgentsReconcileCommand must set
auto_discover = True rather than narrowing config.agents.enabled to just
the required agents.

The root cause: _resolve_agent_states() intentionally populates
excluded_agents (for disabled entries) but does NOT populate
enabled_agents.  This means has_explicit_agent_selection is False,
so the reconcile guard falls through to the `else` branch and sets
auto_discover = True.  If it instead narrowed enabled to the tiny
required set, the reconciler would remove every agent not in that set.

See: src/claude_mpm/cli/commands/agents_reconcile.py lines 45-49
See: src/claude_mpm/services/agents/pipeline_config.py _resolve_agent_states()
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

from claude_mpm.services.agents.pipeline_config import AgentPipelineConfig

# ---------------------------------------------------------------------------
# Helpers (same pattern as test_agent_pipeline_config.py)
# ---------------------------------------------------------------------------


def _make_unified_config(
    enabled: list[str] | None = None,
    required: list[str] | None = None,
    include_universal: bool = True,
) -> MagicMock:
    """Build a minimal UnifiedConfig mock."""
    uc = MagicMock()
    uc.agents.enabled = enabled if enabled is not None else []
    uc.agents.required = required if required is not None else []
    uc.agents.include_universal = include_universal
    uc.agents.auto_discover = False
    return uc


def _make_agent_sources(repos: list | None = None) -> MagicMock:
    """Build a minimal AgentSourceConfiguration mock."""
    acs = MagicMock()
    acs.get_enabled_repositories.return_value = repos or []
    return acs


def _patch_config_sources(uc_mock: MagicMock):
    """Context manager that patches both config source imports."""
    return (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    )


# ---------------------------------------------------------------------------
# Regression test: sparse agent_states.json must not narrow deployed set
# ---------------------------------------------------------------------------


class TestReconcileMassRemovalGuard:
    """Regression tests for the mass-removal guard in agents reconcile.

    The guard logic (agents_reconcile.py):

        effective_agents = pipeline_config.get_agents_to_deploy()
        if effective_agents and pipeline_config.has_explicit_agent_selection:
            config.agents.enabled = list(effective_agents)
        else:
            config.agents.auto_discover = True

    When agent_states.json is sparse (only a few entries, all enabled),
    has_explicit_agent_selection must be False so the else branch runs,
    setting auto_discover = True.  This prevents the reconciler from
    removing every agent not in the tiny required set.
    """

    def test_sparse_agent_states_does_not_narrow_deployed_set(self, tmp_path: Path):
        """REGRESSION: A sparse agent_states.json with 2 enabled agents must
        NOT cause has_explicit_agent_selection to be True.

        If it were True, the reconciler would set config.agents.enabled to
        only the required agents, causing mass-removal of all other agents.
        Instead, the guard must fall through to auto_discover = True.
        """
        # Arrange: sparse agent_states.json with only 2 agents marked enabled
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir()
        sparse_states = {
            "engineer": {"enabled": True},
            "qa": {"enabled": True},
        }
        (config_dir / "agent_states.json").write_text(json.dumps(sparse_states))

        # No explicit enabled list in UnifiedConfig, small required set
        uc_mock = _make_unified_config(enabled=[], required=["engineer"])

        patches = _patch_config_sources(uc_mock)
        with patches[0], patches[1]:
            pipeline_config = AgentPipelineConfig.resolve(
                mode="reconcile",
                project_dir=tmp_path,
            )

        # Act & Assert Step 1: has_explicit_agent_selection must be False
        # because _resolve_agent_states() does NOT populate enabled_agents
        # for sparse files -- it only populates excluded_agents.
        assert pipeline_config.enabled_agents == set(), (
            "Sparse agent_states.json must NOT populate enabled_agents. "
            "Populating it would create a tiny whitelist causing mass-removal."
        )
        assert pipeline_config.has_explicit_agent_selection is False, (
            "has_explicit_agent_selection must be False when only "
            "agent_states.json is the source (no profile, no config enabled list)."
        )

        # Act & Assert Step 2: simulate the reconcile guard logic
        # (mirrors agents_reconcile.py lines 45-49)
        effective_agents = pipeline_config.get_agents_to_deploy()
        if effective_agents and pipeline_config.has_explicit_agent_selection:
            # This branch must NOT execute for sparse agent_states.json
            auto_discover = False
        else:
            # This is the safe path -- auto_discover prevents mass removal
            auto_discover = True

        assert auto_discover is True, (
            "The reconcile guard must set auto_discover = True when "
            "has_explicit_agent_selection is False. Otherwise, agents "
            "not in the sparse list would be mass-removed."
        )

    def test_sparse_agent_states_with_one_disabled_still_safe(self, tmp_path: Path):
        """Even when agent_states.json has a mix of enabled/disabled entries,
        has_explicit_agent_selection remains False if no profile or config
        provides an explicit enabled list.
        """
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir()
        states = {
            "engineer": {"enabled": True},
            "qa": {"enabled": True},
            "java-engineer": {"enabled": False},
        }
        (config_dir / "agent_states.json").write_text(json.dumps(states))

        uc_mock = _make_unified_config(enabled=[], required=["engineer", "qa"])

        patches = _patch_config_sources(uc_mock)
        with patches[0], patches[1]:
            pipeline_config = AgentPipelineConfig.resolve(
                mode="reconcile",
                project_dir=tmp_path,
            )

        # enabled_agents is empty (sparse file does not whitelist)
        assert pipeline_config.enabled_agents == set()
        assert pipeline_config.has_explicit_agent_selection is False

        # excluded_agents correctly contains the disabled agent
        assert "java-engineer" in pipeline_config.excluded_agents

        # The reconcile guard sets auto_discover = True
        effective_agents = pipeline_config.get_agents_to_deploy()
        guard_sets_auto_discover = not (
            effective_agents and pipeline_config.has_explicit_agent_selection
        )
        assert guard_sets_auto_discover is True

        # effective_agents contains required minus excluded
        assert "engineer" in effective_agents
        assert "qa" in effective_agents
        assert "java-engineer" not in effective_agents

    def test_explicit_enabled_config_does_narrow_deployed_set(self, tmp_path: Path):
        """Contrast: when UnifiedConfig has an explicit enabled list,
        has_explicit_agent_selection IS True, and the guard correctly
        narrows the deployed set (this is intentional, not mass-removal).
        """
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir()

        # Explicit enabled list in config (not from agent_states.json)
        uc_mock = _make_unified_config(
            enabled=["python-engineer", "qa"],
            required=["engineer"],
        )

        patches = _patch_config_sources(uc_mock)
        with patches[0], patches[1]:
            pipeline_config = AgentPipelineConfig.resolve(
                mode="reconcile",
                project_dir=tmp_path,
            )

        # With explicit enabled list, has_explicit_agent_selection IS True
        assert pipeline_config.has_explicit_agent_selection is True

        # The guard would narrow the deployed set (intentional behavior)
        effective_agents = pipeline_config.get_agents_to_deploy()
        guard_sets_auto_discover = not (
            effective_agents and pipeline_config.has_explicit_agent_selection
        )
        assert guard_sets_auto_discover is False

        # Effective set is enabled + required
        assert "python-engineer" in effective_agents
        assert "qa" in effective_agents
        assert "engineer" in effective_agents
