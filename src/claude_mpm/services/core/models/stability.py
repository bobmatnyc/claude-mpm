"""
Stability Monitoring Data Models for Claude MPM Framework
===========================================================

WHY: This module defines data structures for stability monitoring operations,
including memory leak detection, log pattern matching, and resource usage tracking.

DESIGN DECISION: Uses dataclasses for immutability and type safety. Provides
clear data structures for proactive monitoring and crash prevention.

ARCHITECTURE:
- MemoryTrend: Memory usage trend analysis with leak detection
- LogPatternMatch: Log pattern match with severity and context
- ResourceUsage: Comprehensive resource usage snapshot
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MemoryTrend:
    """
    Memory usage trend analysis result.

    WHY: Provides structured data for memory leak detection, including
    historical measurements, slope calculation, and leak detection status.

    Attributes:
        deployment_id: Unique deployment identifier
        timestamps: List of measurement timestamps
        memory_mb: List of memory measurements in megabytes
        slope_mb_per_minute: Calculated memory growth rate (MB/minute)
        is_leaking: Whether a memory leak was detected
        window_size: Number of measurements in the analysis window
        threshold_mb_per_minute: Leak detection threshold used
    """

    deployment_id: str
    timestamps: List[datetime] = field(default_factory=list)
    memory_mb: List[float] = field(default_factory=list)
    slope_mb_per_minute: float = 0.0
    is_leaking: bool = False
    window_size: int = 0
    threshold_mb_per_minute: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with datetimes converted to ISO format
        """
        data = asdict(self)
        data["timestamps"] = [ts.isoformat() for ts in self.timestamps]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryTrend":
        """
        Create MemoryTrend from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            MemoryTrend instance
        """
        # Convert ISO strings to datetime
        if isinstance(data.get("timestamps"), list):
            data["timestamps"] = [
                datetime.fromisoformat(ts) if isinstance(ts, str) else ts
                for ts in data["timestamps"]
            ]

        return cls(**data)

    @property
    def latest_memory_mb(self) -> float:
        """Get the most recent memory measurement."""
        return self.memory_mb[-1] if self.memory_mb else 0.0

    @property
    def oldest_memory_mb(self) -> float:
        """Get the oldest memory measurement in the window."""
        return self.memory_mb[0] if self.memory_mb else 0.0

    @property
    def time_span_minutes(self) -> float:
        """Get the time span covered by the measurements in minutes."""
        if len(self.timestamps) < 2:
            return 0.0
        delta = self.timestamps[-1] - self.timestamps[0]
        return delta.total_seconds() / 60.0


@dataclass
class LogPatternMatch:
    """
    Result of a log pattern match.

    WHY: Contains all information about a detected error pattern in logs,
    enabling analysis, alerting, and debugging of issues before they cause crashes.

    Attributes:
        deployment_id: Unique deployment identifier
        pattern: Regex pattern that matched
        line: The log line that matched
        timestamp: When the match was detected
        severity: Error severity level (ERROR, CRITICAL, WARNING)
        line_number: Line number in log file (if available)
        context: Additional context lines (before/after)
    """

    deployment_id: str
    pattern: str
    line: str
    timestamp: datetime = field(default_factory=datetime.now)
    severity: str = "ERROR"
    line_number: int = 0
    context: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with datetime converted to ISO format
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogPatternMatch":
        """
        Create LogPatternMatch from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            LogPatternMatch instance
        """
        # Convert ISO string to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)

    @property
    def is_critical(self) -> bool:
        """Check if this match represents a critical error."""
        return self.severity == "CRITICAL"


@dataclass
class ResourceUsage:
    """
    Comprehensive resource usage snapshot.

    WHY: Provides detailed resource consumption metrics across multiple
    resource types to enable preemptive action before exhaustion.

    Attributes:
        deployment_id: Unique deployment identifier
        file_descriptors: Current file descriptor count
        max_file_descriptors: Maximum file descriptors allowed (ulimit -n)
        threads: Current thread count
        connections: Current network connection count
        disk_free_mb: Free disk space in working directory (MB)
        is_critical: Whether any resource exceeds 80% threshold
        timestamp: When the measurement was taken
        details: Additional resource-specific details
    """

    deployment_id: str
    file_descriptors: int = 0
    max_file_descriptors: int = 0
    threads: int = 0
    connections: int = 0
    disk_free_mb: float = 0.0
    is_critical: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with datetime converted to ISO format
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceUsage":
        """
        Create ResourceUsage from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            ResourceUsage instance
        """
        # Convert ISO string to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)

    @property
    def fd_usage_percent(self) -> float:
        """Calculate file descriptor usage percentage."""
        if self.max_file_descriptors == 0:
            return 0.0
        return (self.file_descriptors / self.max_file_descriptors) * 100.0

    @property
    def is_fd_critical(self) -> bool:
        """Check if file descriptor usage is critical (>80%)."""
        return self.fd_usage_percent >= 80.0  # >= instead of > for 80% exactly

    def get_critical_resources(self) -> List[str]:
        """
        Get list of resources at critical levels.

        Returns:
            List of resource names exceeding 80% threshold
        """
        critical = []

        if self.is_fd_critical:
            critical.append(
                f"file_descriptors ({self.file_descriptors}/{self.max_file_descriptors})"
            )

        # Check thread count (threshold from details if available)
        thread_threshold = self.details.get("thread_threshold", 1000)
        if self.threads > thread_threshold * 0.8:
            critical.append(f"threads ({self.threads})")

        # Check connection count (threshold from details if available)
        connection_threshold = self.details.get("connection_threshold", 500)
        if self.connections > connection_threshold * 0.8:
            critical.append(f"connections ({self.connections})")

        # Check disk space (threshold from details if available)
        disk_threshold_mb = self.details.get("disk_threshold_mb", 100)
        if self.disk_free_mb < disk_threshold_mb:
            critical.append(f"disk_space ({self.disk_free_mb:.1f}MB free)")

        return critical


__all__ = [
    "LogPatternMatch",
    "MemoryTrend",
    "ResourceUsage",
]
