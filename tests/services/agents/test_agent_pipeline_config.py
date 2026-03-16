"""Unit tests for AgentPipelineConfig.

Covers all 11 required test cases for Phase 2 of agent pipeline unification.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from claude_mpm.services.agents.pipeline_config import AgentPipelineConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unified_config(
    enabled: list[str] | None = None,
    required: list[str] | None = None,
    include_universal: bool = True,
) -> MagicMock:
    """Build a minimal UnifiedConfig mock."""
    uc = MagicMock()
    uc.agents.enabled = enabled if enabled is not None else []
    uc.agents.required = (
        required
        if required is not None
        else [
            "engineer",
            "research",
            "qa",
            "web-qa",
            "documentation",
            "ops",
            "ticketing",
        ]
    )
    uc.agents.include_universal = include_universal
    return uc


def _make_agent_sources(repos: list | None = None) -> MagicMock:
    """Build a minimal AgentSourceConfiguration mock."""
    acs = MagicMock()
    acs.get_enabled_repositories.return_value = repos or []
    return acs


# ---------------------------------------------------------------------------
# Test 1: startup mode returns required + universal flag, no enabled override
# ---------------------------------------------------------------------------


def test_resolve_startup_mode_uses_enabled_required_universal(tmp_path: Path):
    """Startup mode: no enabled list in config → required set is populated."""
    required = ["engineer", "research", "qa"]
    uc_mock = _make_unified_config(enabled=[], required=required)

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        # Use tmp_path so no agent_states.json is found on disk
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    assert cfg.mode == "startup"
    assert cfg.required_agents == set(required)
    assert cfg.enabled_agents == set()
    assert cfg.include_universal is True


# ---------------------------------------------------------------------------
# Test 2: deploy_all mode returns all cached minus excluded
# ---------------------------------------------------------------------------


def test_resolve_deploy_all_mode_returns_all_cached():
    """deploy_all mode: get_agents_to_deploy returns cached set minus excluded."""
    uc_mock = _make_unified_config()

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="deploy_all")

    cached = {"engineer", "research", "qa", "java-engineer"}
    cfg.excluded_agents = {"java-engineer"}

    result = cfg.get_agents_to_deploy(cached_agents=cached)
    assert result == {"engineer", "research", "qa"}


# ---------------------------------------------------------------------------
# Test 3: profile overrides enabled list from UnifiedConfig
# ---------------------------------------------------------------------------


def test_resolve_profile_overrides_enabled(tmp_path: Path):
    """Profile enabled list takes precedence over UnifiedConfig.agents.enabled."""
    # Write a minimal profile YAML
    profiles_dir = tmp_path / ".claude-mpm" / "profiles"
    profiles_dir.mkdir(parents=True)
    profile_yaml = profiles_dir / "myprofile.yaml"
    profile_yaml.write_text(
        "profile:\n  name: myprofile\nagents:\n  enabled:\n    - python-engineer\n    - qa\n"
    )

    uc_mock = _make_unified_config(enabled=["engineer"], required=["engineer"])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(
            mode="startup",
            profile="myprofile",
            project_dir=tmp_path,
        )

    assert cfg.enabled_agents == {"python-engineer", "qa"}


# ---------------------------------------------------------------------------
# Test 4: repositories are populated from AgentSourceConfiguration
# ---------------------------------------------------------------------------


def test_resolve_reads_agent_sources():
    """Repositories field is populated from AgentSourceConfiguration.load()."""
    fake_repo = MagicMock()
    fake_repo.url = "https://github.com/example/agents"
    uc_mock = _make_unified_config()

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(repos=[fake_repo]),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="startup")

    assert len(cfg.repositories) == 1
    assert cfg.repositories[0].url == "https://github.com/example/agents"


# ---------------------------------------------------------------------------
# Test 5: fallback when config sources raise exceptions
# ---------------------------------------------------------------------------


def test_resolve_fallback_on_config_error(tmp_path: Path):
    """resolve() is fail-safe: exceptions from config sources → warnings, not raise."""
    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            side_effect=RuntimeError("disk error"),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            side_effect=ValueError("bad config"),
        ),
    ):
        # Use tmp_path so no agent_states.json is found on disk
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    # No exception raised
    assert cfg.mode == "startup"
    # Both errors captured as warnings
    assert len(cfg.warnings) == 2
    assert any("disk error" in w for w in cfg.warnings)
    assert any("bad config" in w for w in cfg.warnings)
    # Fields default to empty / safe values
    assert cfg.repositories == []
    assert cfg.enabled_agents == set()
    assert cfg.required_agents == set()


# ---------------------------------------------------------------------------
# Test 6: resolve() is idempotent
# ---------------------------------------------------------------------------


def test_resolve_idempotent(tmp_path: Path):
    """Calling resolve() twice with same args returns equivalent configs."""
    uc_mock = _make_unified_config(required=["engineer", "qa"])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        # Use tmp_path so no agent_states.json is found on disk
        cfg1 = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)
        cfg2 = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    assert cfg1.required_agents == cfg2.required_agents
    assert cfg1.enabled_agents == cfg2.enabled_agents
    assert cfg1.mode == cfg2.mode


# ---------------------------------------------------------------------------
# Test 7: agent_states.json integration — disabled agents added to excluded
# ---------------------------------------------------------------------------


def test_resolve_agent_states_json_integration(tmp_path: Path):
    """Agents disabled in agent_states.json appear in excluded_agents."""
    config_dir = tmp_path / ".claude-mpm"
    config_dir.mkdir()
    states = {
        "engineer": {"enabled": True},
        "java-engineer": {"enabled": False},
        "research": {"enabled": False},
    }
    (config_dir / "agent_states.json").write_text(json.dumps(states))

    uc_mock = _make_unified_config(enabled=[], required=["engineer"])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    assert "java-engineer" in cfg.excluded_agents
    assert "research" in cfg.excluded_agents
    assert "engineer" not in cfg.excluded_agents


# ---------------------------------------------------------------------------
# Test 8: agent_states.json NOT read when enabled_agents is non-empty
# ---------------------------------------------------------------------------


def test_resolve_agent_states_only_when_enabled_empty(tmp_path: Path):
    """_resolve_agent_states is skipped when enabled_agents already populated."""
    config_dir = tmp_path / ".claude-mpm"
    config_dir.mkdir()
    states = {"java-engineer": {"enabled": False}}
    (config_dir / "agent_states.json").write_text(json.dumps(states))

    # enabled list is non-empty — agent_states bridge should NOT fire
    uc_mock = _make_unified_config(enabled=["python-engineer", "qa"], required=[])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    # enabled_agents populated → agent_states bridge skipped
    assert cfg.enabled_agents == {"python-engineer", "qa"}
    assert cfg.excluded_agents == set()


# ---------------------------------------------------------------------------
# Test 9: absent key in agent_states.json means enabled (sparse-override)
# ---------------------------------------------------------------------------


def test_resolve_agent_states_absent_means_enabled(tmp_path: Path):
    """Sparse-override: absent entry in agent_states.json == enabled."""
    config_dir = tmp_path / ".claude-mpm"
    config_dir.mkdir()
    # Only one agent explicitly disabled; others absent (not mentioned)
    states = {"java-engineer": {"enabled": False}}
    (config_dir / "agent_states.json").write_text(json.dumps(states))

    uc_mock = _make_unified_config(enabled=[], required=[])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    # Only explicitly-disabled agent is excluded
    assert cfg.excluded_agents == {"java-engineer"}
    # Absent agents are NOT in excluded_agents
    assert "engineer" not in cfg.excluded_agents
    assert "research" not in cfg.excluded_agents


# ---------------------------------------------------------------------------
# Test 10: get_agents_to_deploy for startup mode
# ---------------------------------------------------------------------------


def test_get_agents_to_deploy_startup_mode():
    """Startup mode: get_agents_to_deploy returns enabled + required - excluded."""
    cfg = AgentPipelineConfig(
        mode="startup",
        enabled_agents={"python-engineer", "typescript-engineer"},
        required_agents={"engineer", "qa"},
        excluded_agents={"qa"},
    )

    result = cfg.get_agents_to_deploy()

    assert "python-engineer" in result
    assert "typescript-engineer" in result
    assert "engineer" in result
    # qa is in required but also excluded — must NOT appear
    assert "qa" not in result


# ---------------------------------------------------------------------------
# Test 11: get_agents_to_deploy for deploy_all mode
# ---------------------------------------------------------------------------


def test_get_agents_to_deploy_deploy_all_mode():
    """deploy_all mode: get_agents_to_deploy returns cached_agents minus excluded."""
    cfg = AgentPipelineConfig(
        mode="deploy_all",
        excluded_agents={"legacy-agent"},
    )
    cached = {"engineer", "qa", "legacy-agent", "python-engineer"}

    result = cfg.get_agents_to_deploy(cached_agents=cached)

    assert result == {"engineer", "qa", "python-engineer"}
    assert "legacy-agent" not in result


# ---------------------------------------------------------------------------
# Test 12: startup bridge propagates enabled_agents to UnifiedConfig (Fix 2)
# ---------------------------------------------------------------------------


def test_startup_bridge_propagates_enabled_agents_to_unified_config(tmp_path: Path):
    """Sparse agent_states.json only excludes agents; it does NOT whitelist.

    A sparse agent_states.json with only a few entries must NOT be interpreted
    as a comprehensive allow-list.  Only agents with enabled=False are excluded;
    agents with enabled=True (or absent) are left alone.  The effective set
    is determined by required_agents (+ any config-driven enabled_agents)
    minus excluded_agents.
    """
    config_dir = tmp_path / ".claude-mpm"
    config_dir.mkdir()
    states = {
        "engineer": {"enabled": True},
        "qa": {"enabled": True},
        "java-engineer": {"enabled": False},
    }
    (config_dir / "agent_states.json").write_text(json.dumps(states))

    uc_mock = _make_unified_config(enabled=[], required=["engineer"])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    effective = cfg.get_agents_to_deploy()

    # engineer is in required → present in effective
    assert "engineer" in effective
    # qa is NOT in required or enabled_agents (sparse file does not whitelist) → absent
    assert "qa" not in effective
    # java-engineer is excluded → absent
    assert "java-engineer" not in effective
    # The sparse file only populated excluded_agents, not enabled_agents
    assert cfg.enabled_agents == set()
    assert cfg.excluded_agents == {"java-engineer"}


# ---------------------------------------------------------------------------
# Test 13: _resolve_agent_states with malformed JSON produces warning, no crash
# ---------------------------------------------------------------------------


def test_resolve_agent_states_malformed_json(tmp_path: Path):
    """Malformed agent_states.json produces a warning but does not raise."""
    config_dir = tmp_path / ".claude-mpm"
    config_dir.mkdir()
    (config_dir / "agent_states.json").write_text("{invalid json")

    uc_mock = _make_unified_config(enabled=[], required=[])

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="startup", project_dir=tmp_path)

    assert cfg.excluded_agents == set()
    assert cfg.enabled_agents == set()
    assert len(cfg.warnings) >= 1
    assert any("agent_states" in w for w in cfg.warnings)


# ---------------------------------------------------------------------------
# Test 14: invalid mode falls back to startup
# ---------------------------------------------------------------------------


def test_resolve_invalid_mode_falls_back_to_startup():
    """An unrecognised mode string falls back to 'startup' with a logged warning."""
    uc_mock = _make_unified_config()

    with (
        patch(
            "claude_mpm.config.agent_sources.AgentSourceConfiguration.load",
            return_value=_make_agent_sources(),
        ),
        patch(
            "claude_mpm.core.unified_config.UnifiedConfig",
            return_value=uc_mock,
        ),
    ):
        cfg = AgentPipelineConfig.resolve(mode="INVALID")

    assert cfg.mode == "startup"
