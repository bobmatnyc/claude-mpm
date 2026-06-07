"""Tests for socketio_daemon.py PID-path consistency (issue #695).

WHAT: Verifies that the wrapper's is_running() / stop / status / restart all
      derive the same port-keyed PID-file path that start_server() writes, so
      that a daemon started on any port can be reliably queried and stopped.

WHY:  Before the fix the module had a hardcoded ``DEFAULT_PID_FILE`` pointing
      to port 8765.  stop/status/restart used that constant regardless of the
      ``--port`` argument, so they always read the wrong file when a different
      port was in use (#695).
"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.scripts.socketio_daemon import (
    DEFAULT_PORT,
    _pid_file_for_port,
    is_running,
    restart_server,
    start_server,
    status_server,
    stop_server,
)

# ---------------------------------------------------------------------------
# _pid_file_for_port — canonical path helper
# ---------------------------------------------------------------------------


class TestPidFileForPort:
    """Unit tests for the canonical PID-file path helper."""

    def test_default_port_under_home_claude_mpm(self) -> None:
        """_pid_file_for_port(8765) must be under ~/.claude-mpm/."""
        p = _pid_file_for_port(DEFAULT_PORT)
        assert p.parent == Path.home() / ".claude-mpm"

    def test_filename_contains_port(self) -> None:
        """PID-file name must embed the port number."""
        for port in (8765, 9000, 12345):
            p = _pid_file_for_port(port)
            assert str(port) in p.name, f"Port {port} missing from {p.name}"

    def test_different_ports_give_different_paths(self) -> None:
        """Two distinct ports must produce two distinct PID-file paths."""
        p_a = _pid_file_for_port(8765)
        p_b = _pid_file_for_port(9000)
        assert p_a != p_b

    def test_same_port_is_idempotent(self) -> None:
        """Calling _pid_file_for_port with the same port twice is idempotent."""
        assert _pid_file_for_port(8765) == _pid_file_for_port(8765)

    def test_naming_convention_matches_socketio_server_prefix(self) -> None:
        """PID-file names follow the socketio-server-{port}.pid convention."""
        p = _pid_file_for_port(8765)
        assert p.name == "socketio-server-8765.pid"


# ---------------------------------------------------------------------------
# PID-path consistency: start vs stop/status/restart
# ---------------------------------------------------------------------------


class TestPidPathConsistency:
    """Assert that start and stop/status/restart agree on the PID-file path.

    This is the core regression test for issue #695: before the fix,
    stop/status/restart used DEFAULT_PID_FILE (8765) regardless of port.
    """

    @pytest.mark.parametrize("port", [DEFAULT_PORT, 9001, 19765])
    def test_all_commands_derive_pid_path_via_helper(
        self, port: int, tmp_path: Path
    ) -> None:
        """start, stop, status, and restart must all call _pid_file_for_port with
        the port they were given — never a hardcoded constant (#695).

        Approach: patch _pid_file_for_port with a spy that records calls, stub out
        all I/O side-effects, then assert the spy was called with *port* in each
        command.  This catches any regression where a command bypasses the helper.
        """
        fake_pid_file = tmp_path / f"socketio-server-{port}.pid"
        fake_pid_file.write_text("12345")

        _target = "claude_mpm.scripts.socketio_daemon._pid_file_for_port"
        _is_running = "claude_mpm.scripts.socketio_daemon.is_running"
        _start_server = "claude_mpm.scripts.socketio_daemon.start_server"
        _stop_server = "claude_mpm.scripts.socketio_daemon.stop_server"

        # --- stop_server ---
        with (
            patch(_target, wraps=_pid_file_for_port) as spy_stop,
            patch(_is_running, side_effect=[True, False, False]),
            patch("os.kill"),
        ):
            stop_server(port=port)
        spy_stop.assert_called_with(port)

        # --- status_server ---
        with (
            patch(_target, wraps=_pid_file_for_port) as spy_status,
            patch(_is_running, side_effect=lambda f: f == _pid_file_for_port(port)),
        ):
            status_server(port=port)
        spy_status.assert_called_with(port)

        # --- restart_server (delegates to stop_server + start_server) ---
        with (
            patch(_target, wraps=_pid_file_for_port) as spy_restart,
            patch(_is_running, return_value=False),
            patch(_stop_server, return_value=True),
            patch(_start_server, return_value=True),
            patch("time.sleep"),
        ):
            restart_server(port=port)
        # restart calls _pid_file_for_port(port) for its is_running guard
        spy_restart.assert_called_with(port)

    def test_stop_uses_port_keyed_pid_file(self, tmp_path: Path, monkeypatch) -> None:
        """stop_server(port=9001) must look at the 9001 PID file, not 8765."""
        port = 9001
        pid_file = tmp_path / f"socketio-server-{port}.pid"
        wrong_pid_file = tmp_path / f"socketio-server-{DEFAULT_PORT}.pid"

        # Write PID to the correct (port-keyed) file
        pid_file.write_text("12345")

        # Redirect both paths into tmp_path
        monkeypatch.setattr(
            "claude_mpm.scripts.socketio_daemon._pid_file_for_port",
            lambda p: tmp_path / f"socketio-server-{p}.pid",
        )

        with patch("os.kill") as mock_kill:
            # stop_server calls is_running three times:
            #   1. initial guard (`if not is_running(pid_file)`)  → True (running)
            #   2. loop body  (`if not is_running(pid_file): break`) → False (stopped)
            #   3. force-kill guard (`if is_running(pid_file)`)       → False (already gone)
            with patch(
                "claude_mpm.scripts.socketio_daemon.is_running",
                side_effect=[True, False, False],
            ):
                result = stop_server(port=port)

        assert result is True
        # SIGTERM must have been sent to the PID from the correct file
        mock_kill.assert_any_call(12345, signal.SIGTERM)
        # The wrong (default-port) PID file must never have been created
        assert not wrong_pid_file.exists()

    def test_status_uses_port_keyed_pid_file(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        """status_server(port=9002) must read the 9002 PID file, not 8765."""
        port = 9002
        pid_file = tmp_path / f"socketio-server-{port}.pid"
        pid_file.write_text("99999")

        monkeypatch.setattr(
            "claude_mpm.scripts.socketio_daemon._pid_file_for_port",
            lambda p: tmp_path / f"socketio-server-{p}.pid",
        )

        with patch(
            "claude_mpm.scripts.socketio_daemon.is_running",
            side_effect=lambda f: f == pid_file,
        ):
            result = status_server(port=port)

        assert result is True
        output = capsys.readouterr().out
        assert "99999" in output, "PID must appear in status output"

    def test_restart_stops_correct_port(self, tmp_path: Path, monkeypatch) -> None:
        """restart_server(port=9003) must stop port 9003, not 8765."""
        port = 9003

        monkeypatch.setattr(
            "claude_mpm.scripts.socketio_daemon._pid_file_for_port",
            lambda p: tmp_path / f"socketio-server-{p}.pid",
        )

        stopped_ports: list[int] = []
        started_ports: list[int] = []

        def _fake_stop(port=DEFAULT_PORT):
            stopped_ports.append(port)
            return True

        def _fake_start(port=DEFAULT_PORT, daemon=True):
            started_ports.append(port)
            return True

        with (
            patch(
                "claude_mpm.scripts.socketio_daemon.stop_server", side_effect=_fake_stop
            ),
            patch(
                "claude_mpm.scripts.socketio_daemon.start_server",
                side_effect=_fake_start,
            ),
            patch(
                "claude_mpm.scripts.socketio_daemon.is_running",
                return_value=True,
            ),
            patch("time.sleep"),
        ):
            result = restart_server(port=port)

        assert result is True
        assert stopped_ports == [port], (
            f"Expected stop on port {port}, got {stopped_ports}"
        )
        assert started_ports == [port], (
            f"Expected start on port {port}, got {started_ports}"
        )


# ---------------------------------------------------------------------------
# is_running — unit tests with tmp_path (never touches ~/.claude-mpm)
# ---------------------------------------------------------------------------


class TestIsRunning:
    """Whitebox unit tests for is_running(), injecting tmp_path."""

    def test_returns_false_when_no_pid_file(self, tmp_path: Path) -> None:
        """is_running returns False when PID file is absent."""
        assert is_running(tmp_path / "nonexistent.pid") is False

    def test_returns_true_when_pid_alive(self, tmp_path: Path) -> None:
        """is_running returns True when the PID file contains the current PID."""
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(str(os.getpid()))
        assert is_running(pid_file) is True

    def test_returns_false_and_cleans_stale_pid_file(self, tmp_path: Path) -> None:
        """is_running removes a stale PID file whose process no longer exists."""
        pid_file = tmp_path / "stale.pid"
        pid_file.write_text("999999999")  # extremely unlikely to exist
        assert is_running(pid_file) is False
        assert not pid_file.exists(), "Stale PID file must be removed"

    def test_returns_false_for_invalid_pid_content(self, tmp_path: Path) -> None:
        """is_running returns False for a PID file with non-integer content."""
        pid_file = tmp_path / "bad.pid"
        pid_file.write_text("not-a-pid")
        assert is_running(pid_file) is False


# ---------------------------------------------------------------------------
# No DEFAULT_PID_FILE constant on the module
# ---------------------------------------------------------------------------


class TestNoPidFileModuleConstant:
    """Guard against the regression being re-introduced as a module constant."""

    def test_DEFAULT_PID_FILE_is_not_exported(self) -> None:
        """The module must NOT export a DEFAULT_PID_FILE constant.

        The old constant was hardcoded to port 8765 and caused stop/status to
        use the wrong path for any other port (issue #695).
        """
        import claude_mpm.scripts.socketio_daemon as mod

        assert not hasattr(mod, "DEFAULT_PID_FILE"), (
            "DEFAULT_PID_FILE must not exist on the module — it caused stop/status "
            "to always read the port-8765 PID file regardless of --port (#695). "
            "Use _pid_file_for_port(port) everywhere instead."
        )
