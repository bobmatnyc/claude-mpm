"""Tests for additive block override semantics in FileLoader.

Verifies that load_workflow_file, load_memory_file, and load_agent_delegation_file
concatenate user + project overrides (additive) and fall back to the system default
only when neither override exists.
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.core.framework.loaders.file_loader import FileLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_loader() -> FileLoader:
    return FileLoader()


# ---------------------------------------------------------------------------
# _load_tier_file_additive unit tests
# ---------------------------------------------------------------------------


class TestLoadTierFileAdditive:
    """Unit tests for _load_tier_file_additive."""

    def _run(
        self,
        loader: FileLoader,
        filename: str,
        project_dir: Path,
        framework_path: Path,
        include_system: bool = True,
    ) -> tuple[str | None, str | None]:
        return loader._load_tier_file_additive(
            filename, project_dir, framework_path, include_system=include_system
        )

    def test_system_fallback_only(self, tmp_path):
        """When no user/project overrides exist, return system default."""
        system_agents = tmp_path / "src" / "claude_mpm" / "agents"
        system_agents.mkdir(parents=True)
        (system_agents / "WORKFLOW.md").write_text("# System Workflow")

        framework_path = tmp_path
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = _make_loader()
        content, level = self._run(loader, "WORKFLOW.md", project_dir, framework_path)

        assert content == "# System Workflow"
        assert level == "system"

    def test_project_only_replaces_system(self, tmp_path, monkeypatch):
        """Project override alone replaces the system default."""
        # System
        system_agents = tmp_path / "src" / "claude_mpm" / "agents"
        system_agents.mkdir(parents=True)
        (system_agents / "WORKFLOW.md").write_text("# System Workflow")

        # Project override
        project_dir = tmp_path / "project"
        project_claude_mpm = project_dir / ".claude-mpm"
        project_claude_mpm.mkdir(parents=True)
        (project_claude_mpm / "WORKFLOW.md").write_text("# Project Workflow")

        # No user home override: point home to an empty dir
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        loader = _make_loader()
        content, level = self._run(loader, "WORKFLOW.md", project_dir, tmp_path)

        assert content == "# Project Workflow"
        assert level == "project"

    def test_user_only_replaces_system(self, tmp_path, monkeypatch):
        """User override alone replaces the system default."""
        # System
        system_agents = tmp_path / "src" / "claude_mpm" / "agents"
        system_agents.mkdir(parents=True)
        (system_agents / "WORKFLOW.md").write_text("# System Workflow")

        # User override
        fake_home = tmp_path / "home"
        user_claude_mpm = fake_home / ".claude-mpm"
        user_claude_mpm.mkdir(parents=True)
        (user_claude_mpm / "WORKFLOW.md").write_text("# User Workflow")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        # No project override
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = _make_loader()
        content, level = self._run(loader, "WORKFLOW.md", project_dir, tmp_path)

        assert content == "# User Workflow"
        assert level == "user"

    def test_user_and_project_concatenated(self, tmp_path, monkeypatch):
        """Both user and project overrides are concatenated; system is NOT included."""
        # System (should not appear in output)
        system_agents = tmp_path / "src" / "claude_mpm" / "agents"
        system_agents.mkdir(parents=True)
        (system_agents / "WORKFLOW.md").write_text("# System Workflow")

        # User override
        fake_home = tmp_path / "home"
        user_claude_mpm = fake_home / ".claude-mpm"
        user_claude_mpm.mkdir(parents=True)
        (user_claude_mpm / "WORKFLOW.md").write_text("# User Workflow")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        # Project override
        project_dir = tmp_path / "project"
        project_claude_mpm = project_dir / ".claude-mpm"
        project_claude_mpm.mkdir(parents=True)
        (project_claude_mpm / "WORKFLOW.md").write_text("# Project Workflow")

        loader = _make_loader()
        content, level = self._run(loader, "WORKFLOW.md", project_dir, tmp_path)

        assert content is not None
        assert "# User Workflow" in content
        assert "# Project Workflow" in content
        assert "# System Workflow" not in content
        # level label: project takes precedence when both exist
        assert level == "project"

    def test_user_and_project_order(self, tmp_path, monkeypatch):
        """User content appears before project content in the concatenated output."""
        fake_home = tmp_path / "home"
        user_claude_mpm = fake_home / ".claude-mpm"
        user_claude_mpm.mkdir(parents=True)
        (user_claude_mpm / "MEMORY.md").write_text("USER_PART")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        project_dir = tmp_path / "project"
        project_claude_mpm = project_dir / ".claude-mpm"
        project_claude_mpm.mkdir(parents=True)
        (project_claude_mpm / "MEMORY.md").write_text("PROJECT_PART")

        loader = _make_loader()
        content, _ = self._run(loader, "MEMORY.md", project_dir, tmp_path)

        assert content is not None
        assert content.index("USER_PART") < content.index("PROJECT_PART")

    def test_no_sources_returns_none(self, tmp_path, monkeypatch):
        """When no sources exist at all, return (None, None)."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = _make_loader()
        content, level = self._run(
            loader, "MEMORY.md", project_dir, tmp_path, include_system=True
        )

        assert content is None
        assert level is None

    def test_include_system_false_skips_system(self, tmp_path, monkeypatch):
        """When include_system=False, system path is never consulted."""
        system_agents = tmp_path / "src" / "claude_mpm" / "agents"
        system_agents.mkdir(parents=True)
        (system_agents / "MEMORY.md").write_text("# System Memory")

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loader = _make_loader()
        content, level = self._run(
            loader, "MEMORY.md", project_dir, tmp_path, include_system=False
        )

        assert content is None
        assert level is None


