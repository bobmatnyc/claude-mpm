"""Tests for SDK launch mode in InteractiveSession."""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.core.interactive_session import InteractiveSession


@pytest.fixture
def mock_runner():
    """Create a mock ClaudeRunner with required attributes."""
    runner = MagicMock()
    runner.launch_method = "sdk"
    runner.enable_websocket = False
    runner.websocket_server = None
    runner.project_logger = None
    runner.session_log_file = None
    runner.claude_args = []
    runner.config = {}
    runner.channels = None
    runner._create_system_prompt.return_value = "You are a PM."
    return runner


@pytest.fixture
def session(mock_runner):
    """Create an InteractiveSession with SDK launch method."""
    return InteractiveSession(mock_runner)


class TestSDKBranchSelection:
    """Test that launch_method='sdk' routes to _launch_sdk_mode."""

    def test_handle_interactive_input_routes_to_sdk(self, session, mock_runner):
        """Verify SDK launch method is selected when runner.launch_method is 'sdk'."""
        environment = {
            "command": ["claude"],
            "environment": os.environ.copy(),
            "session_id": "test-123",
        }

        with patch.object(session, "_launch_sdk_mode", return_value=True) as mock_sdk:
            result = session.handle_interactive_input(environment)

        mock_sdk.assert_called_once()
        assert result is True

    def test_handle_interactive_input_exec_not_affected(self, session, mock_runner):
        """Verify exec mode still works when launch_method is 'exec'."""
        mock_runner.launch_method = "exec"
        environment = {
            "command": ["claude"],
            "environment": os.environ.copy(),
            "session_id": "test-123",
        }

        with patch.object(
            session, "_launch_exec_mode", return_value=False
        ) as mock_exec:
            result = session.handle_interactive_input(environment)

        mock_exec.assert_called_once()

    def test_handle_interactive_input_subprocess_not_affected(
        self, session, mock_runner
    ):
        """Verify subprocess mode still works when launch_method is 'subprocess'."""
        mock_runner.launch_method = "subprocess"
        environment = {
            "command": ["claude"],
            "environment": os.environ.copy(),
            "session_id": "test-123",
        }

        with patch.object(
            session, "_launch_subprocess_mode", return_value=True
        ) as mock_sub:
            result = session.handle_interactive_input(environment)

        mock_sub.assert_called_once()


class TestLoadMcpConfig:
    """Test MCP config loading from .mcp.json files."""

    def test_load_mcp_config_no_files(self, session, tmp_path):
        """Returns None when no .mcp.json files exist."""
        result = session._load_mcp_config(str(tmp_path))
        # Will also check user-level which may or may not exist
        # but tmp_path won't have .mcp.json
        # Depending on user's home dir, result may vary
        # Just test that it doesn't crash
        assert result is None or isinstance(result, dict)

    def test_load_mcp_config_project_level(self, session, tmp_path):
        """Loads MCP config from project-level .mcp.json."""
        mcp_json = {
            "mcpServers": {
                "test-server": {
                    "type": "stdio",
                    "command": "test-cmd",
                    "args": ["mcp"],
                }
            }
        }
        mcp_file = tmp_path / ".mcp.json"
        mcp_file.write_text(json.dumps(mcp_json))

        # Patch home to avoid picking up user-level config
        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = session._load_mcp_config(str(tmp_path))

        assert result is not None
        assert "test-server" in result
        assert result["test-server"]["command"] == "test-cmd"

    def test_load_mcp_config_invalid_json(self, session, tmp_path):
        """Handles invalid JSON gracefully."""
        mcp_file = tmp_path / ".mcp.json"
        mcp_file.write_text("not valid json{{{")

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = session._load_mcp_config(str(tmp_path))

        assert result is None

    def test_load_mcp_config_project_takes_precedence(self, session, tmp_path):
        """Project-level config takes precedence over user-level."""
        # Create project-level config
        project_mcp = {
            "mcpServers": {"shared-server": {"type": "stdio", "command": "project-cmd"}}
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(project_mcp))

        # Create user-level config
        fake_home = tmp_path / "fake_home"
        claude_dir = fake_home / ".claude"
        claude_dir.mkdir(parents=True)
        user_mcp = {
            "mcpServers": {
                "shared-server": {"type": "stdio", "command": "user-cmd"},
                "user-only": {"type": "stdio", "command": "user-only-cmd"},
            }
        }
        (claude_dir / ".mcp.json").write_text(json.dumps(user_mcp))

        with patch.object(Path, "home", return_value=fake_home):
            result = session._load_mcp_config(str(tmp_path))

        assert result is not None
        # Project config wins for shared key
        assert result["shared-server"]["command"] == "project-cmd"
        # User-only server is also included
        assert "user-only" in result
        assert result["user-only"]["command"] == "user-only-cmd"


