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


class TestModelConfigLayeredMerge:
    """Tests for layered deep-merge of configuration files.

    WHY: ``ModelConfigManager.load_config`` should support per-project
    overrides that selectively override individual keys (including nested
    keys) from a user-level config without wiping unrelated keys. This
    test class covers the deep-merge behavior added to fix issue #359.
    """

    @staticmethod
    def _write_yaml(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_deep_merge_helper_scalar_override(self) -> None:
        """Higher-priority scalar should override lower-priority scalar."""
        from claude_mpm.config.model_config import ModelConfigManager

        base = {"provider": "claude", "timeout": 30}
        overlay = {"provider": "ollama"}

        result = ModelConfigManager._deep_merge(base, overlay)

        assert result == {"provider": "ollama", "timeout": 30}

    def test_deep_merge_helper_nested_dict_preserves_siblings(self) -> None:
        """Nested overrides must NOT wipe sibling keys at the same level."""
        from claude_mpm.config.model_config import ModelConfigManager

        base = {
            "models": {
                "planning": "claude-opus-4",
                "coding": "claude-sonnet-4",
                "review": "claude-haiku-4",
            }
        }
        overlay = {"models": {"planning": "claude-opus-4-7"}}

        result = ModelConfigManager._deep_merge(base, overlay)

        assert result == {
            "models": {
                "planning": "claude-opus-4-7",  # Overridden
                "coding": "claude-sonnet-4",  # Preserved
                "review": "claude-haiku-4",  # Preserved
            }
        }

    def test_deep_merge_helper_lists_are_replaced_not_concatenated(self) -> None:
        """Lists in overlay must REPLACE base lists, not concatenate."""
        from claude_mpm.config.model_config import ModelConfigManager

        base = {"tools": ["a", "b", "c"]}
        overlay = {"tools": ["x", "y"]}

        result = ModelConfigManager._deep_merge(base, overlay)

        assert result == {"tools": ["x", "y"]}

    def test_deep_merge_helper_does_not_mutate_inputs(self) -> None:
        """``_deep_merge`` must not mutate either input dict."""
        from claude_mpm.config.model_config import ModelConfigManager

        base = {"models": {"planning": "a", "coding": "b"}}
        overlay = {"models": {"planning": "c"}}
        base_snapshot = {"models": {"planning": "a", "coding": "b"}}
        overlay_snapshot = {"models": {"planning": "c"}}

        ModelConfigManager._deep_merge(base, overlay)

        assert base == base_snapshot
        assert overlay == overlay_snapshot

    def test_deep_merge_helper_type_mismatch_overlay_wins(self) -> None:
        """When base is dict and overlay is scalar (or vice versa), overlay wins."""
        from claude_mpm.config.model_config import ModelConfigManager

        # Dict in base, scalar in overlay
        result1 = ModelConfigManager._deep_merge(
            {"models": {"planning": "a"}}, {"models": "disabled"}
        )
        assert result1 == {"models": "disabled"}

        # Scalar in base, dict in overlay
        result2 = ModelConfigManager._deep_merge(
            {"models": "disabled"}, {"models": {"planning": "a"}}
        )
        assert result2 == {"models": {"planning": "a"}}

    def test_load_config_no_files_returns_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no config files present, defaults should be returned."""
        from claude_mpm.config.model_config import (
            ModelConfigManager,
            ModelProviderConfig,
        )

        # Run from an empty temp directory and point HOME to a fresh dir
        # so ~/.claude-mpm/configuration.yaml does not exist either.
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        # Re-evaluate the home-relative default path under the new HOME.
        monkeypatch.setattr(
            ModelConfigManager,
            "DEFAULT_CONFIG_PATHS",
            [
                str(Path("~/.claude-mpm/configuration.yaml").expanduser()),
                ".claude-mpm/configuration.yaml",
                "configuration.yaml",
                ".claude/configuration.yaml",
            ],
        )

        # Strip env var overrides that might leak in.
        for env_var in (
            "MODEL_PROVIDER",
            "OLLAMA_HOST",
            "OLLAMA_ENABLED",
            "OLLAMA_TIMEOUT",
            "OLLAMA_FALLBACK_TO_CLOUD",
            "CLAUDE_ENABLED",
            "CLAUDE_MODEL",
            "CLAUDE_MAX_TOKENS",
            "CLAUDE_TEMPERATURE",
            "ANTHROPIC_API_KEY",
        ):
            monkeypatch.delenv(env_var, raising=False)

        config = ModelConfigManager.load_config()

        # Should be a fully-defaulted config.
        assert isinstance(config, ModelProviderConfig)
        assert config.provider == "auto"
        assert config.ollama.enabled is True
        assert config.claude.enabled is True

    def test_load_config_single_file_no_regression(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single config file should load correctly (no layering needed)."""
        from claude_mpm.config.model_config import ModelConfigManager

        monkeypatch.chdir(tmp_path)
        # Point HOME away so we only have the project file.
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        for env_var in (
            "MODEL_PROVIDER",
            "OLLAMA_HOST",
            "OLLAMA_ENABLED",
            "OLLAMA_TIMEOUT",
            "OLLAMA_FALLBACK_TO_CLOUD",
            "CLAUDE_ENABLED",
            "CLAUDE_MODEL",
            "CLAUDE_MAX_TOKENS",
            "CLAUDE_TEMPERATURE",
            "ANTHROPIC_API_KEY",
        ):
            monkeypatch.delenv(env_var, raising=False)

        # Recompute DEFAULT_CONFIG_PATHS for this test's HOME.
        monkeypatch.setattr(
            ModelConfigManager,
            "DEFAULT_CONFIG_PATHS",
            [
                str(Path("~/.claude-mpm/configuration.yaml").expanduser()),
                ".claude-mpm/configuration.yaml",
                "configuration.yaml",
                ".claude/configuration.yaml",
            ],
        )

        self._write_yaml(
            tmp_path / ".claude" / "configuration.yaml",
            "provider: ollama\n"
            "ollama:\n"
            "  host: http://example.com:11434\n"
            "  timeout: 60\n",
        )

        config = ModelConfigManager.load_config()

        assert config.provider == "ollama"
        assert config.ollama.host == "http://example.com:11434"
        assert config.ollama.timeout == 60
        # Defaults preserved for unspecified fields.
        assert config.ollama.enabled is True
        assert config.claude.enabled is True

    def test_load_config_project_overrides_user_scalar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project-level scalar key overrides user-level scalar key."""
        from claude_mpm.config.model_config import ModelConfigManager

        home_dir = tmp_path / "home"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setenv("HOME", str(home_dir))
        for env_var in (
            "MODEL_PROVIDER",
            "OLLAMA_HOST",
            "OLLAMA_ENABLED",
            "OLLAMA_TIMEOUT",
            "OLLAMA_FALLBACK_TO_CLOUD",
            "CLAUDE_ENABLED",
            "CLAUDE_MODEL",
            "CLAUDE_MAX_TOKENS",
            "CLAUDE_TEMPERATURE",
            "ANTHROPIC_API_KEY",
        ):
            monkeypatch.delenv(env_var, raising=False)

        user_config_path = home_dir / ".claude-mpm" / "configuration.yaml"
        monkeypatch.setattr(
            ModelConfigManager,
            "DEFAULT_CONFIG_PATHS",
            [
                str(user_config_path),
                ".claude-mpm/configuration.yaml",
                "configuration.yaml",
                ".claude/configuration.yaml",
            ],
        )

        # User-level: provider=claude
        self._write_yaml(user_config_path, "provider: claude\n")
        # Project-level: override provider=ollama
        self._write_yaml(
            project_dir / ".claude" / "configuration.yaml",
            "provider: ollama\n",
        )

        config = ModelConfigManager.load_config()

        assert config.provider == "ollama"

    def test_load_config_project_overrides_nested_without_wiping_siblings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project nested override preserves user nested siblings.

        This is the core regression test for issue #359: a project config
        that only overrides ``ollama.host`` must NOT wipe other keys
        under ``ollama`` defined at the user level.
        """
        from claude_mpm.config.model_config import ModelConfigManager

        home_dir = tmp_path / "home"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setenv("HOME", str(home_dir))
        for env_var in (
            "MODEL_PROVIDER",
            "OLLAMA_HOST",
            "OLLAMA_ENABLED",
            "OLLAMA_TIMEOUT",
            "OLLAMA_FALLBACK_TO_CLOUD",
            "CLAUDE_ENABLED",
            "CLAUDE_MODEL",
            "CLAUDE_MAX_TOKENS",
            "CLAUDE_TEMPERATURE",
            "ANTHROPIC_API_KEY",
        ):
            monkeypatch.delenv(env_var, raising=False)

        user_config_path = home_dir / ".claude-mpm" / "configuration.yaml"
        monkeypatch.setattr(
            ModelConfigManager,
            "DEFAULT_CONFIG_PATHS",
            [
                str(user_config_path),
                ".claude-mpm/configuration.yaml",
                "configuration.yaml",
                ".claude/configuration.yaml",
            ],
        )

        # User-level: full ollama configuration with multiple keys
        self._write_yaml(
            user_config_path,
            "provider: auto\n"
            "ollama:\n"
            "  enabled: true\n"
            "  host: http://user-host:11434\n"
            "  timeout: 45\n"
            "  fallback_to_cloud: true\n"
            "claude:\n"
            "  enabled: true\n"
            "  model: opus\n"
            "  max_tokens: 8192\n",
        )
        # Project-level: ONLY override ollama.host
        self._write_yaml(
            project_dir / ".claude" / "configuration.yaml",
            "ollama:\n  host: http://project-host:11434\n",
        )

        config = ModelConfigManager.load_config()

        # Project override took effect
        assert config.ollama.host == "http://project-host:11434"
        # Sibling keys under ollama preserved from user-level
        assert config.ollama.enabled is True
        assert config.ollama.timeout == 45
        assert config.ollama.fallback_to_cloud is True
        # Top-level siblings preserved from user-level
        assert config.provider == "auto"
        # Unrelated nested section (claude) fully preserved
        assert config.claude.enabled is True
        assert config.claude.model == "opus"
        assert config.claude.max_tokens == 8192

    def test_load_config_lists_replaced_not_concatenated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lists in higher-priority config replace lower-priority lists."""
        from claude_mpm.config.model_config import ModelConfigManager

        home_dir = tmp_path / "home"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        monkeypatch.chdir(project_dir)
        monkeypatch.setenv("HOME", str(home_dir))
        for env_var in (
            "MODEL_PROVIDER",
            "OLLAMA_HOST",
            "OLLAMA_ENABLED",
            "OLLAMA_TIMEOUT",
            "OLLAMA_FALLBACK_TO_CLOUD",
            "CLAUDE_ENABLED",
            "CLAUDE_MODEL",
            "CLAUDE_MAX_TOKENS",
            "CLAUDE_TEMPERATURE",
            "ANTHROPIC_API_KEY",
        ):
            monkeypatch.delenv(env_var, raising=False)

        user_config_path = home_dir / ".claude-mpm" / "configuration.yaml"
        monkeypatch.setattr(
            ModelConfigManager,
            "DEFAULT_CONFIG_PATHS",
            [
                str(user_config_path),
                ".claude-mpm/configuration.yaml",
                "configuration.yaml",
                ".claude/configuration.yaml",
            ],
        )

        # ``ollama.models`` is a dict[str, str], so to test list-replacement
        # we use a synthetic structure with extra=allow on OllamaConfig and
        # an arbitrary list field. We piggy-back on Pydantic's extra='allow'.
        self._write_yaml(
            user_config_path,
            "ollama:\n  custom_tags:\n    - alpha\n    - beta\n    - gamma\n",
        )
        self._write_yaml(
            project_dir / ".claude" / "configuration.yaml",
            "ollama:\n  custom_tags:\n    - one\n    - two\n",
        )

        config = ModelConfigManager.load_config()

        # Access via __dict__ since custom_tags is via extra='allow'
        custom_tags = getattr(config.ollama, "custom_tags", None)
        # Lists must be replaced, not concatenated
        assert custom_tags == ["one", "two"]
