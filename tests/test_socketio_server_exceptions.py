#!/usr/bin/env python3
"""
Comprehensive test suite for Socket.IO server enhanced error handling.

This test suite validates the new error classes and their integration with the
standalone Socket.IO server, ensuring proper error reporting and troubleshooting guidance.
"""

import json
import os

# Add the source directory to the Python path for testing
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from claude_mpm.services.exceptions import (
        DaemonConflictError,
        HealthCheckError,
        PortConflictError,
        RecoveryFailedError,
        StaleProcessError,
        format_troubleshooting_guide,
    )
    from claude_mpm.services.socketio_server import SocketIOServer

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import modules for testing: {e}")
    IMPORTS_AVAILABLE = False


@unittest.skipIf(not IMPORTS_AVAILABLE, "Required modules not available")
class TestSocketIOServerExceptions(unittest.TestCase):
    """Test cases for enhanced Socket.IO server error classes."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_port = 8999  # Use a high port to avoid conflicts
        self.test_host = "localhost"
        self.test_pid = 12345
        self.temp_dir = Path(tmp_path)
        self.pidfile_path = self.temp_dir / f"test_socketio_{self.test_port}.pid"

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        if self.pidfile_path.exists():
            self.pidfile_path.unlink()
        if self.temp_dir.exists():
            self.temp_dir.rmdir()

    def test_daemon_conflict_error_creation():
        """Test DaemonConflictError creation with full context."""
        process_info = {
            "pid": self.test_pid,
            "status": "running",
            "name": "python",
            "create_time": time.time() - 3600,  # Started 1 hour ago
            "memory_info": {"rss": 50 * 1024 * 1024},  # 50MB
        }

        error = DaemonConflictError(
            port=self.test_port,
            existing_pid=self.test_pid,
            existing_server_id="test-server-123",
            process_info=process_info,
            pidfile_path=self.pidfile_path,
        )

        # Test basic properties
        self.assertEqual(error.port, self.test_port)
        self.assertEqual(error.existing_pid, self.test_pid)
        self.assertEqual(error.existing_server_id, "test-server-123")
        self.assertEqual(error.process_info, process_info)
        self.assertEqual(error.pidfile_path, self.pidfile_path)

        # Test error message contains key information
        error_msg = str(error)
        self.assertIn(f"port {self.test_port}", error_msg)
        self.assertIn(f"PID: {self.test_pid}", error_msg)
        self.assertIn("test-server-123", error_msg)
        self.assertIn("RESOLUTION STEPS", error_msg)

        # Test resolution steps are included
        resolution_steps = error.context["resolution_steps"]
        self.assertIsInstance(resolution_steps, list)
        self.assertTrue(len(resolution_steps) > 0)
        self.assertTrue(any("kill -TERM" in step for step in resolution_steps))

        # Test to_dict method
        error_dict = error.to_dict()
        self.assertEqual(error_dict["error_type"], "DaemonConflictError")
        self.assertEqual(error_dict["context"]["port"], self.test_port)
        self.assertIn("timestamp", error_dict)

    def test_port_conflict_error_creation():
        """Test PortConflictError creation and messaging."""
        conflicting_process = {
            "pid": 9876,
            "name": "nginx",
            "cmdline": ["nginx", "-g", "daemon off;"],
        }

        error = PortConflictError(
            port=self.test_port,
            host=self.test_host,
            conflicting_process=conflicting_process,
        )

        # Test properties
        self.assertEqual(error.port, self.test_port)
        self.assertEqual(error.host, self.test_host)
        self.assertEqual(error.conflicting_process, conflicting_process)

        # Test error message
        error_msg = str(error)
        self.assertIn(f"Port: {self.test_port}", error_msg)
        self.assertIn("nginx", error_msg)
        self.assertIn("PID: 9876", error_msg)
        self.assertIn("RESOLUTION STEPS", error_msg)

        # Test platform-specific commands are included
        resolution_steps = error.context["resolution_steps"]
        self.assertTrue(
            any("lsof" in step or "netstat" in step for step in resolution_steps)
        )

    def test_stale_process_error_creation():
        """Test StaleProcessError creation with different statuses."""
        validation_errors = ["Process no longer exists", "PID file is stale"]

        error = StaleProcessError(
            pid=self.test_pid,
            pidfile_path=self.pidfile_path,
            process_status="not_found",
            validation_errors=validation_errors,
        )

        # Test properties
        self.assertEqual(error.pid, self.test_pid)
        self.assertEqual(error.process_status, "not_found")
        self.assertEqual(error.validation_errors, validation_errors)

        # Test error message
        error_msg = str(error)
        self.assertIn("Stale process", error_msg)
        self.assertIn(f"PID: {self.test_pid}", error_msg)
        self.assertIn("Process no longer exists", error_msg)

        # Test zombie process handling
        zombie_error = StaleProcessError(
            pid=self.test_pid, pidfile_path=self.pidfile_path, process_status="zombie"
        )

        zombie_msg = str(zombie_error)
        self.assertIn("zombie", zombie_msg)
        resolution_steps = zombie_error.context["resolution_steps"]
        self.assertTrue(any("parent process" in step for step in resolution_steps))

    def test_recovery_failed_error_creation():
        """Test RecoveryFailedError creation and messaging."""
        health_status = {
            "status": "degraded",
            "uptime": 3600,
            "clients_connected": 5,
            "events_processed": 1000,
            "errors": 25,
        }

        error = RecoveryFailedError(
            recovery_action="restart",
            failure_reason="Process would not terminate gracefully",
            attempt_count=3,
            health_status=health_status,
            last_successful_recovery="2024-01-15T10:30:00Z",
        )

        # Test properties
        self.assertEqual(error.recovery_action, "restart")
        self.assertEqual(error.failure_reason, "Process would not terminate gracefully")
        self.assertEqual(error.attempt_count, 3)
        self.assertEqual(error.health_status, health_status)

        # Test error message
        error_msg = str(error)
        self.assertIn("Automatic recovery failed", error_msg)
        self.assertIn("Failed Action: restart", error_msg)
        self.assertIn("Attempt Count: 3", error_msg)
        self.assertIn("CURRENT HEALTH STATUS", error_msg)
        self.assertIn("Events Processed: 1000", error_msg)

        # Test different recovery actions have appropriate resolution steps
        resolution_steps = error.context["resolution_steps"]
        self.assertTrue(any("Manually stop" in step for step in resolution_steps))

    def test_health_check_error_creation():
        """Test HealthCheckError creation with threshold information."""
        check_details = {"cpu_usage": 85.5, "memory_usage": 512, "check_duration": 2.3}

        threshold_exceeded = {
            "cpu": {"current": 85.5, "threshold": 80.0},
            "memory": {"current": 512, "threshold": 500},
        }

        error = HealthCheckError(
            check_name="cpu_usage_monitor",
            check_status="critical",
            check_details=check_details,
            threshold_exceeded=threshold_exceeded,
        )

        # Test properties
        self.assertEqual(error.check_name, "cpu_usage_monitor")
        self.assertEqual(error.check_status, "critical")
        self.assertEqual(error.check_details, check_details)
        self.assertEqual(error.threshold_exceeded, threshold_exceeded)

        # Test error message
        error_msg = str(error)
        self.assertIn("Health check failed", error_msg)
        self.assertIn("cpu_usage_monitor", error_msg)
        self.assertIn("CRITICAL", error_msg)
        self.assertIn("THRESHOLDS EXCEEDED", error_msg)
        self.assertIn("Cpu: 85.5 (threshold: 80.0)", error_msg)

        # Test CPU-specific resolution steps
        resolution_steps = error.context["resolution_steps"]
        self.assertTrue(any("CPU" in step for step in resolution_steps))

    def test_format_troubleshooting_guide():
        """Test the comprehensive troubleshooting guide formatter."""
        error = PortConflictError(port=self.test_port, host=self.test_host)

        guide = format_troubleshooting_guide(error)

        # Test guide structure
        self.assertIn("TROUBLESHOOTING GUIDE", guide)
        self.assertIn("ERROR TYPE: PortConflictError", guide)
        self.assertIn("DIAGNOSTIC COMMANDS", guide)
        self.assertIn("COMMON SOLUTIONS", guide)
        self.assertIn("GETTING HELP", guide)
        self.assertIn("ERROR CONTEXT DATA", guide)

        # Test diagnostic commands are included
        self.assertIn(f"lsof -i :{self.test_port}", guide)
        self.assertIn("ps aux | grep socketio", guide)


@unittest.skipIf(not IMPORTS_AVAILABLE, "Required modules not available")
class TestSocketIOServerErrorIntegration(unittest.TestCase):
    """Test integration of error classes with SocketIOServer."""

    def setUp(self):
        """Set up test server instance."""
        self.test_port = 9000  # Use a different port to avoid conflicts
        self.temp_dir = Path(tmp_path)

        # Create server instance
        self.server = SocketIOServer(
            host="localhost", port=self.test_port, server_id="test-server"
        )

        # Override pidfile path to use temp directory
        self.server.pidfile_path = self.temp_dir / f"test_socketio_{self.test_port}.pid"

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        if self.server.pidfile_path.exists():
            self.server.pidfile_path.unlink()
        if self.temp_dir.exists():
            self.temp_dir.rmdir()

    def create_mock_pidfile(self, pid: int = 12345, server_id: str = "mock-server"):
        """Helper to create a mock PID file."""
        pidfile_content = {
            "pid": pid,
            "server_id": server_id,
            "server_version": "1.0.0",
            "port": self.test_port,
            "host": "localhost",
            "start_time": datetime.utcnow().isoformat() + "Z",
        }

        with self.server.pidfile_path.open("w") as f:
            json.dump(pidfile_content, f)

    def test_daemon_conflict_detection_with_enhanced_errors():
        """Test daemon conflict detection raises enhanced errors."""
        # Create a mock PID file
        self.create_mock_pidfile(pid=99999)  # Use unlikely PID

        # Mock process validation to simulate running server
        with patch.object(self.server, "_validate_process_identity") as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "is_zombie": False,
                "is_our_server": True,
                "process_info": {"pid": 99999, "status": "running", "name": "python"},
            }

            # Test with raise_on_conflict=True should raise DaemonConflictError
            with self.assertRaises(DaemonConflictError) as context:
                self.server.is_already_running(raise_on_conflict=True)

            error = context.exception
            self.assertEqual(error.port, self.test_port)
            self.assertEqual(error.existing_pid, 99999)
            self.assertIn("mock-server", error.existing_server_id)

    def test_stale_process_detection_with_enhanced_errors():
        """Test stale process detection raises enhanced errors."""
        # Create a mock PID file
        self.create_mock_pidfile(pid=99998)

        # Mock process validation to simulate stale process
        with patch.object(self.server, "_validate_process_identity") as mock_validate:
            mock_validate.return_value = {
                "is_valid": False,
                "is_zombie": False,
                "is_our_server": False,
                "process_info": {},
                "validation_errors": ["Process 99998 does not exist"],
            }

            # Test with raise_on_conflict=True should raise StaleProcessError
            with self.assertRaises(StaleProcessError) as context:
                self.server.is_already_running(raise_on_conflict=True)

            error = context.exception
            self.assertEqual(error.pid, 99998)
            self.assertEqual(error.process_status, "not_found")
            self.assertIn("Process 99998 does not exist", error.validation_errors)

    def test_zombie_process_detection_with_enhanced_errors():
        """Test zombie process detection raises enhanced errors."""
        # Create a mock PID file
        self.create_mock_pidfile(pid=99997)

        # Mock process validation to simulate zombie process
        with patch.object(self.server, "_validate_process_identity") as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "is_zombie": True,
                "is_our_server": True,
                "process_info": {"pid": 99997, "status": "zombie"},
                "validation_errors": ["Process 99997 is a zombie"],
            }

            # Test with raise_on_conflict=True should raise StaleProcessError
            with self.assertRaises(StaleProcessError) as context:
                self.server.is_already_running(raise_on_conflict=True)

            error = context.exception
            self.assertEqual(error.pid, 99997)
            self.assertEqual(error.process_status, "zombie")

    @patch("socket.socket")
    def test_port_conflict_detection_with_enhanced_errors(self):
        """Test port conflict detection raises enhanced errors."""
        # Mock socket to simulate port in use
        mock_sock_instance = Mock()
        mock_sock_instance.connect_ex.return_value = 0  # Success = port in use
        self.return_value.__enter__.return_value = mock_sock_instance

        # Test port conflict detection
        with self.assertRaises(PortConflictError) as context:
            self.server._check_port_only(raise_on_conflict=True)

        error = context.exception
        self.assertEqual(error.port, self.test_port)
        self.assertEqual(error.host, "localhost")

    def test_server_start_with_enhanced_error_handling():
        """Test server start with enhanced error handling."""
        # Create a mock PID file to simulate conflict
        self.create_mock_pidfile()

        with patch.object(self.server, "_validate_process_identity") as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "is_zombie": False,
                "is_our_server": True,
                "process_info": {"pid": 12345, "status": "running"},
            }

            # Test that start() returns False and logs appropriate error
            with patch.object(self.server, "logger") as mock_logger:
                result = self.server.start()

                self.assertFalse(result)
                # Verify enhanced error logging was called
                mock_logger.error.assert_called()
                error_call_args = mock_logger.error.call_args[0][0]
                self.assertIn("TROUBLESHOOTING GUIDE", error_call_args)

    def test_pidfile_lock_conflict_raises_daemon_error():
        """Test PID file lock conflict raises DaemonConflictError."""
        # Mock file locking to fail
        with patch.object(self.server, "_acquire_pidfile_lock", return_value=False):
            with patch("builtins.open", mock_open=True):
                with self.assertRaises(DaemonConflictError) as context:
                    self.server.create_pidfile()

                error = context.exception
                self.assertEqual(error.port, self.test_port)
                self.assertEqual(error.existing_pid, 0)  # Unknown PID


def mock_open(*args, **kwargs):
    """Mock open function for testing."""
    return MagicMock()


class TestErrorMessageContent(unittest.TestCase):
    """Test the content and usefulness of error messages."""

    @unittest.skipIf(not IMPORTS_AVAILABLE, "Required modules not available")
    def test_daemon_conflict_error_actionable_content():
        """Test that DaemonConflictError provides actionable guidance."""
        error = DaemonConflictError(
            port=8080,
            existing_pid=1234,
            existing_server_id="production-server",
            pidfile_path=Path("/tmp/test.pid"),
        )

        message = str(error)

        # Test that message contains specific commands user can run
        self.assertIn("ps -p 1234", message)
        self.assertIn("kill -TERM 1234", message)
        self.assertIn("kill -KILL 1234", message)
        self.assertIn("rm /tmp/test.pid", message)
        self.assertIn("--port", message)

        # Test that message explains the situation clearly
        self.assertIn("conflict detected", message)
        self.assertIn("production-server", message)
        self.assertIn("RESOLUTION STEPS", message)

    @unittest.skipIf(not IMPORTS_AVAILABLE, "Required modules not available")
    def test_error_messages_are_not_too_verbose():
        """Test that error messages are informative but not overwhelming."""
        error = PortConflictError(port=9090)
        message = str(error)

        # Message should be comprehensive but manageable
        lines = message.split("\n")
        self.assertLess(len(lines), 30, "Error message should not exceed 30 lines")

        # Should have clear sections
        sections = [line for line in lines if line.isupper() and ":" in line]
        self.assertGreaterEqual(
            len(sections), 2, "Should have at least 2 clear sections"
        )

    @unittest.skipIf(not IMPORTS_AVAILABLE, "Required modules not available")
    def test_troubleshooting_guide_comprehensiveness():
        """Test that troubleshooting guide covers essential areas."""
        error = RecoveryFailedError(
            recovery_action="restart", failure_reason="Process hung"
        )

        guide = format_troubleshooting_guide(error)

        # Should cover essential diagnostic areas
        essential_topics = [
            "DIAGNOSTIC COMMANDS",
            "COMMON SOLUTIONS",
            "GETTING HELP",
            "ERROR CONTEXT",
        ]

        for topic in essential_topics:
            self.assertIn(topic, guide, f"Troubleshooting guide should cover {topic}")


if __name__ == "__main__":
    # Run tests using unittest's built-in discovery
    if IMPORTS_AVAILABLE:
        unittest.main(verbosity=2)
    else:
        print("Skipping tests due to missing imports")
        sys.exit(1)
