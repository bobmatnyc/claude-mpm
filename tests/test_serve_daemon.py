"""Smoke tests for Phase 1 of the Global Session Runner Daemon.

Tests cover:
- serve_parser registers the expected subcommands
- SessionCreate accepts the project_root field
- ProcessManager._get_global_sessions_dir() returns the correct path
- Session persistence writes to ~/.claude-mpm/sessions/
- manage_serve('start') delegates to ServeDaemon.start()
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# serve_parser
# ---------------------------------------------------------------------------


class TestServeParser:
    """Verify that serve_parser registers all required subcommands and flags."""

    def _build_parser(self) -> argparse.ArgumentParser:
        from claude_mpm.cli.parsers.serve_parser import (
            add_serve_subparser,  # type: ignore[import-not-found]
        )

        root = argparse.ArgumentParser()
        subparsers = root.add_subparsers(dest="command")
        add_serve_subparser(subparsers)
        return root

    def test_import_succeeds(self) -> None:
        """serve_parser module must be importable."""
        import claude_mpm.cli.parsers.serve_parser as _m  # type: ignore[import-not-found]

        assert _m is not None

    def test_start_subcommand(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "start"])
        assert args.serve_command == "start"

    def test_stop_subcommand(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "stop"])
        assert args.serve_command == "stop"

    def test_restart_subcommand(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "restart"])
        assert args.serve_command == "restart"

    def test_status_subcommand(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "status"])
        assert args.serve_command == "status"

    def test_default_port(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "start"])
        assert args.port == 7777

    def test_custom_port(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "start", "--port", "8888"])
        assert args.port == 8888

    def test_default_host(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "start"])
        assert args.host == "127.0.0.1"

    def test_foreground_background_mutually_exclusive(self) -> None:
        parser = self._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["serve", "start", "--foreground", "--background"])

    def test_channels_flag(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "start", "--channels", "telegram,slack"])
        assert args.channels == "telegram,slack"

    def test_project_root_flag(self) -> None:
        parser = self._build_parser()
        args = parser.parse_args(["serve", "start", "--project-root", "/tmp/myproject"])
        assert args.project_root == "/tmp/myproject"


# ---------------------------------------------------------------------------
# SessionCreate model
# ---------------------------------------------------------------------------


class TestSessionCreateModel:
    """Verify that SessionCreate accepts the project_root field."""

    def test_project_root_accepted(self) -> None:
        from claude_mpm.services.ui_service.models.session import SessionCreate

        sc = SessionCreate(project_root="/home/user/myproject")  # type: ignore[call-arg]
        assert sc.project_root == "/home/user/myproject"

    def test_project_root_defaults_to_none(self) -> None:
        from claude_mpm.services.ui_service.models.session import SessionCreate

        sc = SessionCreate()  # type: ignore[call-arg]
        assert sc.project_root is None

    def test_project_root_present_in_managed_session_state(self) -> None:
        from datetime import UTC, datetime

        from claude_mpm.services.ui_service.models.session import ManagedSessionState

        now = datetime.now(tz=UTC)
        state = ManagedSessionState(
            id="abc",
            created_at=now,
            last_activity=now,
            project_root="/some/root",
        )
        assert state.project_root == "/some/root"


# ---------------------------------------------------------------------------
# ProcessManager._get_global_sessions_dir
# ---------------------------------------------------------------------------


class TestProcessManagerGlobalSessionsDir:
    """Verify _get_global_sessions_dir returns the correct home-relative path."""

    def test_returns_correct_path(self) -> None:
        from claude_mpm.services.ui_service.process_manager import ProcessManager

        pm = ProcessManager()
        sessions_dir = pm._get_global_sessions_dir()
        expected = Path.home() / ".claude-mpm" / "sessions"
        assert sessions_dir == expected

    def test_creates_directory(self, tmp_path: Path) -> None:
        from claude_mpm.services.ui_service.process_manager import ProcessManager

        pm = ProcessManager()
        with patch.object(Path, "home", return_value=tmp_path):
            sessions_dir = pm._get_global_sessions_dir()
            assert sessions_dir.exists()


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


class TestSessionPersistence:
    """Verify that session state is written to ~/.claude-mpm/sessions/."""

    def test_persist_session_creates_file(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        from claude_mpm.services.ui_service.models.session import SessionStatus
        from claude_mpm.services.ui_service.process_manager import (
            ManagedSession,
            ProcessManager,
        )

        pm = ProcessManager()
        now = datetime.now(tz=UTC)
        session = ManagedSession(
            id="test-session-123",
            claude_session_id=None,
            process=None,
            status=SessionStatus.idle,
            model="claude-opus-4-5",
            cwd="/tmp",
            project_root="/tmp/proj",
            created_at=now,
            last_activity=now,
            context_tokens_used=0,
            context_tokens_total=200000,
            permission_mode="default",
        )

        # Patch home() so we write to a temp dir, not the real home.
        sessions_dir = tmp_path / ".claude-mpm" / "sessions"
        sessions_dir.mkdir(parents=True)

        with patch.object(pm, "_get_global_sessions_dir", return_value=sessions_dir):
            pm._persist_session(session)

        expected_file = sessions_dir / "test-session-123.json"
        assert expected_file.exists(), "Session JSON file should have been created"

        data = json.loads(expected_file.read_text())
        assert data["id"] == "test-session-123"
        assert data["project_root"] == "/tmp/proj"
        assert data["model"] == "claude-opus-4-5"

    def test_persist_session_silently_handles_errors(self) -> None:
        """Persistence errors must not propagate to callers."""
        from datetime import UTC, datetime

        from claude_mpm.services.ui_service.models.session import SessionStatus
        from claude_mpm.services.ui_service.process_manager import (
            ManagedSession,
            ProcessManager,
        )

        pm = ProcessManager()
        now = datetime.now(tz=UTC)
        session = ManagedSession(
            id="bad-session",
            claude_session_id=None,
            process=None,
            status=SessionStatus.idle,
            model="claude-opus-4-5",
            cwd="/tmp",
            created_at=now,
            last_activity=now,
            context_tokens_used=0,
            context_tokens_total=200000,
            permission_mode="default",
        )

        with patch.object(
            pm,
            "_get_global_sessions_dir",
            side_effect=OSError("disk full"),
        ):
            # Must not raise
            pm._persist_session(session)


# ---------------------------------------------------------------------------
# manage_serve delegates to ServeDaemon.start()
# ---------------------------------------------------------------------------


class TestManageServe:
    """Verify that manage_serve with 'start' action calls daemon.start()."""

    def _make_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "serve_command": "start",
            "port": 7777,
            "host": "127.0.0.1",
            "foreground": False,
            "background": True,
            "force": False,
            "channels": None,
            "project_root": None,
            "verbose": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_manage_serve_start_calls_daemon(self) -> None:
        from claude_mpm.cli.commands.serve import (
            manage_serve,  # type: ignore[import-not-found]
        )

        args = self._make_args()

        mock_lifecycle = MagicMock()
        # First call: not running (allow start). Second call: running (post-verify).
        mock_lifecycle.is_running.side_effect = [False, True]
        mock_lifecycle.get_pid.return_value = 12345
        mock_daemon = MagicMock()
        mock_daemon.lifecycle = mock_lifecycle
        mock_daemon.start.return_value = True

        with (
            patch(
                "claude_mpm.cli.commands.serve.ServeDaemon",
                return_value=mock_daemon,
            ),
            patch("claude_mpm.cli.commands.serve.time") as mock_time,
        ):
            mock_time.sleep = MagicMock()
            result = manage_serve(args)

        mock_daemon.start.assert_called_once_with(force_restart=False)
        assert result == 0

    def test_manage_serve_status_returns_zero(self) -> None:
        from claude_mpm.cli.commands.serve import (
            manage_serve,  # type: ignore[import-not-found]
        )

        args = self._make_args(serve_command="status")

        mock_lifecycle = MagicMock()
        mock_lifecycle.is_running.return_value = False
        mock_lifecycle.get_pid.return_value = None
        mock_daemon = MagicMock()
        mock_daemon.lifecycle = mock_lifecycle
        mock_daemon.status.return_value = {
            "service": "claude-mpm-serve",
            "running": False,
            "host": "127.0.0.1",
            "port": 7777,
            "pid": None,
            "url": None,
        }

        with patch(
            "claude_mpm.cli.commands.serve.ServeDaemon",
            return_value=mock_daemon,
        ):
            result = manage_serve(args)

        assert result == 0

    def test_manage_serve_stop_returns_zero_when_not_running(self) -> None:
        from claude_mpm.cli.commands.serve import (
            manage_serve,  # type: ignore[import-not-found]
        )

        args = self._make_args(serve_command="stop")

        mock_lifecycle = MagicMock()
        mock_lifecycle.is_running.return_value = False
        mock_daemon = MagicMock()
        mock_daemon.lifecycle = mock_lifecycle

        with patch(
            "claude_mpm.cli.commands.serve.ServeDaemon",
            return_value=mock_daemon,
        ):
            result = manage_serve(args)

        assert result == 0
