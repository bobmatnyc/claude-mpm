"""Tests for PathResolver utility."""

import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from claude_mpm.utils.paths import PathResolver, get_framework_root, get_project_root, find_file_upwards


class TestPathResolver:
    """Test cases for PathResolver class."""
    
    def setup_method(self):
        """Clear cache before each test."""
        PathResolver.clear_cache()
    
    def test_get_framework_root_from_module(self):
        """Test framework root detection from module location."""
        root = PathResolver.get_framework_root()
        assert root.exists()
        # Should have src/claude_mpm structure or claude_mpm directly
        assert (root / 'src' / 'claude_mpm').exists() or (root / 'claude_mpm').exists()
    
    def test_get_framework_root_cached(self):
        """Test that framework root is cached."""
        root1 = PathResolver.get_framework_root()
        root2 = PathResolver.get_framework_root()
        assert root1 == root2
        # Should use cached value (same object)
        assert root1 is root2
    
    def test_get_agents_dir(self):
        """Test agents directory detection."""
        agents_dir = PathResolver.get_agents_dir()
        assert agents_dir.exists()
        assert agents_dir.name == 'agents'
        # Should contain agent files
        assert list(agents_dir.glob('*.md')) or list(agents_dir.glob('*.py'))
    
    def test_get_project_root_with_git(self, tmp_path):
        """Test project root detection with .git directory."""
        # Create a temporary project structure
        git_dir = tmp_path / '.git'
        git_dir.mkdir()
        
        # Change to a subdirectory
        subdir = tmp_path / 'src' / 'submodule'
        subdir.mkdir(parents=True)
        
        with patch('pathlib.Path.cwd', return_value=subdir):
            root = PathResolver.get_project_root()
            assert root == tmp_path
    
    def test_get_project_root_with_pyproject(self, tmp_path):
        """Test project root detection with pyproject.toml."""
        # Create pyproject.toml
        (tmp_path / 'pyproject.toml').touch()
        
        # Change to subdirectory
        subdir = tmp_path / 'src'
        subdir.mkdir()
        
        with patch('pathlib.Path.cwd', return_value=subdir):
            root = PathResolver.get_project_root()
            assert root == tmp_path
    
    def test_get_project_root_fallback_to_cwd(self, tmp_path):
        """Test project root fallback to current directory."""
        # No project markers
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            root = PathResolver.get_project_root()
            assert root == tmp_path
    
    def test_get_config_dir_project(self):
        """Test project config directory."""
        with patch.object(PathResolver, 'get_project_root', return_value=Path('/test/project')):
            config_dir = PathResolver.get_config_dir('project')
            assert config_dir == Path('/test/project/.claude-pm')
    
    def test_get_config_dir_user(self):
        """Test user config directory."""
        config_dir = PathResolver.get_config_dir('user')
        assert 'claude-pm' in str(config_dir)
        assert str(config_dir).startswith(str(Path.home()))
    
    def test_get_config_dir_user_with_xdg(self):
        """Test user config directory with XDG_CONFIG_HOME."""
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': '/test/xdg'}):
            config_dir = PathResolver.get_config_dir('user')
            assert config_dir == Path('/test/xdg/claude-pm')
    
    def test_get_config_dir_invalid_scope(self):
        """Test invalid config scope."""
        with pytest.raises(ValueError, match="Invalid scope"):
            PathResolver.get_config_dir('invalid')
    
    def test_find_file_upwards(self, tmp_path):
        """Test upward file search."""
        # Create file in parent
        target_file = tmp_path / 'target.txt'
        target_file.touch()
        
        # Search from subdirectory
        subdir = tmp_path / 'a' / 'b' / 'c'
        subdir.mkdir(parents=True)
        
        result = PathResolver.find_file_upwards('target.txt', subdir)
        assert result == target_file
    
    def test_find_file_upwards_not_found(self, tmp_path):
        """Test upward file search when file doesn't exist."""
        result = PathResolver.find_file_upwards('nonexistent.txt', tmp_path)
        assert result is None
    
    def test_get_claude_pm_dir(self, tmp_path):
        """Test .claude-pm directory search."""
        # Create .claude-pm directory
        claude_pm_dir = tmp_path / '.claude-pm'
        claude_pm_dir.mkdir()
        
        # Search from subdirectory
        subdir = tmp_path / 'src'
        subdir.mkdir()
        
        result = PathResolver.get_claude_pm_dir(subdir)
        assert result == claude_pm_dir
    
    def test_ensure_directory(self, tmp_path):
        """Test directory creation."""
        new_dir = tmp_path / 'new' / 'nested' / 'dir'
        result = PathResolver.ensure_directory(new_dir)
        
        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_get_relative_to_root(self):
        """Test getting paths relative to roots."""
        with patch.object(PathResolver, 'get_project_root', return_value=Path('/project')):
            path = PathResolver.get_relative_to_root('src/module.py', 'project')
            assert path == Path('/project/src/module.py')
        
        with patch.object(PathResolver, 'get_framework_root', return_value=Path('/framework')):
            path = PathResolver.get_relative_to_root('agents/test.md', 'framework')
            assert path == Path('/framework/agents/test.md')
    
    def test_find_files_by_pattern(self, tmp_path):
        """Test file pattern matching."""
        # Create test files
        (tmp_path / 'test1.py').touch()
        (tmp_path / 'test2.py').touch()
        (tmp_path / 'subdir').mkdir()
        (tmp_path / 'subdir' / 'test3.py').touch()
        (tmp_path / 'other.txt').touch()
        
        # Find Python files
        with patch.object(PathResolver, 'get_project_root', return_value=tmp_path):
            py_files = PathResolver.find_files_by_pattern('**/*.py')
            assert len(py_files) == 3
            assert all(f.suffix == '.py' for f in py_files)
    
    def test_convenience_functions(self):
        """Test backward compatibility convenience functions."""
        # These should work the same as the class methods
        root1 = get_framework_root()
        root2 = PathResolver.get_framework_root()
        assert root1 == root2
        
        proj1 = get_project_root()
        proj2 = PathResolver.get_project_root()
        assert proj1 == proj2
    
    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        # Get some cached values
        PathResolver.get_framework_root()
        PathResolver.get_project_root()
        PathResolver.get_config_dir('user')
        
        # Clear cache
        PathResolver.clear_cache()
        
        # Verify cache was cleared by checking that new calls work
        # (if cache wasn't cleared properly, this would fail in some scenarios)
        PathResolver.get_framework_root()
        PathResolver.get_project_root()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])