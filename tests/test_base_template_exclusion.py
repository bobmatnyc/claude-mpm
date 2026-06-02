"""Tests for BASE composition template exclusion from agent deployment and discovery.

Covers:
- ``is_base_template`` predicate correctness (Part 1a)
- ``AgentDiscoveryService.get_filtered_templates`` excludes BASE templates (Part 1b)
- ``AgentDiscoveryService.list_available_agents`` excludes BASE templates (Part 1c)
- Migration: removes BASE files from a tmp .claude/agents/, leaves real agents (Part 2)
- Migration: idempotent on a clean directory (Part 2 idempotency)
- Composition: ``_discover_base_agent_templates`` still finds BASE templates (Part 3)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.utils.agent_filters import is_base_template

# ---------------------------------------------------------------------------
# Part 1a: is_base_template predicate
# ---------------------------------------------------------------------------


class TestIsBaseTemplate:
    """Verify the canonical BASE-template predicate."""

    @pytest.mark.parametrize(
        "filename",
        [
            "BASE-AGENT.md",
            "BASE_AGENT.md",
            "BASE-ENGINEER.md",
            "BASE_ENGINEER.md",
            "BASE-QA.md",
            "BASE_QA.md",
            "BASE-OPS.md",
            "BASE_OPS.md",
            "BASE-RESEARCH.md",
            "BASE_RESEARCH.md",
            "BASE-PM.md",
            "BASE_PM.md",
            "base-agent.md",
            "base_agent.md",
            "base-engineer.md",
            "Base-Ops.md",
            # Path forms
            "/some/path/BASE-ENGINEER.md",
            "~/.claude/agents/BASE-QA.md",
            # No extension variants
            "BASE-AGENT",
            "BASE_OPS",
        ],
    )
    def test_base_template_matches(self, filename: str) -> None:
        """All BASE-*/BASE_* filenames should match is_base_template."""
        assert is_base_template(filename) is True, f"{filename!r} should be a template"

    @pytest.mark.parametrize(
        "filename",
        [
            "engineer.md",
            "python-engineer.md",
            "code-critic.md",
            "qa.md",
            "ops.md",
            "research.md",
            "pm.md",
            "security.md",
            "documentation.md",
            "api-qa.md",
            "gcp-ops.md",
            "refactoring-engineer.md",
            "README.md",
            "CHANGELOG.md",
            # Names that contain BASE but don't start with it
            "my-base-agent.md",
            "not-base.md",
            "",
        ],
    )
    def test_real_agents_not_matched(self, filename: str) -> None:
        """Real agent names must NOT match is_base_template."""
        assert is_base_template(filename) is False, (
            f"{filename!r} should NOT be a template"
        )


# ---------------------------------------------------------------------------
# Part 1b: AgentDiscoveryService.get_filtered_templates excludes BASE templates
# ---------------------------------------------------------------------------


class TestGetFilteredTemplatesExcludesBase:
    """AgentDiscoveryService must not include BASE templates in deployment list."""

    def _make_mock_md_file(self, tmp_path: Path, name: str, valid: bool = True) -> Path:
        """Write a minimal .md file (with or without valid frontmatter)."""
        f = tmp_path / name
        if valid:
            f.write_text(
                "---\nname: test\nagent_id: test\ndescription: Test agent.\n---\n# Content\n",
                encoding="utf-8",
            )
        else:
            f.write_text("# No frontmatter here\n", encoding="utf-8")
        return f

    def test_base_templates_excluded_from_filtered_list(self, tmp_path: Path) -> None:
        """BASE-*.md files must be absent from get_filtered_templates output."""
        from claude_mpm.services.agents.deployment.agent_discovery_service import (
            AgentDiscoveryService,
        )

        # Populate a fake templates dir
        self._make_mock_md_file(tmp_path, "engineer.md", valid=True)
        self._make_mock_md_file(tmp_path, "BASE-ENGINEER.md", valid=False)
        self._make_mock_md_file(tmp_path, "BASE_QA.md", valid=False)
        self._make_mock_md_file(tmp_path, "BASE-AGENT.md", valid=False)

        svc = AgentDiscoveryService(tmp_path)

        # Patch _validate_template_file so only "engineer.md" passes validation.
        def _fake_validate(tf: Path) -> bool:
            return tf.name == "engineer.md"

        with patch.object(svc, "_validate_template_file", side_effect=_fake_validate):
            result = svc.get_filtered_templates(excluded_agents=[], config=None)

        names = [p.name for p in result]
        assert "engineer.md" in names
        assert "BASE-ENGINEER.md" not in names
        assert "BASE_QA.md" not in names
        assert "BASE-AGENT.md" not in names

    def test_base_templates_excluded_from_available_agents(
        self, tmp_path: Path
    ) -> None:
        """BASE-*.md files must be absent from list_available_agents output."""
        from claude_mpm.services.agents.deployment.agent_discovery_service import (
            AgentDiscoveryService,
        )

        # Minimal valid frontmatter for a real agent
        (tmp_path / "engineer.md").write_text(
            "---\nname: engineer\nagent_id: engineer\ndescription: Engineer.\nversion: 1.0.0\n---\n# Engineer\n",
            encoding="utf-8",
        )
        # BASE templates — intentionally missing 'description' / 'name' fields
        (tmp_path / "BASE-ENGINEER.md").write_text(
            "# BASE ENGINEER\n\nNo frontmatter.\n", encoding="utf-8"
        )
        (tmp_path / "BASE_QA.md").write_text(
            "# BASE QA\n\nNo frontmatter.\n", encoding="utf-8"
        )

        svc = AgentDiscoveryService(tmp_path)
        # Suppress git-cache discovery so we only test the local branch.
        with patch.object(svc, "discover_git_cached_agents", return_value=[]):
            agents = svc.list_available_agents(log_discovery=False)

        names = [a.get("name", "") for a in agents]
        assert any("engineer" in n.lower() for n in names), (
            "engineer agent should be listed"
        )
        for a in agents:
            assert not is_base_template(a.get("file", "")), (
                f"BASE template appeared in agent list: {a}"
            )


# ---------------------------------------------------------------------------
# Part 2: Migration removes BASE files and leaves real agents intact
# ---------------------------------------------------------------------------


class TestMigrateRemoveDeployedBaseTemplates:
    """Migration must remove BASE files, leave real agents, return True always."""

    def test_removes_base_files_from_agents_dir(self, tmp_path: Path) -> None:
        """Migration must delete BASE-*.md files from the agents dir."""
        from claude_mpm.migrations.migrate_remove_deployed_base_templates import (
            _remove_base_templates_from_dir,
        )

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        base_files = ["BASE-AGENT.md", "BASE_ENGINEER.md", "BASE-QA.md", "BASE_OPS.md"]
        real_files = ["engineer.md", "qa.md", "python-engineer.md"]

        for name in base_files + real_files:
            (agents_dir / name).write_text("# dummy\n", encoding="utf-8")

        removed = _remove_base_templates_from_dir(agents_dir)

        assert set(removed) == set(base_files), (
            f"Expected all BASE files removed; got {removed}"
        )
        for name in real_files:
            assert (agents_dir / name).exists(), (
                f"Real agent {name} was wrongly removed"
            )
        for name in base_files:
            assert not (agents_dir / name).exists(), f"BASE file {name} should be gone"

    def test_migration_idempotent_on_clean_dir(self, tmp_path: Path) -> None:
        """Migration must return True even when no BASE files are present."""
        from claude_mpm.migrations.migrate_remove_deployed_base_templates import (
            run_migration,
        )

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.md").write_text("# Engineer\n", encoding="utf-8")

        # Patch scan dirs so we only touch our tmp dir.
        with (
            patch(
                "claude_mpm.migrations.migrate_remove_deployed_base_templates.Path.home"
            ) as mock_home,
            patch(
                "claude_mpm.migrations.migrate_remove_deployed_base_templates.Path.cwd"
            ) as mock_cwd,
        ):
            mock_home.return_value = tmp_path
            mock_cwd.return_value = tmp_path
            result = run_migration()

        assert result is True
        # Real agent untouched
        assert (agents_dir / "engineer.md").exists()

    def test_run_migration_returns_true_when_files_removed(
        self, tmp_path: Path
    ) -> None:
        """Migration must return True even when BASE files are found and removed."""
        from claude_mpm.migrations.migrate_remove_deployed_base_templates import (
            run_migration,
        )

        user_agents_dir = tmp_path / "user" / ".claude" / "agents"
        user_agents_dir.mkdir(parents=True)
        (user_agents_dir / "BASE-ENGINEER.md").write_text(
            "# template\n", encoding="utf-8"
        )
        (user_agents_dir / "engineer.md").write_text("# real\n", encoding="utf-8")

        with (
            patch(
                "claude_mpm.migrations.migrate_remove_deployed_base_templates.Path.home"
            ) as mock_home,
            patch(
                "claude_mpm.migrations.migrate_remove_deployed_base_templates.Path.cwd"
            ) as mock_cwd,
        ):
            mock_home.return_value = tmp_path / "user"
            mock_cwd.return_value = tmp_path  # project dir has no .claude/agents
            result = run_migration()

        assert result is True
        assert not (user_agents_dir / "BASE-ENGINEER.md").exists()
        assert (user_agents_dir / "engineer.md").exists()

    def test_migration_handles_missing_directory(self, tmp_path: Path) -> None:
        """Migration must not raise when agents dirs do not exist."""
        from claude_mpm.migrations.migrate_remove_deployed_base_templates import (
            run_migration,
        )

        with (
            patch(
                "claude_mpm.migrations.migrate_remove_deployed_base_templates.Path.home"
            ) as mock_home,
            patch(
                "claude_mpm.migrations.migrate_remove_deployed_base_templates.Path.cwd"
            ) as mock_cwd,
        ):
            mock_home.return_value = tmp_path / "nonexistent_home"
            mock_cwd.return_value = tmp_path / "nonexistent_project"
            result = run_migration()

        assert result is True


# ---------------------------------------------------------------------------
# Part 3: Composition — _discover_base_agent_templates still works
# ---------------------------------------------------------------------------


class TestDiscoverBaseAgentTemplatesNotBroken:
    """_discover_base_agent_templates must still find BASE files for composition."""

    def test_composition_discovery_finds_base_templates(self, tmp_path: Path) -> None:
        """Composition walk must locate BASE-AGENT.md for assembly — not blocked."""
        from claude_mpm.services.agents.deployment.agent_template_builder import (
            AgentTemplateBuilder,
        )

        # Structure: repo root with BASE-AGENT.md, subdir with an agent file
        repo_root = tmp_path
        (repo_root / "BASE-AGENT.md").write_text(
            "# Base Agent\nShared instructions.\n", encoding="utf-8"
        )

        subdir = repo_root / "engineers"
        subdir.mkdir()
        agent_file = subdir / "python-engineer.md"
        agent_file.write_text(
            "# Python Engineer\nSpecific instructions.\n", encoding="utf-8"
        )

        builder = AgentTemplateBuilder()
        # Prevent walking above tmp_path by using a file inside it
        found = builder._discover_base_agent_templates(agent_file)

        assert len(found) >= 1, "Should discover at least the root BASE-AGENT.md"
        found_names = {f.name for f in found}
        assert "BASE-AGENT.md" in found_names, (
            f"BASE-AGENT.md not found; got: {found_names}"
        )

    def test_composition_discovery_finds_underscore_variant(
        self, tmp_path: Path
    ) -> None:
        """Composition walk must also find BASE_AGENT.md (underscore form)."""
        from claude_mpm.services.agents.deployment.agent_template_builder import (
            AgentTemplateBuilder,
        )

        repo_root = tmp_path
        (repo_root / "BASE_AGENT.md").write_text(
            "# Base Agent\nShared.\n", encoding="utf-8"
        )

        subdir = repo_root / "ops"
        subdir.mkdir()
        agent_file = subdir / "gcp-ops.md"
        agent_file.write_text("# GCP Ops\nOps specific.\n", encoding="utf-8")

        builder = AgentTemplateBuilder()
        found = builder._discover_base_agent_templates(agent_file)

        assert len(found) >= 1
        found_names = {f.name for f in found}
        assert "BASE_AGENT.md" in found_names
