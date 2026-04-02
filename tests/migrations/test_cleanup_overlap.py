"""Tests for the startup overlap cleanup system.

Tests use tmp_path and monkeypatch to avoid touching real ~/.claude/ directories.
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
# Agent overlap tests
# ---------------------------------------------------------------------------


class TestCleanupAgentOverlap:
    """Tests for cleanup_agent_overlap."""

    def test_archives_duplicates(self, fake_home: Path, fake_project: Path):
        """When both user and project copies exist, project copy is archived."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "pm", content="# user pm")
        _setup_agent_file(fake_project / ".claude", "pm", content="# project pm")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            result = cleanup_agent_overlap(fake_project)

        assert "pm" in result["archived"]
        # Project file removed
        assert not (fake_project / ".claude" / "agents" / "pm.md").exists()
        # Archived copy exists
        archived_files = list(
            (fake_project / ".claude" / "agents" / "archived").rglob("pm.md")
        )
        assert len(archived_files) == 1

    @pytest.mark.usefixtures("fake_home")
    def test_skips_non_duplicates(self, fake_project: Path):
        """Agent only at project level should NOT be archived (no user copy)."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        # Only project copy, no user copy
        _setup_agent_file(fake_project / ".claude", "pm", content="# project pm")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            result = cleanup_agent_overlap(fake_project)

        assert "pm" in result["skipped"]
        assert result["archived"] == []
        # Project file still there
        assert (fake_project / ".claude" / "agents" / "pm.md").exists()


# ---------------------------------------------------------------------------
# Skill overlap tests
# ---------------------------------------------------------------------------


class TestCleanupSkillOverlap:
    """Tests for cleanup_skill_overlap."""

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
# Stale agent names tests
# ---------------------------------------------------------------------------


class TestCleanupStaleAgentNames:
    """Tests for cleanup_stale_agent_names."""

    def test_archives_stale_suffix(self, fake_home: Path):
        """Stale '-agent' suffixed file gets archived when correct name exists."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "research-agent", content="# stale")
        _setup_agent_file(user_claude, "research", content="# correct")

        result = cleanup_stale_agent_names()

        assert "research-agent" in result["archived"]
        # Stale file removed
        assert not (user_claude / "agents" / "research-agent.md").exists()
        # Correct file untouched
        assert (user_claude / "agents" / "research.md").exists()

    def test_skips_when_no_correct_replacement(self, fake_home: Path):
        """Stale file should NOT be archived if the correct name is missing."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "research-agent", content="# stale")
        # No "research.md" exists

        result = cleanup_stale_agent_names()

        assert "research-agent" in result["skipped"]
        # Stale file still there
        assert (user_claude / "agents" / "research-agent.md").exists()


# ---------------------------------------------------------------------------
# Dry-run tests
# ---------------------------------------------------------------------------


class TestDryRun:
    """Tests for dry_run=True mode."""

    def test_does_not_modify_agents(self, fake_home: Path, fake_project: Path):
        """dry_run=True leaves all files in place."""
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

        assert "pm" in result["archived"]  # Reported as would-archive
        assert project_file.exists()  # But file still there
        # No archive directory created
        assert not (fake_project / ".claude" / "agents" / "archived").exists()

    def test_does_not_modify_stale_agents(self, fake_home: Path):
        """dry_run=True leaves stale agent files in place."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        stale_file = _setup_agent_file(user_claude, "research-agent")
        _setup_agent_file(user_claude, "research")

        result = cleanup_stale_agent_names(dry_run=True)

        assert "research-agent" in result["archived"]
        assert stale_file.exists()


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Tests that running cleanup twice does not error or double-archive."""

    def test_second_run_agent_overlap(self, fake_home: Path, fake_project: Path):
        """Running agent overlap cleanup twice doesn't error."""
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

        assert "pm" in result1["archived"]
        # Second run: project file gone, so it's skipped
        assert "pm" in result2["skipped"]
        assert result2["errors"] == []

    def test_second_run_stale_agents(self, fake_home: Path):
        """Running stale cleanup twice doesn't error."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "research-agent")
        _setup_agent_file(user_claude, "research")

        result1 = cleanup_stale_agent_names()
        result2 = cleanup_stale_agent_names()

        assert "research-agent" in result1["archived"]
        assert "research-agent" in result2["skipped"]
        assert result2["errors"] == []


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest:
    """Tests for _cleanup_manifest.json creation."""

    def test_manifest_written_for_agent_overlap(
        self, fake_home: Path, fake_project: Path
    ):
        """Verify _cleanup_manifest.json exists and has correct structure."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_agent_overlap

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "pm", content="# user pm")
        _setup_agent_file(fake_project / ".claude", "pm", content="# project pm")

        with patch(
            "claude_mpm.migrations.cleanup_overlap._get_user_level_agents",
            return_value=frozenset({"pm"}),
        ):
            cleanup_agent_overlap(fake_project)

        # Find manifest
        manifests = list(
            (fake_project / ".claude" / "agents" / "archived").rglob(
                "_cleanup_manifest.json"
            )
        )
        assert len(manifests) == 1

        manifest = json.loads(manifests[0].read_text())
        assert "cleanup_date" in manifest
        assert "reason" in manifest
        assert "source_level" in manifest
        assert manifest["source_level"] == "project"
        assert "superseded_by" in manifest
        assert "archived_files" in manifest
        assert "pm.md" in manifest["archived_files"]

    def test_manifest_written_for_stale_agents(self, fake_home: Path):
        """Verify manifest is written when stale agents are archived."""
        from claude_mpm.migrations.cleanup_overlap import cleanup_stale_agent_names

        user_claude = fake_home / ".claude"
        _setup_agent_file(user_claude, "research-agent")
        _setup_agent_file(user_claude, "research")

        cleanup_stale_agent_names()

        manifests = list(
            (user_claude / "agents" / "archived").rglob("_cleanup_manifest.json")
        )
        assert len(manifests) == 1

        manifest = json.loads(manifests[0].read_text())
        assert manifest["source_level"] == "user"
        assert "research-agent.md" in manifest["archived_files"]


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
