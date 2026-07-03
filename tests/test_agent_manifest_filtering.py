"""Tests for per-project agent manifest filtering (issue #923).

WHAT: Verifies that ``FrameworkLoader._generate_agent_capabilities_section``
filters the deployed-agent catalog by ``.claude-mpm/agent_manifest.json``
when the manifest is present, falls back to today's full-catalog behavior
when it is absent, and tolerates manifest entries that reference agent IDs
no longer present on disk. Also covers the ``agent_manifest`` module's
write/read round trip in isolation.

WHY: Issue #923 -- the PM's "Available Agent Capabilities" system prompt
section previously exposed every ``.claude/agents/*.md`` file regardless of
project relevance (~50 agents in practice). This module pins the filtering
behavior added to ``framework_loader.py`` and the manifest persistence
helpers in ``agent_manifest.py`` so both remain backward compatible for
projects that never ran auto-configure.

References
----------
GitHub issue: https://github.com/bobmatnyc/claude-mpm/issues/923
LINK: none
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.agent_manifest import (
    get_manifest_path,
    read_agent_manifest,
    write_agent_manifest,
)

_AGENT_MD_TEMPLATE = """---
name: {agent_id}
description: Test agent {agent_id}
model: sonnet
---

# {agent_id}

Test agent instructions.
"""


def _write_agent_md(agents_dir: Path, agent_id: str) -> None:
    """Write a minimal deployable agent .md file with YAML frontmatter."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{agent_id}.md").write_text(
        _AGENT_MD_TEMPLATE.format(agent_id=agent_id), encoding="utf-8"
    )


def _make_loader():
    """Build a FrameworkLoader with capability/metadata caching disabled so
    each call regenerates from disk instead of returning a stale cached
    string (mirrors the pattern used in test_local_agent_templates.py)."""
    from claude_mpm.core.framework_loader import FrameworkLoader

    with patch("claude_mpm.core.framework_loader.CacheManager") as mock_cache_cls:
        mock_cache = MagicMock()
        mock_cache.get_capabilities.return_value = None
        mock_cache.get_agent_metadata.return_value = None
        mock_cache_cls.return_value = mock_cache
        mock_cache_cls.__name__ = "CacheManager"  # avoid MagicMock repr leaking
        return FrameworkLoader()


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    """Chdir into an isolated project directory and neutralize
    ``Path.home()`` so the real ``~/.claude/agents`` catalog on the
    developer/CI machine can't leak into assertions about the project's
    deployed-agent set.

    Also clears ``CLAUDE_MPM_USER_PWD``: when set (e.g. this very repo's dev
    environment), ``PathResolver._get_working_dir()``/``find_project_root()``
    prefer it over ``Path.cwd()``, which would otherwise silently point
    project-root resolution back at the real repo instead of ``project_dir``
    and break every test in this module.
    """
    project_dir = tmp_path / "project"
    fake_home = tmp_path / "fake_home"
    project_dir.mkdir()
    fake_home.mkdir()

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.delenv("CLAUDE_MPM_USER_PWD", raising=False)

    return project_dir


