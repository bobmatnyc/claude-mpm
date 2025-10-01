"""Tests for deployment-root hook installation."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.hooks.claude_hooks.installer import HookInstaller


class TestDeploymentRootHooks:
    """Test the deployment-root hook installation."""

    def test_get_hook_script_path_development(self):
        """Test finding hook script in development environment."""
        installer = HookInstaller()

        # Mock claude_mpm to simulate development structure
        with patch(
            "claude_mpm.__file__", "/path/to/project/src/claude_mpm/__init__.py"
        ), patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = True
            # Mock os.stat and os.chmod for executable check
            with patch("os.stat", return_value=MagicMock(st_mode=0o755)):
                with patch("os.chmod"):
                    path = installer.get_hook_script_path()

                    assert "scripts/claude-hook-handler.sh" in str(path)
                    assert "/src/claude_mpm/scripts/" in str(path)

    def test_get_hook_script_path_pip_install(self):
        """Test finding hook script in pip installation."""
        installer = HookInstaller()

        # Mock claude_mpm to simulate pip install structure
        with patch(
            "claude_mpm.__file__",
            "/usr/local/lib/python3.11/site-packages/claude_mpm/__init__.py",
        ), patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = True
            # Mock os.stat and os.chmod for executable check
            with patch("os.stat", return_value=MagicMock(st_mode=0o755)):
                with patch("os.chmod"):
                    path = installer.get_hook_script_path()

                    assert "scripts/claude-hook-handler.sh" in str(path)
                    assert "site-packages/claude_mpm/scripts/" in str(path)

    def test_get_hook_script_path_not_found(self):
        """Test error when hook script is not found."""
        installer = HookInstaller()

        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError) as exc_info:
                installer.get_hook_script_path()

            assert "Hook handler script not found" in str(exc_info.value)

    def test_install_hooks_uses_deployment_root(self, tmp_path):
        """Test that install_hooks uses deployment-root script."""
        installer = HookInstaller()

        # Create a temporary Claude directory
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        installer.claude_dir = claude_dir
        installer.settings_file = claude_dir / "settings.json"

        # Mock version check to be compatible
        installer.is_version_compatible = MagicMock(return_value=(True, "Compatible"))

        # Mock get_hook_script_path
        mock_script_path = Path(
            "/path/to/src/claude_mpm/scripts/claude-hook-handler.sh"
        )
        installer.get_hook_script_path = MagicMock(return_value=mock_script_path)

        # Mock _install_commands and _cleanup_old_deployment
        installer._install_commands = MagicMock()
        installer._cleanup_old_deployment = MagicMock()

        # Run installation
        result = installer.install_hooks()

        assert result is True
        installer.get_hook_script_path.assert_called_once()
        installer._cleanup_old_deployment.assert_called_once()

        # Check settings were updated
        assert installer.settings_file.exists()
        with installer.settings_file.open() as f:
            settings = json.load(f)

        assert "hooks" in settings

        # Check that hooks point to deployment-root script
        for event_type in ["Stop", "SubagentStop", "PreToolUse"]:
            if event_type in settings["hooks"]:
                for config in settings["hooks"][event_type]:
                    if "hooks" in config:
                        for hook in config["hooks"]:
                            if hook.get("type") == "command":
                                assert hook["command"] == str(mock_script_path)

    def test_cleanup_old_deployment(self, tmp_path):
        """Test cleanup of old deployed scripts."""
        installer = HookInstaller()

        # Create temporary hooks directory with old script
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        old_script = hooks_dir / "claude-mpm-hook.sh"
        old_script.write_text("#!/bin/bash\n# Old script")

        installer.hooks_dir = hooks_dir

        # Run cleanup
        installer._cleanup_old_deployment()

        # Check old script was removed
        assert not old_script.exists()
        # Check empty directory was removed
        assert not hooks_dir.exists()

    def test_verify_hooks_with_deployment_root(self):
        """Test hook verification with deployment-root script."""
        installer = HookInstaller()

        # Mock version compatibility
        installer.is_version_compatible = MagicMock(return_value=(True, "Compatible"))

        # Mock get_hook_script_path
        mock_script_path = MagicMock()
        mock_script_path.exists.return_value = True
        installer.get_hook_script_path = MagicMock(return_value=mock_script_path)

        # Mock os.access for executable check
        with patch("os.access", return_value=True):
            # Mock settings file
            installer.settings_file = MagicMock()
            installer.settings_file.exists.return_value = True

            # Mock settings content
            mock_settings = {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {"type": "command", "command": str(mock_script_path)}
                            ]
                        }
                    ],
                    "SubagentStop": [
                        {
                            "hooks": [
                                {"type": "command", "command": str(mock_script_path)}
                            ]
                        }
                    ],
                    "SubagentStart": [
                        {
                            "hooks": [
                                {"type": "command", "command": str(mock_script_path)}
                            ]
                        }
                    ],
                    "PreToolUse": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {"type": "command", "command": str(mock_script_path)}
                            ],
                        }
                    ],
                    "PostToolUse": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {"type": "command", "command": str(mock_script_path)}
                            ],
                        }
                    ],
                }
            }

            with patch("builtins.open", create=True):
                with patch("json.load", return_value=mock_settings):
                    is_valid, issues = installer.verify_hooks()

            assert is_valid is True
            assert len(issues) == 0

    def test_get_status_shows_deployment_type(self):
        """Test that status includes deployment type."""
        installer = HookInstaller()

        # Mock everything needed for status
        installer.get_claude_version = MagicMock(return_value="1.0.92")
        installer.is_version_compatible = MagicMock(return_value=(True, "Compatible"))

        mock_script_path = MagicMock()
        mock_script_path.exists.return_value = True
        installer.get_hook_script_path = MagicMock(return_value=mock_script_path)

        installer.verify_hooks = MagicMock(return_value=(True, []))
        installer.settings_file = MagicMock()
        installer.settings_file.exists.return_value = True

        with patch("builtins.open", create=True):
            with patch("json.load", return_value={"hooks": {}}):
                status = installer.get_status()

        assert status["deployment_type"] == "deployment-root"
        assert status["hook_script"] == str(mock_script_path)
        assert status["installed"] is True
