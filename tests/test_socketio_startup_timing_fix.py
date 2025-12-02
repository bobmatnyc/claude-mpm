#!/usr/bin/env python3
"""
Test to verify Socket.IO server startup timing fixes.

WHY: This test verifies that the timing improvements to _start_standalone_socketio_server
and _check_socketio_server_running address the false negative startup failures by:
1. Testing improved timing parameters
2. Verifying retry logic in health checks
3. Ensuring more graceful error messages
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.run import (
    _check_socketio_server_running,
    _start_standalone_socketio_server,
)
from claude_mpm.core.logger import get_logger


class TestSocketIOStartupTimingFix(unittest.TestCase):
    def setUp(self):
        self.logger = get_logger("test")

    def test_improved_timing_constants():
        """Test that improved timing constants are in place."""
        # This test verifies the constants are present in the source code
        import inspect

        source = inspect.getsource(_start_standalone_socketio_server)

        # Verify improved timing constants
        self.assertIn(
            "max_attempts = 30", source, "max_attempts should be increased to 30"
        )
        self.assertIn(
            "initial_delay = 1.0", source, "initial_delay should be increased to 1.0s"
        )
        self.assertIn(
            "max_delay = 3.0", source, "max_delay should be increased to 3.0s"
        )

        # Verify initial daemon startup delay is present
        self.assertIn(
            "time.sleep(0.5)", source, "Initial daemon startup delay should be present"
        )

    def test_health_check_retry_logic():
        """Test that health check has retry logic for robustness."""
        import inspect

        source = inspect.getsource(_check_socketio_server_running)

        # Verify retry logic is present
        self.assertIn("max_retries = 3", source, "Health check should have retry logic")
        self.assertIn(
            "for retry in range(max_retries)", source, "Should iterate through retries"
        )
        self.assertIn("timeout=10", source, "HTTP timeout should be increased to 10s")
        self.assertIn(
            "settimeout(2.0)", source, "TCP timeout should be increased to 2.0s"
        )

    def test_better_error_messages():
        """Test that improved error messages are present."""
        import inspect

        source = inspect.getsource(_start_standalone_socketio_server)

        # Check for specific improved error messages
        self.assertIn(
            "Server may still be starting",
            source,
            "Should mention server may still be starting",
        )
        self.assertIn(
            "initialization can take 15+ seconds",
            source,
            "Should mention 15+ second initialization time",
        )
        self.assertIn(
            "daemon process might be running",
            source,
            "Should mention daemon might be running",
        )

    @patch("claude_mpm.cli.commands.run._check_socketio_server_running")
    @patch("subprocess.run")
    def test_startup_timing_simulation(self, mock_health_check):
        """Simulate startup with improved timing."""
        # Mock successful daemon start
        self.return_value.returncode = 0

        # Simulate server becoming ready after several attempts (as would happen with Python 3.13)
        mock_health_check.side_effect = [False] * 8 + [True]  # Ready after 8 attempts

        start_time = time.time()
        result = _start_standalone_socketio_server(8765, self.logger)
        end_time = time.time()

        self.assertTrue(result, "Server startup should succeed")

        # Should make multiple health check attempts
        self.assertEqual(
            mock_health_check.call_count, 9, "Should make 9 health check attempts"
        )

        print(f"✓ Simulated startup completed in {end_time - start_time:.2f}s")
        print(f"✓ Made {mock_health_check.call_count} health check attempts")

    @patch("socket.socket")
    @patch("urllib.request.urlopen")
    def test_health_check_retry_behavior(self, mock_socket):
        """Test health check retry behavior for various failure scenarios."""
        # Mock TCP connection success
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock

        # Test scenario: Server starting but HTTP not ready (should retry)
        from urllib.error import HTTPError

        self.side_effect = [
            HTTPError("", 503, "Service Unavailable", {}, None),  # Server starting
            HTTPError("", 503, "Service Unavailable", {}, None),  # Still starting
            MagicMock(
                getcode=lambda: 200, read=lambda: b'{"status": "ok"}'
            ),  # Finally ready
        ]

        with patch("time.sleep"):  # Speed up test by mocking sleep
            result = _check_socketio_server_running(8765, self.logger)

        self.assertTrue(result, "Health check should succeed after retries")
        self.assertEqual(self.call_count, 3, "Should make 3 HTTP attempts")
        print("✓ Health check retry logic working correctly")

    @patch("socket.socket")
    @patch("urllib.request.urlopen")
    def test_health_check_timeout_behavior(self, mock_socket):
        """Test health check behavior with connection timeouts."""
        # Mock TCP connection success
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock

        # Test scenario: Connection timeouts (should retry)
        from urllib.error import URLError

        self.side_effect = [
            URLError("Connection refused"),  # Connection refused
            URLError("Connection refused"),  # Still refused
            MagicMock(
                getcode=lambda: 200, read=lambda: b'{"status": "ok"}'
            ),  # Finally ready
        ]

        with patch("time.sleep"):  # Speed up test by mocking sleep
            result = _check_socketio_server_running(8765, self.logger)

        self.assertTrue(result, "Health check should succeed after connection retries")
        self.assertEqual(self.call_count, 3, "Should make 3 HTTP attempts")
        print("✓ Connection timeout retry logic working correctly")


def main():
    """Run the timing fix verification tests."""
    print("🔧 Testing Socket.IO Startup Timing Fixes")
    print("=" * 50)

    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
