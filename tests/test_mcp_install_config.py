#!/usr/bin/env python3
"""Test MCP installation configuration.

WHY: Ensures that the MCP installation always configures Claude Code
with the correct claude-mpm command, not the old Python script approach.

DESIGN DECISION: We test all possible scenarios for finding the claude-mpm
executable to ensure robust configuration across different environments.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.mcp_install_commands import MCPInstallCommands


class TestMCPInstallConfig(unittest.TestCase):
    """Test MCP installation configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = MagicMock()
        self.installer = MCPInstallCommands(self.logger)

    def test_find_claude_mpm_in_path():
        """Test finding claude-mpm in system PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/claude-mpm"

            result = self.installer._find_claude_mpm_executable()

            self.assertEqual(result, "/usr/local/bin/claude-mpm")
            mock_which.assert_called_once_with("claude-mpm")

    def test_find_claude_mpm_in_venv():
        """Test finding claude-mpm in virtual environment."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            # Mock virtual environment detection
            with patch("sys.prefix", "/path/to/venv"):
                with patch("sys.base_prefix", "/usr"):
                    with patch("pathlib.Path.exists") as mock_exists:
                        mock_exists.return_value = True

                        result = self.installer._find_claude_mpm_executable()

                        expected = str(Path("/path/to/venv") / "bin" / "claude-mpm")
                        self.assertEqual(result, expected)

    def test_find_claude_mpm_python_module():
        """Test falling back to Python module when executable not found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            # Mock no venv by setting prefix == base_prefix
            original_prefix = sys.prefix
            sys.prefix = sys.base_prefix

            try:
                # Mock Path to return False for all exists() checks
                with patch.object(Path, "exists", return_value=False):
                    # Mock claude_mpm module exists - this makes the import succeed
                    with patch.dict("sys.modules", {"claude_mpm": MagicMock()}):
                        result = self.installer._find_claude_mpm_executable()

                        # When falling back to Python module, it returns sys.executable
                        self.assertEqual(result, sys.executable)
            finally:
                sys.prefix = original_prefix

    def test_configure_with_direct_command():
        """Test configuration with direct claude-mpm command."""
        with tmp_path as tmpdir:
            config_path = Path(tmpdir) / "settings.local.json"

            with patch.object(
                self.installer, "_get_claude_config_path", return_value=config_path
            ), patch.object(
                self.installer,
                "_find_claude_mpm_executable",
                return_value="/usr/local/bin/claude-mpm",
            ):
                success = self.installer._configure_claude_desktop(force=True)

                self.assertTrue(success)

                # Verify configuration
                with config_path.open() as f:
                    config = json.load(f)

                mcp_config = config["mcpServers"]["claude-mpm-gateway"]
                self.assertEqual(mcp_config["command"], "/usr/local/bin/claude-mpm")
                self.assertEqual(mcp_config["args"], ["mcp", "server"])
                self.assertIn("PYTHONPATH", mcp_config["env"])
                self.assertEqual(mcp_config["env"]["MCP_MODE"], "production")

    def test_configure_with_python_module():
        """Test configuration when using Python -m claude_mpm."""
        with tmp_path as tmpdir:
            config_path = Path(tmpdir) / "settings.local.json"

            with patch.object(
                self.installer, "_get_claude_config_path", return_value=config_path
            ), patch.object(
                self.installer,
                "_find_claude_mpm_executable",
                return_value=sys.executable,
            ):
                success = self.installer._configure_claude_desktop(force=True)

                self.assertTrue(success)

                # Verify configuration
                with config_path.open() as f:
                    config = json.load(f)

                mcp_config = config["mcpServers"]["claude-mpm-gateway"]
                self.assertEqual(mcp_config["command"], sys.executable)
                self.assertEqual(
                    mcp_config["args"], ["-m", "claude_mpm", "mcp", "server"]
                )
                self.assertIn("PYTHONPATH", mcp_config["env"])
                self.assertEqual(mcp_config["env"]["MCP_MODE"], "production")

    def test_never_uses_script_path():
        """Test that configuration never uses the old scripts/mcp_server.py path."""
        with tmp_path as tmpdir:
            config_path = Path(tmpdir) / "settings.local.json"

            # Test with various executable paths
            test_paths = [
                "/usr/local/bin/claude-mpm",
                "/path/to/venv/bin/claude-mpm",
                sys.executable,  # Python for -m usage
            ]

            for test_path in test_paths:
                with patch.object(
                    self.installer, "_get_claude_config_path", return_value=config_path
                ), patch.object(
                    self.installer,
                    "_find_claude_mpm_executable",
                    return_value=test_path,
                ):
                    success = self.installer._configure_claude_desktop(force=True)
                    self.assertTrue(success)

                    # Verify configuration never contains script path
                    with config_path.open() as f:
                        config_json = f.read()

                    self.assertNotIn("mcp_server.py", config_json)
                    self.assertNotIn("scripts/", config_json)

                    # Verify it uses proper command
                    config = json.loads(config_json)
                    mcp_config = config["mcpServers"]["claude-mpm-gateway"]

                    # Command should either be claude-mpm executable or python
                    self.assertTrue(
                        "claude-mpm" in mcp_config["command"]
                        or "python" in mcp_config["command"].lower()
                    )


if __name__ == "__main__":
    unittest.main()
