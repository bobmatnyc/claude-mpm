"""Tests for exec-based daemon fork safety (issue #693).

WHAT: Verifies that every refactored daemon manager in claude_mpm uses
      exec-based subprocess.Popen(start_new_session=True) rather than raw
      os.fork(), and that PID-file lifecycle, stdio redirection, stop/restart,
      and idempotency semantics are all preserved.

WHY:  raw os.fork() from a multithreaded Python parent on macOS causes
      EXC_BAD_ACCESS / SIGSEGV when CoreFoundation is touched after fork but
      before exec.  The fix (issue #693) replaces every double-fork path with
      subprocess.Popen(start_new_session=True).  These tests guard against
      regression on both macOS and Linux.

Reference: docs/developer/daemon-fork-safety.md
"""

from __future__ import annotations

import ast
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SRC = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(_SRC))

_SERVICES = _SRC / "claude_mpm" / "services"


def _source_has_no_fork(module_path: Path) -> bool:
    """AST-based check that a Python file contains no os.fork() call."""
    source = module_path.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        # Match: os.fork()
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "fork"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
        ):
            return False
    return True


# ---------------------------------------------------------------------------
# No-fork invariant: static AST check
# ---------------------------------------------------------------------------


class TestNoForkInvariant:
    """Verify that no os.fork() call appears in any refactored daemon module."""

    @pytest.mark.parametrize(
        "rel_path",
        [
            "infrastructure/daemon_manager.py",
            "communication/message_consumer.py",
            "monitor/management/lifecycle.py",
            "monitor/daemon_manager.py",
        ],
    )
    def test_no_os_fork_call(self, rel_path: str) -> None:
        """Module must not contain any os.fork() call (AST-verified)."""
        module_path = _SERVICES / rel_path
        assert module_path.exists(), f"Module not found: {module_path}"
        assert _source_has_no_fork(module_path), (
            f"{rel_path} still contains an os.fork() call — "
            "this is the regression that caused EXC_BAD_ACCESS on macOS "
            "(see issue #693 and docs/developer/daemon-fork-safety.md)"
        )


# ---------------------------------------------------------------------------
# infrastructure/daemon_manager.py — SocketIODaemonManager
# ---------------------------------------------------------------------------