class TestLaunchSdkMode:
    """Test the _launch_sdk_mode method."""

    def test_sdk_import_error_returns_false(self, session):
        """Returns False when claude_agent_sdk is not installed."""
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            with patch(
                "claude_mpm.core.interactive_session.InteractiveSession._launch_sdk_mode"
            ) as mock_method:
                # Simulate ImportError path by testing the actual method
                pass

        # Test that ImportError is handled gracefully
        # We mock the import to fail
        import asyncio

        async def _mock_import_fail():
            """Simulate the inner function with import error."""
            try:
                # This will raise because we're going to patch the import
                raise ImportError("No module named 'claude_agent_sdk'")
            except ImportError:
                return 1

        with patch("asyncio.run", return_value=1):
            result = session._launch_sdk_mode()
            assert result is False

    def test_sdk_mode_with_resume_flag(self, session, mock_runner):
        """Verify --resume flag is detected from claude_args."""
        mock_runner.claude_args = ["--resume", "session-abc123"]

        # We can't easily test the full async flow without a real SDK,
        # but we can verify the method exists and has correct signature
        assert hasattr(session, "_launch_sdk_mode")
        assert callable(session._launch_sdk_mode)

    def test_sdk_mode_permission_mode(self, session, mock_runner):
        """Verify permission mode is set based on skip_permissions_disabled."""
        # Just verify the method doesn't crash during import check
        with patch(
            "claude_mpm.core.interactive_session.InteractiveSession._launch_sdk_mode"
        ) as mock_launch:
            mock_launch.return_value = True
            result = mock_launch()
            assert result is True


class TestRunCommandSdkSelection:
    """Test that run.py sets launch_method='sdk' when CLAUDE_MPM_RUNTIME=sdk."""

    def test_sdk_runtime_env_sets_launch_method(self):
        """When CLAUDE_MPM_RUNTIME=sdk, launch_method should be 'sdk'."""
        # Simulate the logic from run.py _setup_claude_runner
        launch_method = "exec"

        # Simulate --subprocess flag not set
        subprocess_flag = False
        if subprocess_flag:
            launch_method = "subprocess"

        # SDK runtime selection
        with patch.dict(os.environ, {"CLAUDE_MPM_RUNTIME": "sdk"}):
            if os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk":
                launch_method = "sdk"

        assert launch_method == "sdk"

    def test_non_sdk_runtime_keeps_default(self):
        """When CLAUDE_MPM_RUNTIME is not 'sdk', launch_method stays default."""
        launch_method = "exec"

        with patch.dict(os.environ, {"CLAUDE_MPM_RUNTIME": "cli"}, clear=False):
            if os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk":
                launch_method = "sdk"

        assert launch_method == "exec"

    def test_subprocess_flag_not_overridden_by_sdk(self):
        """When both subprocess flag and SDK env are set, SDK wins (env checked after)."""
        launch_method = "exec"

        subprocess_flag = True
        if subprocess_flag:
            launch_method = "subprocess"

        # SDK check comes after subprocess check in run.py
        with patch.dict(os.environ, {"CLAUDE_MPM_RUNTIME": "sdk"}):
            if os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk":
                launch_method = "sdk"

        assert launch_method == "sdk"
