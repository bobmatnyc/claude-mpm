"""
Stability Monitoring Interfaces for Claude MPM Framework
==========================================================

WHY: This module defines interfaces for proactive stability monitoring including
memory leak detection, log monitoring, and resource exhaustion prevention.

DESIGN DECISION: Separated from health checks to enable preventive monitoring
that triggers actions BEFORE crashes occur. Provides early warning systems.

ARCHITECTURE:
- IMemoryLeakDetector: Interface for memory leak detection using trend analysis
- ILogMonitor: Interface for real-time log file monitoring and pattern matching
- IResourceMonitor: Interface for comprehensive resource usage tracking

USAGE:
    memory_detector = MemoryLeakDetector(leak_threshold_mb_per_minute=10.0)
    log_monitor = LogMonitor(log_file="/var/log/app.log")
    resource_monitor = ResourceMonitor(fd_threshold_percent=0.8)

    # Integrate with health monitoring
    health_manager.add_stability_monitors(
        memory_detector=memory_detector,
        log_monitor=log_monitor,
        resource_monitor=resource_monitor,
    )
"""

from abc import ABC, abstractmethod
from typing import Callable, List

from claude_mpm.services.core.models.stability import (
    LogPatternMatch,
    MemoryTrend,
    ResourceUsage,
)


class IMemoryLeakDetector(ABC):
    """
    Interface for memory leak detection using trend analysis.

    WHY: Memory leaks are a common cause of process crashes. Early detection
    enables preemptive restarts BEFORE the OOM killer terminates the process.

    DESIGN DECISION: Uses slope-based trend analysis over a rolling window
    to detect sustained memory growth patterns, filtering out normal variations.

    Algorithm:
    1. Maintain rolling window of memory measurements (timestamp, memory_mb)
    2. Calculate linear regression slope (MB per minute)
    3. Detect leak if slope exceeds threshold (default: 10 MB/minute)
    4. Trigger alert when leak detected and memory > 80% limit

    Thread Safety: Implementations must be thread-safe for concurrent access.
    """

    @abstractmethod
    def record_memory_usage(self, deployment_id: str, memory_mb: float) -> None:
        """
        Record a memory usage measurement.

        WHY: Builds historical data for trend analysis. Should be called
        periodically (e.g., every 30s) to collect sufficient data points.

        Args:
            deployment_id: Deployment identifier
            memory_mb: Current memory usage in megabytes
        """

    @abstractmethod
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

    @abstractmethod
    def is_leaking(self, deployment_id: str) -> bool:
        """
        Check if deployment has a detected memory leak.

        Returns:
            True if leak detected (sustained memory growth)
        """

    @abstractmethod
    def register_leak_callback(
        self, callback: Callable[[str, MemoryTrend], None]
    ) -> None:
        """
        Register callback for leak detection events.

        Args:
            callback: Function called with (deployment_id, trend) when leak detected
        """


class ILogMonitor(ABC):
    """
    Interface for real-time log file monitoring and pattern matching.

    WHY: Application logs contain early warning signals (exceptions, OOM errors,
    segfaults) that predict imminent crashes. Real-time monitoring enables
    proactive intervention.

    DESIGN DECISION: Uses watchdog library for efficient file system monitoring.
    Avoids polling by receiving file modification events from the OS.

    Pattern Matching:
    - Regex-based patterns for flexibility
    - Configurable patterns per deployment
    - Built-in patterns for common errors:
      * OutOfMemoryError
      * Segmentation fault
      * Exception: / Traceback
      * Database connection errors
      * Network timeouts

    Thread Safety: Uses watchdog's thread-safe event handling.
    """

    @abstractmethod
    def start_monitoring(self, log_file: str, deployment_id: str) -> None:
        """
        Start monitoring a log file for error patterns.

        WHY: Begins watching the log file for new entries. Uses OS-level
        file system events for efficiency.

        Args:
            log_file: Path to log file to monitor
            deployment_id: Deployment identifier for callbacks
        """

    @abstractmethod
    def stop_monitoring(self, deployment_id: str) -> None:
        """
        Stop monitoring a deployment's log file.

        Args:
            deployment_id: Deployment identifier
        """

    @abstractmethod
    def add_pattern(self, pattern: str, severity: str = "ERROR") -> None:
        """
        Add an error pattern to monitor.

        Args:
            pattern: Regex pattern to match
            severity: Error severity (ERROR, CRITICAL, WARNING)
        """

    @abstractmethod
    def get_recent_matches(
        self, deployment_id: str, limit: int = 10
    ) -> List[LogPatternMatch]:
        """
        Get recent pattern matches for a deployment.

        Args:
            deployment_id: Deployment identifier
            limit: Maximum number of matches to return

        Returns:
            List of LogPatternMatch objects, newest first
        """

    @abstractmethod
    def register_match_callback(
        self, callback: Callable[[str, LogPatternMatch], None]
    ) -> None:
        """
        Register callback for pattern matches.

        Args:
            callback: Function called with (deployment_id, match) when pattern detected
        """


class IResourceMonitor(ABC):
    """
    Interface for comprehensive resource usage monitoring.

    WHY: Resource exhaustion (file descriptors, threads, connections, disk space)
    causes crashes and degradation. Monitoring enables preemptive action at 80%
    thresholds before hitting hard limits.

    DESIGN DECISION: Extends basic resource health checks with:
    - Higher granularity (more frequent checks)
    - Percentage-based thresholds (80% of ulimit)
    - Trend analysis for growth rate
    - Integration with restart manager for preemptive restarts

    Resource Types:
    1. File Descriptors: Critical for I/O operations (Unix: ulimit -n)
    2. Threads: Memory and scheduling overhead
    3. Network Connections: Socket exhaustion
    4. Disk Space: Working directory availability

    Thread Safety: Implementations must be thread-safe.
    """

    @abstractmethod
    def check_resources(self, deployment_id: str) -> ResourceUsage:
        """
        Check resource usage for a deployment.

        WHY: Provides comprehensive snapshot of resource consumption across
        all monitored resource types.

        Args:
            deployment_id: Deployment identifier

        Returns:
            ResourceUsage with current metrics and critical status

        Raises:
            ValueError: If deployment not found
        """

    @abstractmethod
    def is_critical(self, deployment_id: str) -> bool:
        """
        Check if any resource is at critical threshold (>80%).

        Returns:
            True if any resource exceeds 80% of limit
        """

    @abstractmethod
    def register_critical_callback(
        self, callback: Callable[[str, ResourceUsage], None]
    ) -> None:
        """
        Register callback for critical resource usage.

        Args:
            callback: Function called with (deployment_id, usage) when critical
        """


__all__ = [
    "ILogMonitor",
    "IMemoryLeakDetector",
    "IResourceMonitor",
]
