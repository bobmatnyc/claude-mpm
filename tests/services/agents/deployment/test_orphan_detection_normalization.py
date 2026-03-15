"""Tests for orphan detection filename normalization.

Verifies that _detect_and_remove_orphaned_agents() correctly handles
agents whose deployed filename differs from their cache filename due to:
- normalize_deployment_filename() stripping -agent suffix
- Frontmatter agent_id overrides

These tests focus on the normalization logic added to fix the bug where
cache filenames like 'content-agent.md' were not being recognized as
matching deployed filenames like 'content.md'.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.deployment_reconciler import DeploymentResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROVENANCE_MODULE = "claude_mpm.utils.agent_provenance"
GET_PATH_MANAGER_TARGET = "claude_mpm.core.unified_paths.get_path_manager"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_mpm_agent(path: Path, name: str, agent_id: str | None = None) -> None:
    """Write a mock MPM-managed agent file with frontmatter."""
    frontmatter_lines = [
        "---",
        f"name: {name}",
        "author: claude-mpm",
        "version: 1.0.0",
    ]
    if agent_id:
        frontmatter_lines.append(f"agent_id: {agent_id}")
    frontmatter_lines.append("---")
    frontmatter_lines.append(f"\n# {name}\n\nInstructions here.")
    path.write_text("\n".join(frontmatter_lines))


def _write_user_agent(path: Path, name: str) -> None:
    """Write a mock user-created agent file."""
    path.write_text(
        f"---\nname: {name}\nauthor: john-doe\nversion: 1.0.0\n---\n"
        f"# {name}\n\nUser instructions."
    )


def _make_config(
    *,
    enabled: list[str] | None = None,
    required: list[str] | None = None,
) -> MagicMock:
    """Create a minimal UnifiedConfig mock."""
    config = MagicMock()
    config.agents.enabled = enabled if enabled is not None else []
    config.agents.required = required if required is not None else []
    return config


def _make_deployment_result() -> DeploymentResult:
    """Create an empty DeploymentResult."""
    return DeploymentResult(deployed=[], removed=[], unchanged=[], errors=[])


def _make_path_manager_mock(cache_agents_dir: Path) -> MagicMock:
    """Return a mock path_manager wired to *cache_agents_dir*."""
    pm = MagicMock()
    pm.get_cache_dir.return_value = cache_agents_dir.parent
    return pm


def _call_detect(
    tmp_path: Path,
    cache_dir: Path,
    config: MagicMock,
) -> list[str]:
    """Invoke _detect_and_remove_orphaned_agents with standard mocks."""

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

            return _detect_and_remove_orphaned_agents(
                tmp_path, config, _make_deployment_result()
            )


# ---------------------------------------------------------------------------
# Tests: _extract_agent_id_from_frontmatter helper
# ---------------------------------------------------------------------------


class TestExtractAgentIdFromFrontmatter:
    """Unit tests for the _extract_agent_id_from_frontmatter helper."""

    def _extract(self, content: str) -> str | None:
        from claude_mpm.services.agents.deployment.startup_reconciliation import (
            _extract_agent_id_from_frontmatter,
        )

        return _extract_agent_id_from_frontmatter(content)

    def test_returns_agent_id_when_present(self) -> None:
        """Returns the agent_id value when frontmatter contains it."""
        content = "---\nname: web-ui\nagent_id: web-ui-engineer\nauthor: claude-mpm\n---\n\n# Agent"
        assert self._extract(content) == "web-ui-engineer"

    def test_returns_none_when_no_frontmatter(self) -> None:
        """Returns None when file has no YAML frontmatter."""
        content = "# Just a heading\n\nNo frontmatter here."
        assert self._extract(content) is None

    def test_returns_none_when_no_agent_id_field(self) -> None:
        """Returns None when frontmatter exists but has no agent_id key."""
        content = (
            "---\nname: some-agent\nauthor: claude-mpm\nversion: 1.0.0\n---\n\n# Agent"
        )
        assert self._extract(content) is None

    def test_handles_single_quoted_agent_id(self) -> None:
        """Strips single quotes from agent_id value."""
        content = "---\nagent_id: 'my-agent'\n---\n\n# Agent"
        assert self._extract(content) == "my-agent"

    def test_handles_double_quoted_agent_id(self) -> None:
        """Strips double quotes from agent_id value."""
        content = '---\nagent_id: "my-agent"\n---\n\n# Agent'
        assert self._extract(content) == "my-agent"

    def test_handles_incomplete_frontmatter(self) -> None:
        """Returns None when frontmatter delimiter appears only once."""
        content = "---\nagent_id: my-agent\nno closing delimiter"
        assert self._extract(content) is None


# ---------------------------------------------------------------------------
# Tests: -agent suffix stripping in normalization
# ---------------------------------------------------------------------------


class TestAgentSuffixNormalization:
    """Verify that cache files with -agent suffix are not flagged as orphans."""

    def test_cache_content_agent_matches_deployed_content(self, tmp_path: Path) -> None:
        """content-agent.md in cache matches content.md in deploy dir — NOT orphan."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Cache has 'content-agent.md'; deployed as 'content.md'
        _write_mpm_agent(cache_dir / "content-agent.md", "content-agent")
        deployed_file = deploy_dir / "content.md"
        _write_mpm_agent(deployed_file, "content")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "content" not in removed, (
            "content.md should NOT be removed: content-agent.md in cache normalizes to content"
        )
        assert deployed_file.exists(), "content.md must be preserved"

    def test_cache_tmux_agent_matches_deployed_tmux(self, tmp_path: Path) -> None:
        """tmux-agent.md in cache matches tmux.md in deploy dir — NOT orphan."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        _write_mpm_agent(cache_dir / "tmux-agent.md", "tmux-agent")
        deployed_file = deploy_dir / "tmux.md"
        _write_mpm_agent(deployed_file, "tmux")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "tmux" not in removed
        assert deployed_file.exists()

    def test_cache_memory_manager_agent_matches_deployed_memory_manager(
        self, tmp_path: Path
    ) -> None:
        """memory-manager-agent.md in cache matches memory-manager.md — NOT orphan."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        _write_mpm_agent(cache_dir / "memory-manager-agent.md", "memory-manager-agent")
        deployed_file = deploy_dir / "memory-manager.md"
        _write_mpm_agent(deployed_file, "memory-manager")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "memory-manager" not in removed
        assert deployed_file.exists()


