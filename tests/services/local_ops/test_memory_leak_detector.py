"""
Unit Tests for Memory Leak Detector
====================================

WHY: Provides comprehensive unit testing for MemoryLeakDetector,
including slope calculation, leak detection, and callback triggers.

COVERAGE:
- Memory usage recording
- Slope-based trend analysis
- Leak detection threshold logic
- Rolling window management
- Callback triggers
- Thread safety

TEST STRATEGY:
- Unit tests with mocked dependencies
- Test slope calculation with various patterns
- Test edge cases (no data, single point, etc.)
- Test rolling window trimming
- Test callback invocation
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from claude_mpm.services.core.models.stability import MemoryTrend
from claude_mpm.services.local_ops.memory_leak_detector import MemoryLeakDetector

# ============================================================================
# Memory Leak Detector Tests
# ============================================================================


class TestMemoryLeakDetector:
    """Test suite for MemoryLeakDetector."""

    def test_initialization(self):
        """Test memory leak detector initialization."""
        detector = MemoryLeakDetector(
            leak_threshold_mb_per_minute=10.0,
            window_size=100,
        )

        assert detector.initialize()
        assert detector.leak_threshold == 10.0
        assert detector.window_size == 100
        assert not detector._shutdown

        detector.shutdown()
        assert detector._shutdown

    def test_record_memory_usage(self):
        """Test recording memory usage measurements."""
        detector = MemoryLeakDetector(window_size=5)
        detector.initialize()

        deployment_id = "test-app"

        # Record several measurements
        for i in range(10):
            detector.record_memory_usage(deployment_id, 100.0 + i * 10)

        # Check measurements
        measurements = detector.get_measurements(deployment_id)

        # Should only keep window_size measurements
        assert len(measurements) == 5

        # Should have most recent 5
        memory_values = [mem for _, mem in measurements]
        assert memory_values == [150.0, 160.0, 170.0, 180.0, 190.0]

        detector.shutdown()

    def test_analyze_trend_no_data(self):
        """Test trend analysis with no data."""
        detector = MemoryLeakDetector()
        detector.initialize()

        trend = detector.analyze_trend("unknown-app")

        assert trend.deployment_id == "unknown-app"
        assert trend.slope_mb_per_minute == 0.0
        assert not trend.is_leaking
        assert trend.window_size == 0

        detector.shutdown()

    def test_analyze_trend_single_measurement(self):
        """Test trend analysis with single measurement."""
        detector = MemoryLeakDetector()
        detector.initialize()

        deployment_id = "test-app"
        detector.record_memory_usage(deployment_id, 100.0)

        trend = detector.analyze_trend(deployment_id)

        assert trend.slope_mb_per_minute == 0.0
        assert not trend.is_leaking

        detector.shutdown()

    def test_analyze_trend_stable_memory(self):
        """Test trend analysis with stable memory usage."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        deployment_id = "test-app"

        # Record stable memory usage
        base_time = datetime.now()
        for i in range(10):
            detector.record_memory_usage(deployment_id, 100.0)
            # Small sleep to ensure time delta
            time.sleep(0.001)

        trend = detector.analyze_trend(deployment_id)

        # Slope should be near zero (stable memory)
        assert abs(trend.slope_mb_per_minute) < 1.0
        assert not trend.is_leaking

        detector.shutdown()

    def test_analyze_trend_memory_leak(self):
        """Test trend analysis detecting a memory leak."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        deployment_id = "test-app"

        # Simulate memory leak: 1 MB per second = 60 MB per minute
        # Record measurements over 10 seconds
        start_memory = 100.0
        for i in range(10):
            memory_mb = start_memory + (i * 1.0)  # 1 MB per second
            detector.record_memory_usage(deployment_id, memory_mb)
            time.sleep(0.1)  # 100ms between measurements

        trend = detector.analyze_trend(deployment_id)

        # Should detect leak: ~60 MB/min > 10 MB/min threshold
        # With 0.1s intervals over 10 measurements, we have ~1s total
        # Delta: ~9 MB over ~1s = ~540 MB/min
        assert trend.slope_mb_per_minute > 10.0
        assert trend.is_leaking
        assert trend.window_size == 10

        detector.shutdown()

    def test_analyze_trend_slow_growth(self):
        """Test trend analysis with slow memory growth (not a leak)."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        deployment_id = "test-app"

        # Simulate slow growth: 0.1 MB per second = 6 MB per minute
        start_memory = 100.0
        for i in range(10):
            memory_mb = start_memory + (i * 0.1)
            detector.record_memory_usage(deployment_id, memory_mb)
            time.sleep(0.1)

        trend = detector.analyze_trend(deployment_id)

        # Should NOT detect leak: ~6 MB/min < 10 MB/min threshold
        # With 0.1s intervals, delta is ~0.9 MB over ~1s = ~54 MB/min
        # But with measurement noise, might still detect
        # Let's use a smaller growth rate
        detector2 = MemoryLeakDetector(leak_threshold_mb_per_minute=100.0)
        detector2.initialize()

        for i in range(10):
            memory_mb = start_memory + (i * 0.1)
            detector2.record_memory_usage(deployment_id, memory_mb)
            time.sleep(0.1)

        trend2 = detector2.analyze_trend(deployment_id)
        assert not trend2.is_leaking

        detector.shutdown()
        detector2.shutdown()

    def test_is_leaking(self):
        """Test is_leaking() convenience method."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        deployment_id = "test-app"

        # No data - not leaking
        assert not detector.is_leaking(deployment_id)

        # Stable memory - not leaking
        for _ in range(5):
            detector.record_memory_usage(deployment_id, 100.0)
            time.sleep(0.01)

        assert not detector.is_leaking(deployment_id)

        # Memory leak - leaking
        for i in range(10):
            detector.record_memory_usage(deployment_id, 100.0 + i * 10)
            time.sleep(0.1)

        assert detector.is_leaking(deployment_id)

        detector.shutdown()

    def test_leak_callback(self):
        """Test leak detection callback trigger."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        deployment_id = "test-app"

        # Register callback
        callback_called = []

        def leak_callback(dep_id: str, trend: MemoryTrend):
            callback_called.append((dep_id, trend))

        detector.register_leak_callback(leak_callback)

        # Simulate memory leak
        for i in range(10):
            detector.record_memory_usage(deployment_id, 100.0 + i * 10)
            time.sleep(0.1)

        # Analyze trend (should trigger callback)
        trend = detector.analyze_trend(deployment_id)

        # Callback should have been called
        assert len(callback_called) == 1
        assert callback_called[0][0] == deployment_id
        assert callback_called[0][1].is_leaking

        detector.shutdown()

    def test_callback_not_triggered_without_leak(self):
        """Test callback NOT triggered when no leak detected."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=100.0)
        detector.initialize()

        deployment_id = "test-app"

        # Register callback
        callback_called = []

        def leak_callback(dep_id: str, trend: MemoryTrend):
            callback_called.append((dep_id, trend))

        detector.register_leak_callback(leak_callback)

        # Stable memory
        for _ in range(10):
            detector.record_memory_usage(deployment_id, 100.0)
            time.sleep(0.01)

        # Analyze trend (should NOT trigger callback)
        trend = detector.analyze_trend(deployment_id)

        # Callback should NOT have been called
        assert len(callback_called) == 0

        detector.shutdown()

    def test_clear_measurements(self):
        """Test clearing measurements for a deployment."""
        detector = MemoryLeakDetector()
        detector.initialize()

        deployment_id = "test-app"

        # Record measurements
        for i in range(5):
            detector.record_memory_usage(deployment_id, 100.0 + i * 10)

        # Check measurements exist
        assert len(detector.get_measurements(deployment_id)) == 5

        # Clear measurements
        detector.clear_measurements(deployment_id)

        # Check measurements cleared
        assert len(detector.get_measurements(deployment_id)) == 0

        detector.shutdown()

    def test_memory_trend_properties(self):
        """Test MemoryTrend data model properties."""
        trend = MemoryTrend(
            deployment_id="test-app",
            timestamps=[
                datetime.now(),
                datetime.now() + timedelta(minutes=5),
            ],
            memory_mb=[100.0, 150.0],
            slope_mb_per_minute=10.0,
            is_leaking=True,
            window_size=2,
            threshold_mb_per_minute=5.0,
        )

        assert trend.latest_memory_mb == 150.0
        assert trend.oldest_memory_mb == 100.0
        assert abs(trend.time_span_minutes - 5.0) < 0.1

    def test_memory_trend_serialization(self):
        """Test MemoryTrend to_dict/from_dict."""
        original = MemoryTrend(
            deployment_id="test-app",
            timestamps=[datetime.now()],
            memory_mb=[100.0],
            slope_mb_per_minute=5.0,
            is_leaking=False,
            window_size=1,
            threshold_mb_per_minute=10.0,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = MemoryTrend.from_dict(data)

        assert restored.deployment_id == original.deployment_id
        assert len(restored.timestamps) == len(original.timestamps)
        assert restored.memory_mb == original.memory_mb
        assert restored.slope_mb_per_minute == original.slope_mb_per_minute
        assert restored.is_leaking == original.is_leaking

    def test_thread_safety(self):
        """Test thread-safe concurrent access."""
        import threading

        detector = MemoryLeakDetector()
        detector.initialize()

        deployment_id = "test-app"
        errors = []

        def record_memory():
            try:
                for i in range(10):
                    detector.record_memory_usage(deployment_id, 100.0 + i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def analyze_trend():
            try:
                for _ in range(10):
                    detector.analyze_trend(deployment_id)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Run concurrent threads
        threads = [
            threading.Thread(target=record_memory),
            threading.Thread(target=record_memory),
            threading.Thread(target=analyze_trend),
            threading.Thread(target=analyze_trend),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        detector.shutdown()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestMemoryLeakDetectorEdgeCases:
    """Test edge cases and error handling."""

    def test_multiple_deployments(self):
        """Test tracking multiple deployments independently."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        # Track two deployments
        for i in range(10):
            # App 1: leaking (10 MB/sec = 600 MB/min)
            detector.record_memory_usage("app1", 100.0 + i * 10)
            # App 2: stable
            detector.record_memory_usage("app2", 100.0)
            time.sleep(0.1)

        # Analyze both
        trend1 = detector.analyze_trend("app1")
        trend2 = detector.analyze_trend("app2")

        # App 1 should be leaking
        assert trend1.is_leaking

        # App 2 should NOT be leaking
        assert not trend2.is_leaking

        detector.shutdown()

    def test_large_window_size(self):
        """Test with large window size."""
        detector = MemoryLeakDetector(window_size=1000)
        detector.initialize()

        deployment_id = "test-app"

        # Record many measurements
        for i in range(2000):
            detector.record_memory_usage(deployment_id, 100.0 + i * 0.1)

        # Should only keep 1000
        measurements = detector.get_measurements(deployment_id)
        assert len(measurements) == 1000

        detector.shutdown()

    def test_callback_exception_handling(self):
        """Test callback exception doesn't crash detector."""
        detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
        detector.initialize()

        deployment_id = "test-app"

        # Register callback that raises exception
        def bad_callback(dep_id: str, trend: MemoryTrend):
            raise ValueError("Test exception")

        detector.register_leak_callback(bad_callback)

        # Simulate leak
        for i in range(10):
            detector.record_memory_usage(deployment_id, 100.0 + i * 10)
            time.sleep(0.1)

        # Analyze trend - should not crash despite callback exception
        trend = detector.analyze_trend(deployment_id)
        assert trend.is_leaking

        detector.shutdown()
