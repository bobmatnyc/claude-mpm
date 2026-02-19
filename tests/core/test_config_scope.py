"""
Tests for ConfigScope enum and path resolver functions
=====================================================

WHY: Tests the ConfigScope abstraction that maps configuration scope
(project vs user) to filesystem paths for agents, skills, and archives.
Critical for auto-configure v2 deployment targeting.

FOCUS: Integration testing over unit testing per research recommendations.
Tests both PROJECT and USER scopes with real path resolution.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.core.config_scope import (
    ConfigScope,
    resolve_agents_dir,
    resolve_archive_dir,
    resolve_config_dir,
    resolve_skills_dir,
)


class TestConfigScopeBackwardCompatibility:
    """ConfigScope(str, Enum) must compare equal to raw strings."""

    def test_project_equals_string(self) -> None:
        assert ConfigScope.PROJECT == "project"

    def test_user_equals_string(self) -> None:
        assert ConfigScope.USER == "user"

    def test_project_value(self) -> None:
        assert ConfigScope.PROJECT.value == "project"

    def test_user_value(self) -> None:
        assert ConfigScope.USER.value == "user"

    def test_string_comparison_in_condition(self) -> None:
        """Simulate existing CLI code that uses raw string comparison."""
        scope = ConfigScope.PROJECT
        assert scope == "project"
        assert scope != "user"


class TestResolveAgentsDir:
    """Tests for resolve_agents_dir()."""

    def test_project_scope(self) -> None:
        project = Path("/project")
        result = resolve_agents_dir(ConfigScope.PROJECT, project)
        assert result == Path("/project/.claude/agents")

    def test_user_scope_ignores_project_path(self) -> None:
        project = Path("/project")
        result = resolve_agents_dir(ConfigScope.USER, project)
        assert result == Path.home() / ".claude" / "agents"

    def test_project_scope_with_nested_path(self) -> None:
        project = Path("/home/user/workspace/my-project")
        result = resolve_agents_dir(ConfigScope.PROJECT, project)
        assert result == Path("/home/user/workspace/my-project/.claude/agents")


class TestResolveSkillsDir:
    """Tests for resolve_skills_dir()."""

    def test_default_returns_project_scope(self) -> None:
        """Default (no args) uses PROJECT scope with cwd."""
        result = resolve_skills_dir()
        assert result == Path.cwd() / ".claude" / "skills"

    def test_project_scope_with_explicit_path(self) -> None:
        result = resolve_skills_dir(ConfigScope.PROJECT, Path("/project"))
        assert result == Path("/project/.claude/skills")

    def test_project_scope_defaults_to_cwd(self) -> None:
        """PROJECT scope without project_path falls back to cwd."""
        result = resolve_skills_dir(ConfigScope.PROJECT)
        assert result == Path.cwd() / ".claude" / "skills"

    def test_user_scope_returns_user_home(self) -> None:
        result = resolve_skills_dir(ConfigScope.USER)
        assert result == Path.home() / ".claude" / "skills"

    def test_user_scope_ignores_project_path(self) -> None:
        """USER scope should always resolve to home, regardless of project_path."""
        result = resolve_skills_dir(ConfigScope.USER, Path("/project"))
        assert result == Path.home() / ".claude" / "skills"


class TestResolveArchiveDir:
    """Tests for resolve_archive_dir()."""

    def test_project_scope(self) -> None:
        project = Path("/project")
        result = resolve_archive_dir(ConfigScope.PROJECT, project)
        assert result == Path("/project/.claude/agents/unused")

    def test_user_scope(self) -> None:
        project = Path("/project")
        result = resolve_archive_dir(ConfigScope.USER, project)
        assert result == Path.home() / ".claude" / "agents" / "unused"

    def test_archive_is_subdirectory_of_agents(self) -> None:
        """Archive dir must be a child of the agents dir for the same scope."""
        project = Path("/project")
        agents = resolve_agents_dir(ConfigScope.PROJECT, project)
        archive = resolve_archive_dir(ConfigScope.PROJECT, project)
        assert str(archive).startswith(str(agents))
        assert archive == agents / "unused"


class TestResolveConfigDir:
    """Tests for resolve_config_dir()."""

    def test_project_scope(self) -> None:
        project = Path("/project")
        result = resolve_config_dir(ConfigScope.PROJECT, project)
        assert result == Path("/project/.claude-mpm")

    def test_user_scope(self) -> None:
        project = Path("/project")
        result = resolve_config_dir(ConfigScope.USER, project)
        assert result == Path.home() / ".claude-mpm"

    def test_user_scope_ignores_project_path(self) -> None:
        """User scope should always resolve to home, regardless of project_path."""
        result_a = resolve_config_dir(ConfigScope.USER, Path("/project-a"))
        result_b = resolve_config_dir(ConfigScope.USER, Path("/project-b"))
        assert result_a == result_b
        assert result_a == Path.home() / ".claude-mpm"


class TestScopeIntegration:
    """Integration tests for cross-scope deployment scenarios."""

    def test_cross_scope_deployment_isolation(self, tmp_path):
        """Test that PROJECT and USER deployments are isolated."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
            mock_home.return_value = tmp_path / "home"

            # Get all PROJECT scope paths
            project_agents = resolve_agents_dir(ConfigScope.PROJECT, project_path)
            project_skills = resolve_skills_dir(ConfigScope.PROJECT, project_path)
            project_archive = resolve_archive_dir(ConfigScope.PROJECT, project_path)

            # Get all USER scope paths
            user_agents = resolve_agents_dir(ConfigScope.USER, project_path)
            user_skills = resolve_skills_dir(ConfigScope.USER, project_path)
            user_archive = resolve_archive_dir(ConfigScope.USER, project_path)

            # Ensure complete isolation
            project_paths = {project_agents, project_skills, project_archive}
            user_paths = {user_agents, user_skills, user_archive}

            # No overlap between scopes
            assert project_paths.isdisjoint(user_paths)

            # PROJECT paths contain project directory
            for path in project_paths:
                assert str(project_path) in str(path)

            # USER paths contain home directory
            for path in user_paths:
                assert str(tmp_path / "home") in str(path)

    def test_scope_switching_during_auto_configure(self, tmp_path):
        """Test switching scopes during auto-configure workflow."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
            mock_home.return_value = tmp_path / "home"

            # Simulate auto-configure workflow switching scopes

            # Phase 1: Analyze project-scoped agents
            project_agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)

            # Phase 2: Check user-scoped skills compatibility
            user_skills_dir = resolve_skills_dir(ConfigScope.USER, project_path)

            # Phase 3: Deploy to project scope (typical)
            final_agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)
            final_skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)

            # Verify workflow consistency
            assert project_agents_dir == final_agents_dir
            assert user_skills_dir != final_skills_dir  # Different scopes

            # Verify deployment directories exist in expected places
            assert "project" in str(final_agents_dir)
            assert "project" in str(final_skills_dir)


@pytest.mark.integration
class TestConfigScopePathReality:
    """Integration tests using real filesystem operations."""

    def test_path_resolution_with_real_filesystem(self, tmp_path):
        """Test path resolution against real filesystem structure."""
        # Setup realistic project structure
        project_root = tmp_path / "my_app"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "README.md").write_text("# My App")

        # Resolve paths
        agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_root)
        skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_root)
        archive_dir = resolve_archive_dir(ConfigScope.PROJECT, project_root)
        config_dir = resolve_config_dir(ConfigScope.PROJECT, project_root)

        # Create directories to test they're writable
        agents_dir.mkdir(parents=True)
        skills_dir.mkdir(parents=True)
        archive_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)

        # Verify structure matches expectations
        assert agents_dir.exists()
        assert skills_dir.exists()
        assert archive_dir.exists()
        assert config_dir.exists()

        # Verify hierarchy
        assert agents_dir.parent.parent == project_root  # project/.claude/agents
        assert skills_dir.parent.parent == project_root  # project/.claude/skills
        assert archive_dir.parent == agents_dir  # .claude/agents/unused
        assert config_dir.parent == project_root  # project/.claude-mpm

    def test_permissions_and_accessibility(self, tmp_path):
        """Test that resolved paths are accessible for deployment."""
        project_path = tmp_path / "permissions_test"
        project_path.mkdir()

        # Get all resolver functions
        resolvers = [
            (resolve_agents_dir, "agents"),
            (resolve_skills_dir, "skills"),
            (resolve_archive_dir, "archive"),
            (resolve_config_dir, "config"),
        ]

        for scope in [ConfigScope.PROJECT, ConfigScope.USER]:
            with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
                mock_home.return_value = tmp_path / "home"

                for resolver_func, name in resolvers:
                    if name == "skills" and scope == ConfigScope.PROJECT:
                        # skills resolver has different signature
                        path = resolver_func(scope, project_path)
                    else:
                        path = resolver_func(scope, project_path)

                    # Test path creation
                    path.mkdir(parents=True, exist_ok=True)
                    assert path.exists()

                    # Test file writing (deployment simulation)
                    test_file = path / f"test_{name}.yml"
                    test_file.write_text("test: content")
                    assert test_file.exists()

                    # Test reading
                    content = test_file.read_text()
                    assert "test: content" in content

    def test_auto_configure_phase_transitions(self, tmp_path):
        """Test path resolution during auto-configure phase transitions."""
        project_path = tmp_path / "phase_test"
        project_path.mkdir()

        with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
            mock_home.return_value = tmp_path / "home"

            # Phase 0: Initial analysis (no scope preference)
            analysis_paths = {}
            for scope in [ConfigScope.PROJECT, ConfigScope.USER]:
                analysis_paths[scope] = {
                    "agents": resolve_agents_dir(scope, project_path),
                    "skills": resolve_skills_dir(scope, project_path),
                    "config": resolve_config_dir(scope, project_path),
                }

            # Phase 1: Min confidence validation (typically project-scoped)
            validation_agents_dir = resolve_agents_dir(
                ConfigScope.PROJECT, project_path
            )

            # Phase 2: Skill deployment (could be either scope)
            project_skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)
            user_skills_dir = resolve_skills_dir(ConfigScope.USER, project_path)

            # Verify phase consistency
            assert (
                validation_agents_dir == analysis_paths[ConfigScope.PROJECT]["agents"]
            )
            assert project_skills_dir == analysis_paths[ConfigScope.PROJECT]["skills"]
            assert user_skills_dir == analysis_paths[ConfigScope.USER]["skills"]

            # Verify cross-phase isolation
            assert validation_agents_dir != analysis_paths[ConfigScope.USER]["agents"]
            assert project_skills_dir != user_skills_dir