# ---------------------------------------------------------------------------
# Tests: frontmatter agent_id override
# ---------------------------------------------------------------------------


class TestFrontmatterAgentIdOverride:
    """Verify that frontmatter agent_id overrides are respected during orphan detection."""

    def test_frontmatter_agent_id_prevents_orphan_removal(self, tmp_path: Path) -> None:
        """web-ui.md with agent_id: web-ui-engineer matches deployed web-ui-engineer.md."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Cache: web-ui.md with frontmatter agent_id overriding deployed name
        _write_mpm_agent(cache_dir / "web-ui.md", "web-ui", agent_id="web-ui-engineer")
        # Deployed as web-ui-engineer.md (the agent_id)
        deployed_file = deploy_dir / "web-ui-engineer.md"
        _write_mpm_agent(deployed_file, "web-ui-engineer")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "web-ui-engineer" not in removed, (
            "web-ui-engineer.md should NOT be removed: "
            "web-ui.md in cache declares agent_id: web-ui-engineer"
        )
        assert deployed_file.exists()

    def test_frontmatter_agent_id_with_underscore_is_normalized(
        self, tmp_path: Path
    ) -> None:
        """agent_id with underscores is normalized to dashes before matching.

        Uses an agent_id that does NOT end in '_agent' because
        normalize_deployment_filename() strips '-agent' suffixes.
        Real-world agent_ids follow this convention.
        """
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Cache agent declares agent_id with underscores (e.g. my_special_tool)
        _write_mpm_agent(
            cache_dir / "my-tool.md", "my-tool", agent_id="my_special_tool"
        )
        deployed_file = deploy_dir / "my-special-tool.md"
        _write_mpm_agent(deployed_file, "my-special-tool")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "my-special-tool" not in removed
        assert deployed_file.exists()


# ---------------------------------------------------------------------------
# Tests: all 4 renamed agents survive together
# ---------------------------------------------------------------------------


class TestAllRenamedAgentsSurvive:
    """The 4 agents renamed in the fix should all survive orphan detection."""

    def test_all_four_renamed_agents_survive(self, tmp_path: Path) -> None:
        """tmux, content, memory-manager (via -agent suffix) and web-ui-engineer
        (via agent_id frontmatter) are all preserved."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Build cache
        _write_mpm_agent(cache_dir / "tmux-agent.md", "tmux-agent")
        _write_mpm_agent(cache_dir / "content-agent.md", "content-agent")
        _write_mpm_agent(cache_dir / "memory-manager-agent.md", "memory-manager-agent")
        _write_mpm_agent(cache_dir / "web-ui.md", "web-ui", agent_id="web-ui-engineer")

        # Build deployed
        deployed_files = {
            "tmux": deploy_dir / "tmux.md",
            "content": deploy_dir / "content.md",
            "memory-manager": deploy_dir / "memory-manager.md",
            "web-ui-engineer": deploy_dir / "web-ui-engineer.md",
        }
        for stem, path in deployed_files.items():
            _write_mpm_agent(path, stem)

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        for stem, path in deployed_files.items():
            assert stem not in removed, (
                f"{stem}.md should NOT be removed during orphan detection"
            )
            assert path.exists(), f"{stem}.md must remain on disk"


