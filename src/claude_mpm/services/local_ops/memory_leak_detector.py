"""
Memory Leak Detector for Claude MPM Framework
==============================================

WHY: Detects memory leaks BEFORE they cause OOM crashes by analyzing memory
usage trends over time using linear regression slope analysis.

DESIGN DECISION: Uses rolling window of memory measurements with configurable
size and threshold. Calculates slope to detect sustained memory growth patterns.

ARCHITECTURE:
- Rolling window of (timestamp, memory_mb) measurements per deployment
- Slope-based leak detection: MB/minute growth rate
- Configurable thresholds and window sizes
- Callback system for leak detection alerts
- Thread-safe with proper locking

USAGE:
    detector = MemoryLeakDetector(
        leak_threshold_mb_per_minute=10.0,
        window_size=100,
    )
    detector.initialize()

    # Record memory usage periodically
    detector.record_memory_usage(deployment_id, memory_mb)

    # Check for leaks
    trend = detector.analyze_trend(deployment_id)
    if trend.is_leaking:
        print(f"Leak detected! Slope: {trend.slope_mb_per_minute} MB/min")
"""

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Tuple

from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.stability import IMemoryLeakDetector
from claude_mpm.services.core.models.stability import MemoryTrend


class MemoryLeakDetector(SyncBaseService, IMemoryLeakDetector):
    """
    Memory leak detection service using trend analysis.

    WHY: Provides early warning of memory leaks by analyzing memory growth
    patterns over time, enabling preemptive restarts before OOM crashes.

    Algorithm:
    1. Maintain rolling window of memory measurements
    2. Calculate linear slope (MB per minute)
    3. Detect leak if slope exceeds threshold (default: 10 MB/min)

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    def __init__(
        self,
        leak_threshold_mb_per_minute: float = 10.0,
        window_size: int = 100,
    ):
        """
        Initialize memory leak detector.

        Args:
            leak_threshold_mb_per_minute: Threshold for leak detection (default: 10.0)
            window_size: Number of measurements to keep in rolling window (default: 100)
        """
        super().__init__("MemoryLeakDetector")
        self.leak_threshold = leak_threshold_mb_per_minute
        self.window_size = window_size

        # Memory measurements: deployment_id -> List[(timestamp, memory_mb)]
        self._measurements: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)

        # Thread safety
        self._lock = threading.Lock()

        # Leak detection callbacks
        self._leak_callbacks: List[Callable[[str, MemoryTrend], None]] = []

    def initialize(self) -> bool:
        """
        Initialize the memory leak detector.

        Returns:
            True if initialization successful
        """
        self._initialized = True
        self.log_info(
            f"Memory leak detector initialized "
            f"(threshold={self.leak_threshold} MB/min, window={self.window_size})"
        )
        return True

    def shutdown(self) -> None:
        """Shutdown memory leak detector and clear data."""
        with self._lock:
            self._measurements.clear()
            self._leak_callbacks.clear()

        self._shutdown = True
        self.log_info("Memory leak detector shutdown complete")

    def record_memory_usage(self, deployment_id: str, memory_mb: float) -> None:
        """
        Record a memory usage measurement.

        WHY: Builds historical data for trend analysis. Should be called
        periodically (e.g., every 30s) to collect sufficient data points.

        Args:
            deployment_id: Deployment identifier
            memory_mb: Current memory usage in megabytes
        """
        with self._lock:
            # Add new measurement
            timestamp = datetime.now(tz=timezone.utc)
            self._measurements[deployment_id].append((timestamp, memory_mb))

            # Trim to window size
            if len(self._measurements[deployment_id]) > self.window_size:
                self._measurements[deployment_id] = self._measurements[deployment_id][
                    -self.window_size :
                ]

            self.log_debug(
                f"Recorded memory usage for {deployment_id}: {memory_mb:.2f}MB "
                f"({len(self._measurements[deployment_id])} measurements)"
            )

    def analyze_trend(self, deployment_id: str) -> MemoryTrend:
        """
        Analyze memory usage trend for leak detection.

        WHY: Computes slope of memory usage over time to detect sustained
        growth patterns characteristic of memory leaks.

        Args:
            deployment_id: Deployment identifier

        Returns:
            MemoryTrend with slope analysis and leak detection result

        Algorithm:
            slope_mb_per_minute = (recent_memory - old_memory) / time_delta_minutes
            is_leaking = slope_mb_per_minute > threshold
        """
        with self._lock:
            measurements = self._measurements.get(deployment_id, [])

            # Need at least 2 measurements for trend analysis
            if len(measurements) < 2:
                return MemoryTrend(
                    deployment_id=deployment_id,
                    timestamps=[],
                    memory_mb=[],
                    slope_mb_per_minute=0.0,
                    is_leaking=False,
                    window_size=0,
                    threshold_mb_per_minute=self.leak_threshold,
                )

            # Extract timestamps and memory values
            timestamps = [ts for ts, _ in measurements]
            memory_mb = [mem for _, mem in measurements]

            # Calculate slope using simple linear trend
            slope = self._calculate_slope(measurements)

            # Detect leak if slope exceeds threshold
            is_leaking = slope > self.leak_threshold

            trend = MemoryTrend(
                deployment_id=deployment_id,
                timestamps=timestamps,
                memory_mb=memory_mb,
                slope_mb_per_minute=slope,
                is_leaking=is_leaking,
                window_size=len(measurements),
                threshold_mb_per_minute=self.leak_threshold,
            )

            # Trigger callbacks if leak detected
            if is_leaking:
                self.log_warning(
                    f"Memory leak detected for {deployment_id}: "
                    f"{slope:.2f} MB/min (threshold: {self.leak_threshold} MB/min)"
                )
                self._trigger_leak_callbacks(deployment_id, trend)

            return trend

    def is_leaking(self, deployment_id: str) -> bool:
        """
        Check if deployment has a detected memory leak.

        Returns:
            True if leak detected (sustained memory growth)
        """
        trend = self.analyze_trend(deployment_id)
        return trend.is_leaking

    def register_leak_callback(
        self, callback: Callable[[str, MemoryTrend], None]
    ) -> None:
        """
        Register callback for leak detection events.

        Args:
            callback: Function called with (deployment_id, trend) when leak detected
        """
        with self._lock:
            self._leak_callbacks.append(callback)
            self.log_debug(f"Registered leak callback: {callback.__name__}")

    def _calculate_slope(self, measurements: List[Tuple[datetime, float]]) -> float:
        """
        Calculate memory growth slope using simple linear regression.

        WHY: Linear slope provides a robust measure of sustained memory growth,
        filtering out normal variations and temporary spikes.

        Args:
            measurements: List of (timestamp, memory_mb) tuples

        Returns:
            Slope in MB per minute

        Algorithm:
            Simple two-point slope: (y2 - y1) / (x2 - x1)
            Where x is time in minutes, y is memory in MB
        """
        if len(measurements) < 2:
            return 0.0

        # Get first and last measurements
        first_timestamp, first_memory = measurements[0]
        last_timestamp, last_memory = measurements[-1]

        # Calculate time delta in minutes
        time_delta_seconds = (last_timestamp - first_timestamp).total_seconds()
        time_delta_minutes = time_delta_seconds / 60.0

        if time_delta_minutes == 0:
            return 0.0

        # Calculate slope (MB per minute)
        memory_delta = last_memory - first_memory
        return memory_delta / time_delta_minutes

    def _trigger_leak_callbacks(self, deployment_id: str, trend: MemoryTrend) -> None:
        """
        Trigger registered callbacks for leak detection.

        Args:
            deployment_id: Deployment that has a leak
            trend: MemoryTrend with leak analysis
        """
        for callback in self._leak_callbacks:
            try:
                callback(deployment_id, trend)
            except Exception as e:
                self.log_error(f"Error in leak callback {callback.__name__}: {e}")

    def get_measurements(self, deployment_id: str) -> List[Tuple[datetime, float]]:
        """
        Get all measurements for a deployment (for testing/debugging).

        Args:
            deployment_id: Deployment identifier

        Returns:
            List of (timestamp, memory_mb) tuples
        """
        with self._lock:
            return list(self._measurements.get(deployment_id, []))

    def clear_measurements(self, deployment_id: str) -> None:
        """
        Clear measurements for a deployment (e.g., after restart).

        Args:
            deployment_id: Deployment identifier
        """
        with self._lock:
            if deployment_id in self._measurements:
                del self._measurements[deployment_id]
                self.log_debug(f"Cleared measurements for {deployment_id}")


__all__ = ["MemoryLeakDetector"]
