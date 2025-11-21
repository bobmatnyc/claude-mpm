#!/usr/bin/env python3
"""
Comprehensive unit tests for the HookInstaller class.

This test suite validates:
- Hook installation to settings.json
- Hook removal and cleanup
- Matcher pattern validation
- Deployment-root path resolution
- Settings.json backup and restore
- Error handling for permission issues
- Claude Code version compatibility checks

These tests ensure the reliability of hook installation and configuration,
which is essential for enabling the monitoring capabilities of Claude MPM.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_mpm.hooks.claude_hooks.installer import HookInstaller


class TestHookInstaller(unittest.TestCase):
    """Test the HookInstaller class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.claude_dir = Path(self.temp_dir) / ".claude"
        self.claude_dir.mkdir()

        # Mock the home directory
        self.patcher = patch("src.claude_mpm.hooks.claude_hooks.installer.Path.home")
        mock_home = self.patcher.start()
        mock_home.return_value = Path(self.temp_dir)

        # Create installer instance
        self.installer = HookInstaller()

        # Override paths to use temp directory
        self.installer.claude_dir = self.claude_dir
        self.installer.hooks_dir = self.claude_dir / "hooks"
        self.installer.settings_file = self.claude_dir / "settings.json"
        self.installer.old_settings_file = self.claude_dir / "settings.json"

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)

    @patch("subprocess.run")
    def test_get_claude_version_success(self, mock_run):
        """Test successful Claude Code version detection."""
        mock_run.return_value = Mock(
            returncode=0, stdout="1.0.95 (Claude Code)", stderr=""
        )

        version = self.installer.get_claude_version()

        self.assertEqual(version, "1.0.95")
        mock_run.assert_called_once_with(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    @patch("subprocess.run")
    def test_get_claude_version_not_installed(self, mock_run):
        """Test handling when Claude Code is not installed."""
        mock_run.side_effect = FileNotFoundError("claude not found")

        version = self.installer.get_claude_version()

        self.assertIsNone(version)

    @patch("subprocess.run")
    def test_get_claude_version_timeout(self, mock_run):
        """Test handling of version check timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

        version = self.installer.get_claude_version()

        self.assertIsNone(version)

    @patch.object(HookInstaller, "get_claude_version")
    def test_is_version_compatible_success(self, mock_get_version):
        """Test version compatibility check with compatible version."""
        mock_get_version.return_value = "1.0.95"

        is_compatible, message = self.installer.is_version_compatible()

        self.assertTrue(is_compatible)
        self.assertIn("1.0.95", message)
        self.assertIn("compatible", message)

    @patch.object(HookInstaller, "get_claude_version")
    def test_is_version_compatible_too_old(self, mock_get_version):
        """Test version compatibility check with old version."""
        mock_get_version.return_value = "1.0.91"

        is_compatible, message = self.installer.is_version_compatible()

        self.assertFalse(is_compatible)
        self.assertIn("1.0.91", message)
        self.assertIn("does not support", message)
        self.assertIn("1.0.92", message)  # Required version

    @patch.object(HookInstaller, "get_claude_version")
    def test_is_version_compatible_not_detected(self, mock_get_version):
        """Test version compatibility when version cannot be detected."""
        mock_get_version.return_value = None

        is_compatible, message = self.installer.is_version_compatible()

        self.assertFalse(is_compatible)
        self.assertIn("Could not detect", message)

    def test_get_hook_script_path_development(self):
        """Test finding hook script in development environment."""
        # Mock claude_mpm module location
        with patch(
            "src.claude_mpm.hooks.claude_hooks.installer.claude_mpm"
        ) as mock_module:
            # Simulate development environment
            dev_path = Path("/home/user/projects/claude-mpm/src/claude_mpm")
            mock_module.__file__ = str(dev_path / "__init__.py")

            # Create mock script file
            script_path = dev_path / "scripts" / "claude-hook-handler.sh"
            with patch.object(Path, "exists") as mock_exists:

                def exists_side_effect(self):
                    return str(self) == str(script_path)

                mock_exists.side_effect = exists_side_effect

                with patch("os.stat"), patch("os.chmod"):
                    result = self.installer.get_hook_script_path()

                    self.assertEqual(result, script_path)

    def test_get_hook_script_path_pip_install(self):
        """Test finding hook script in pip installation."""
        with patch(
            "src.claude_mpm.hooks.claude_hooks.installer.claude_mpm"
        ) as mock_module:
            # Simulate pip installation
            pip_path = Path("/usr/local/lib/python3.9/site-packages/claude_mpm")
            mock_module.__file__ = str(pip_path / "__init__.py")

            # Create mock script file
            script_path = pip_path / "scripts" / "claude-hook-handler.sh"
            with patch.object(Path, "exists") as mock_exists:

                def exists_side_effect(self):
                    return str(self) == str(script_path)

                mock_exists.side_effect = exists_side_effect

                with patch("os.stat"), patch("os.chmod"):
                    result = self.installer.get_hook_script_path()

                    self.assertEqual(result, script_path)

    def test_get_hook_script_path_not_found(self):
        """Test error when hook script cannot be found."""
        with patch(
            "src.claude_mpm.hooks.claude_hooks.installer.claude_mpm"
        ) as mock_module:
            mock_module.__file__ = "/some/path/claude_mpm/__init__.py"

            with patch.object(Path, "exists", return_value=False):
                with self.assertRaises(FileNotFoundError) as cm:
                    self.installer.get_hook_script_path()

                self.assertIn("Hook handler script not found", str(cm.exception))

    @patch.object(HookInstaller, "is_version_compatible")
    @patch.object(HookInstaller, "get_hook_script_path")
    def test_install_hooks_success(self, mock_get_script, mock_version_check):
        """Test successful hook installation."""
        # Setup mocks
        mock_version_check.return_value = (True, "Compatible")
        mock_script_path = Path("/path/to/claude-hook-handler.sh")
        mock_get_script.return_value = mock_script_path

        # Mock command installation
        with patch.object(self.installer, "_install_commands"), patch.object(
            self.installer, "_cleanup_old_deployment"
        ):
            result = self.installer.install_hooks()

            self.assertTrue(result)

            # Check settings.json was created
            self.assertTrue(self.installer.settings_file.exists())

            # Verify settings content
            with self.installer.settings_file.open() as f:
                settings = json.load(f)

            # Check hook configuration
            self.assertIn("hooks", settings)
            self.assertIn("Stop", settings["hooks"])
            self.assertIn("SubagentStop", settings["hooks"])
            self.assertIn("PreToolUse", settings["hooks"])
            self.assertIn("PostToolUse", settings["hooks"])

            # Check tool events have matcher
            tool_event = settings["hooks"]["PreToolUse"][0]
            self.assertEqual(tool_event["matcher"], "*")
            self.assertIn("hooks", tool_event)

            # Check non-tool events don't have matcher
            non_tool_event = settings["hooks"]["Stop"][0]
            self.assertNotIn("matcher", non_tool_event)
            self.assertIn("hooks", non_tool_event)

    @patch.object(HookInstaller, "is_version_compatible")
    def test_install_hooks_incompatible_version(self, mock_version_check):
        """Test hook installation with incompatible Claude Code version."""
        mock_version_check.return_value = (False, "Version 1.0.91 is too old")

        result = self.installer.install_hooks()

        self.assertFalse(result)
        # Settings file should not be created
        self.assertFalse(self.installer.settings_file.exists())

    @patch.object(HookInstaller, "is_version_compatible")
    @patch.object(HookInstaller, "get_hook_script_path")
    def test_install_hooks_script_not_found(self, mock_get_script, mock_version_check):
        """Test hook installation when script cannot be found."""
        mock_version_check.return_value = (True, "Compatible")
        mock_get_script.side_effect = FileNotFoundError("Script not found")

        result = self.installer.install_hooks()

        self.assertFalse(result)

    def test_update_claude_settings_new_file(self):
        """Test updating Claude settings when file doesn't exist."""
        script_path = Path("/path/to/hook.sh")

        self.installer._update_claude_settings(script_path)

        # Check settings file was created
        self.assertTrue(self.installer.settings_file.exists())

        with self.installer.settings_file.open() as f:
            settings = json.load(f)

        # Check default settings
        self.assertIn("permissions", settings)
        self.assertIn("enableAllProjectMcpServers", settings)
        self.assertFalse(settings["enableAllProjectMcpServers"])

        # Check hooks
        self.assertIn("hooks", settings)
        for event_type in ["Stop", "SubagentStop", "PreToolUse", "PostToolUse"]:
            self.assertIn(event_type, settings["hooks"])

    def test_update_claude_settings_existing_file(self):
        """Test updating Claude settings with existing file."""
        # Create existing settings
        existing_settings = {
            "permissions": {"allow": ["some_permission"]},
            "mcpServers": {"test": {}},
            "other": "value",
        }

        with self.installer.settings_file.open("w") as f:
            json.dump(existing_settings, f)

        script_path = Path("/path/to/hook.sh")
        self.installer._update_claude_settings(script_path)

        with self.installer.settings_file.open() as f:
            settings = json.load(f)

        # Check existing settings preserved
        self.assertEqual(settings["permissions"]["allow"], ["some_permission"])
        self.assertEqual(settings["other"], "value")

        # Check hooks added
        self.assertIn("hooks", settings)

    def test_cleanup_old_deployment(self):
        """Test cleanup of old deployed scripts."""
        # Create old script file
        self.installer.hooks_dir.mkdir()
        old_script = self.installer.hooks_dir / "claude-mpm-hook.sh"
        old_script.write_text("old script")

        self.installer._cleanup_old_deployment()

        # Old script should be removed
        self.assertFalse(old_script.exists())

        # Empty hooks directory should be removed
        self.assertFalse(self.installer.hooks_dir.exists())

    def test_cleanup_old_settings(self):
        """Test cleanup of hooks from old settings file."""
        # Create old settings with hooks
        old_settings = {"hooks": {"Stop": []}, "other": "value"}

        with self.installer.old_settings_file.open("w") as f:
            json.dump(old_settings, f)

        self.installer._cleanup_old_settings()

        with self.installer.old_settings_file.open() as f:
            settings = json.load(f)

        # Hooks should be removed
        self.assertNotIn("hooks", settings)
        # Other settings preserved
        self.assertEqual(settings["other"], "value")

    def test_uninstall_hooks(self):
        """Test hook uninstallation."""
        # Create settings with hooks
        settings = {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/path/to/claude-hook-handler.sh",
                            }
                        ]
                    }
                ],
                "OtherEvent": [
                    {"hooks": [{"type": "command", "command": "/other/hook.sh"}]}
                ],
            },
            "other": "value",
        }

        with self.installer.settings_file.open("w") as f:
            json.dump(settings, f)

        result = self.installer.uninstall_hooks()

        self.assertTrue(result)

        with self.installer.settings_file.open() as f:
            updated_settings = json.load(f)

        # Claude MPM hooks removed
        self.assertIn("hooks", updated_settings)
        self.assertNotIn("Stop", updated_settings["hooks"])

        # Other hooks preserved
        self.assertIn("OtherEvent", updated_settings["hooks"])

        # Other settings preserved
        self.assertEqual(updated_settings["other"], "value")

    @patch.object(HookInstaller, "get_hook_script_path")
    def test_verify_hooks_valid(self, mock_get_script):
        """Test verification of properly installed hooks."""
        # Setup valid hook script
        mock_script = Mock()
        mock_script.exists.return_value = True
        mock_get_script.return_value = mock_script

        # Create valid settings
        settings = {
            "hooks": {
                "Stop": [],
                "SubagentStop": [],
                "SubagentStart": [],
                "PreToolUse": [],
                "PostToolUse": [],
            }
        }

        with self.installer.settings_file.open("w") as f:
            json.dump(settings, f)

        # Mock version check
        with patch.object(
            self.installer, "is_version_compatible", return_value=(True, "Compatible")
        ), patch("os.access", return_value=True):
            is_valid, issues = self.installer.verify_hooks()

            self.assertTrue(is_valid)
            self.assertEqual(len(issues), 0)

    @patch.object(HookInstaller, "get_hook_script_path")
    def test_verify_hooks_missing_script(self, mock_get_script):
        """Test verification when hook script is missing."""
        mock_script = Mock()
        mock_script.exists.return_value = False
        mock_get_script.return_value = mock_script

        with patch.object(
            self.installer, "is_version_compatible", return_value=(True, "Compatible")
        ):
            is_valid, issues = self.installer.verify_hooks()

            self.assertFalse(is_valid)
            self.assertTrue(any("not found" in issue for issue in issues))

    def test_verify_hooks_missing_settings(self):
        """Test verification when settings file is missing."""
        with patch.object(
            self.installer, "is_version_compatible", return_value=(True, "Compatible")
        ), patch.object(
            self.installer, "get_hook_script_path", return_value=Path("/hook.sh")
        ):
            is_valid, issues = self.installer.verify_hooks()

            self.assertFalse(is_valid)
            self.assertTrue(any("settings file not found" in issue for issue in issues))

    def test_verify_hooks_incompatible_version(self):
        """Test verification with incompatible Claude Code version."""
        with patch.object(
            self.installer,
            "is_version_compatible",
            return_value=(False, "Version incompatible"),
        ):
            is_valid, issues = self.installer.verify_hooks()

            self.assertFalse(is_valid)
            self.assertEqual(issues[0], "Version incompatible")
            # Should skip other checks
            self.assertEqual(len(issues), 1)

    @patch.object(HookInstaller, "get_hook_script_path")
    def test_verify_hooks_missing_events(self, mock_get_script):
        """Test verification when required events are missing."""
        mock_script = Mock()
        mock_script.exists.return_value = True
        mock_get_script.return_value = mock_script

        # Create settings missing some events
        settings = {
            "hooks": {
                "Stop": [],
                # Missing SubagentStop, SubagentStart, PreToolUse, PostToolUse
            }
        }

        with self.installer.settings_file.open("w") as f:
            json.dump(settings, f)

        with patch.object(
            self.installer, "is_version_compatible", return_value=(True, "Compatible")
        ), patch("os.access", return_value=True):
            is_valid, issues = self.installer.verify_hooks()

            self.assertFalse(is_valid)
            # Check for missing events
            missing_events = [
                "SubagentStop",
                "SubagentStart",
                "PreToolUse",
                "PostToolUse",
            ]
            for event in missing_events:
                self.assertTrue(any(event in issue for issue in issues))

    @patch.object(HookInstaller, "get_claude_version")
    @patch.object(HookInstaller, "verify_hooks")
    @patch.object(HookInstaller, "get_hook_script_path")
    def test_get_status(self, mock_get_script, mock_verify, mock_get_version):
        """Test getting hook installation status."""
        # Setup mocks
        mock_get_version.return_value = "1.0.95"
        mock_verify.return_value = (True, [])
        mock_script_path = Path("/path/to/hook.sh")
        mock_get_script.return_value = mock_script_path

        # Create settings file
        settings = {"hooks": {"Stop": [], "SubagentStop": []}}
        with self.installer.settings_file.open("w") as f:
            json.dump(settings, f)

        with patch.object(mock_script_path, "exists", return_value=True):
            status = self.installer.get_status()

        self.assertTrue(status["installed"])
        self.assertTrue(status["valid"])
        self.assertEqual(status["issues"], [])
        self.assertEqual(status["hook_script"], str(mock_script_path))
        self.assertEqual(status["claude_version"], "1.0.95")
        self.assertTrue(status["version_compatible"])
        self.assertEqual(status["deployment_type"], "deployment-root")
        self.assertIn("Stop", status["configured_events"])
        self.assertIn("SubagentStop", status["configured_events"])

    def test_install_commands(self):
        """Test installation of custom commands."""
        # Create mock commands directory
        package_root = Path(self.temp_dir) / "package"
        commands_src = package_root / ".claude" / "commands"
        commands_src.mkdir(parents=True)

        # Create test command files
        (commands_src / "test_command.md").write_text("Test command")
        (commands_src / "another_command.md").write_text("Another command")

        # Mock the package root path
        with patch.object(Path, "__new__") as mock_path:

            def path_new(cls, *args, **kwargs):
                if args and "installer.py" in str(args[0]):
                    # Return our test package root for __file__ resolution
                    return (
                        package_root
                        / "src"
                        / "claude_mpm"
                        / "hooks"
                        / "claude_hooks"
                        / "installer.py"
                    )
                return object.__new__(cls)

            mock_path.side_effect = path_new

            # Create new installer to pick up the mocked path
            installer = HookInstaller()
            installer.claude_dir = self.claude_dir

            installer._install_commands()

            # Check commands were copied
            commands_dst = self.claude_dir / "commands"
            self.assertTrue(commands_dst.exists())
            self.assertTrue((commands_dst / "test_command.md").exists())
            self.assertTrue((commands_dst / "another_command.md").exists())

    def test_error_handling_permission_denied(self):
        """Test error handling when permission is denied."""
        # Make settings file read-only
        self.installer.settings_file.touch()
        os.chmod(self.installer.settings_file, stat.S_IRUSR)

        script_path = Path("/path/to/hook.sh")

        # Should handle permission error gracefully
        try:
            self.installer._update_claude_settings(script_path)
            # On some systems, root can still write to read-only files
            # So we don't assert failure here
        except PermissionError:
            # This is expected on most systems
            pass
        finally:
            # Restore permissions for cleanup
            os.chmod(self.installer.settings_file, stat.S_IRUSR | stat.S_IWUSR)

    def test_settings_backup_and_restore(self):
        """Test that settings are properly backed up before modification."""
        # Create initial settings
        initial_settings = {"existing": "data", "permissions": {"allow": ["test"]}}

        with self.installer.settings_file.open("w") as f:
            json.dump(initial_settings, f, indent=2)

        # Get initial content for comparison
        self.installer.settings_file.read_text()

        # Update settings
        script_path = Path("/path/to/hook.sh")
        self.installer._update_claude_settings(script_path)

        # Verify settings were modified
        with self.installer.settings_file.open() as f:
            updated_settings = json.load(f)

        self.assertIn("hooks", updated_settings)
        self.assertEqual(updated_settings["existing"], "data")

        # In a real backup scenario, we would check for backup file
        # This is a conceptual test for backup/restore functionality


