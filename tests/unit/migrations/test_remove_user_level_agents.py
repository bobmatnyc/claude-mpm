"""Tests for the v6.5.81 remove-user-level-agents migration (issue #924, Fix A).

The migration removes MPM-owned agent files from the shared ``~/.claude/agents/``
directory, identifying them by frontmatter markers.  Non-MPM agent files must be
left untouched, and a missing directory is a successful no-op.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.migrations.v6_5_81_remove_user_level_agents import run_migration


@pytest.fixture()
def fake_home():
    """Yield a temporary directory to stand in for ``Path.home()``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _write_agent(agents_dir: Path, name: str, frontmatter: str) -> Path:
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / f"{name}.md"
    path.write_text(f"---\n{frontmatter}\n---\n\n# {name}\n", encoding="utf-8")
    return path


def test_removes_mpm_owned_agent(fake_home):
    """An agent whose frontmatter marks it MPM-owned is removed."""
    agents_dir = fake_home / ".claude" / "agents"
    mpm_agent = _write_agent(
        agents_dir, "engineer", "name: engineer\nauthor: claude-mpm"
    )
    assert mpm_agent.exists()

    with patch("pathlib.Path.home", return_value=fake_home):
        result = run_migration()

    assert result is True
    assert not mpm_agent.exists(), "MPM-owned agent must be removed"


def test_removes_external_source_agent(fake_home):
    """The ``source: external`` marker also identifies an MPM-owned agent."""
    agents_dir = fake_home / ".claude" / "agents"
    external_agent = _write_agent(
        agents_dir, "research", "name: research\nsource: external"
    )

    with patch("pathlib.Path.home", return_value=fake_home):
        result = run_migration()

    assert result is True
    assert not external_agent.exists()


def test_skips_non_mpm_agent(fake_home):
    """An agent without MPM markers is left untouched."""
    agents_dir = fake_home / ".claude" / "agents"
    user_agent = _write_agent(
        agents_dir, "my-custom-agent", "name: my-custom-agent\nauthor: alice"
    )
    assert user_agent.exists()

    with patch("pathlib.Path.home", return_value=fake_home):
        result = run_migration()

    assert result is True
    assert user_agent.exists(), "Non-MPM agent must be preserved"


def test_skips_agent_without_frontmatter(fake_home):
    """A file with no YAML frontmatter is not considered MPM-owned."""
    agents_dir = fake_home / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    plain = agents_dir / "notes.md"
    plain.write_text("# just some notes\n", encoding="utf-8")

    with patch("pathlib.Path.home", return_value=fake_home):
        result = run_migration()

    assert result is True
    assert plain.exists()


def test_handles_missing_dir(fake_home):
    """A missing ~/.claude/agents/ directory is a successful no-op."""
    assert not (fake_home / ".claude" / "agents").exists()

    with patch("pathlib.Path.home", return_value=fake_home):
        result = run_migration()

    assert result is True


def test_mixed_dir_removes_only_mpm(fake_home):
    """Only MPM-owned files are removed; user files remain."""
    agents_dir = fake_home / ".claude" / "agents"
    mpm_agent = _write_agent(agents_dir, "qa", "name: qa\ncategory: claude-mpm")
    user_agent = _write_agent(agents_dir, "custom", "name: custom\nauthor: bob")

    with patch("pathlib.Path.home", return_value=fake_home):
        result = run_migration()

    assert result is True
    assert not mpm_agent.exists()
    assert user_agent.exists()
