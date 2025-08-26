"""Tests for get_path_manager() utility."""

from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.core.unified_paths import (
    get_framework_root,
    get_path_manager,
    get_project_root,
)


class TestUnifiedPathManager:
    """Test cases for UnifiedPathManager class."""

    def setup_method(self):
        """Clear cache before each test."""
        get_path_manager().clear_cache()

    def test_get_framework_root_from_module():
        """Test framework root detection from module location."""
        root = get_path_manager().framework_root
        assert root.exists()
        # Should have src/claude_mpm structure or claude_mpm directly
        assert (root / "src" / "claude_mpm").exists() or (root / "claude_mpm").exists()

    def test_get_framework_root_cached():
        """Test that framework root is cached."""
        root1 = get_path_manager().framework_root
        root2 = get_path_manager().framework_root
        assert root1 == root2

    def test_get_agents_dir():
        """Test agents directory detection."""
        agents_dir = get_path_manager().get_agents_dir("framework")
        assert agents_dir.exists()
        assert agents_dir.name == "agents"
        # Should contain agent files
        assert list(agents_dir.glob("*.md")) or list(agents_dir.glob("*.py"))

    def test_get_project_root_with_git(self):
        """Test project root detection with .git directory."""
        # Create a temporary project structure
        git_dir = self / ".git"
        git_dir.mkdir()

        # Change to a subdirectory
        subdir = self / "src" / "submodule"
        subdir.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=subdir):
            root = get_path_manager().project_root
            assert root == self

    def test_get_project_root_with_pyproject(self):
        """Test project root detection with pyproject.toml."""
        # Create pyproject.toml
        (self / "pyproject.toml").touch()

        # Change to subdirectory
        subdir = self / "src"
        subdir.mkdir()

        with patch("pathlib.Path.cwd", return_value=subdir):
            root = get_path_manager().project_root
            assert root == self

    def test_get_project_root_fallback_to_cwd(self):
        """Test project root fallback to current directory."""
        # No project markers
        with patch("pathlib.Path.cwd", return_value=self):
            root = get_path_manager().project_root
            assert root == self

    def test_get_config_dir_project():
        """Test project config directory."""
        config_dir = get_path_manager().get_config_dir("project")
        assert config_dir.name == ".claude-mpm"
        assert config_dir.parent == get_path_manager().project_root

    def test_get_config_dir_user():
        """Test user config directory."""
        config_dir = get_path_manager().get_config_dir("user")
        assert "claude-mpm" in str(config_dir)
        assert str(config_dir).startswith(str(Path.home()))

    def test_get_config_dir_user_with_xdg():
        """Test user config directory (unified implementation uses home directory)."""
        # The unified implementation uses home directory, not XDG
        config_dir = get_path_manager().get_config_dir("user")
        assert config_dir == Path.home() / ".claude-mpm"

    def test_get_config_dir_invalid_scope():
        """Test invalid config scope."""
        with pytest.raises(ValueError, match="Invalid scope"):
            get_path_manager().get_config_dir("invalid")

    def test_find_file_upwards(self):
        """Test upward file search."""
        # Create file in parent
        target_file = self / "target.txt"
        target_file.touch()

        # Search from subdirectory
        subdir = self / "a" / "b" / "c"
        subdir.mkdir(parents=True)

        result = get_path_manager().find_file_upwards("target.txt", subdir)
        assert result == target_file

    def test_find_file_upwards_not_found(self):
        """Test upward file search when file doesn't exist."""
        result = get_path_manager().find_file_upwards("nonexistent.txt", self)
        assert result is None

    def test_get_project_config_dir():
        """Test project config directory method."""
        config_dir = get_path_manager().get_project_config_dir()
        assert config_dir.name == ".claude-mpm"
        assert config_dir.parent == get_path_manager().project_root

    def test_ensure_directory(self):
        """Test directory creation."""
        new_dir = self / "new" / "nested" / "dir"
        result = get_path_manager().ensure_directory(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_get_relative_to_root():
        """Test getting paths relative to roots."""
        # Test with actual project root
        path = get_path_manager().get_relative_to_root("src/module.py", "project")
        expected = get_path_manager().project_root / "src/module.py"
        assert path == expected

        # Test with actual framework root
        path = get_path_manager().get_relative_to_root("agents/test.md", "framework")
        expected = get_path_manager().framework_root / "agents/test.md"
        assert path == expected

    def test_convenience_functions():
        """Test backward compatibility convenience functions."""
        # These should work the same as the class methods
        root1 = get_framework_root()
        root2 = get_path_manager().framework_root
        assert root1 == root2

        proj1 = get_project_root()
        proj2 = get_path_manager().project_root
        assert proj1 == proj2

    def test_cache_clearing():
        """Test cache clearing functionality."""
        # Get some cached values
        get_path_manager().framework_root
        get_path_manager().project_root
        get_path_manager().get_config_dir("user")

        # Clear cache
        get_path_manager().clear_cache()

        # Verify cache was cleared by checking that new calls work
        # (if cache wasn't cleared properly, this would fail in some scenarios)
        get_path_manager().framework_root
        get_path_manager().project_root


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
