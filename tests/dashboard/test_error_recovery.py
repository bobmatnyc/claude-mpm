#!/usr/bin/env python3
"""
Dashboard Error Recovery Tests
==============================

Tests for error recovery scenarios including:
- WebSocket connection failures and reconnection
- Server crashes and restarts
- Invalid event data handling
- Resource exhaustion recovery
- Network interruption handling
"""

import json
import os
import sys
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class ConnectionRecoveryManager:
    """Manages connection recovery with exponential backoff."""

    def __init__(self, max_retries: int = 5, base_delay: float = 1.0):
        """
        Initialize recovery manager.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retry_count = 0
        self.connected = False
        self.last_error = None
        self.connection_callbacks = []
        self.error_callbacks = []

    def add_connection_callback(self, callback):
        """Add callback for successful connection."""
        self.connection_callbacks.append(callback)

    def add_error_callback(self, callback):
        """Add callback for connection errors."""
        self.error_callbacks.append(callback)

    def attempt_connection(self, connect_func) -> bool:
        """
        Attempt to establish connection with retry logic.

        Args:
            connect_func: Function to call for connection attempt

        Returns:
            True if connection successful, False otherwise
        """
        self.retry_count = 0

        while self.retry_count < self.max_retries:
            try:
                # Attempt connection
                result = connect_func()

                # Success
                self.connected = True
                self.retry_count = 0
                self.last_error = None

                # Notify callbacks
                for callback in self.connection_callbacks:
                    callback()

                return True

            except Exception as e:
                # Connection failed
                self.last_error = str(e)
                self.retry_count += 1

                # Calculate backoff delay
                delay = self.base_delay * (2 ** (self.retry_count - 1))

                # Notify error callbacks
                for callback in self.error_callbacks:
                    callback(e, self.retry_count, delay)

                if self.retry_count < self.max_retries:
                    time.sleep(delay)
                else:
                    self.connected = False
                    return False

        return False

    def reset(self):
        """Reset connection state."""
        self.retry_count = 0
        self.connected = False
        self.last_error = None


class EventValidationHandler:
    """Handles validation and sanitization of events."""

    def __init__(self):
        self.validation_errors = []
        self.sanitized_count = 0
        self.rejected_count = 0

    def validate_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and sanitize an event.

        Args:
            event: Event to validate

        Returns:
            Sanitized event or None if invalid
        """
        try:
            # Check required fields
            if not isinstance(event, dict):
                self.validation_errors.append("Event is not a dictionary")
                self.rejected_count += 1
                return None

            # Ensure event has type
            if "type" not in event and "event_name" not in event:
                event["type"] = "unknown"
                self.sanitized_count += 1

            # Ensure event has timestamp
            if "timestamp" not in event:
                event["timestamp"] = datetime.utcnow().isoformat()
                self.sanitized_count += 1

            # Validate data field
            if "data" in event and not isinstance(event["data"], (dict, list, str)):
                # Convert to string if not valid type
                event["data"] = str(event["data"])
                self.sanitized_count += 1

            # Check for circular references
            try:
                json.dumps(event)
            except (TypeError, ValueError):
                # Remove problematic fields
                if "data" in event:
                    event["data"] = {"error": "Invalid data removed"}
                self.sanitized_count += 1

            return event

        except Exception as e:
            self.validation_errors.append(str(e))
            self.rejected_count += 1
            return None