class TestSocketIODaemonManagerExecSpawn:
    """Exec-based spawn semantics for SocketIODaemonManager."""

    def _make_manager(self, tmp_path: Path, port: int = 19765) -> Any:
        """Return a SocketIODaemonManager with paths redirected to tmp_path."""
        from claude_mpm.services.infrastructure.daemon_manager import (
            SocketIODaemonManager,
        )

        m = SocketIODaemonManager(host="localhost", port=port)
        m.config_dir = tmp_path
        # Use port-keyed names matching the production logic
        m.pid_file = tmp_path / f"socketio-server-{port}.pid"
        m.log_file = tmp_path / f"socketio-server-{port}.log"
        return m

    def test_start_calls_popen_with_start_new_session(self, tmp_path: Path) -> None:
        """start() must call subprocess.Popen(start_new_session=True) — not os.fork()."""
        m = self._make_manager(tmp_path)

        fake_proc = MagicMock()
        fake_proc.pid = 42
        fake_proc.poll.return_value = None  # still running

        def _write_pid_side_effect(*args, **kwargs) -> MagicMock:
            # Simulate the child writing the PID file
            m.pid_file.write_text("42")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("os.fork must not be called")),
            patch(
                "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                side_effect=_write_pid_side_effect,
            ) as mock_popen,
        ):
            result = m.start()

        assert result is True
        mock_popen.assert_called_once()
        _call = mock_popen.call_args
        assert _call.kwargs.get("start_new_session") is True or (
            len(_call.args) >= 1 and _call.args[0] and True
        ), "start_new_session=True must be passed to Popen"
        assert _call.kwargs.get("start_new_session") is True

    def test_start_passes_daemon_env_key(self, tmp_path: Path) -> None:
        """start() must pass CLAUDE_MPM_SOCKETIO_DAEMON=1 in the child env."""
        from claude_mpm.services.infrastructure.daemon_manager import (
            _SOCKETIO_DAEMON_ENV_KEY,
        )

        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 99
        fake_proc.poll.return_value = None

        def _write_pid(*a, **kw) -> MagicMock:
            m.pid_file.write_text("99")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                side_effect=_write_pid,
            ) as mock_popen,
        ):
            m.start()

        env_passed = mock_popen.call_args.kwargs.get("env", {})
        assert env_passed.get(_SOCKETIO_DAEMON_ENV_KEY) == "1", (
            f"Child env must contain {_SOCKETIO_DAEMON_ENV_KEY}=1"
        )

    def test_start_uses_devnull_stdin(self, tmp_path: Path) -> None:
        """Popen must receive stdin=DEVNULL (detached from terminal)."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 7
        fake_proc.poll.return_value = None

        def _write_pid(*a, **kw) -> MagicMock:
            m.pid_file.write_text("7")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                side_effect=_write_pid,
            ) as mock_popen,
        ):
            m.start()

        assert mock_popen.call_args.kwargs.get("stdin") == subprocess.DEVNULL

    def test_start_returns_false_when_already_running(self, tmp_path: Path) -> None:
        """start() must return False if is_running() is True (idempotent)."""
        m = self._make_manager(tmp_path)

        with patch.object(m, "is_running", return_value=True):
            with patch("os.fork", side_effect=AssertionError("no fork")):
                result = m.start()

        assert result is False

    def test_pid_file_lifecycle(self, tmp_path: Path) -> None:
        """stop() reads PID file, sends SIGTERM, and PID file is cleaned up."""
        m = self._make_manager(tmp_path)
        pid_file = m.pid_file

        # Write a fake PID
        test_pid = 12345
        pid_file.write_text(str(test_pid))

        with (
            patch("os.kill") as mock_kill,
            patch.object(m, "is_running", side_effect=[True, False]),
        ):
            result = m.stop()

        assert result is True
        mock_kill.assert_any_call(test_pid, signal.SIGTERM)

    def test_stop_handles_missing_pid_file(self, tmp_path: Path) -> None:
        """stop() returns False gracefully if no PID file exists."""
        m = self._make_manager(tmp_path)
        # Ensure no PID file
        m.pid_file.unlink(missing_ok=True)

        with patch.object(m, "is_running", return_value=False):
            result = m.stop()

        # stop() returns False when not running
        assert result is False

    def test_restart_calls_stop_then_start(self, tmp_path: Path) -> None:
        """restart() delegates to stop() then start() in order."""
        m = self._make_manager(tmp_path)
        calls: list[str] = []

        with (
            patch.object(m, "stop", side_effect=lambda: calls.append("stop")),
            patch.object(m, "start", side_effect=lambda: calls.append("start") or True),
            patch("time.sleep"),
        ):
            m.restart()

        assert calls == ["stop", "start"], f"Expected stop then start, got {calls}"

    def test_daemon_child_runs_foreground_on_env_flag(self, tmp_path: Path) -> None:
        """When CLAUDE_MPM_SOCKETIO_DAEMON=1 is set, start() calls _run_server() directly."""
        from claude_mpm.services.infrastructure.daemon_manager import (
            _SOCKETIO_DAEMON_ENV_KEY,
        )

        m = self._make_manager(tmp_path)

        with (
            patch.dict(os.environ, {_SOCKETIO_DAEMON_ENV_KEY: "1"}),
            patch.object(m, "is_running", return_value=False),
            patch.object(m, "_check_port_conflict", return_value=None),
            patch.object(m, "_run_server") as mock_run,
        ):
            result = m.start()

        mock_run.assert_called_once()
        assert result is True

    def test_start_new_session_cross_platform(self, tmp_path: Path) -> None:
        """start_new_session=True must be set regardless of platform (Linux and macOS)."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 55
        fake_proc.poll.return_value = None

        def _write_pid(*a, **kw) -> MagicMock:
            m.pid_file.write_text("55")
            return fake_proc

        for platform_str in ("darwin", "linux"):
            with (
                patch("sys.platform", platform_str),
                patch("os.fork", side_effect=AssertionError("no fork")),
                patch(
                    "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                    side_effect=_write_pid,
                ) as mock_popen,
            ):
                m.pid_file.unlink(missing_ok=True)
                m.start()
            assert mock_popen.call_args.kwargs.get("start_new_session") is True, (
                f"start_new_session must be True on {platform_str}"
            )

    def test_popen_never_uses_pipe_for_stdout_stderr(self, tmp_path: Path) -> None:
        """Popen must NOT route stdout or stderr to subprocess.PIPE (would buffer without consumer)."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 66
        fake_proc.poll.return_value = None

        def _write_pid(*a, **kw) -> MagicMock:
            m.pid_file.write_text("66")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                side_effect=_write_pid,
            ) as mock_popen,
        ):
            m.start()

        assert mock_popen.call_args.kwargs.get("stdout") != subprocess.PIPE, (
            "stdout must not be subprocess.PIPE — daemon output would buffer without a consumer"
        )
        assert mock_popen.call_args.kwargs.get("stderr") != subprocess.PIPE, (
            "stderr must not be subprocess.PIPE — daemon output would buffer without a consumer"
        )

    def test_popen_close_fds_not_false(self, tmp_path: Path) -> None:
        """Popen must not pass close_fds=False — that leaks all parent fds into the daemon."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 67
        fake_proc.poll.return_value = None

        def _write_pid(*a, **kw) -> MagicMock:
            m.pid_file.write_text("67")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                side_effect=_write_pid,
            ) as mock_popen,
        ):
            m.start()

        # close_fds should not be explicitly False; absent or True are both acceptable.
        assert mock_popen.call_args.kwargs.get("close_fds") is not False, (
            "close_fds must not be False — that leaks parent fds into the daemon child"
        )

    def test_two_instances_have_distinct_pid_files(self, tmp_path: Path) -> None:
        """Two SocketIODaemonManagers on different ports must use different PID file paths."""
        m_a = self._make_manager(tmp_path, port=19765)
        m_b = self._make_manager(tmp_path, port=19766)

        assert m_a.pid_file != m_b.pid_file, (
            "Managers on different ports must use different PID files to avoid clobbering"
        )
        assert str(m_a.port) in str(m_a.pid_file), (
            "PID file path must contain the port number"
        )
        assert str(m_b.port) in str(m_b.pid_file), (
            "PID file path must contain the port number"
        )
        # Log files too
        assert m_a.log_file != m_b.log_file
        assert str(m_a.port) in str(m_a.log_file)
        assert str(m_b.port) in str(m_b.log_file)

    def test_pid_file_validated_by_positive_integer_not_exact_match(
        self, tmp_path: Path
    ) -> None:
        """Parent accepts any valid positive PID written by the child, not only process.pid."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        # process.pid is 100, but child writes its own os.getpid() = 101
        fake_proc.pid = 100
        fake_proc.poll.return_value = None

        def _write_pid_with_different_pid(*a, **kw) -> MagicMock:
            m.pid_file.write_text("101")  # child's actual PID differs from process.pid
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.infrastructure.daemon_manager.subprocess.Popen",
                side_effect=_write_pid_with_different_pid,
            ),
        ):
            result = m.start()

        assert result is True, (
            "Parent must accept any valid positive PID written by the child, "
            "not require it to exactly match process.pid"
        )


# ---------------------------------------------------------------------------
# communication/message_consumer.py — --daemon mode
# ---------------------------------------------------------------------------


class TestMessageConsumerExecSpawn:
    """Exec-based --daemon spawn for MessageConsumer.main()."""

    def _run_main_daemon(self) -> tuple[MagicMock, dict[str, Any]]:
        """Invoke main() with --daemon and capture Popen call."""
        captured: dict[str, Any] = {}

        def _fake_popen(cmd, **kwargs) -> MagicMock:
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return MagicMock()

        with (
            patch("os.fork", side_effect=AssertionError("os.fork must not be called")),
            patch(
                "claude_mpm.services.communication.message_consumer.subprocess.Popen",
                side_effect=_fake_popen,
            ) as mock_popen,
            patch("sys.argv", ["message_consumer", "--daemon"]),
        ):
            from claude_mpm.services.communication import message_consumer

            message_consumer.main()

        return mock_popen, captured

    def test_daemon_flag_uses_popen_not_fork(self) -> None:
        """--daemon must call subprocess.Popen, never os.fork()."""
        mock_popen, _captured = self._run_main_daemon()
        mock_popen.assert_called_once()

    def test_daemon_flag_sets_start_new_session(self) -> None:
        """Popen call must include start_new_session=True."""
        _, captured = self._run_main_daemon()
        assert captured["kwargs"].get("start_new_session") is True

    def test_daemon_flag_sets_stdin_devnull(self) -> None:
        """Popen call must route stdin to DEVNULL (detached)."""
        _, captured = self._run_main_daemon()
        assert captured["kwargs"].get("stdin") == subprocess.DEVNULL

    def test_daemon_flag_sets_recursion_guard_env(self) -> None:
        """Child env must contain CLAUDE_MPM_MSG_CONSUMER_DAEMON=1."""
        _, captured = self._run_main_daemon()
        env = captured["kwargs"].get("env", {})
        assert env.get("CLAUDE_MPM_MSG_CONSUMER_DAEMON") == "1"

    def test_daemon_cmd_includes_module_flag(self) -> None:
        """Child argv must re-invoke the same module with -m."""
        _, captured = self._run_main_daemon()
        cmd = captured["cmd"]
        assert "-m" in cmd
        assert "claude_mpm.services.communication.message_consumer" in cmd

    def test_daemon_workers_forwarded(self) -> None:
        """--workers N must appear in child argv."""
        captured: dict[str, Any] = {}

        def _fake_popen(cmd, **kwargs) -> MagicMock:
            captured["cmd"] = cmd
            return MagicMock()

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.communication.message_consumer.subprocess.Popen",
                side_effect=_fake_popen,
            ),
            patch("sys.argv", ["message_consumer", "--daemon", "--workers", "4"]),
        ):
            from claude_mpm.services.communication import message_consumer

            message_consumer.main()

        assert "4" in captured.get("cmd", [])

    def test_recursion_guard_prevents_respawn_when_already_child(self) -> None:
        """When CLAUDE_MPM_MSG_CONSUMER_DAEMON=1 is set, --daemon must NOT spawn again."""
        from claude_mpm.services.communication import message_consumer

        consumer_instance = MagicMock()
        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.communication.message_consumer.subprocess.Popen",
                side_effect=AssertionError("must not spawn a second subprocess"),
            ),
            patch.dict(os.environ, {"CLAUDE_MPM_MSG_CONSUMER_DAEMON": "1"}),
            patch("sys.argv", ["message_consumer", "--daemon"]),
            patch(
                "claude_mpm.services.communication.message_consumer.MessageConsumer",
                return_value=consumer_instance,
            ),
        ):
            message_consumer.main()

        # Must have run the consumer directly (foreground), not spawned again
        consumer_instance.run.assert_called_once()

    def test_popen_never_uses_pipe_for_stdout_stderr(self) -> None:
        """Popen must NOT route stdout or stderr to subprocess.PIPE."""
        _, captured = self._run_main_daemon()
        assert captured["kwargs"].get("stdout") != subprocess.PIPE, (
            "stdout must not be PIPE — daemon output would buffer without a consumer"
        )
        assert captured["kwargs"].get("stderr") != subprocess.PIPE, (
            "stderr must not be PIPE — daemon output would buffer without a consumer"
        )


# ---------------------------------------------------------------------------
# monitor/management/lifecycle.py — DaemonLifecycle
# ---------------------------------------------------------------------------


class TestDaemonLifecycleExecSpawn:
    """Exec-based spawn semantics for DaemonLifecycle."""

    def _make_lifecycle(self, tmp_path: Path) -> Any:
        from claude_mpm.services.monitor.management.lifecycle import DaemonLifecycle

        lc = DaemonLifecycle(
            pid_file=str(tmp_path / "monitor.pid"),
            log_file=str(tmp_path / "monitor.log"),
            port=19766,
        )
        return lc

    def test_daemonize_uses_popen_not_fork(self, tmp_path: Path) -> None:
        """daemonize() must use subprocess.Popen, not os.fork()."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 200

        with (
            patch("os.fork", side_effect=AssertionError("os.fork must not be called")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            result = lc.daemonize()

        assert result is True
        mock_popen.assert_called_once()

    def test_daemonize_sets_start_new_session(self, tmp_path: Path) -> None:
        """Popen must receive start_new_session=True."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 201

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        assert mock_popen.call_args.kwargs.get("start_new_session") is True

    def test_daemonize_stdin_devnull(self, tmp_path: Path) -> None:
        """Popen must receive stdin=DEVNULL."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 202

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        assert mock_popen.call_args.kwargs.get("stdin") == subprocess.DEVNULL

    def test_daemonize_env_marks_subprocess_daemon(self, tmp_path: Path) -> None:
        """Child env must carry CLAUDE_MPM_SUBPROCESS_DAEMON=1."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 203

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        env = mock_popen.call_args.kwargs.get("env", {})
        assert env.get("CLAUDE_MPM_SUBPROCESS_DAEMON") == "1"

    def test_daemonize_passes_startup_status_file_env(self, tmp_path: Path) -> None:
        """Child env must carry CLAUDE_MPM_STARTUP_STATUS_FILE so it can report back."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 204

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        env = mock_popen.call_args.kwargs.get("env", {})
        assert "CLAUDE_MPM_STARTUP_STATUS_FILE" in env

    def test_daemonize_redirects_stdout_to_log_file(self, tmp_path: Path) -> None:
        """Popen stdout must be redirected to the log file, not DEVNULL."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 205

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        # stdout must not be DEVNULL — it should be the opened log file handle
        stdout_arg = mock_popen.call_args.kwargs.get("stdout")
        assert stdout_arg != subprocess.DEVNULL, (
            "Log output must be redirected to a file, not discarded"
        )

    def test_stop_daemon_signals_correct_pid(self, tmp_path: Path) -> None:
        """stop_daemon() sends SIGTERM to the PID from the PID file."""
        lc = self._make_lifecycle(tmp_path)
        pid_path = Path(lc.pid_file)
        test_pid = 55555
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(test_pid))

        with (
            patch("os.kill") as mock_kill,
            patch.object(lc, "is_running", side_effect=[True, False]),
        ):
            result = lc.stop_daemon()

        assert result is True
        mock_kill.assert_any_call(test_pid, signal.SIGTERM)

    def test_pid_file_written_and_cleaned(self, tmp_path: Path) -> None:
        """write_pid_file() writes current PID; cleanup() removes it."""
        lc = self._make_lifecycle(tmp_path)
        pid_path = Path(lc.pid_file)
        pid_path.parent.mkdir(parents=True, exist_ok=True)

        lc.write_pid_file()
        assert pid_path.exists()
        written_pid = int(pid_path.read_text().strip())
        assert written_pid == os.getpid()

        lc.cleanup()
        assert not pid_path.exists()

    def test_is_running_false_without_pid_file(self, tmp_path: Path) -> None:
        """is_running() returns False when PID file is absent."""
        lc = self._make_lifecycle(tmp_path)
        Path(lc.pid_file).unlink(missing_ok=True)
        assert lc.is_running() is False

    def test_report_startup_success_writes_status_file(self, tmp_path: Path) -> None:
        """_report_startup_success() writes 'success' to the status file."""
        from pathlib import Path as _Path

        from claude_mpm.core.enums import OperationResult

        lc = self._make_lifecycle(tmp_path)
        status_file = tmp_path / "startup.status"
        status_file.write_text("starting")
        lc.startup_status_file = _Path(status_file)

        lc._report_startup_success()
        assert status_file.read_text().strip() == OperationResult.SUCCESS

    def test_report_startup_error_writes_status_file(self, tmp_path: Path) -> None:
        """_report_startup_error() writes 'error:<msg>' to the status file."""
        from pathlib import Path as _Path

        lc = self._make_lifecycle(tmp_path)
        status_file = tmp_path / "startup.status"
        status_file.write_text("starting")
        lc.startup_status_file = _Path(status_file)

        lc._report_startup_error("port in use")
        content = status_file.read_text().strip()
        assert content.startswith("error:")
        assert "port in use" in content

    def test_daemonize_popen_close_fds_not_false(self, tmp_path: Path) -> None:
        """daemonize() Popen must not pass close_fds=False — that leaks all parent fds."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 206

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        assert mock_popen.call_args.kwargs.get("close_fds") is not False, (
            "close_fds must not be False — that leaks parent fds into the daemon child"
        )

    def test_daemonize_popen_never_uses_pipe_for_stdout_stderr(
        self, tmp_path: Path
    ) -> None:
        """daemonize() Popen must NOT route stdout or stderr to subprocess.PIPE."""
        lc = self._make_lifecycle(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 207

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.management.lifecycle.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
            patch.object(lc, "_parent_wait_for_startup", return_value=True),
        ):
            lc.daemonize()

        assert mock_popen.call_args.kwargs.get("stdout") != subprocess.PIPE, (
            "stdout must not be PIPE — log output would buffer without a consumer"
        )
        assert mock_popen.call_args.kwargs.get("stderr") != subprocess.PIPE, (
            "stderr must not be PIPE — log output would buffer without a consumer"
        )


# ---------------------------------------------------------------------------
# monitor/daemon_manager.py — DaemonManager (legacy fork removed)
# ---------------------------------------------------------------------------


class TestMonitorDaemonManagerExecSpawn:
    """Exec-based spawn for monitor/daemon_manager.py DaemonManager."""

    def _make_manager(self, tmp_path: Path) -> Any:
        from claude_mpm.services.monitor.daemon_manager import DaemonManager

        m = DaemonManager(
            port=19767,
            host="localhost",
            pid_file=str(tmp_path / "monitor-daemon-19767.pid"),
            log_file=str(tmp_path / "monitor-daemon-19767.log"),
        )
        return m

    def test_start_daemon_subprocess_uses_popen_not_fork(self, tmp_path: Path) -> None:
        """start_daemon_subprocess() must use Popen, not os.fork()."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 300
        fake_proc.poll.return_value = None  # still running

        # Simulate PID file written + port becomes bound
        def _fake_popen(cmd, **kwargs) -> MagicMock:
            Path(m.pid_file).write_text("300")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("os.fork must not be called")),
            patch(
                "claude_mpm.services.monitor.daemon_manager.subprocess.Popen",
                side_effect=_fake_popen,
            ) as mock_popen,
            patch.object(m, "_is_port_available", return_value=False),
            patch.object(m, "_verify_daemon_health", return_value=True),
        ):
            result = m.start_daemon_subprocess()

        assert result is True
        mock_popen.assert_called_once()

    def test_start_daemon_subprocess_start_new_session(self, tmp_path: Path) -> None:
        """Popen must include start_new_session=True."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 301
        fake_proc.poll.return_value = None

        def _fake_popen(cmd, **kwargs) -> MagicMock:
            Path(m.pid_file).write_text("301")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.daemon_manager.subprocess.Popen",
                side_effect=_fake_popen,
            ) as mock_popen,
            patch.object(m, "_is_port_available", return_value=False),
            patch.object(m, "_verify_daemon_health", return_value=True),
        ):
            m.start_daemon_subprocess()

        assert mock_popen.call_args.kwargs.get("start_new_session") is True

    def test_start_daemon_subprocess_passes_recursion_guard(
        self, tmp_path: Path
    ) -> None:
        """Child env must contain CLAUDE_MPM_SUBPROCESS_DAEMON=1."""
        m = self._make_manager(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 302
        fake_proc.poll.return_value = None

        def _fake_popen(cmd, **kwargs) -> MagicMock:
            Path(m.pid_file).write_text("302")
            return fake_proc

        with (
            patch("os.fork", side_effect=AssertionError("no fork")),
            patch(
                "claude_mpm.services.monitor.daemon_manager.subprocess.Popen",
                side_effect=_fake_popen,
            ) as mock_popen,
            patch.object(m, "_is_port_available", return_value=False),
            patch.object(m, "_verify_daemon_health", return_value=True),
        ):
            m.start_daemon_subprocess()

        env = mock_popen.call_args.kwargs.get("env", {})
        assert env.get("CLAUDE_MPM_SUBPROCESS_DAEMON") == "1"

    def test_daemonize_legacy_path_returns_false(self, tmp_path: Path) -> None:
        """daemonize() (legacy stub) must return False and log an error."""
        m = self._make_manager(tmp_path)
        with patch.object(m.logger, "error") as mock_error:
            result = m.daemonize()
        assert result is False
        mock_error.assert_called_once()
        logged = mock_error.call_args[0][0]
        assert "os.fork" in logged or "daemonize" in logged

    def test_use_subprocess_daemon_returns_true_without_env(
        self, tmp_path: Path
    ) -> None:
        """use_subprocess_daemon() returns True unless already inside a subprocess."""
        m = self._make_manager(tmp_path)
        env_backup = os.environ.pop("CLAUDE_MPM_SUBPROCESS_DAEMON", None)
        try:
            assert m.use_subprocess_daemon() is True
        finally:
            if env_backup is not None:
                os.environ["CLAUDE_MPM_SUBPROCESS_DAEMON"] = env_backup

    def test_use_subprocess_daemon_returns_false_when_child(
        self, tmp_path: Path
    ) -> None:
        """use_subprocess_daemon() returns False when already the exec'd child."""
        m = self._make_manager(tmp_path)
        with patch.dict(os.environ, {"CLAUDE_MPM_SUBPROCESS_DAEMON": "1"}):
            assert m.use_subprocess_daemon() is False

    def test_stop_daemon_signals_pid_from_file(self, tmp_path: Path) -> None:
        """stop_daemon() reads PID file and sends SIGTERM."""
        m = self._make_manager(tmp_path)
        Path(m.pid_file).write_text("77777")

        with (
            patch("os.kill") as mock_kill,
        ):
            # Simulate process disappearing after SIGTERM
            mock_kill.side_effect = [None, ProcessLookupError]
            result = m.stop_daemon()

        assert result is True
        first_call_args = mock_kill.call_args_list[0]
        assert first_call_args[0][0] == 77777
        assert first_call_args[0][1] == signal.SIGTERM

    def test_write_and_cleanup_pid_file(self, tmp_path: Path) -> None:
        """write_pid_file() writes current PID; cleanup_pid_file() removes it."""
        m = self._make_manager(tmp_path)

        m.write_pid_file()
        assert Path(m.pid_file).exists()
        assert int(Path(m.pid_file).read_text().strip()) == os.getpid()

        m.cleanup_pid_file()
        assert not Path(m.pid_file).exists()

    def test_is_running_false_for_nonexistent_process(self, tmp_path: Path) -> None:
        """is_running() returns False if PID file references a dead process."""
        m = self._make_manager(tmp_path)
        # Use a PID that almost certainly does not exist
        Path(m.pid_file).write_text("999999999")
        assert m.is_running() is False
        # Stale PID file must be removed
        assert not Path(m.pid_file).exists()

    def test_already_running_idempotent(self, tmp_path: Path) -> None:
        """start_daemon() returns True immediately if daemon is already running."""
        m = self._make_manager(tmp_path)
        with patch.object(m, "is_running", return_value=True):
            with patch("os.fork", side_effect=AssertionError("no fork")):
                result = m.start_daemon()
        assert result is True


# ---------------------------------------------------------------------------
# Cross-cutting: verify no os.fork in the broader services package
# ---------------------------------------------------------------------------


class TestNoForkInServicesPackage:
    """Grep-level check: no os.fork( in the services subtree."""

    def test_grep_no_raw_fork(self) -> None:
        """AST-based check: no live os.fork() call exists in services/ Python files.

        We intentionally use the AST (not grep) so that os.fork() appearing only
        in comments, docstrings, or string literals does not trip the check.
        """
        live_forks: list[str] = []
        for py_file in _SERVICES.rglob("*.py"):
            try:
                source = py_file.read_text()
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "fork"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                ):
                    live_forks.append(f"{py_file}:{node.lineno}")

        assert live_forks == [], (
            "Found live os.fork() AST call-sites in services/:\n"
            + "\n".join(live_forks)
            + "\n\nSee issue #693 — raw os.fork() in a multithreaded Python parent "
            "causes EXC_BAD_ACCESS / SIGSEGV on macOS."
        )