class TestCapabilitiesManifestFiltering:
    """FrameworkLoader._generate_agent_capabilities_section manifest behavior."""

    def test_manifest_present_filters_to_listed_agents(self, isolated_project):
        """A manifest listing a subset of deployed agents narrows the
        capabilities section to just that subset."""
        agents_dir = isolated_project / ".claude" / "agents"
        _write_agent_md(agents_dir, "engineer")
        _write_agent_md(agents_dir, "python-engineer")
        _write_agent_md(agents_dir, "rust-engineer")

        write_agent_manifest(isolated_project, ["engineer", "python-engineer"])

        capabilities = _make_loader()._generate_agent_capabilities_section()

        assert "`engineer`" in capabilities
        assert "`python-engineer`" in capabilities
        assert "`rust-engineer`" not in capabilities

    def test_manifest_absent_keeps_full_catalog(self, isolated_project):
        """Regression guard: with no manifest file, every deployed agent
        still appears (today's pre-#923 behavior, unchanged)."""
        agents_dir = isolated_project / ".claude" / "agents"
        _write_agent_md(agents_dir, "engineer")
        _write_agent_md(agents_dir, "python-engineer")
        _write_agent_md(agents_dir, "rust-engineer")

        manifest_path = get_manifest_path(isolated_project)
        assert not manifest_path.exists()

        capabilities = _make_loader()._generate_agent_capabilities_section()

        assert "`engineer`" in capabilities
        assert "`python-engineer`" in capabilities
        assert "`rust-engineer`" in capabilities

    def test_manifest_referencing_missing_agent_id_does_not_crash(
        self, isolated_project
    ):
        """A stale manifest entry for an agent ID that no longer exists on
        disk must be skipped gracefully, not raise."""
        agents_dir = isolated_project / ".claude" / "agents"
        _write_agent_md(agents_dir, "engineer")

        write_agent_manifest(isolated_project, ["engineer", "long-retired-agent-xyz"])

        capabilities = _make_loader()._generate_agent_capabilities_section()

        assert "`engineer`" in capabilities
        assert "long-retired-agent-xyz" not in capabilities

    def test_empty_manifest_yields_no_agents_but_does_not_crash(self, isolated_project):
        """An empty (but present) manifest filters every project-specific
        agent out. ``generate_capabilities_section`` treats an empty
        deployed-agent list the same as "no agents found" and returns its
        generic fallback text -- this must not crash, and must not include
        the project-specific agent that the manifest filtered out."""
        agents_dir = isolated_project / ".claude" / "agents"
        _write_agent_md(agents_dir, "python-engineer")

        write_agent_manifest(isolated_project, [])

        capabilities = _make_loader()._generate_agent_capabilities_section()

        assert "Available Agent Capabilities" in capabilities
        assert "`python-engineer`" not in capabilities


class TestFilterAgentsByManifestUnit:
    """Direct unit tests for FrameworkLoader._filter_agents_by_manifest."""

    def test_returns_unchanged_list_without_manifest(self, isolated_project):
        loader = _make_loader()
        deployed = [{"id": "engineer"}, {"id": "qa"}]

        result = loader._filter_agents_by_manifest(deployed, isolated_project)

        assert result == deployed

    def test_filters_by_manifest_ids(self, isolated_project):
        write_agent_manifest(isolated_project, ["engineer"])
        loader = _make_loader()
        deployed = [{"id": "engineer"}, {"id": "qa"}]

        result = loader._filter_agents_by_manifest(deployed, isolated_project)

        assert result == [{"id": "engineer"}]

    def test_manifest_read_error_falls_back_to_full_list(
        self, isolated_project, monkeypatch
    ):
        """If reading the manifest raises for any reason, filtering must
        fail open (return the unfiltered list) rather than propagate."""
        import claude_mpm.services.agents.agent_manifest as agent_manifest_module

        def _boom(_project_path):
            raise RuntimeError("simulated read failure")

        monkeypatch.setattr(agent_manifest_module, "read_agent_manifest", _boom)

        loader = _make_loader()
        deployed = [{"id": "engineer"}, {"id": "qa"}]

        result = loader._filter_agents_by_manifest(deployed, isolated_project)

        assert result == deployed