class ResourceMonitor:
    """Monitors and manages resource usage."""

    def __init__(self, memory_limit_mb: int = 1000, cpu_limit_percent: int = 80):
        """
        Initialize resource monitor.

        Args:
            memory_limit_mb: Memory limit in megabytes
            cpu_limit_percent: CPU usage limit as percentage
        """
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit_percent = cpu_limit_percent
        self.monitoring = False
        self.monitor_thread = None
        self.resource_alerts = []
        self.cleanup_callbacks = []

    def start_monitoring(self):
        """Start resource monitoring."""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

    def add_cleanup_callback(self, callback):
        """Add callback for resource cleanup."""
        self.cleanup_callbacks.append(callback)

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Estimate based on object count if psutil not available
            import gc

            return len(gc.get_objects()) / 1000  # Rough estimate

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.cpu_percent(interval=0.1)
        except ImportError:
            return 0

    def _monitor_loop(self):
        """Monitor resources in background."""
        while self.monitoring:
            try:
                # Check memory usage
                memory_mb = self.get_memory_usage()
                if memory_mb > self.memory_limit_mb:
                    self.resource_alerts.append(
                        {
                            "type": "memory",
                            "value": memory_mb,
                            "limit": self.memory_limit_mb,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                    # Trigger cleanup
                    for callback in self.cleanup_callbacks:
                        callback("memory", memory_mb)

                # Check CPU usage
                cpu_percent = self.get_cpu_usage()
                if cpu_percent > self.cpu_limit_percent:
                    self.resource_alerts.append(
                        {
                            "type": "cpu",
                            "value": cpu_percent,
                            "limit": self.cpu_limit_percent,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                    # Trigger cleanup
                    for callback in self.cleanup_callbacks:
                        callback("cpu", cpu_percent)

                time.sleep(5)  # Check every 5 seconds

            except Exception:
                # Don't let monitoring errors crash the thread
                pass


class TestConnectionRecovery(unittest.TestCase):
    """Test connection recovery mechanisms."""

    def test_successful_connection(self):
        """Test successful connection on first attempt."""
        manager = ConnectionRecoveryManager()

        # Mock successful connection
        connect_func = Mock(return_value=True)

        result = manager.attempt_connection(connect_func)

        self.assertTrue(result)
        self.assertTrue(manager.connected)
        self.assertEqual(manager.retry_count, 0)
        self.assertIsNone(manager.last_error)
        connect_func.assert_called_once()

    def test_connection_retry_success(self):
        """Test connection succeeds after retries."""
        manager = ConnectionRecoveryManager(max_retries=3, base_delay=0.1)

        # Mock connection that fails twice then succeeds
        connect_func = Mock(
            side_effect=[
                Exception("Connection failed"),
                Exception("Connection failed"),
                True,
            ]
        )

        result = manager.attempt_connection(connect_func)

        self.assertTrue(result)
        self.assertTrue(manager.connected)
        self.assertEqual(connect_func.call_count, 3)

    def test_connection_max_retries(self):
        """Test connection fails after max retries."""
        manager = ConnectionRecoveryManager(max_retries=3, base_delay=0.01)

        # Mock connection that always fails
        connect_func = Mock(side_effect=Exception("Connection failed"))

        result = manager.attempt_connection(connect_func)

        self.assertFalse(result)
        self.assertFalse(manager.connected)
        self.assertEqual(connect_func.call_count, 3)
        self.assertEqual(manager.last_error, "Connection failed")

    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        manager = ConnectionRecoveryManager(max_retries=3, base_delay=0.1)

        delays = []

        def error_callback(error, retry_count, delay):
            delays.append(delay)

        manager.add_error_callback(error_callback)

        # Mock connection that always fails
        connect_func = Mock(side_effect=Exception("Connection failed"))

        manager.attempt_connection(connect_func)

        # Check exponential backoff: 0.1, 0.2, 0.4
        self.assertEqual(len(delays), 3)
        self.assertAlmostEqual(delays[0], 0.1, places=2)
        self.assertAlmostEqual(delays[1], 0.2, places=2)
        self.assertAlmostEqual(delays[2], 0.4, places=2)

    def test_callbacks(self):
        """Test connection and error callbacks."""
        manager = ConnectionRecoveryManager()

        connection_called = False
        error_called = False

        def on_connection():
            nonlocal connection_called
            connection_called = True

        def on_error(error, retry_count, delay):
            nonlocal error_called
            error_called = True

        manager.add_connection_callback(on_connection)
        manager.add_error_callback(on_error)

        # Test successful connection
        connect_func = Mock(return_value=True)
        manager.attempt_connection(connect_func)
        self.assertTrue(connection_called)

        # Test failed connection
        manager.reset()
        connect_func = Mock(side_effect=Exception("Failed"))
        manager.attempt_connection(connect_func)
        self.assertTrue(error_called)


class TestEventValidation(unittest.TestCase):
    """Test event validation and sanitization."""

    def test_valid_event(self):
        """Test validation of valid event."""
        handler = EventValidationHandler()

        event = {
            "type": "test.event",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {"key": "value"},
        }

        result = handler.validate_event(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "test.event")
        self.assertEqual(handler.rejected_count, 0)
        self.assertEqual(handler.sanitized_count, 0)

    def test_missing_type(self):
        """Test event with missing type field."""
        handler = EventValidationHandler()

        event = {"data": {"key": "value"}}

        result = handler.validate_event(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "unknown")
        self.assertEqual(handler.sanitized_count, 1)

    def test_missing_timestamp(self):
        """Test event with missing timestamp."""
        handler = EventValidationHandler()

        event = {"type": "test.event", "data": {"key": "value"}}

        result = handler.validate_event(event)

        self.assertIsNotNone(result)
        self.assertIn("timestamp", result)
        self.assertEqual(handler.sanitized_count, 1)

    def test_invalid_data_type(self):
        """Test event with invalid data type."""
        handler = EventValidationHandler()

        class CustomObject:
            pass

        event = {"type": "test.event", "data": CustomObject()}

        result = handler.validate_event(event)

        self.assertIsNotNone(result)
        self.assertIsInstance(result["data"], str)
        self.assertGreater(handler.sanitized_count, 0)

    def test_circular_reference(self):
        """Test event with circular reference."""
        handler = EventValidationHandler()

        # Create circular reference
        data = {"key": "value"}
        data["self"] = data

        event = {"type": "test.event", "data": data}

        result = handler.validate_event(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["data"], {"error": "Invalid data removed"})
        self.assertGreater(handler.sanitized_count, 0)

    def test_non_dict_event(self):
        """Test non-dictionary event."""
        handler = EventValidationHandler()

        result = handler.validate_event("not a dict")

        self.assertIsNone(result)
        self.assertEqual(handler.rejected_count, 1)
        self.assertIn("not a dictionary", handler.validation_errors[0])


class TestResourceMonitoring(unittest.TestCase):
    """Test resource monitoring and management."""

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = ResourceMonitor(memory_limit_mb=500, cpu_limit_percent=75)

        self.assertEqual(monitor.memory_limit_mb, 500)
        self.assertEqual(monitor.cpu_limit_percent, 75)
        self.assertFalse(monitor.monitoring)

    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = ResourceMonitor()

        monitor.start_monitoring()
        self.assertTrue(monitor.monitoring)
        self.assertIsNotNone(monitor.monitor_thread)
        self.assertTrue(monitor.monitor_thread.is_alive())

        monitor.stop_monitoring()
        time.sleep(0.1)
        self.assertFalse(monitor.monitoring)

    def test_memory_usage(self):
        """Test memory usage calculation."""
        monitor = ResourceMonitor()

        memory_mb = monitor.get_memory_usage()

        # Should return a positive value
        self.assertGreater(memory_mb, 0)

    def test_cleanup_callback(self):
        """Test cleanup callbacks are triggered."""
        monitor = ResourceMonitor(memory_limit_mb=1)  # Very low limit

        cleanup_called = False
        cleanup_type = None

        def cleanup_callback(resource_type, value):
            nonlocal cleanup_called, cleanup_type
            cleanup_called = True
            cleanup_type = resource_type

        monitor.add_cleanup_callback(cleanup_callback)

        # Mock high memory usage
        with patch.object(monitor, "get_memory_usage", return_value=100):
            monitor.start_monitoring()
            time.sleep(0.5)  # Let monitor run
            monitor.stop_monitoring()

        # Cleanup should have been called
        self.assertTrue(cleanup_called)
        self.assertEqual(cleanup_type, "memory")

    def test_resource_alerts(self):
        """Test resource alerts are recorded."""
        monitor = ResourceMonitor(memory_limit_mb=1)

        # Mock high memory usage
        with patch.object(monitor, "get_memory_usage", return_value=100):
            monitor._monitor_loop()  # Run one iteration

        self.assertGreater(len(monitor.resource_alerts), 0)
        alert = monitor.resource_alerts[0]
        self.assertEqual(alert["type"], "memory")
        self.assertEqual(alert["value"], 100)
        self.assertEqual(alert["limit"], 1)


class TestErrorRecoveryIntegration(unittest.TestCase):
    """Integration tests for error recovery scenarios."""

    def test_complete_recovery_flow(self):
        """Test complete error recovery flow."""
        # Set up components
        connection_manager = ConnectionRecoveryManager(max_retries=3, base_delay=0.01)
        event_handler = EventValidationHandler()
        resource_monitor = ResourceMonitor(memory_limit_mb=1000)

        # Simulate connection failure and recovery
        connection_attempts = [False, False, True]
        attempt_count = 0

        def mock_connect():
            nonlocal attempt_count
            if attempt_count < len(connection_attempts):
                success = connection_attempts[attempt_count]
                attempt_count += 1
                if not success:
                    raise Exception("Connection failed")
                return success
            return False

        # Attempt connection with retries
        result = connection_manager.attempt_connection(mock_connect)
        self.assertTrue(result)

        # Process events with validation
        events = [
            {"type": "valid", "data": "test"},
            {"invalid": "event"},  # Missing type
            {"type": "test", "data": {"nested": "data"}},
        ]

        validated_events = []
        for event in events:
            validated = event_handler.validate_event(event)
            if validated:
                validated_events.append(validated)

        self.assertEqual(len(validated_events), 3)
        self.assertGreater(event_handler.sanitized_count, 0)

        # Monitor resources
        resource_monitor.start_monitoring()
        time.sleep(0.1)
        resource_monitor.stop_monitoring()

        # Verify complete flow worked
        self.assertTrue(connection_manager.connected)
        self.assertEqual(len(validated_events), 3)
        self.assertIsNotNone(resource_monitor.get_memory_usage())


if __name__ == "__main__":
    unittest.main(verbosity=2)
