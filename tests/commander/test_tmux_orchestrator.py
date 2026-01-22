"""Unit tests for TmuxOrchestrator."""

import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.commander.tmux_orchestrator import (
    TmuxNotFoundError,
    TmuxOrchestrator,
)


class TestTmuxOrchestrator:
    """Test suite for TmuxOrchestrator class."""

    @patch("shutil.which")
    def test_init_raises_when_tmux_not_found(self, mock_which):
        """Test initialization fails when tmux is not installed."""
        mock_which.return_value = None

        with pytest.raises(TmuxNotFoundError) as exc_info:
            TmuxOrchestrator()

        assert "tmux not found" in str(exc_info.value)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_session_exists_returns_true_when_exists(self, mock_run, mock_which):
        """Test session_exists returns True when session exists."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        orchestrator = TmuxOrchestrator(session_name="test-session")
        result = orchestrator.session_exists()

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["tmux", "has-session", "-t", "test-session"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_session_exists_returns_false_when_not_exists(self, mock_run, mock_which):
        """Test session_exists returns False when session doesn't exist."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

        orchestrator = TmuxOrchestrator(session_name="test-session")
        result = orchestrator.session_exists()

        assert result is False

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_session_creates_new_session(self, mock_run, mock_which):
        """Test create_session creates a new tmux session."""
        mock_which.return_value = "/usr/bin/tmux"

        # First call: has-session returns False (doesn't exist)
        # Second call: new-session succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr=""),  # has-session
            Mock(returncode=0, stdout="", stderr=""),  # new-session
        ]

        orchestrator = TmuxOrchestrator(session_name="test-session")
        result = orchestrator.create_session()

        assert result is True
        assert mock_run.call_count == 2

        # Verify new-session command
        new_session_call = mock_run.call_args_list[1][0][0]
        assert "new-session" in new_session_call
        assert "-d" in new_session_call
        assert "-s" in new_session_call
        assert "test-session" in new_session_call

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_session_returns_false_when_exists(self, mock_run, mock_which):
        """Test create_session returns False when session already exists."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        orchestrator = TmuxOrchestrator(session_name="test-session")
        result = orchestrator.create_session()

        assert result is False
        # Only has-session called, not new-session
        assert mock_run.call_count == 1

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pane_returns_target(self, mock_run, mock_which):
        """Test create_pane creates pane and returns target."""
        mock_which.return_value = "/usr/bin/tmux"

        # First call: new-window
        # Second call: list-panes to get new pane ID
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # new-window
            Mock(returncode=0, stdout="%0\n%1\n%2\n", stderr=""),  # list-panes
        ]

        orchestrator = TmuxOrchestrator(session_name="test-session")
        target = orchestrator.create_pane("my-project", "/path/to/project")

        assert target == "%2"  # Last pane ID in list (not prefixed with session)
        assert mock_run.call_count == 2

        # Verify new-window command
        new_window_call = mock_run.call_args_list[0][0][0]
        assert "new-window" in new_window_call
        assert "-c" in new_window_call
        assert "/path/to/project" in new_window_call

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_send_keys_with_enter(self, mock_run, mock_which):
        """Test send_keys sends keys with Enter by default."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        orchestrator = TmuxOrchestrator()
        result = orchestrator.send_keys("%0", "echo 'hello'")

        assert result is True
        mock_run.assert_called_once()

        call_args = mock_run.call_args[0][0]
        assert call_args == [
            "tmux",
            "send-keys",
            "-t",
            "%0",
            "echo 'hello'",
            "Enter",
        ]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_send_keys_without_enter(self, mock_run, mock_which):
        """Test send_keys can omit Enter key."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        orchestrator = TmuxOrchestrator()
        result = orchestrator.send_keys("%0", "ls -la", enter=False)

        assert result is True

        call_args = mock_run.call_args[0][0]
        assert "Enter" not in call_args
        assert "ls -la" in call_args

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_capture_output_returns_pane_content(self, mock_run, mock_which):
        """Test capture_output returns pane output."""
        mock_which.return_value = "/usr/bin/tmux"
        expected_output = "Line 1\nLine 2\nLine 3\n"
        mock_run.return_value = Mock(returncode=0, stdout=expected_output, stderr="")

        orchestrator = TmuxOrchestrator()
        output = orchestrator.capture_output("%0", lines=50)

        assert output == expected_output
        mock_run.assert_called_once()

        call_args = mock_run.call_args[0][0]
        assert "capture-pane" in call_args
        assert "-S" in call_args
        assert "-50" in call_args

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_list_panes_returns_pane_info(self, mock_run, mock_which):
        """Test list_panes returns structured pane information."""
        mock_which.return_value = "/usr/bin/tmux"

        # First call: session_exists (has-session)
        # Second call: list-panes
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # has-session
            Mock(
                returncode=0,
                stdout="%0|/path/to/proj1|12345|1\n%1|/path/to/proj2|12346|0\n",
                stderr="",
            ),
        ]

        orchestrator = TmuxOrchestrator(session_name="test-session")
        panes = orchestrator.list_panes()

        assert len(panes) == 2
        assert panes[0] == {
            "id": "%0",
            "path": "/path/to/proj1",
            "pid": "12345",
            "active": True,
        }
        assert panes[1] == {
            "id": "%1",
            "path": "/path/to/proj2",
            "pid": "12346",
            "active": False,
        }

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_list_panes_returns_empty_when_session_not_exists(
        self, mock_run, mock_which
    ):
        """Test list_panes returns empty list when session doesn't exist."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

        orchestrator = TmuxOrchestrator()
        panes = orchestrator.list_panes()

        assert panes == []

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_kill_pane_kills_target(self, mock_run, mock_which):
        """Test kill_pane kills the specified pane."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        orchestrator = TmuxOrchestrator()
        result = orchestrator.kill_pane("%0")

        assert result is True
        mock_run.assert_called_once()

        call_args = mock_run.call_args[0][0]
        assert call_args == ["tmux", "kill-pane", "-t", "%0"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_kill_session_when_exists(self, mock_run, mock_which):
        """Test kill_session kills the session when it exists."""
        mock_which.return_value = "/usr/bin/tmux"

        # First call: has-session (exists)
        # Second call: kill-session
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # has-session
            Mock(returncode=0, stdout="", stderr=""),  # kill-session
        ]

        orchestrator = TmuxOrchestrator(session_name="test-session")
        result = orchestrator.kill_session()

        assert result is True
        assert mock_run.call_count == 2

        kill_call = mock_run.call_args_list[1][0][0]
        assert "kill-session" in kill_call
        assert "test-session" in kill_call

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_kill_session_when_not_exists(self, mock_run, mock_which):
        """Test kill_session returns False when session doesn't exist."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

        orchestrator = TmuxOrchestrator()
        result = orchestrator.kill_session()

        assert result is False
        # Only has-session called
        assert mock_run.call_count == 1

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_run_tmux_raises_on_file_not_found(self, mock_run, mock_which):
        """Test _run_tmux raises TmuxNotFoundError when tmux binary not found."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.side_effect = FileNotFoundError("tmux not found")

        orchestrator = TmuxOrchestrator()

        with pytest.raises(TmuxNotFoundError):
            orchestrator.session_exists()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_run_tmux_raises_on_command_failure(self, mock_run, mock_which):
        """Test _run_tmux raises CalledProcessError on command failure with check=True."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["tmux", "send-keys"],
            output="error",
        )

        orchestrator = TmuxOrchestrator()

        with pytest.raises(subprocess.CalledProcessError):
            orchestrator.send_keys("invalid-target", "test")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_custom_session_name(self, mock_run, mock_which):
        """Test TmuxOrchestrator can use custom session name."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        orchestrator = TmuxOrchestrator(session_name="my-custom-session")

        orchestrator.session_exists()

        call_args = mock_run.call_args[0][0]
        assert "my-custom-session" in call_args

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_pane_handles_empty_pane_list(self, mock_run, mock_which):
        """Test create_pane raises error when pane list is empty."""
        mock_which.return_value = "/usr/bin/tmux"

        # First call: new-window
        # Second call: list-panes returns empty
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # new-window
            Mock(returncode=0, stdout="", stderr=""),  # list-panes (empty)
        ]

        orchestrator = TmuxOrchestrator()

        with pytest.raises(RuntimeError, match="Failed to create pane"):
            orchestrator.create_pane("test", "/tmp")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_list_panes_handles_malformed_output(self, mock_run, mock_which):
        """Test list_panes handles malformed output gracefully."""
        mock_which.return_value = "/usr/bin/tmux"

        # First call: session_exists
        # Second call: list-panes with malformed data
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # has-session
            Mock(
                returncode=0,
                stdout="%0|/path|12345|1\nmalformed\n%1|incomplete",  # Partial data
                stderr="",
            ),
        ]

        orchestrator = TmuxOrchestrator()
        panes = orchestrator.list_panes()

        # Should only parse the valid line
        assert len(panes) == 1
        assert panes[0]["id"] == "%0"
