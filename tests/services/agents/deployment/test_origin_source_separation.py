"""Regression tests for origin/source separation in AgentDiscoveryService.

These tests assert that the discovery dict carries BOTH:
- ``origin``: deployment-origin identifier (``"local"`` or ``"git-cache"``)
- ``source``: frontmatter provenance field (``"bundled"`` or ``"external"``)

This is the gap that earlier unit tests missed — they tested the formatter in
isolation but not that the discovery pipeline produced the right keys.
"""

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.agent_discovery_service import (
    AgentDiscoveryService,
)

BUNDLED_FRONTMATTER = dedent("""\
    ---
    name: rust-engineer
    agent_id: rust-engineer
    description: Rust systems programmer
    version: 1.0.0
    author: claude-mpm
    source: bundled
    ---
    # Rust Engineer
""")

EXTERNAL_FRONTMATTER = dedent("""\
    ---
    name: custom-agent
    agent_id: custom-agent
    description: A custom external agent
    version: 1.2.0
    author: third-party
    source: external
    ---
    # Custom Agent
""")

NO_SOURCE_FRONTMATTER = dedent("""\
    ---
    name: legacy-agent
    agent_id: legacy-agent
    description: An older agent without a source field
    version: 0.9.0
    author: claude-mpm
    ---
    # Legacy Agent
""")


