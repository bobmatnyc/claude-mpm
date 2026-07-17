"""Tests for the startup overlap cleanup system.

Tests use tmp_path and monkeypatch to avoid touching real ~/.claude/ directories.

Fix A for issue #924 removed user-level agent routing: ``cleanup_agent_overlap``
and ``cleanup_stale_agent_names`` are now no-ops (they return empty results and
touch no files).  Skill overlap cleanup is a separate concern and remains active.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_agent_file(base: Path, name: str, content: str = "# agent") -> Path:
    """Create a .md agent file under base/agents/."""
    agents_dir = base / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / f"{name}.md"
    agent_file.write_text(content)
    return agent_file


def _setup_skill_dir(base: Path, name: str) -> Path:
    """Create a skill directory with a SKILL.md under base/skills/."""
    skill_dir = base / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"# {name} skill")
    return skill_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Override Path.home() to return a temp directory."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def fake_project(tmp_path: Path):
    """Return a temp directory used as the project root."""
    project = tmp_path / "project"
    project.mkdir()
    return project


# ---------------------------------------------------------------------------
# Agent overlap tests (now a no-op)
# ---------------------------------------------------------------------------


class TestCleanupAgentOverlapIsNoOp:
    """cleanup_agent_overlap is a no-op after Fix A for #924."""

    def test_does_not_archive_duplicates(self, fake_home: Path, fake_project: Path):
        """Even when both user and project copies exist, nothing is archived."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "pm", content="# user pm")
        project_file = _setup_agent_file(
            fake_project / ".claude", "pm", content="# project pm"
        )

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            result = cleanup_agent_overlap(fake_project)

        assert result == {"archived": [], "skipped": [], "errors": []}
        # Project file left intact — no archiving.
        assert project_file.exists()
        assert not (fake_project / ".claude" / "agents" / "archived").exists()

    @pytest.mark.usefixtures("fake_home")
    def test_returns_empty_result(self, fake_project: Path):
        """The no-op returns empty result lists regardless of inputs."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        _setup_agent_file(fake_project / ".claude", "pm", content="# project pm")

        result = cleanup_agent_overlap(fake_project)

        assert result == {"archived": [], "skipped": [], "errors": []}


# ---------------------------------------------------------------------------
# Skill overlap tests (unchanged behavior)
# ---------------------------------------------------------------------------


