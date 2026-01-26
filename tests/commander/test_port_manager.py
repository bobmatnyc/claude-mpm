"""Tests for Commander port manager."""

import os
import socket
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.commander.port_manager import (
    CommanderPortManager,
    PortStatus,
    ProcessInfo,
    check_and_handle_port_conflict,
)


@pytest.fixture
def temp_pid_dir(tmp_path: Path) -> Path:
    """Create temporary directory for PID files.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Path to temporary PID directory
    """
    pid_dir = tmp_path / ".claude-mpm" / "commander"
    pid_dir.mkdir(parents=True, exist_ok=True)
    return pid_dir


@pytest.fixture
def port_manager(temp_pid_dir: Path) -> CommanderPortManager:
    """Create port manager with temporary directories.

    Args:
        temp_pid_dir: Temporary directory for PID files

    Returns:
        CommanderPortManager instance
    """
    manager = CommanderPortManager(port=19999, host="127.0.0.1")
    # Override config dir to use temp directory
    manager.config_dir = temp_pid_dir
    manager.pid_file = temp_pid_dir / "commander-19999.pid"
    return manager


@pytest.fixture
def free_port() -> int:
    """Find a free port for testing.

    Returns:
        Available port number
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestProcessInfo:
    """Tests for ProcessInfo namedtuple."""

    def test_creation(self):
        """Test ProcessInfo creation."""
        info = ProcessInfo(
            pid=1234,
            name="python",
            cmdline="python -m claude_mpm.commander",
            is_commander=True,
            is_healthy=True,
        )

        assert info.pid == 1234
        assert info.name == "python"
        assert info.is_commander is True
        assert info.is_healthy is True


class TestPortStatus:
    """Tests for PortStatus dataclass."""

    def test_creation_minimal(self):
        """Test PortStatus with minimal fields."""
        status = PortStatus(port=8766, available=True)

        assert status.port == 8766
        assert status.available is True
        assert status.process is None
        assert status.pid_file_pid is None
        assert status.pid_file_exists is False
        assert status.recommendation == ""

    def test_creation_full(self):
        """Test PortStatus with all fields."""
        process = ProcessInfo(
            pid=1234,
            name="python",
            cmdline="python -m claude_mpm",
            is_commander=True,
            is_healthy=True,
        )
        status = PortStatus(
            port=8766,
            available=False,
            process=process,
            pid_file_pid=1234,
            pid_file_exists=True,
            recommendation="Port in use",
        )

        assert status.port == 8766
        assert status.available is False
        assert status.process == process
        assert status.pid_file_pid == 1234
        assert status.pid_file_exists is True


class TestCommanderPortManager:
    """Tests for CommanderPortManager."""

    def test_init_default(self):
        """Test default initialization."""
        manager = CommanderPortManager()

        assert manager.port == 8766
        assert manager.host == "127.0.0.1"
        assert manager.pid_file.name == "commander-8766.pid"

    def test_init_custom_port(self):
        """Test initialization with custom port."""
        manager = CommanderPortManager(port=9000)

        assert manager.port == 9000
        assert manager.pid_file.name == "commander-9000.pid"

    def test_is_port_available_free(self, free_port: int):
        """Test port availability check when port is free."""
        manager = CommanderPortManager(port=free_port)

        assert manager.is_port_available() is True

    def test_is_port_available_in_use(self, free_port: int):
        """Test port availability check when port is in use."""
        # Bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", free_port))
        sock.listen(1)

        try:
            manager = CommanderPortManager(port=free_port)
            assert manager.is_port_available() is False
        finally:
            sock.close()

    def test_is_commander_process_true(self, port_manager: CommanderPortManager):
        """Test commander process identification - positive cases."""
        # Should match commander patterns
        assert port_manager._is_commander_process(
            "python -m claude_mpm.commander daemon"
        )
        assert port_manager._is_commander_process(
            "/usr/bin/python3 claude-mpm commander"
        )
        assert port_manager._is_commander_process(
            "uvicorn claude_mpm.commander.api:app"
        )

    def test_is_commander_process_false(self, port_manager: CommanderPortManager):
        """Test commander process identification - negative cases."""
        # Should NOT match - not our process
        assert not port_manager._is_commander_process("python some_other_app.py")
        assert not port_manager._is_commander_process("uvicorn myapp:app")
        assert not port_manager._is_commander_process("")
        assert not port_manager._is_commander_process("nginx master process")

    def test_write_pid_file(self, port_manager: CommanderPortManager):
        """Test PID file writing."""
        assert port_manager.write_pid_file(12345) is True
        assert port_manager.pid_file.exists()
        assert port_manager.pid_file.read_text().strip() == "12345"

    def test_get_pid_from_file(self, port_manager: CommanderPortManager):
        """Test PID file reading."""
        port_manager.pid_file.write_text("54321")

        assert port_manager.get_pid_from_file() == 54321

    def test_get_pid_from_file_not_exists(self, port_manager: CommanderPortManager):
        """Test PID file reading when file doesn't exist."""
        assert port_manager.get_pid_from_file() is None

    def test_get_pid_from_file_invalid(self, port_manager: CommanderPortManager):
        """Test PID file reading with invalid content."""
        port_manager.pid_file.write_text("not-a-number")

        assert port_manager.get_pid_from_file() is None

    def test_cleanup_pid_file(self, port_manager: CommanderPortManager):
        """Test PID file cleanup."""
        port_manager.pid_file.write_text("12345")

        assert port_manager.cleanup_pid_file() is True
        assert not port_manager.pid_file.exists()

    def test_cleanup_pid_file_not_exists(self, port_manager: CommanderPortManager):
        """Test PID file cleanup when file doesn't exist."""
        # Should not raise, returns True
        assert port_manager.cleanup_pid_file() is True

    def test_is_pid_stale_process_not_exists(self, port_manager: CommanderPortManager):
        """Test stale PID detection for non-existent process."""
        # Use a very high PID that likely doesn't exist
        assert port_manager.is_pid_stale(999999999) is True

    def test_is_pid_stale_current_process(self, port_manager: CommanderPortManager):
        """Test stale PID detection for current process."""
        # Current process is definitely running
        current_pid = os.getpid()

        # Mock _is_commander_process to return True for current process
        with patch.object(port_manager, "_is_commander_process", return_value=True):
            assert port_manager.is_pid_stale(current_pid) is False

    def test_get_port_status_available(
        self, port_manager: CommanderPortManager, free_port: int
    ):
        """Test port status when port is available."""
        port_manager.port = free_port
        port_manager.pid_file = port_manager.config_dir / f"commander-{free_port}.pid"

        status = port_manager.get_port_status()

        assert status.available is True
        assert status.process is None
        assert "available" in status.recommendation.lower()

    def test_get_port_status_in_use(
        self, port_manager: CommanderPortManager, free_port: int
    ):
        """Test port status when port is in use."""
        # Bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", free_port))
        sock.listen(1)

        try:
            port_manager.port = free_port
            status = port_manager.get_port_status()

            assert status.available is False
        finally:
            sock.close()


