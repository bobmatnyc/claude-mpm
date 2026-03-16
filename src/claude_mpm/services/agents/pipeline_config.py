"""Agent pipeline configuration resolver.

Consolidates the 6 config sources used across agent pipeline commands into a
single resolved config object, with per-command resolution modes.

Resolution modes:
    startup       - used by sync_remote_agents_on_startup()
    deploy_all    - deploy everything in cache minus exclusions
    reconcile     - used by agents_reconcile command
    configure     - used by configure command
    auto_configure - used by auto_configure command

Design: fail-safe — all _resolve_* helpers catch exceptions and append
warnings; resolve() never raises.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_VALID_MODES = frozenset(
    {"startup", "deploy_all", "reconcile", "configure", "auto_configure"}
)


@dataclass
class AgentPipelineConfig:
    """Consolidated, resolved configuration for agent pipeline commands.

    Attributes:
        repositories:      Enabled GitRepository instances from AgentSourceConfiguration.
        enabled_agents:    Explicit set of agent IDs to deploy (from UnifiedConfig or profile).
        required_agents:   Agents that are always deployed (from UnifiedConfig.agents.required).
        include_universal: Whether to auto-include universal-category agents.
        excluded_agents:   Agents that must NOT be deployed (from agent_states.json disabled list).
        mode:              Resolution mode — controls get_agents_to_deploy() behaviour.
        warnings:          Non-fatal issues collected during resolution.
    """

    repositories: list = field(default_factory=list)
    enabled_agents: set = field(default_factory=set)
    required_agents: set = field(default_factory=set)
    include_universal: bool = True
    excluded_agents: set = field(default_factory=set)
    mode: str = "startup"
    warnings: list = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Public factory                                                        #
    # ------------------------------------------------------------------ #

    @classmethod
    def resolve(
        cls,
        mode: str = "startup",
        profile: str | None = None,
        project_dir: Path | None = None,
    ) -> AgentPipelineConfig:
        """Resolve all config sources into a single AgentPipelineConfig.

        Args:
            mode:        One of the _VALID_MODES values.
            profile:     Active profile name (optional — may be None).
            project_dir: Project root for reading .claude-mpm/agent_states.json.
                         Defaults to Path.cwd() when needed.

        Returns:
            Fully-resolved AgentPipelineConfig; never raises.
        """
        if mode not in _VALID_MODES:
            logger.warning("Unknown pipeline mode %r — falling back to 'startup'", mode)
            mode = "startup"

        config = cls(mode=mode)

        config._resolve_repositories()
        config._resolve_unified_config()

        if profile:
            config._resolve_profile(profile, project_dir)

        # Phase 2b bridge: read agent_states.json when no explicit enabled set
        if mode in ("startup", "reconcile") and not config.enabled_agents:
            config._resolve_agent_states(project_dir)

        return config

    # ------------------------------------------------------------------ #
    # Private resolution helpers (all fail-safe)                           #
    # ------------------------------------------------------------------ #

    def _resolve_repositories(self) -> None:
        """Populate repositories from AgentSourceConfiguration."""
        try:
            from claude_mpm.config.agent_sources import AgentSourceConfiguration

            agent_sources = AgentSourceConfiguration.load()
            self.repositories = agent_sources.get_enabled_repositories()
        except Exception as exc:
            msg = f"Could not load agent source configuration: {exc}"
            logger.warning(msg)
            self.warnings.append(msg)

    def _resolve_unified_config(self) -> None:
        """Populate enabled_agents, required_agents, include_universal from UnifiedConfig."""
        try:
            from claude_mpm.core.unified_config import UnifiedConfig

            unified = UnifiedConfig()
            if unified.agents.enabled:
                self.enabled_agents = set(unified.agents.enabled)
            if unified.agents.required:
                self.required_agents = set(unified.agents.required)
            self.include_universal = unified.agents.include_universal
        except Exception as exc:
            msg = f"Could not load unified config: {exc}"
            logger.warning(msg)
            self.warnings.append(msg)

    def _resolve_profile(
        self, profile_name: str, project_dir: Path | None = None
    ) -> None:
        """Override enabled_agents from a named deployment profile.

        The profile's enabled agent list fully replaces any enabled list
        previously set by _resolve_unified_config.
        """
        try:
            from claude_mpm.services.profile_manager import ProfileManager

            effective_dir = project_dir or Path.cwd()
            pm = ProfileManager(project_dir=effective_dir)
            success = pm.load_profile(profile_name)

            if success:
                profile_agents = pm.get_enabled_agents()
                if profile_agents:
                    self.enabled_agents = profile_agents
                    logger.info(
                        "Profile '%s': %d agents enabled",
                        profile_name,
                        len(profile_agents),
                    )
            else:
                msg = f"Profile '{profile_name}' not found or failed to load"
                logger.warning(msg)
                self.warnings.append(msg)

        except Exception as exc:
            msg = f"Could not load profile '{profile_name}': {exc}"
            logger.warning(msg)
            self.warnings.append(msg)

    def _resolve_agent_states(self, project_dir: Path | None = None) -> None:
        """Read agent_states.json and populate enabled_agents and excluded_agents.

        Searches project scope first, then user scope (~/.claude-mpm/), using
        the first file found.  Project scope takes precedence.

        Sparse-override semantics: absent key means *enabled*.
        Agents with enabled=True are added to enabled_agents.
        Agents with enabled=False are added to excluded_agents.
        """
        try:
            effective_dir = project_dir or Path.cwd()
            candidate_paths = [
                effective_dir / ".claude-mpm" / "agent_states.json",
                Path.home() / ".claude-mpm" / "agent_states.json",
            ]

            states_path: Path | None = None
            for candidate in candidate_paths:
                if candidate.exists():
                    states_path = candidate
                    break

            if states_path is None:
                return

            with states_path.open() as fh:
                states: dict = json.load(fh)

            for agent_name, agent_state in states.items():
                if isinstance(agent_state, dict):
                    enabled = agent_state.get("enabled", True)
                else:
                    # Treat unexpected formats as enabled (defensive)
                    enabled = True

                if enabled:
                    self.enabled_agents.add(agent_name)
                else:
                    self.excluded_agents.add(agent_name)

        except Exception as exc:
            msg = f"Could not read agent_states.json: {exc}"
            logger.warning(msg)
            self.warnings.append(msg)

    # ------------------------------------------------------------------ #
    # Deployment helpers                                                    #
    # ------------------------------------------------------------------ #

    def get_agents_to_deploy(self, cached_agents: set | None = None) -> set:
        """Return the set of agent IDs that should be deployed.

        Args:
            cached_agents: All agents available in the local cache.
                           Required when mode == 'deploy_all'.

        Returns:
            Set of agent IDs to deploy, respecting excluded_agents.
        """
        if self.mode == "deploy_all":
            # Future-proofing: agents.py:_deploy_agents() is not yet wired to use
            # AgentPipelineConfig. This mode preserves the current "deploy everything"
            # behavior for when the caller is eventually migrated.
            base = (cached_agents or set()).copy()
            return base - self.excluded_agents

        if self.mode == "auto_configure":
            return self.enabled_agents - self.excluded_agents

        # startup / reconcile / configure: merge enabled + required
        agents: set = set()
        if self.enabled_agents:
            agents.update(self.enabled_agents)
        agents.update(self.required_agents)
        return agents - self.excluded_agents