class TestCleanupSkillOverlap:
    """Tests for cleanup_skill_overlap (still active)."""

    def test_archives_duplicates(self, fake_home: Path, fake_project: Path):
        """When both user and project copies exist, project copy is archived."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_skill_overlap

        user_claude = fake_home / ".claude"
        _setup_skill_dir(user_claude, "mpm-help")
        _setup_skill_dir(fake_project / ".claude", "mpm-help")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_skills",
            return_value=frozenset({"mpm-help"}),
        ):
            result = cleanup_skill_overlap(fake_project)

        assert "mpm-help" in result["archived"]
        # Project dir removed
        assert not (fake_project / ".claude" / "skills" / "mpm-help").exists()
        # Archived copy exists
        archived_dirs = list(
            (fake_project / ".claude" / "skills" / "archived").rglob("mpm-help")
        )
        assert len(archived_dirs) == 1


# ---------------------------------------------------------------------------
# Stale agent names tests (now a no-op)
# ---------------------------------------------------------------------------


class TestCleanupStaleAgentNamesIsNoOp:
    """cleanup_stale_agent_names is a no-op after Fix A for #924."""

    def test_does_not_archive_stale_suffix(self, fake_home: Path):
        """A stale '-agent' suffixed file is left untouched."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        stale_file = _setup_agent_file(user_claude, "research-agent", content="# stale")
        _setup_agent_file(user_claude, "research", content="# correct")

        result = cleanup_stale_agent_names()

        assert result == {"archived": [], "skipped": [], "errors": []}
        # Both files remain — nothing archived.
        assert stale_file.exists()
        assert (user_claude / "agents" / "research.md").exists()
        assert not (user_claude / "agents" / "archived").exists()


# ---------------------------------------------------------------------------
# Dry-run tests (no-op functions ignore dry_run and archive nothing)
# ---------------------------------------------------------------------------


class TestDryRun:
    """Tests for dry_run=True mode against the no-op agent functions."""

    def test_does_not_modify_agents(self, fake_home: Path, fake_project: Path):
        """dry_run=True on the no-op still leaves all files in place."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "pm", content="# user pm")
        project_file = _setup_agent_file(
            fake_project / ".claude", "pm", content="# project pm"
        )

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            result = cleanup_agent_overlap(fake_project, dry_run=True)

        assert result["archived"] == []
        assert project_file.exists()
        assert not (fake_project / ".claude" / "agents" / "archived").exists()

    def test_does_not_modify_stale_agents(self, fake_home: Path):
        """dry_run=True on the no-op leaves stale agent files in place."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        stale_file = _setup_agent_file(user_claude, "research-agent")
        _setup_agent_file(user_claude, "research")

        result = cleanup_stale_agent_names(dry_run=True)

        assert result["archived"] == []
        assert stale_file.exists()


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Tests that running cleanup twice does not error or double-archive."""

    def test_second_run_agent_overlap(self, fake_home: Path, fake_project: Path):
        """Running agent overlap cleanup twice doesn't error (no-op)."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "pm", content="# user pm")
        _setup_agent_file(fake_project / ".claude", "pm", content="# project pm")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            result1 = cleanup_agent_overlap(fake_project)
            result2 = cleanup_agent_overlap(fake_project)

        assert result1 == {"archived": [], "skipped": [], "errors": []}
        assert result2 == {"archived": [], "skipped": [], "errors": []}

    def test_second_run_stale_agents(self, fake_home: Path):
        """Running stale cleanup twice doesn't error (no-op)."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "research-agent")
        _setup_agent_file(user_claude, "research")

        result1 = cleanup_stale_agent_names()
        result2 = cleanup_stale_agent_names()

        assert result1 == {"archived": [], "skipped": [], "errors": []}
        assert result2 == {"archived": [], "skipped": [], "errors": []}


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest:
    """The no-op agent/stale functions never write a manifest.

    Skill overlap still writes a manifest, so that path is covered here.
    """

    def test_no_manifest_written_for_agent_overlap(
        self, fake_home: Path, fake_project: Path
    ):
        """No _cleanup_manifest.json is created by the no-op agent cleanup."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "pm", content="# user pm")
        _setup_agent_file(fake_project / ".claude", "pm", content="# project pm")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            cleanup_agent_overlap(fake_project)

        manifests = list(
            (fake_project / ".claude" / "agents").rglob("_cleanup_manifest.json")
        )
        assert manifests == []

    def test_manifest_written_for_skill_overlap(
        self, fake_home: Path, fake_project: Path
    ):
        """Skill overlap cleanup still writes a manifest with correct structure."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_skill_overlap

        user_claude = fake_home / ".claude"
        _setup_skill_dir(user_claude, "mpm-help")
        _setup_skill_dir(fake_project / ".claude", "mpm-help")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_skills",
            return_value=frozenset({"mpm-help"}),
        ):
            cleanup_skill_overlap(fake_project)

        manifests = list(
            (fake_project / ".claude" / "skills" / "archived").rglob(
                "_cleanup_manifest.json"
            )
        )
        assert len(manifests) == 1

        manifest = json.loads(manifests[0].read_text())
        assert "cleanup_date" in manifest
        assert manifest["source_level"] == "project"
        assert "mpm-help" in manifest["archived_files"]


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------


class TestRunOverlapCleanup:
    """Tests for the run_overlap_cleanup orchestrator."""

    @pytest.mark.usefixtures("fake_home")
    def test_returns_combined_results(self, fake_project: Path):
        """Orchestrator returns combined results from all three cleanups."""
        from claude_mpm.migrations.cleanup_overlap import run_overlap_cleanup

        with (
            patch(
                "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
                return_value=frozenset(),
            ),
            patch(
                "claude_mpm.migrations.cleanup_overlap._get_user_level_skills",
                return_value=frozenset(),
            ),
        ):
            result = run_overlap_cleanup(fake_project)

        assert "agents" in result
        assert "skills" in result
        assert "stale_agents" in result
        for key in ("agents", "skills", "stale_agents"):
            assert "archived" in result[key]
            assert "skipped" in result[key]
            assert "errors" in result[key]