# ---------------------------------------------------------------------------
# Tests: true orphans are still removed
# ---------------------------------------------------------------------------


class TestTrueOrphansAreRemoved:
    """Regression guard: genuine orphans must still be removed after the fix."""

    def test_true_mpm_orphan_is_removed(self, tmp_path: Path) -> None:
        """MPM agent deployed but absent from cache and config is removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Put something in cache so expected_stems is non-empty
        _write_mpm_agent(cache_dir / "active-agent.md", "active-agent")

        # True orphan: MPM-managed, not in cache under any name
        orphan_file = deploy_dir / "old-removed-agent.md"
        _write_mpm_agent(orphan_file, "old-removed-agent")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "old-removed-agent" in removed, (
            "True MPM orphan not present in cache should be removed"
        )
        assert not orphan_file.exists(), "Orphan file should be deleted from disk"

    def test_orphan_removed_while_normalized_agents_preserved(
        self, tmp_path: Path
    ) -> None:
        """Orphan is removed while normalized (suffix-stripped) agents are preserved."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Cache has content-agent (normalizes to content)
        _write_mpm_agent(cache_dir / "content-agent.md", "content-agent")

        # Deployed: content.md (normalized match), and an orphan
        preserved_file = deploy_dir / "content.md"
        _write_mpm_agent(preserved_file, "content")
        orphan_file = deploy_dir / "stale-deprecated.md"
        _write_mpm_agent(orphan_file, "stale-deprecated")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "content" not in removed
        assert preserved_file.exists()
        assert "stale-deprecated" in removed
        assert not orphan_file.exists()


# ---------------------------------------------------------------------------
# Tests: user agents are preserved regardless
# ---------------------------------------------------------------------------


class TestUserAgentsPreserved:
    """User-authored agents must never be removed by orphan detection."""

    def test_user_agent_not_in_cache_is_preserved(self, tmp_path: Path) -> None:
        """User agent absent from cache is NOT removed (existing behavior)."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # Put something in cache so expected_stems is non-empty
        _write_mpm_agent(cache_dir / "some-mpm-agent.md", "some-mpm-agent")

        # User agent — not in cache
        user_file = deploy_dir / "my-custom-workflow.md"
        _write_user_agent(user_file, "my-custom-workflow")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "my-custom-workflow" not in removed, (
            "User agent must be preserved even if absent from cache"
        )
        assert user_file.exists()

    def test_user_agent_preserved_alongside_mpm_orphan(self, tmp_path: Path) -> None:
        """User agent and MPM orphan coexist: only the MPM orphan is removed."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        _write_mpm_agent(cache_dir / "active-agent.md", "active-agent")

        user_file = deploy_dir / "user-special.md"
        _write_user_agent(user_file, "user-special")

        orphan_file = deploy_dir / "mpm-orphan.md"
        _write_mpm_agent(orphan_file, "mpm-orphan")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        assert "user-special" not in removed
        assert user_file.exists()
        assert "mpm-orphan" in removed
        assert not orphan_file.exists()