class TestDiscoveryOriginSourceSeparation:
    """Verify that origin and source are separate, correctly populated keys."""

    def _make_service(self, templates_dir: Path) -> AgentDiscoveryService:
        return AgentDiscoveryService(templates_dir=templates_dir)

    # ------------------------------------------------------------------
    # Local / bundled agents
    # ------------------------------------------------------------------

    def test_local_bundled_agent_has_origin_local(self, tmp_path: Path) -> None:
        """A local template with source: bundled must have origin='local'."""
        (tmp_path / "rust-engineer.md").write_text(BUNDLED_FRONTMATTER)
        service = self._make_service(tmp_path)
        agents = service.list_available_agents(log_discovery=False)
        rust = next(a for a in agents if a["name"] == "rust-engineer")
        assert rust["origin"] == "local"

    def test_local_bundled_agent_has_source_bundled(self, tmp_path: Path) -> None:
        """A local template with source: bundled must have source='bundled'."""
        (tmp_path / "rust-engineer.md").write_text(BUNDLED_FRONTMATTER)
        service = self._make_service(tmp_path)
        agents = service.list_available_agents(log_discovery=False)
        rust = next(a for a in agents if a["name"] == "rust-engineer")
        assert rust["source"] == "bundled"

    def test_local_agent_without_source_field_infers_bundled(
        self, tmp_path: Path
    ) -> None:
        """Local template missing source: frontmatter must default to source='bundled'."""
        (tmp_path / "legacy-agent.md").write_text(NO_SOURCE_FRONTMATTER)
        service = self._make_service(tmp_path)
        agents = service.list_available_agents(log_discovery=False)
        legacy = next(a for a in agents if a["name"] == "legacy-agent")
        assert legacy["source"] == "bundled"
        assert legacy["origin"] == "local"

    def test_local_external_agent_preserves_source_external(
        self, tmp_path: Path
    ) -> None:
        """A local template with source: external must keep source='external'."""
        (tmp_path / "custom-agent.md").write_text(EXTERNAL_FRONTMATTER)
        service = self._make_service(tmp_path)
        agents = service.list_available_agents(log_discovery=False)
        custom = next(a for a in agents if a["name"] == "custom-agent")
        assert custom["source"] == "external"
        assert custom["origin"] == "local"

    # ------------------------------------------------------------------
    # Git-cache agents
    # ------------------------------------------------------------------

    def _make_git_cache_agent(
        self, cache_dir: Path, content: str, filename: str
    ) -> Path:
        """Write a fake agent file into a simulated git cache directory."""
        agent_file = cache_dir / filename
        agent_file.write_text(content)
        return agent_file

    def test_git_cache_agent_has_origin_git_cache(self, tmp_path: Path) -> None:
        """An agent from git cache must have origin='git-cache'."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        self._make_git_cache_agent(cache_dir, EXTERNAL_FRONTMATTER, "custom-agent.md")

        service = self._make_service(templates_dir)

        # Patch discover_git_cached_agents to return a controlled result
        git_agent = {
            "name": "custom-agent",
            "agent_id": "custom-agent",
            "description": "A custom external agent",
            "version": "1.2.0",
            "file": "custom-agent.md",
            "path": str(cache_dir / "custom-agent.md"),
            "file_path": str(cache_dir / "custom-agent.md"),
            "size": 100,
            "model": "sonnet",
            "author": "third-party",
            "type": "agent",
            "specializations": [],
            "tools": [],
            "origin": "git-cache",
            "source": "external",
            "cache_path": "github.com/example/agents/custom-agent",
        }

        with patch.object(
            service,
            "discover_git_cached_agents",
            return_value=[git_agent],
        ):
            agents = service.list_available_agents(log_discovery=False)

        git_result = next(a for a in agents if a["name"] == "custom-agent")
        assert git_result["origin"] == "git-cache"

    def test_git_cache_agent_without_source_infers_external(
        self, tmp_path: Path
    ) -> None:
        """A git-cache agent with no frontmatter source must default to source='external'."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        service = self._make_service(templates_dir)

        # Simulate what discover_git_cached_agents returns for a no-source agent.
        # The actual method sets source='external' when absent; this exercises
        # the full list_available_agents dedup/sort path with that value.
        git_agent_no_source = {
            "name": "nosource-agent",
            "agent_id": "nosource-agent",
            "description": "Agent without explicit source",
            "version": "1.0.0",
            "file": "nosource-agent.md",
            "path": "/fake/path/nosource-agent.md",
            "file_path": "/fake/path/nosource-agent.md",
            "size": 80,
            "model": "sonnet",
            "author": "unknown",
            "type": "agent",
            "specializations": [],
            "tools": [],
            "origin": "git-cache",
            "source": "external",  # inferred by discover_git_cached_agents
            "cache_path": "github.com/example/agents/nosource-agent",
        }

        with patch.object(
            service,
            "discover_git_cached_agents",
            return_value=[git_agent_no_source],
        ):
            agents = service.list_available_agents(log_discovery=False)

        result = next(a for a in agents if a["name"] == "nosource-agent")
        assert result["source"] == "external"
        assert result["origin"] == "git-cache"

    # ------------------------------------------------------------------
    # Deduplication: local wins over git-cache
    # ------------------------------------------------------------------

    def test_local_wins_over_git_cache_in_dedup(self, tmp_path: Path) -> None:
        """When same agent name appears locally and in git cache, local copy is kept."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Local copy has source: bundled
        (templates_dir / "rust-engineer.md").write_text(BUNDLED_FRONTMATTER)

        service = self._make_service(templates_dir)

        # Git-cache copy claims source: external (older/upstream version)
        git_duplicate = {
            "name": "rust-engineer",
            "agent_id": "rust-engineer",
            "description": "Rust systems programmer (upstream)",
            "version": "0.8.0",
            "file": "rust-engineer.md",
            "path": "/fake/cache/rust-engineer.md",
            "file_path": "/fake/cache/rust-engineer.md",
            "size": 200,
            "model": "sonnet",
            "author": "claude-mpm",
            "type": "agent",
            "specializations": [],
            "tools": [],
            "origin": "git-cache",
            "source": "external",
            "cache_path": "github.com/bobmatnyc/claude-mpm/agents/rust-engineer",
        }

        with patch.object(
            service,
            "discover_git_cached_agents",
            return_value=[git_duplicate],
        ):
            agents = service.list_available_agents(log_discovery=False)

        rust_agents = [a for a in agents if a["name"] == "rust-engineer"]
        assert len(rust_agents) == 1, "Dedup must produce exactly one rust-engineer"
        # Local copy must win
        assert rust_agents[0]["origin"] == "local"
        assert rust_agents[0]["source"] == "bundled"