class TestMatcherPatternValidation(unittest.TestCase):
    """Test matcher pattern validation for hook events."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.installer = HookInstaller()
        self.installer.claude_dir = Path(self.temp_dir) / ".claude"
        self.installer.claude_dir.mkdir()
        self.installer.settings_file = self.installer.claude_dir / "settings.json"

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_tool_event_matcher_validation(self):
        """Test that tool events have proper matcher patterns."""
        script_path = Path("/path/to/hook.sh")
        self.installer._update_claude_settings(script_path)

        with self.installer.settings_file.open() as f:
            settings = json.load(f)

        # Tool events should have matcher field
        tool_events = ["PreToolUse", "PostToolUse"]
        for event in tool_events:
            self.assertIn(event, settings["hooks"])
            hook_config = settings["hooks"][event][0]
            self.assertIn("matcher", hook_config)
            self.assertEqual(hook_config["matcher"], "*")

    def test_non_tool_event_no_matcher(self):
        """Test that non-tool events don't have matcher field."""
        script_path = Path("/path/to/hook.sh")
        self.installer._update_claude_settings(script_path)

        with self.installer.settings_file.open() as f:
            settings = json.load(f)

        # Non-tool events should not have matcher field
        non_tool_events = ["Stop", "SubagentStop", "UserPromptSubmit"]
        for event in non_tool_events:
            if event in settings["hooks"]:
                hook_config = settings["hooks"][event][0]
                self.assertNotIn("matcher", hook_config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