class TestProjectRootResolution:
    """Regression coverage: the manifest lookup must use the resolved
    project root threaded in by ``_generate_agent_capabilities_section``,
    not an independently-derived ``Path.cwd()``, so the two can't silently
    disagree about which project they're looking at."""

    def test_manifest_and_agents_found_from_a_subdirectory(self, tmp_path, monkeypatch):
        """cwd inside a nested subdirectory of the project must still
        resolve to the real project root (via a ``.git`` marker), so both
        the deployed-agent glob and the manifest lookup find the right
        files -- even though a bare ``Path.cwd()`` would look in
        ``nested_cwd/.claude/agents`` (nonexistent) instead."""
        project_dir = tmp_path / "project"
        fake_home = tmp_path / "fake_home"
        nested_cwd = project_dir / "subdir" / "nested"
        project_dir.mkdir()
        fake_home.mkdir()
        nested_cwd.mkdir(parents=True)
        (project_dir / ".git").mkdir()  # project-root marker for find_project_root

        agents_dir = project_dir / ".claude" / "agents"
        _write_agent_md(agents_dir, "engineer")
        _write_agent_md(agents_dir, "python-engineer")
        write_agent_manifest(project_dir, ["engineer"])

        monkeypatch.chdir(nested_cwd)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        monkeypatch.delenv("CLAUDE_MPM_USER_PWD", raising=False)

        capabilities = _make_loader()._generate_agent_capabilities_section()

        assert "`engineer`" in capabilities
        assert "`python-engineer`" not in capabilities

    def test_filter_uses_passed_project_root_not_cwd(self, tmp_path, monkeypatch):
        """_filter_agents_by_manifest must read the manifest from the
        explicitly-passed project_root, not from Path.cwd()."""
        real_project = tmp_path / "real_project"
        elsewhere_cwd = tmp_path / "elsewhere"
        real_project.mkdir()
        elsewhere_cwd.mkdir()

        write_agent_manifest(real_project, ["engineer"])

        # cwd points somewhere else entirely -- a manifest lookup that
        # incorrectly used Path.cwd() would find no manifest here and fail
        # open (return the unfiltered list) instead of filtering.
        monkeypatch.chdir(elsewhere_cwd)
        monkeypatch.delenv("CLAUDE_MPM_USER_PWD", raising=False)

        loader = _make_loader()
        deployed = [{"id": "engineer"}, {"id": "qa"}]

        result = loader._filter_agents_by_manifest(deployed, real_project)

        assert result == [{"id": "engineer"}]


class TestAgentManifestReadWrite:
    """Unit tests for the agent_manifest module in isolation (no FrameworkLoader)."""

    def test_read_returns_none_when_absent(self, tmp_path):
        assert read_agent_manifest(tmp_path) is None

    def test_write_then_read_round_trip_dedupes_and_sorts(self, tmp_path):
        write_agent_manifest(tmp_path, ["qa", "engineer", "engineer"])

        agent_ids = read_agent_manifest(tmp_path)

        assert agent_ids == ["engineer", "qa"]

    def test_write_creates_manifest_file_at_expected_path(self, tmp_path):
        write_agent_manifest(tmp_path, ["engineer"])

        expected = tmp_path / ".claude-mpm" / "agent_manifest.json"
        assert expected.exists()

        data = json.loads(expected.read_text(encoding="utf-8"))
        assert data["agent_ids"] == ["engineer"]
        assert "generated_at" in data
        assert "schema_version" in data

    def test_write_persists_toolchain_summary(self, tmp_path):
        write_agent_manifest(
            tmp_path,
            ["python-engineer"],
            toolchain_summary={"primary_language": "python"},
        )

        data = json.loads(get_manifest_path(tmp_path).read_text(encoding="utf-8"))
        assert data["toolchain_summary"] == {"primary_language": "python"}

    def test_read_returns_none_on_malformed_json(self, tmp_path):
        manifest_dir = tmp_path / ".claude-mpm"
        manifest_dir.mkdir()
        (manifest_dir / "agent_manifest.json").write_text(
            "{not valid json", encoding="utf-8"
        )

        assert read_agent_manifest(tmp_path) is None

    def test_read_returns_none_when_agent_ids_key_missing(self, tmp_path):
        manifest_dir = tmp_path / ".claude-mpm"
        manifest_dir.mkdir()
        (manifest_dir / "agent_manifest.json").write_text(
            json.dumps({"schema_version": 1}), encoding="utf-8"
        )

        assert read_agent_manifest(tmp_path) is None

    def test_read_returns_none_when_agent_ids_not_a_list(self, tmp_path):
        manifest_dir = tmp_path / ".claude-mpm"
        manifest_dir.mkdir()
        (manifest_dir / "agent_manifest.json").write_text(
            json.dumps({"agent_ids": "engineer"}), encoding="utf-8"
        )

        assert read_agent_manifest(tmp_path) is None

    def test_read_ignores_non_string_entries(self, tmp_path):
        manifest_dir = tmp_path / ".claude-mpm"
        manifest_dir.mkdir()
        (manifest_dir / "agent_manifest.json").write_text(
            json.dumps({"agent_ids": ["engineer", 42, None, "qa"]}),
            encoding="utf-8",
        )

        assert read_agent_manifest(tmp_path) == ["engineer", "qa"]
