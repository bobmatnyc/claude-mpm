"""Tests for claude_mpm.core.config_scope module.

Verifies scope-based path resolution and backward compatibility
of the ConfigScope str enum.
"""

from pathlib import Path

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