# ---------------------------------------------------------------------------
# Public API tests: load_workflow_file, load_memory_file,
# load_agent_delegation_file
# ---------------------------------------------------------------------------


class TestPublicLoadersAdditive:
    """Verify that the public loaders delegate to _load_tier_file_additive."""

    def _framework_path(self, tmp_path: Path) -> Path:
        """Create a fake framework path with system agent files."""
        system_agents = tmp_path / "src" / "claude_mpm" / "agents"
        system_agents.mkdir(parents=True)
        (system_agents / "WORKFLOW.md").write_text("# System WORKFLOW")
        (system_agents / "MEMORY.md").write_text("# System MEMORY")
        (system_agents / "AGENT_DELEGATION.md").write_text("# System AGENT_DELEGATION")
        return tmp_path

    def _user_overrides(self, tmp_path: Path, monkeypatch) -> Path:
        fake_home = tmp_path / "home"
        user_dir = fake_home / ".claude-mpm"
        user_dir.mkdir(parents=True)
        (user_dir / "WORKFLOW.md").write_text("User WORKFLOW")
        (user_dir / "MEMORY.md").write_text("User MEMORY")
        (user_dir / "AGENT_DELEGATION.md").write_text("User AGENT_DELEGATION")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        return fake_home

    def _project_overrides(self, project_dir: Path) -> None:
        proj_dir = project_dir / ".claude-mpm"
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "WORKFLOW.md").write_text("Project WORKFLOW")
        (proj_dir / "MEMORY.md").write_text("Project MEMORY")
        (proj_dir / "AGENT_DELEGATION.md").write_text("Project AGENT_DELEGATION")

    # -- workflow_file -------------------------------------------------------

    def test_workflow_system_fallback(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        content, level = _make_loader().load_workflow_file(project_dir, fp)
        assert content == "# System WORKFLOW"
        assert level == "system"

    def test_workflow_additive_user_and_project(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._user_overrides(tmp_path, monkeypatch)
        self._project_overrides(project_dir)

        content, level = _make_loader().load_workflow_file(project_dir, fp)
        assert content is not None
        assert "User WORKFLOW" in content
        assert "Project WORKFLOW" in content
        assert "System WORKFLOW" not in content
        assert level == "project"

    # -- memory_file ---------------------------------------------------------

    def test_memory_system_fallback(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        content, level = _make_loader().load_memory_file(project_dir, fp)
        assert content == "# System MEMORY"
        assert level == "system"

    def test_memory_additive_user_and_project(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._user_overrides(tmp_path, monkeypatch)
        self._project_overrides(project_dir)

        content, level = _make_loader().load_memory_file(project_dir, fp)
        assert content is not None
        assert "User MEMORY" in content
        assert "Project MEMORY" in content
        assert "System MEMORY" not in content
        assert level == "project"

    # -- agent_delegation_file -----------------------------------------------

    def test_agent_delegation_system_fallback(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        content, level = _make_loader().load_agent_delegation_file(project_dir, fp)
        assert content == "# System AGENT_DELEGATION"
        assert level == "system"

    def test_agent_delegation_additive_user_and_project(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._user_overrides(tmp_path, monkeypatch)
        self._project_overrides(project_dir)

        content, level = _make_loader().load_agent_delegation_file(project_dir, fp)
        assert content is not None
        assert "User AGENT_DELEGATION" in content
        assert "Project AGENT_DELEGATION" in content
        assert "System AGENT_DELEGATION" not in content
        assert level == "project"

    def test_agent_delegation_user_only(self, tmp_path, monkeypatch):
        fp = self._framework_path(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._user_overrides(tmp_path, monkeypatch)
        # no project override

        content, level = _make_loader().load_agent_delegation_file(project_dir, fp)
        assert content == "User AGENT_DELEGATION"
        assert level == "user"
