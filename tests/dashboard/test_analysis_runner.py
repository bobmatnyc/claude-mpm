#!/usr/bin/env python3
"""
Unit tests for Code Analysis Runner
====================================

Tests the analysis runner component that manages subprocess execution
of code analysis, including:
- Request queuing and processing
- Subprocess lifecycle management
- Event emission and streaming
- Error handling and cancellation
- Memory management and cleanup
"""

import subprocess
import sys
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_mpm.dashboard.analysis_runner import (AnalysisRequest,
                                                  CodeAnalysisRunner)


class TestAnalysisRequest(unittest.TestCase):
    """Test the AnalysisRequest dataclass."""

    def test_request_creation(self):
        """Test creating an analysis request with all fields."""
        request = AnalysisRequest(
            request_id="test-123",
            path="/test/path",
            languages=["python", "javascript"],
            max_depth=3,
            ignore_patterns=["*.pyc", "__pycache__"],
        )

        self.assertEqual(request.request_id, "test-123")
        self.assertEqual(request.path, "/test/path")
        self.assertEqual(request.languages, ["python", "javascript"])
        self.assertEqual(request.max_depth, 3)
        self.assertEqual(request.ignore_patterns, ["*.pyc", "__pycache__"])
        self.assertIsNotNone(request.timestamp)

    def test_request_default_timestamp(self):
        """Test that timestamp is auto-generated if not provided."""
        request = AnalysisRequest(request_id="test-456", path="/test/path")

        self.assertIsInstance(request.timestamp, datetime)
        self.assertIsNotNone(request.timestamp)

    def test_request_custom_timestamp(self):
        """Test providing a custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        request = AnalysisRequest(
            request_id="test-789", path="/test/path", timestamp=custom_time
        )

        self.assertEqual(request.timestamp, custom_time)


class TestCodeAnalysisRunner(unittest.TestCase):
    """Test the CodeAnalysisRunner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_socketio = MagicMock()
        self.runner = CodeAnalysisRunner(self.mock_socketio)

    def tearDown(self):
        """Clean up after tests."""
        if self.runner.running:
            self.runner.stop()

    def test_initialization(self):
        """Test runner initialization."""
        self.assertIsNotNone(self.runner.logger)
        self.assertEqual(self.runner.server, self.mock_socketio)
        self.assertIsNone(self.runner.current_process)
        self.assertIsNone(self.runner.current_request)
        self.assertIsInstance(self.runner.request_queue, Queue)
        self.assertFalse(self.runner.running)
        self.assertIsNone(self.runner.worker_thread)

        # Check stats initialization
        expected_stats = {
            "analyses_started": 0,
            "analyses_completed": 0,
            "analyses_cancelled": 0,
            "analyses_failed": 0,
            "total_files": 0,
            "total_nodes": 0,
        }
        self.assertEqual(self.runner.stats, expected_stats)

    def test_start_stop(self):
        """Test starting and stopping the runner."""
        # Start the runner
        self.runner.start()
        self.assertTrue(self.runner.running)
        self.assertIsNotNone(self.runner.worker_thread)
        self.assertTrue(self.runner.worker_thread.is_alive())

        # Try starting again (should be idempotent)
        self.runner.start()
        self.assertTrue(self.runner.running)

        # Stop the runner
        self.runner.stop()
        time.sleep(0.1)  # Give thread time to stop
        self.assertFalse(self.runner.running)

    @patch("claude_mpm.dashboard.analysis_runner.Path")
    def test_request_analysis_invalid_path(self, mock_path_class):
        """Test requesting analysis with invalid path."""
        # Mock path that doesn't exist
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value.resolve.return_value = mock_path

        result = self.runner.request_analysis(
            request_id="test-invalid", path="/nonexistent/path"
        )

        self.assertFalse(result)
        # Check error event was emitted
        self.mock_socketio.emit.assert_called()

    @patch("claude_mpm.dashboard.analysis_runner.Path")
    def test_request_analysis_not_directory(self, mock_path_class):
        """Test requesting analysis on a file instead of directory."""
        # Mock path that exists but is not a directory
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = False
        mock_path_class.return_value.resolve.return_value = mock_path

        result = self.runner.request_analysis(
            request_id="test-file", path="/some/file.txt"
        )

        self.assertFalse(result)
        # Check error event was emitted
        self.mock_socketio.emit.assert_called()

    @patch("claude_mpm.dashboard.analysis_runner.Path")
    def test_request_analysis_valid(self, mock_path_class):
        """Test requesting analysis with valid directory."""
        # Mock valid directory path
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = True
        mock_path.__str__.return_value = "/valid/path"
        mock_path_class.return_value.resolve.return_value = mock_path

        result = self.runner.request_analysis(
            request_id="test-valid",
            path="/valid/path",
            languages=["python"],
            max_depth=2,
            ignore_patterns=["*.pyc"],
        )

        self.assertTrue(result)
        self.assertEqual(self.runner.request_queue.qsize(), 1)

        # Check queued event was emitted
        self.mock_socketio.emit.assert_called_with(
            "code:analysis:queued",
            {
                "request_id": "test-valid",
                "path": "/valid/path",
                "queue_size": 1,
            },
            namespace="/dashboard",
        )

    def test_cancel_current_no_process(self):
        """Test cancelling when no process is running."""
        # Should not raise any errors
        self.runner.cancel_current()
        self.assertEqual(self.runner.stats["analyses_cancelled"], 0)

    @patch("subprocess.Popen")
    def test_cancel_current_with_process(self, mock_popen):
        """Test cancelling a running process."""
        # Mock a running process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = None

        self.runner.current_process = mock_process
        self.runner.current_request = AnalysisRequest(
            request_id="test-cancel", path="/test/path"
        )

        self.runner.cancel_current()

        # Check process was terminated
        mock_process.terminate.assert_called_once()
        self.assertEqual(self.runner.stats["analyses_cancelled"], 1)

        # Check cancelled event was emitted
        self.mock_socketio.emit.assert_called_with(
            "code:analysis:cancelled",
            {
                "request_id": "test-cancel",
                "path": "/test/path",
            },
            namespace="/dashboard",
        )

    def test_get_status(self):
        """Test getting runner status."""
        # Initial status
        status = self.runner.get_status()

        self.assertFalse(status["running"])
        self.assertIsNone(status["current_request"])
        self.assertEqual(status["queue_size"], 0)
        self.assertEqual(status["stats"]["analyses_started"], 0)

        # Start runner and add request
        self.runner.start()
        self.runner.current_request = AnalysisRequest(
            request_id="test-status", path="/test/path"
        )
        self.runner.stats["analyses_started"] = 1

        status = self.runner.get_status()

        self.assertTrue(status["running"])
        self.assertIsNotNone(status["current_request"])
        self.assertEqual(status["current_request"]["request_id"], "test-status")
        self.assertEqual(status["stats"]["analyses_started"], 1)

        self.runner.stop()


