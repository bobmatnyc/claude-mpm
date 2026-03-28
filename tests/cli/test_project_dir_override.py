"""Tests for --project-dir flag override of CLAUDE_MPM_USER_PWD.

Verifies the centralized post-parse override in _apply_project_dir_override()
correctly sets the environment variable and working directory.
"""

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory that exists on disk."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def original_env():
    """Save and restore CLAUDE_MPM_USER_PWD around each test."""
    old_value = os.environ.get("CLAUDE_MPM_USER_PWD")
    old_cwd = os.getcwd()
    yield
    if old_value is not None:
        os.environ["CLAUDE_MPM_USER_PWD"] = old_value
    elif "CLAUDE_MPM_USER_PWD" in os.environ:
        del os.environ["CLAUDE_MPM_USER_PWD"]
    os.chdir(old_cwd)


class TestProjectDirOverride:
    """Tests for _apply_project_dir_override."""

    def test_project_dir_sets_env_var(self, temp_dir, original_env):
        """--project-dir sets CLAUDE_MPM_USER_PWD to the resolved path."""
        from claude_mpm.cli import _apply_project_dir_override

        os.environ["CLAUDE_MPM_USER_PWD"] = "/original/path"
        args = SimpleNamespace(project_dir=str(temp_dir))

        _apply_project_dir_override(args)

        assert os.environ["CLAUDE_MPM_USER_PWD"] == str(temp_dir.resolve())

    def test_project_dir_changes_cwd(self, temp_dir, original_env):
        """--project-dir changes os.getcwd() to match."""
        from claude_mpm.cli import _apply_project_dir_override

        args = SimpleNamespace(project_dir=str(temp_dir))

        _apply_project_dir_override(args)

        assert os.getcwd() == str(temp_dir.resolve())

    def test_project_dir_not_set_uses_pwd(self, original_env):
        """Without --project-dir, CLAUDE_MPM_USER_PWD is unchanged."""
        from claude_mpm.cli import _apply_project_dir_override

        original = "/some/original/path"
        os.environ["CLAUDE_MPM_USER_PWD"] = original
        original_cwd = os.getcwd()

        # No project_dir attribute
        args = SimpleNamespace()
        _apply_project_dir_override(args)

        assert os.environ["CLAUDE_MPM_USER_PWD"] == original
        assert os.getcwd() == original_cwd

        # project_dir is None
        args = SimpleNamespace(project_dir=None)
        _apply_project_dir_override(args)

        assert os.environ["CLAUDE_MPM_USER_PWD"] == original
        assert os.getcwd() == original_cwd

    def test_project_dir_nonexistent_errors(self, original_env):
        """Non-existent --project-dir path causes sys.exit(1)."""
        from claude_mpm.cli import _apply_project_dir_override

        args = SimpleNamespace(project_dir="/nonexistent/path/that/does/not/exist")

        with pytest.raises(SystemExit) as exc_info:
            _apply_project_dir_override(args)

        assert exc_info.value.code == 1

    def test_project_dir_resolves_relative(self, temp_dir, original_env):
        """Relative --project-dir path is resolved to absolute."""
        from claude_mpm.cli import _apply_project_dir_override

        # Create a subdirectory
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        # Change to temp_dir so relative path works
        os.chdir(temp_dir)

        args = SimpleNamespace(project_dir="subdir")
        _apply_project_dir_override(args)

        result = os.environ["CLAUDE_MPM_USER_PWD"]
        assert os.path.isabs(result)
        assert result == str(subdir.resolve())
        assert os.getcwd() == str(subdir.resolve())