class TestHandlePortConflict:
    """Tests for handle_port_conflict method."""

    def test_port_available(self, port_manager: CommanderPortManager, free_port: int):
        """Test handling when port is available."""
        port_manager.port = free_port

        can_proceed, message = port_manager.handle_port_conflict()

        assert can_proceed is True
        assert "available" in message.lower()

    def test_port_available_stale_pid_file(
        self, port_manager: CommanderPortManager, free_port: int
    ):
        """Test handling when port is available but stale PID file exists."""
        port_manager.port = free_port
        port_manager.pid_file = port_manager.config_dir / f"commander-{free_port}.pid"
        # Write a stale PID file
        port_manager.pid_file.write_text("999999999")

        can_proceed, message = port_manager.handle_port_conflict()

        assert can_proceed is True
        # Stale PID file should be cleaned up
        assert not port_manager.pid_file.exists() or "stale" in message.lower()


class TestCheckAndHandlePortConflict:
    """Tests for convenience function."""

    def test_available_port(self, free_port: int, temp_pid_dir: Path):
        """Test with available port."""
        with patch(
            "claude_mpm.commander.port_manager.CommanderPortManager"
        ) as MockManager:
            mock_manager = MagicMock()
            MockManager.return_value = mock_manager

            mock_status = PortStatus(
                port=free_port,
                available=True,
                pid_file_exists=False,
            )
            mock_manager.get_port_status.return_value = mock_status
            mock_manager.handle_port_conflict.return_value = (
                True,
                "Port available",
            )

            can_proceed, _message, existing_pid = check_and_handle_port_conflict(
                port=free_port
            )

            assert can_proceed is True
            assert existing_pid is None

    def test_healthy_existing_daemon(self, free_port: int):
        """Test with healthy existing daemon."""
        with patch(
            "claude_mpm.commander.port_manager.CommanderPortManager"
        ) as MockManager:
            mock_manager = MagicMock()
            MockManager.return_value = mock_manager

            process = ProcessInfo(
                pid=12345,
                name="python",
                cmdline="python -m claude_mpm.commander",
                is_commander=True,
                is_healthy=True,
            )
            mock_status = PortStatus(
                port=free_port,
                available=False,
                process=process,
                pid_file_pid=12345,
                pid_file_exists=True,
            )
            mock_manager.get_port_status.return_value = mock_status

            can_proceed, _message, existing_pid = check_and_handle_port_conflict(
                port=free_port
            )

            assert can_proceed is True
            assert existing_pid == 12345


class TestKillProcess:
    """Tests for kill_process method."""

    def test_kill_nonexistent_process(self, port_manager: CommanderPortManager):
        """Test killing non-existent process returns True."""
        # Very high PID that doesn't exist
        result = port_manager.kill_process(999999999)

        assert result is True

    def test_kill_process_no_permission(self, port_manager: CommanderPortManager):
        """Test killing process without permission."""
        # PID 1 is init/systemd, we can't kill it
        with patch("os.kill") as mock_kill:
            mock_kill.side_effect = PermissionError("Operation not permitted")

            # Mock pid_exists to return True
            with patch("claude_mpm.commander.port_manager.psutil") as mock_psutil:
                mock_psutil.pid_exists.return_value = True

                result = port_manager.kill_process(1)

            assert result is False