class TestMemoryManagement(unittest.TestCase):
    """Test memory management and cleanup in the analysis runner."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_socketio = MagicMock()
        self.runner = CodeAnalysisRunner(self.mock_socketio)

    def test_event_cleanup_on_stop(self):
        """Test that events are properly cleaned up when runner stops."""
        self.runner.start()

        # Add multiple requests to queue
        for i in range(5):
            self.runner.request_queue.put(
                AnalysisRequest(request_id=f"test-{i}", path=f"/test/path/{i}")
            )

        # Stop should clear the queue
        self.runner.stop()

        # Queue should have sentinel value
        self.assertFalse(self.runner.running)

    def test_process_cleanup_on_error(self):
        """Test that processes are cleaned up on error."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdout = MagicMock()
            mock_process.stderr = MagicMock()
            mock_process.stdout.readline.side_effect = Exception("Test error")
            mock_popen.return_value = mock_process

            request = AnalysisRequest(request_id="test-error", path="/test/path")

            # Process should handle error gracefully
            self.runner._process_request(request)

            # Check that cleanup occurred
            mock_process.terminate.assert_called()


class TestPerformance(unittest.TestCase):
    """Test performance aspects of the analysis runner."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_socketio = MagicMock()
        self.runner = CodeAnalysisRunner(self.mock_socketio)

    def test_queue_performance(self):
        """Test that large numbers of requests can be queued efficiently."""
        start_time = time.time()

        # Queue 1000 requests
        for i in range(1000):
            self.runner.request_queue.put(
                AnalysisRequest(request_id=f"perf-{i}", path=f"/test/path/{i}")
            )

        elapsed = time.time() - start_time

        # Should complete in under 1 second
        self.assertLess(elapsed, 1.0)
        self.assertEqual(self.runner.request_queue.qsize(), 1000)

    def test_concurrent_request_handling(self):
        """Test handling multiple concurrent analysis requests."""
        self.runner.start()

        # Create multiple threads to add requests
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=lambda idx=i: self.runner.request_queue.put(
                    AnalysisRequest(
                        request_id=f"concurrent-{idx}", path=f"/test/path/{idx}"
                    )
                )
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check all requests were queued
        self.assertEqual(self.runner.request_queue.qsize(), 10)

        self.runner.stop()


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery scenarios in the analysis runner."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_socketio = MagicMock()
        self.runner = CodeAnalysisRunner(self.mock_socketio)

    @patch("subprocess.Popen")
    def test_subprocess_crash_recovery(self, mock_popen):
        """Test recovery from subprocess crash."""
        # Mock a process that crashes
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Non-zero exit code
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_process.stdout.readline.return_value = b""
        mock_process.stderr.read.return_value = b"Error: Process crashed"
        mock_popen.return_value = mock_process

        request = AnalysisRequest(request_id="test-crash", path="/test/path")

        # Process should handle crash gracefully
        self.runner._process_request(request)

        # Check that failure was recorded
        self.assertEqual(self.runner.stats["analyses_failed"], 1)

        # Check error event was emitted
        calls = self.mock_socketio.emit.call_args_list
        error_calls = [c for c in calls if "error" in str(c)]
        self.assertTrue(len(error_calls) > 0)

    @patch("subprocess.Popen")
    def test_timeout_recovery(self, mock_popen):
        """Test recovery from subprocess timeout."""
        # Mock a process that times out
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 2)
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        self.runner.current_process = mock_process
        self.runner.current_request = AnalysisRequest(
            request_id="test-timeout", path="/test/path"
        )

        # Cancel should handle timeout
        self.runner.cancel_current()

        # Check that kill was called after timeout
        mock_process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
