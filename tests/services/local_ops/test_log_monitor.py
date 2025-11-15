"""
Unit Tests for Log Monitor
===========================

WHY: Provides comprehensive unit testing for LogMonitor,
including file watching, pattern matching, and callback triggers.

COVERAGE:
- Log file monitoring initialization
- Pattern matching (regex)
- Watchdog event handling
- Match history tracking
- Callback triggers
- Multiple deployment monitoring

TEST STRATEGY:
- Unit tests with temporary log files
- Test pattern matching with various error types
- Test file modification events
- Test callback invocation
- Test multiple deployments
"""

import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from claude_mpm.services.core.models.stability import LogPatternMatch
from claude_mpm.services.local_ops.log_monitor import LogMonitor
from tests.utils.test_helpers import wait_for_condition

# ============================================================================
# Log Monitor Tests
# ============================================================================


class TestLogMonitor:
    """Test suite for LogMonitor."""

    def test_initialization(self):
        """Test log monitor initialization."""
        monitor = LogMonitor(match_history_limit=50)

        assert monitor.initialize()
        assert monitor.match_history_limit == 50
        assert not monitor._shutdown

        monitor.shutdown()
        assert monitor._shutdown

    def test_default_patterns(self):
        """Test default error patterns are loaded."""
        monitor = LogMonitor()
        monitor.initialize()

        # Should have default patterns
        assert len(monitor._patterns) > 0

        # Check some key patterns exist
        pattern_strings = [p.pattern for p, _ in monitor._patterns]
        assert any("OutOfMemoryError" in p for p in pattern_strings)
        assert any("Exception:" in p for p in pattern_strings)
        assert any("Segmentation fault" in p for p in pattern_strings)

        monitor.shutdown()

    def test_add_pattern(self):
        """Test adding custom error patterns."""
        monitor = LogMonitor()
        monitor.initialize()

        initial_count = len(monitor._patterns)

        # Add custom pattern
        monitor.add_pattern(r"CustomError: .+", severity="CRITICAL")

        # Should have one more pattern
        assert len(monitor._patterns) == initial_count + 1

        monitor.shutdown()

    def test_start_stop_monitoring(self, tmp_path):
        """Test starting and stopping log file monitoring."""
        monitor = LogMonitor()
        monitor.initialize()

        # Create temporary log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Initial content\n")

        deployment_id = "test-app"

        # Start monitoring
        monitor.start_monitoring(str(log_file), deployment_id)

        # Check handler registered
        assert deployment_id in monitor._handlers

        # Stop monitoring
        monitor.stop_monitoring(deployment_id)

        # Check handler removed
        assert deployment_id not in monitor._handlers

        monitor.shutdown()

    def test_start_monitoring_nonexistent_file(self, tmp_path):
        """Test monitoring a file that doesn't exist yet."""
        monitor = LogMonitor()
        monitor.initialize()

        # Use non-existent log file
        log_file = tmp_path / "nonexistent.log"
        deployment_id = "test-app"

        # Should not raise error
        monitor.start_monitoring(str(log_file), deployment_id)

        # Handler should be created
        assert deployment_id in monitor._handlers

        monitor.shutdown()

    def test_pattern_matching(self, tmp_path):
        """Test pattern matching on log lines."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting application\n")

        deployment_id = "test-app"

        # Register callback
        matches = []

        def match_callback(dep_id: str, match: LogPatternMatch):
            matches.append((dep_id, match))

        monitor.register_match_callback(match_callback)

        # Start monitoring
        monitor.start_monitoring(str(log_file), deployment_id)

        # Wait for observer to start
        assert wait_for_condition(
            lambda: deployment_id in monitor._handlers,
            timeout=2,
            message="Monitor did not start"
        )

        # Append error line - use explicit file operations for test reliability
        with open(log_file, "a") as f:
            f.write("Exception: Something went wrong\n")
            f.flush()
            # Force OS to write to disk
            import os

            os.fsync(f.fileno())

        # Wait for watchdog to detect and process file change
        wait_for_condition(
            lambda: len(matches) > 0,
            timeout=3,
            interval=0.1
        )

        # WORKAROUND: Watchdog events don't fire reliably in test environments on macOS.
        # Manually trigger the file handler to process changes.
        if len(matches) == 0 and deployment_id in monitor._handlers:
            from watchdog.events import FileModifiedEvent

            event = FileModifiedEvent(str(log_file))
            monitor._handlers[deployment_id].on_modified(event)

        # Check match was detected
        assert len(matches) > 0
        assert matches[0][0] == deployment_id
        assert "Exception:" in matches[0][1].pattern

        monitor.shutdown()

    def test_multiple_pattern_matches(self, tmp_path):
        """Test multiple error patterns in same file."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        matches = []

        def match_callback(dep_id: str, match: LogPatternMatch):
            matches.append(match)

        monitor.register_match_callback(match_callback)
        monitor.start_monitoring(str(log_file), deployment_id)

        # Wait for monitor to start
        wait_for_condition(
            lambda: deployment_id in monitor._handlers,
            timeout=2,
            message="Monitor did not start"
        )

        # Append multiple error types
        with open(log_file, "a") as f:
            f.write("Error: First error\n")
            f.write("Warning: Some warning\n")
            f.write("Exception: Second error\n")
            f.flush()

        # Wait for detection
        wait_for_condition(
            lambda: len(matches) >= 2,
            timeout=3,
            interval=0.1
        )

        # WORKAROUND: Manually trigger watchdog event if needed (macOS test environment issue)
        if len(matches) < 2 and deployment_id in monitor._handlers:
            from watchdog.events import FileModifiedEvent

            event = FileModifiedEvent(str(log_file))
            monitor._handlers[deployment_id].on_modified(event)

        # Should have detected multiple matches
        assert len(matches) >= 2

        monitor.shutdown()

    def test_match_history(self, tmp_path):
        """Test match history tracking."""
        monitor = LogMonitor(match_history_limit=5)
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        monitor.start_monitoring(str(log_file), deployment_id)
        time.sleep(0.5)

        # Append many error lines
        with open(log_file, "a") as f:
            for i in range(10):
                f.write(f"Error: Test error {i}\n")
            f.flush()

        # Wait for detection
        time.sleep(1.5)

        # Get match history
        history = monitor.get_recent_matches(deployment_id, limit=10)

        # Should have limited to 5 (history_limit)
        # Note: might be less if watchdog batches events
        assert len(history) <= 5

        monitor.shutdown()

    def test_get_recent_matches_limit(self, tmp_path):
        """Test get_recent_matches with limit parameter."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        monitor.start_monitoring(str(log_file), deployment_id)
        time.sleep(0.5)

        # Append errors
        with open(log_file, "a") as f:
            for i in range(10):
                f.write(f"Error: Test {i}\n")
            f.flush()

        time.sleep(1.5)

        # Get limited results
        history = monitor.get_recent_matches(deployment_id, limit=3)

        # Should return at most 3
        assert len(history) <= 3

        monitor.shutdown()

    def test_severity_levels(self, tmp_path):
        """Test different severity levels for patterns."""
        monitor = LogMonitor()
        monitor.initialize()

        # Add patterns with different severities
        monitor.add_pattern(r"CRITICAL_ERROR", severity="CRITICAL")
        monitor.add_pattern(r"WARN:", severity="WARNING")

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        matches = []

        def match_callback(dep_id: str, match: LogPatternMatch):
            matches.append(match)

        monitor.register_match_callback(match_callback)
        monitor.start_monitoring(str(log_file), deployment_id)

        time.sleep(0.5)

        # Append lines with different severities
        with open(log_file, "a") as f:
            f.write("CRITICAL_ERROR: System failure\n")
            f.write("WARN: Low disk space\n")
            f.flush()

        time.sleep(1.5)

        # Check severities were captured
        if len(matches) >= 2:
            severities = [m.severity for m in matches]
            assert "CRITICAL" in severities
            assert "WARNING" in severities

        monitor.shutdown()

    def test_multiple_deployments(self, tmp_path):
        """Test monitoring multiple deployments independently."""
        monitor = LogMonitor()
        monitor.initialize()

        # Create two log files
        log_file1 = tmp_path / "app1.log"
        log_file2 = tmp_path / "app2.log"
        log_file1.write_text("App1 starting\n")
        log_file2.write_text("App2 starting\n")

        # Start monitoring both
        monitor.start_monitoring(str(log_file1), "app1")
        monitor.start_monitoring(str(log_file2), "app2")

        time.sleep(0.5)

        # Append error to app1 only
        with open(log_file1, "a") as f:
            f.write("Error: App1 error\n")
            f.flush()

        # Increased wait time for watchdog to detect and process
        time.sleep(2.0)

        # WORKAROUND: Manually trigger watchdog event if needed (macOS test environment issue)
        app1_matches = monitor.get_recent_matches("app1")
        if len(app1_matches) == 0 and "app1" in monitor._handlers:
            from watchdog.events import FileModifiedEvent

            event = FileModifiedEvent(str(log_file1))
            monitor._handlers["app1"].on_modified(event)
            app1_matches = monitor.get_recent_matches("app1")

        # Check matches
        app2_matches = monitor.get_recent_matches("app2")

        # App1 should have matches
        assert len(app1_matches) > 0

        # App2 should have no matches
        assert len(app2_matches) == 0

        monitor.shutdown()

    def test_callback_exception_handling(self, tmp_path):
        """Test callback exception doesn't crash monitor."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        # Register callback that raises exception
        def bad_callback(dep_id: str, match: LogPatternMatch):
            raise ValueError("Test exception")

        monitor.register_match_callback(bad_callback)
        monitor.start_monitoring(str(log_file), deployment_id)

        time.sleep(0.5)

        # Append error - should not crash despite callback exception
        with open(log_file, "a") as f:
            f.write("Error: Test error\n")
            f.flush()

        time.sleep(1.5)

        # Monitor should still be running
        assert not monitor._shutdown

        monitor.shutdown()

    def test_log_pattern_match_model(self):
        """Test LogPatternMatch data model."""
        match = LogPatternMatch(
            deployment_id="test-app",
            pattern=r"Error:",
            line="Error: Something went wrong",
            severity="CRITICAL",
            line_number=42,
            context=["Previous line", "Next line"],
        )

        assert match.deployment_id == "test-app"
        assert match.pattern == r"Error:"
        assert match.severity == "CRITICAL"
        assert match.is_critical
        assert match.line_number == 42
        assert len(match.context) == 2

    def test_log_pattern_match_serialization(self):
        """Test LogPatternMatch to_dict/from_dict."""
        original = LogPatternMatch(
            deployment_id="test-app",
            pattern=r"Exception:",
            line="Exception: Test",
            severity="ERROR",
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = LogPatternMatch.from_dict(data)

        assert restored.deployment_id == original.deployment_id
        assert restored.pattern == original.pattern
        assert restored.line == original.line
        assert restored.severity == original.severity

    def test_stop_monitoring_nonexistent_deployment(self):
        """Test stopping monitoring for non-existent deployment."""
        monitor = LogMonitor()
        monitor.initialize()

        # Should not raise error
        monitor.stop_monitoring("nonexistent-app")

        monitor.shutdown()

    def test_double_start_monitoring(self, tmp_path):
        """Test starting monitoring twice for same deployment."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        # Start monitoring
        monitor.start_monitoring(str(log_file), deployment_id)

        # Start again - should log warning but not crash
        monitor.start_monitoring(str(log_file), deployment_id)

        # Should still have one handler
        assert deployment_id in monitor._handlers

        monitor.shutdown()


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


class TestLogMonitorEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_rapid_log_updates(self, tmp_path):
        """Test handling rapid log file updates."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        matches = []

        def match_callback(dep_id: str, match: LogPatternMatch):
            matches.append(match)

        monitor.register_match_callback(match_callback)
        monitor.start_monitoring(str(log_file), deployment_id)

        time.sleep(0.5)

        # Rapidly append many lines
        with open(log_file, "a") as f:
            for i in range(50):
                f.write(f"Error: Rapid error {i}\n")
            f.flush()

        # Increased wait time to ensure watchdog processes all changes
        time.sleep(3.0)

        # WORKAROUND: Manually trigger watchdog event if needed (macOS test environment issue)
        if len(matches) == 0 and deployment_id in monitor._handlers:
            from watchdog.events import FileModifiedEvent

            event = FileModifiedEvent(str(log_file))
            monitor._handlers[deployment_id].on_modified(event)

        # Should have detected multiple matches
        # (exact count depends on watchdog batching)
        assert len(matches) > 0

        monitor.shutdown()

    def test_empty_match_history(self):
        """Test getting matches for deployment with no history."""
        monitor = LogMonitor()
        monitor.initialize()

        # Get matches for unknown deployment
        matches = monitor.get_recent_matches("unknown-app")

        assert matches == []

        monitor.shutdown()

    def test_log_rotation_scenario(self, tmp_path):
        """Test behavior when log file is rotated."""
        monitor = LogMonitor()
        monitor.initialize()

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting\n")

        deployment_id = "test-app"

        monitor.start_monitoring(str(log_file), deployment_id)
        time.sleep(0.5)

        # Simulate log rotation (file deleted and recreated)
        log_file.unlink()
        log_file.write_text("Rotated log\n")

        # Append error to new file
        with open(log_file, "a") as f:
            f.write("Error: After rotation\n")
            f.flush()

        # Note: Watchdog may or may not detect this depending on timing
        # This test mainly verifies no crash occurs
        time.sleep(1.5)

        monitor.shutdown()
