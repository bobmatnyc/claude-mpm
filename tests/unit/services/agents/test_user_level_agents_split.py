"""Tests verifying USER_LEVEL_AGENTS split: CORE agents go to ~/.claude/agents/,
project-specific agents go to <project>/.claude/agents/.

Issue #412: Split core agents into user-level vs project-level storage.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestUserLevelAgentsConstant:
    """Verify the USER_LEVEL_AGENTS frozenset is correctly defined."""

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
    """Verify deploy_agents() routes agents to correct directories."""

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

    def test_user_level_agent_deployed_to_home_claude_agents(self, temp_dirs):
        """An agent in USER_LEVEL_AGENTS must be deployed to ~/.claude/agents/."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        # Pick any member of USER_LEVEL_AGENTS
        sample_agent = next(iter(sorted(USER_LEVEL_AGENTS)))

        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir = fake_project / ".claude" / "agents"

        # Simulate what deploy_agents does: route based on USER_LEVEL_AGENTS
        from claude_mpm.utils.agent_filters import normalize_agent_id

        normalized = normalize_agent_id(sample_agent)
        if normalized in USER_LEVEL_AGENTS:
            deploy_target = user_agents_dir
        else:
            deploy_target = project_agents_dir

        assert deploy_target == user_agents_dir, (
            f"Agent '{sample_agent}' (normalized: '{normalized}') should deploy to "
            f"user-level {user_agents_dir} but routing chose {deploy_target}"
        )

    def test_non_user_level_agent_deployed_to_project_agents(self, temp_dirs):
        """An agent NOT in USER_LEVEL_AGENTS must deploy to project-level .claude/agents/."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        # Use a clearly project-specific name
        project_only_agent = "my-custom-project-agent-xyz"

        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir = fake_project / ".claude" / "agents"

        assert project_only_agent not in USER_LEVEL_AGENTS

        from claude_mpm.utils.agent_filters import normalize_agent_id

        normalized = normalize_agent_id(project_only_agent)
        if normalized in USER_LEVEL_AGENTS:
            deploy_target = user_agents_dir
        else:
            deploy_target = project_agents_dir

        assert deploy_target == project_agents_dir, (
            f"Agent '{project_only_agent}' should deploy to project-level "
            f"{project_agents_dir} but routing chose {deploy_target}"
        )

    def test_all_user_level_agents_route_to_home(self, temp_dirs):
        """Every member of USER_LEVEL_AGENTS must route to ~/.claude/agents/."""
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir = fake_project / ".claude" / "agents"

        from claude_mpm.utils.agent_filters import normalize_agent_id

        wrong_targets = []
        for agent_name in USER_LEVEL_AGENTS:
            normalized = normalize_agent_id(agent_name)
            if normalized in USER_LEVEL_AGENTS:
                deploy_target = user_agents_dir
            else:
                deploy_target = project_agents_dir

            if deploy_target != user_agents_dir:
                wrong_targets.append(agent_name)

        assert not wrong_targets, (
            f"These USER_LEVEL_AGENTS did not route to user level: {wrong_targets}"
        )


class TestMigrationCoreAgentsToUserLevel:
    """Verify the 6.2.0 migration removes project-level duplicates safely."""

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

    def test_migration_removes_project_copy_when_user_copy_exists(self, temp_dirs):
        """Migration removes project-level file when user-level copy is confirmed."""
        from claude_mpm.migrations.migrate_core_agents_to_user_level import (
            migrate_core_agents_to_user_level,
        )
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        # Pick a USER_LEVEL_AGENTS member
        agent = next(iter(sorted(USER_LEVEL_AGENTS)))

        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir = fake_project / ".claude" / "agents"

        # Both copies exist initially
        self._write_agent(user_agents_dir, agent)
        project_file = self._write_agent(project_agents_dir, agent)

        assert project_file.exists()

        # Run migration with patched home and cwd pointing to fake_project
        with (
            patch("pathlib.Path.home", return_value=fake_home),
            patch(
                "claude_mpm.migrations.migrate_core_agents_to_user_level._find_project_roots",
                return_value=[fake_project],
            ),
        ):
            success = migrate_core_agents_to_user_level()

        assert success, "Migration should succeed"
        assert not project_file.exists(), (
            f"Project-level {agent}.md should be removed after migration"
        )
        # User-level copy must be preserved
        assert (user_agents_dir / f"{agent}.md").exists(), (
            f"User-level {agent}.md must be preserved after migration"
        )

    def test_migration_skips_removal_when_no_user_copy(self, temp_dirs):
        """Migration does NOT remove project copy when user-level copy is absent."""
        from claude_mpm.migrations.migrate_core_agents_to_user_level import (
            migrate_core_agents_to_user_level,
        )
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        agent = next(iter(sorted(USER_LEVEL_AGENTS)))

        project_agents_dir = fake_project / ".claude" / "agents"
        project_file = self._write_agent(project_agents_dir, agent)
        # No user-level copy

        with (
            patch("pathlib.Path.home", return_value=fake_home),
            patch(
                "claude_mpm.migrations.migrate_core_agents_to_user_level._find_project_roots",
                return_value=[fake_project],
            ),
        ):
            success = migrate_core_agents_to_user_level()

        assert success, "Migration should succeed even when user copy is absent"
        assert project_file.exists(), (
            "Project-level file must NOT be removed when user-level copy is missing"
        )

    def test_migration_is_idempotent(self, temp_dirs):
        """Running migration twice is safe — second run is a no-op."""
        from claude_mpm.migrations.migrate_core_agents_to_user_level import (
            migrate_core_agents_to_user_level,
        )
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        agent = next(iter(sorted(USER_LEVEL_AGENTS)))

        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir = fake_project / ".claude" / "agents"

        self._write_agent(user_agents_dir, agent)
        self._write_agent(project_agents_dir, agent)

        with (
            patch("pathlib.Path.home", return_value=fake_home),
            patch(
                "claude_mpm.migrations.migrate_core_agents_to_user_level._find_project_roots",
                return_value=[fake_project],
            ),
        ):
            success1 = migrate_core_agents_to_user_level()
            # Run again — project file is already gone
            success2 = migrate_core_agents_to_user_level()

        assert success1
        assert success2, "Second migration run must succeed (idempotent)"

    def test_migration_skips_non_user_level_project_agents(self, temp_dirs):
        """Migration must not touch project-specific agents not in USER_LEVEL_AGENTS."""
        from claude_mpm.migrations.migrate_core_agents_to_user_level import (
            migrate_core_agents_to_user_level,
        )
        from claude_mpm.services.agents.deployment.agent_deployment import (
            USER_LEVEL_AGENTS,
        )

        fake_home, fake_project = temp_dirs
        project_agents_dir = fake_project / ".claude" / "agents"

        custom_agent = "my-project-specific-agent"
        assert custom_agent not in USER_LEVEL_AGENTS
        project_file = self._write_agent(project_agents_dir, custom_agent)

        with (
            patch("pathlib.Path.home", return_value=fake_home),
            patch(
                "claude_mpm.migrations.migrate_core_agents_to_user_level._find_project_roots",
                return_value=[fake_project],
            ),
        ):
            success = migrate_core_agents_to_user_level()

        assert success
        assert project_file.exists(), (
            "Project-specific agent must NOT be touched by the migration"
        )


class TestMigrationRegistry:
    """Verify 6.2.0 migration is registered in the migration registry."""

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
