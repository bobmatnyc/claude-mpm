"""
Unit tests for PathResolver service.

This module tests the PathResolver service that was extracted from FrameworkLoader
to handle all path resolution logic including framework detection, npm paths,
and deployment context management.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.services.core.path_resolver import DeploymentContext, PathResolver


class TestPathResolver:
    """Test suite for PathResolver service."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        cache = MagicMock()
        cache.get.return_value = None
        cache.set.return_value = None
        return cache

    @pytest.fixture
    def resolver(self, mock_cache_manager):
        """Create a PathResolver instance with mocked cache."""
        return PathResolver(cache_manager=mock_cache_manager)

    def test_init(self):
        """Test PathResolver initialization."""
        resolver = PathResolver()
        assert resolver.logger is not None
        assert resolver.cache_manager is None
        assert resolver._framework_path is None
        assert resolver._deployment_context is None

    def test_init_with_cache(self, mock_cache_manager):
        """Test PathResolver initialization with cache manager."""
        resolver = PathResolver(cache_manager=mock_cache_manager)
        assert resolver.cache_manager == mock_cache_manager

    def test_resolve_path_absolute(self, resolver):
        """Test resolving absolute paths."""
        abs_path = Path("/usr/local/bin/test")
        result = resolver.resolve_path(str(abs_path))
        assert result == abs_path

    def test_resolve_path_relative_with_base(self, resolver):
        """Test resolving relative paths with base directory."""
        base_dir = Path("/home/user")
        relative_path = "projects/claude-mpm"
        expected = (base_dir / relative_path).resolve()

        result = resolver.resolve_path(relative_path, base_dir)
        assert result == expected

    def test_resolve_path_relative_no_base(self, resolver):
        """Test resolving relative paths without base directory."""
        relative_path = "test/file.txt"
        expected = (Path.cwd() / relative_path).resolve()

        result = resolver.resolve_path(relative_path)
        assert result == expected

    def test_validate_path_exists(self, resolver, tmp_path):
        """Test validating existing path."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        assert resolver.validate_path(test_file, must_exist=True)
        assert resolver.validate_path(test_file, must_exist=False)

    def test_validate_path_not_exists(self, resolver, tmp_path):
        """Test validating non-existing path."""
        test_file = tmp_path / "nonexistent.txt"

        assert not resolver.validate_path(test_file, must_exist=True)
        assert resolver.validate_path(test_file, must_exist=False)

    def test_validate_path_invalid(self, resolver):
        """Test validating invalid path."""
        # Path with null bytes is invalid
        invalid_path = Path("\x00invalid")
        assert not resolver.validate_path(invalid_path)

    @patch("claude_mpm.services.core.path_resolver.Path")
    def test_detect_framework_path_cached(self, mock_path, resolver):
        """Test framework path detection with cached value."""
        # Set cached value
        resolver._framework_path = Path("/cached/path")

        result = resolver.detect_framework_path()
        assert result == Path("/cached/path")

        # Should not call any detection methods
        mock_path.assert_not_called()

    def test_detect_framework_path_from_internal_cache(self, resolver):
        """Test framework path detection from internal cache."""
        resolver._path_cache["framework_path"] = "/cached/framework"

        result = resolver.detect_framework_path()
        assert result == Path("/cached/framework")

    def test_detect_framework_path_packaged_from_cache(self, resolver):
        """Test detecting packaged installation from cache."""
        resolver._path_cache["framework_path"] = "__PACKAGED__"

        result = resolver.detect_framework_path()
        assert result == Path("__PACKAGED__")

    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_via_unified_paths"
    )
    def test_detect_framework_path_via_unified(self, mock_detect, resolver):
        """Test framework path detection via unified paths."""
        mock_detect.return_value = Path("/unified/path")

        result = resolver.detect_framework_path()
        assert result == Path("/unified/path")
        mock_detect.assert_called_once()

        # Should cache the result internally
        assert resolver._path_cache["framework_path"] == "/unified/path"

    @patch("claude_mpm.services.core.path_resolver.PathResolver._detect_via_package")
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_via_unified_paths"
    )
    def test_detect_framework_path_via_package(
        self, mock_unified, mock_package, resolver
    ):
        """Test framework path detection via package."""
        mock_unified.return_value = None
        mock_package.return_value = Path("__PACKAGED__")

        result = resolver.detect_framework_path()
        assert result == Path("__PACKAGED__")

        # Should cache the result internally
        assert resolver._path_cache["framework_path"] == "__PACKAGED__"

    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._check_common_locations"
    )
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_development_mode"
    )
    @patch("claude_mpm.services.core.path_resolver.PathResolver._detect_via_package")
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_via_unified_paths"
    )
    def test_detect_framework_path_development(
        self, mock_unified, mock_package, mock_dev, mock_common, resolver
    ):
        """Test framework path detection in development mode."""
        mock_unified.return_value = None
        mock_package.return_value = None
        mock_dev.return_value = Path("/dev/claude-mpm")

        result = resolver.detect_framework_path()
        assert result == Path("/dev/claude-mpm")

        # Should not check common locations
        mock_common.assert_not_called()

    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._check_common_locations"
    )
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_development_mode"
    )
    @patch("claude_mpm.services.core.path_resolver.PathResolver._detect_via_package")
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_via_unified_paths"
    )
    def test_detect_framework_path_common_locations(
        self, mock_unified, mock_package, mock_dev, mock_common, resolver
    ):
        """Test framework path detection from common locations."""
        mock_unified.return_value = None
        mock_package.return_value = None
        mock_dev.return_value = None
        mock_common.return_value = Path("/home/user/Projects/claude-mpm")

        result = resolver.detect_framework_path()
        assert result == Path("/home/user/Projects/claude-mpm")

    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._check_common_locations"
    )
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_development_mode"
    )
    @patch("claude_mpm.services.core.path_resolver.PathResolver._detect_via_package")
    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_via_unified_paths"
    )
    def test_detect_framework_path_not_found(
        self, mock_unified, mock_package, mock_dev, mock_common, resolver
    ):
        """Test framework path detection when not found."""
        mock_unified.return_value = None
        mock_package.return_value = None
        mock_dev.return_value = None
        mock_common.return_value = None

        result = resolver.detect_framework_path()
        assert result is None

        # Should not cache None
        assert "framework_path" not in resolver._path_cache

    @patch("subprocess.run")
    def test_get_npm_global_path_success(self, mock_run, resolver):
        """Test getting npm global path successfully."""
        # Mock successful npm command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/lib/node_modules\n"
        mock_run.return_value = mock_result

        # Mock path existence
        with patch("claude_mpm.services.core.path_resolver.Path.exists") as mock_exists:
            mock_exists.return_value = True

            result = resolver.get_npm_global_path()
            expected = Path(
                "/usr/local/lib/node_modules/@bobmatnyc/claude-multiagent-pm"
            )
            assert result == expected

            # Should cache the result internally
            assert resolver._path_cache["npm_global_path"] == str(expected)

    @patch("subprocess.run")
    def test_get_npm_global_path_not_exists(self, mock_run, resolver):
        """Test getting npm global path when package doesn't exist."""
        # Mock successful npm command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/lib/node_modules\n"
        mock_run.return_value = mock_result

        # Mock path doesn't exist
        with patch("claude_mpm.services.core.path_resolver.Path.exists") as mock_exists:
            mock_exists.return_value = False

            result = resolver.get_npm_global_path()
            assert result is None

            # Should cache the negative result internally
            assert resolver._path_cache["npm_global_path"] == "NOT_FOUND"

    @patch("subprocess.run")
    def test_get_npm_global_path_command_fails(self, mock_run, resolver):
        """Test getting npm global path when npm command fails."""
        # Mock failed npm command
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = resolver.get_npm_global_path()
        assert result is None

        # Should cache the negative result internally
        assert resolver._path_cache["npm_global_path"] == "NOT_FOUND"

    @patch("subprocess.run")
    def test_get_npm_global_path_exception(self, mock_run, resolver):
        """Test getting npm global path when exception occurs."""
        mock_run.side_effect = FileNotFoundError("npm not found")

        result = resolver.get_npm_global_path()
        assert result is None

        # Should cache the negative result internally
        assert resolver._path_cache["npm_global_path"] == "NOT_FOUND"

    def test_get_npm_global_path_cached(self, resolver):
        """Test getting npm global path from cache."""
        cached_path = "/cached/npm/path"
        resolver._path_cache["npm_global_path"] = cached_path

        result = resolver.get_npm_global_path()
        assert result == Path(cached_path)

    def test_get_npm_global_path_cached_not_found(self, resolver):
        """Test getting npm global path from cache when not found."""
        resolver._path_cache["npm_global_path"] = "NOT_FOUND"

        result = resolver.get_npm_global_path()
        assert result is None

    def test_get_deployment_context_cached(self, resolver):
        """Test getting cached deployment context."""
        resolver._deployment_context = DeploymentContext.DEVELOPMENT

        result = resolver.get_deployment_context()
        assert result == DeploymentContext.DEVELOPMENT

    @patch(
        "claude_mpm.services.core.path_resolver.PathResolver._detect_deployment_context"
    )
    def test_get_deployment_context_detect(self, mock_detect, resolver):
        """Test detecting deployment context."""
        mock_detect.return_value = DeploymentContext.PIP_INSTALL

        result = resolver.get_deployment_context()
        assert result == DeploymentContext.PIP_INSTALL
        assert resolver._deployment_context == DeploymentContext.PIP_INSTALL
        mock_detect.assert_called_once()

    def test_discover_agent_paths_custom_dir(self, resolver, tmp_path):
        """Test discovering agent paths with custom directory."""
        custom_dir = tmp_path / "custom_agents"
        custom_dir.mkdir()

        agents_dir, templates_dir, main_dir = resolver.discover_agent_paths(
            agents_dir=custom_dir
        )

        assert agents_dir == custom_dir
        assert templates_dir is None
        assert main_dir is None

    def test_discover_agent_paths_framework_templates(self, resolver, tmp_path):
        """Test discovering agent paths from framework templates."""
        framework_path = tmp_path / "framework"
        templates_dir = framework_path / "src" / "claude_mpm" / "agents" / "templates"
        main_dir = framework_path / "src" / "claude_mpm" / "agents"

        templates_dir.mkdir(parents=True)
        main_dir.mkdir(parents=True, exist_ok=True)

        # Create test agent file in templates
        (templates_dir / "test.md").touch()

        agents_dir, found_templates, found_main = resolver.discover_agent_paths(
            framework_path=framework_path
        )

        assert agents_dir == templates_dir
        assert found_templates == templates_dir
        assert found_main == main_dir

    def test_discover_agent_paths_framework_main(self, resolver, tmp_path):
        """Test discovering agent paths from framework main directory."""
        framework_path = tmp_path / "framework"
        templates_dir = framework_path / "src" / "claude_mpm" / "agents" / "templates"
        main_dir = framework_path / "src" / "claude_mpm" / "agents"

        main_dir.mkdir(parents=True)
        templates_dir.mkdir(parents=True)

        # Create test agent file in main dir only
        (main_dir / "test.md").touch()

        agents_dir, found_templates, found_main = resolver.discover_agent_paths(
            framework_path=framework_path
        )

        assert agents_dir == main_dir
        assert found_templates == templates_dir
        assert found_main == main_dir

    def test_discover_agent_paths_packaged(self, resolver):
        """Test discovering agent paths for packaged installation."""
        agents_dir, templates_dir, main_dir = resolver.discover_agent_paths(
            framework_path=Path("__PACKAGED__")
        )

        assert agents_dir is None
        assert templates_dir is None
        assert main_dir is None

    def test_get_instruction_file_paths(self, resolver, tmp_path, monkeypatch):
        """Test getting instruction file paths with precedence."""
        # Set up test directories
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create project instructions
        project_claude_dir = project_dir / ".claude-mpm"
        project_claude_dir.mkdir()
        project_instructions = project_claude_dir / "INSTRUCTIONS.md"
        project_instructions.touch()

        # Create user instructions
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))
        user_claude_dir = home_dir / ".claude-mpm"
        user_claude_dir.mkdir()
        user_instructions = user_claude_dir / "INSTRUCTIONS.md"
        user_instructions.touch()

        # Mock framework detection
        with patch.object(resolver, "detect_framework_path") as mock_detect:
            mock_detect.return_value = None

            paths = resolver.get_instruction_file_paths()

            assert paths["project"] == project_instructions
            assert paths["user"] == user_instructions
            assert paths["system"] is None

    def test_get_instruction_file_paths_with_framework(
        self, resolver, tmp_path, monkeypatch
    ):
        """Test getting instruction file paths with framework."""
        # Set up framework directory
        framework_dir = tmp_path / "framework"
        system_instructions = (
            framework_dir / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        )
        system_instructions.mkdir(parents=True, exist_ok=True)
        system_instructions = (
            framework_dir / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        )
        system_instructions.touch()

        # Mock framework detection
        with patch.object(resolver, "detect_framework_path") as mock_detect:
            mock_detect.return_value = framework_dir

            paths = resolver.get_instruction_file_paths()

            assert paths["system"] == system_instructions

    def test_detect_deployment_context_pip_install(self, resolver):
        """Test detecting pip install deployment context."""
        with patch("claude_mpm.services.core.path_resolver.Path") as MockPath:
            mock_file = MockPath.return_value
            mock_file.__str__.return_value = (
                "/usr/lib/python3.9/site-packages/claude_mpm/__init__.py"
            )

            with patch("claude_mpm.__file__", mock_file):
                context = resolver._detect_deployment_context()
                assert context == DeploymentContext.PIP_INSTALL

    def test_detect_deployment_context_system_package(self, resolver):
        """Test detecting system package deployment context."""
        with patch("claude_mpm.services.core.path_resolver.Path") as MockPath:
            mock_file = MockPath.return_value
            mock_file.__str__.return_value = (
                "/usr/lib/python3.9/dist-packages/claude_mpm/__init__.py"
            )

            with patch("claude_mpm.__file__", mock_file):
                context = resolver._detect_deployment_context()
                assert context == DeploymentContext.SYSTEM_PACKAGE

    def test_detect_deployment_context_pipx(self, resolver):
        """Test detecting pipx deployment context."""
        with patch("claude_mpm.services.core.path_resolver.Path") as MockPath:
            mock_file = MockPath.return_value
            mock_file.__str__.return_value = "/home/user/.local/pipx/venvs/claude-mpm/lib/python3.9/site-packages/claude_mpm/__init__.py"

            with patch("claude_mpm.__file__", mock_file):
                context = resolver._detect_deployment_context()
                assert context == DeploymentContext.PIPX_INSTALL

    def test_detect_deployment_context_development(
        self, resolver, tmp_path, monkeypatch
    ):
        """Test detecting development deployment context."""
        # Create pyproject.toml in current directory
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").touch()

        # Mock import error for claude_mpm
        with patch("claude_mpm.__file__", side_effect=ImportError):
            context = resolver._detect_deployment_context()
            assert context == DeploymentContext.DEVELOPMENT

    def test_detect_deployment_context_unknown(self, resolver, tmp_path, monkeypatch):
        """Test detecting unknown deployment context."""
        # Change to a directory without pyproject.toml
        isolated_dir = tmp_path / "isolated"
        isolated_dir.mkdir()
        monkeypatch.chdir(isolated_dir)

        # Mock import error for claude_mpm
        with patch("claude_mpm.__file__", side_effect=ImportError):
            context = resolver._detect_deployment_context()
            assert context == DeploymentContext.UNKNOWN

    def test_ensure_directory_creates_new(self, resolver, tmp_path):
        """Test ensuring a directory exists by creating it."""
        new_dir = tmp_path / "new" / "nested" / "directory"
        assert not new_dir.exists()

        result = resolver.ensure_directory(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_existing(self, resolver, tmp_path):
        """Test ensuring an existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = resolver.ensure_directory(existing_dir)

        assert result == existing_dir
        assert existing_dir.exists()
        assert existing_dir.is_dir()

    def test_ensure_directory_file_exists(self, resolver, tmp_path):
        """Test ensuring directory when a file exists at the path."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="not a directory"):
            resolver.ensure_directory(file_path)

    def test_find_project_root_with_git(self, resolver, tmp_path, monkeypatch):
        """Test finding project root with .git directory."""
        project_root = tmp_path / "project"
        git_dir = project_root / ".git"
        git_dir.mkdir(parents=True)

        subdir = project_root / "src" / "subdir"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)

        result = resolver.find_project_root()
        assert result == project_root

    def test_find_project_root_with_pyproject(self, resolver, tmp_path, monkeypatch):
        """Test finding project root with pyproject.toml."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").touch()

        subdir = project_root / "src" / "subdir"
        subdir.mkdir(parents=True)

        result = resolver.find_project_root(subdir)
        assert result == project_root

    def test_find_project_root_with_claude_mpm(self, resolver, tmp_path):
        """Test finding project root with .claude-mpm directory."""
        project_root = tmp_path / "project"
        claude_dir = project_root / ".claude-mpm"
        claude_dir.mkdir(parents=True)

        subdir = project_root / "src"
        subdir.mkdir()

        result = resolver.find_project_root(subdir)
        assert result == project_root

    def test_find_project_root_not_found(self, resolver, tmp_path):
        """Test finding project root when no indicators exist."""
        isolated_dir = tmp_path / "isolated"
        isolated_dir.mkdir()

        result = resolver.find_project_root(isolated_dir)
        assert result is None

    def test_find_project_root_from_file(self, resolver, tmp_path):
        """Test finding project root starting from a file path."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".git").mkdir()

        file_path = project_root / "src" / "file.py"
        file_path.parent.mkdir(parents=True)
        file_path.touch()

        result = resolver.find_project_root(file_path)
        assert result == project_root

    def test_find_project_root_with_explicit_marker(
        self, resolver, tmp_path, monkeypatch
    ):
        """Test that .claude/project-root marker takes highest priority."""
        # Create parent directory with .claude/project-root marker
        parent_root = tmp_path / "repos"
        parent_root.mkdir()
        claude_dir = parent_root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "project-root").touch()

        # Create subdirectory with .git and settings.local.json
        subdirectory = parent_root / "duetto"
        subdirectory.mkdir()
        (subdirectory / ".git").mkdir()
        claude_subdir = subdirectory / ".claude"
        claude_subdir.mkdir()
        (claude_subdir / "settings.local.json").touch()

        # Change to subdirectory
        monkeypatch.chdir(subdirectory)

        # Should find parent root due to .claude/project-root marker
        result = resolver.find_project_root()
        assert result == parent_root, (
            f"Expected parent_root {parent_root}, but got {result}. "
            "The .claude/project-root marker should take priority over .git"
        )
