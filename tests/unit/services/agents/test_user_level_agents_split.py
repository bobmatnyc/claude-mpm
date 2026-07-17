"""Tests verifying project-local agent routing after Fix A for issue #924.

User-level agent routing has been removed: ALL agents (CORE and project-specific)
now deploy to ``<project>/.claude/agents/`` instead of ``~/.claude/agents/``.  The
``USER_LEVEL_AGENTS`` frozenset is retained (migration/cleanup code still imports
it) but no longer influences deployment targets.

Historical context: Issue #412 originally split core agents into user-level
storage; #924 reverted that split.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestUserLevelAgentsConstant:
    """Verify the USER_LEVEL_AGENTS frozenset is still defined (retained for migrations)."""

    def test_user_level_agents_is_frozenset(self):
        """USER_LEVEL_AGENTS must be a frozenset for immutability."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        assert isinstance(USER_LEVEL_AGENTS, frozenset)

    def test_user_level_agents_contains_required_members(self):
        """All required CORE agents must be present in USER_LEVEL_AGENTS."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        required = {
            "pm",
            "engineer",
            "python-engineer",
            "typescript-engineer",
            "javascript-engineer",
            "golang-engineer",
            "rust-engineer",
            "java-engineer",
            "ruby-engineer",
            "php-engineer",
            "dart-engineer",
            "nextjs-engineer",
            "react-engineer",
            "svelte-engineer",
            "tauri-engineer",
            "phoenix-engineer",
            "research",
            "qa",
            "security",
            "documentation",
            "ops",
            "local-ops",
            "vercel-ops",
            "gcp-ops",
            "web-qa",
            "api-qa",
            "code-analysis",
            "version-control",
            "refactoring-engineer",
            "data-engineer",
            "prompt-engineer",
            "memory-manager",
            "ticketing",
        }
        missing = required - USER_LEVEL_AGENTS
        assert not missing, f"Missing required agents in USER_LEVEL_AGENTS: {missing}"

    def test_user_level_agents_not_empty(self):
        """USER_LEVEL_AGENTS must have at least one member."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        assert len(USER_LEVEL_AGENTS) > 0

    def test_user_level_agents_all_lowercase_kebab(self):
        """All agent names in USER_LEVEL_AGENTS must be lowercase kebab-case."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        for name in USER_LEVEL_AGENTS:
            assert name == name.lower(), f"Agent name not lowercase: {name!r}"
            assert "_" not in name, (
                f"Agent name uses underscores instead of hyphens: {name!r}"
            )


class TestDeployAgentsRouting:
    """Verify deploy_agents() routes ALL agents to project-local .claude/agents/."""

    def _make_template_file(self, tmp_dir: Path, agent_name: str) -> Path:
        """Create a minimal agent template .md file."""
        template = tmp_dir / f"{agent_name}.md"
        template.write_text(
            f"---\nname: {agent_name}\nversion: 1.0.0\n---\n\n# {agent_name}\n"
        )
        return template

    @pytest.fixture()
    def temp_dirs(self):
        """Create temporary directories for user home and project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            fake_home = base / "home"
            fake_project = base / "project"
            fake_home.mkdir()
            fake_project.mkdir()
            yield fake_home, fake_project

    def test_core_agent_deployed_to_project_agents(self, temp_dirs):
        """A CORE (USER_LEVEL_AGENTS) agent must now deploy to project-local dir."""
        from claude_mpm.services.agents.deployment.user_level_routing import (
            skip_project_level_user_agent,
        )

        fake_home, fake_project = temp_dirs
        project_agents_dir = fake_project / ".claude" / "agents"

        core_agent = "engineer"

        # The routing guard is now a no-op, so CORE agents are never skipped for
        # a project-level target and therefore deploy to project-local scope.
        with patch("pathlib.Path.home", return_value=fake_home):
            assert (
                skip_project_level_user_agent(core_agent, project_agents_dir) is False
            )

    def test_non_user_level_agent_deployed_to_project_agents(self, temp_dirs):
        """A project-specific agent still deploys to project-level .claude/agents/."""
        from claude_mpm.services.agents.deployment.user_level_routing import (
            skip_project_level_user_agent,
        )

        fake_home, fake_project = temp_dirs
        project_agents_dir = fake_project / ".claude" / "agents"

        project_only_agent = "my-custom-project-agent-xyz"

        with patch("pathlib.Path.home", return_value=fake_home):
            assert (
                skip_project_level_user_agent(project_only_agent, project_agents_dir)
                is False
            )

    def test_all_user_level_agents_route_to_project(self, temp_dirs):
        """Every member of USER_LEVEL_AGENTS must route to project-local scope."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )
        from claude_mpm.services.agents.deployment.user_level_routing import (
            skip_project_level_user_agent,
        )

        fake_home, fake_project = temp_dirs
        project_agents_dir = fake_project / ".claude" / "agents"

        skipped = []
        with patch("pathlib.Path.home", return_value=fake_home):
            for agent_name in USER_LEVEL_AGENTS:
                if skip_project_level_user_agent(agent_name, project_agents_dir):
                    skipped.append(agent_name)

        assert not skipped, (
            f"These agents were wrongly skipped for project-level deploy: {skipped}"
        )


class TestMigrationCoreAgentsToUserLevelIsNoOp:
    """Verify the 6.2.0 migration is now a no-op (Fix A for #924)."""

    @pytest.fixture()
    def temp_dirs(self):
        """Set up fake home and project directories with agent files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            fake_home = base / "home"
            fake_project = base / "project"
            (fake_home / ".claude" / "agents").mkdir(parents=True)
            (fake_project / ".claude" / "agents").mkdir(parents=True)
            yield fake_home, fake_project

    def _write_agent(self, directory: Path, agent_name: str) -> Path:
        """Write a minimal agent .md file and return its path."""
        path = directory / f"{agent_name}.md"
        path.write_text(
            f"---\nname: {agent_name}\nversion: 1.0.0\n---\n\n# {agent_name}\n"
        )
        return path

    def test_run_migration_returns_true(self):
        """run_migration() is a no-op that always succeeds."""
        from claude_mpm.migrations.migrate_core_agents_to_user_level import (
            run_migration,
        )

        assert run_migration() is True

    def test_run_migration_does_not_touch_project_files(self, temp_dirs):
        """The no-op migration must not remove any project-level agent file."""
        from claude_mpm.migrations.migrate_core_agents_to_user_level import (
            run_migration,
        )
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        agent = next(iter(sorted(USER_LEVEL_AGENTS)))

        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir = fake_project / ".claude" / "agents"
        self._write_agent(user_agents_dir, agent)
        project_file = self._write_agent(project_agents_dir, agent)

        with patch("pathlib.Path.home", return_value=fake_home):
            success = run_migration()

        assert success is True
        assert project_file.exists(), (
            "No-op migration must not remove the project-level agent file"
        )


class TestMigrationRegistry:
    """Verify 6.2.0 migration is still registered (now a no-op)."""

    def test_migration_registered(self):
        """6.2.0_core_agents_to_user_level must be in the migration registry."""
        from claude_mpm.migrations.registry import get_all_migrations

        migration_ids = {m.id for m in get_all_migrations()}
        assert "6.2.0_core_agents_to_user_level" in migration_ids

    def test_migration_version_is_6_2_0(self):
        """The 6.2.0 agent migration must target version 6.2.0."""
        from claude_mpm.migrations.registry import get_all_migrations

        for m in get_all_migrations():
            if m.id == "6.2.0_core_agents_to_user_level":
                assert m.version == "6.2.0"
                return
        pytest.fail("Migration 6.2.0_core_agents_to_user_level not found")

    def test_migration_has_callable_run(self):
        """The 6.2.0 migration run field must be callable."""
        from claude_mpm.migrations.registry import get_all_migrations

        for m in get_all_migrations():
            if m.id == "6.2.0_core_agents_to_user_level":
                assert callable(m.run)
                return
        pytest.fail("Migration 6.2.0_core_agents_to_user_level not found")
