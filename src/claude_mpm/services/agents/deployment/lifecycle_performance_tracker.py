"""Performance tracking for agent lifecycle manager.

This module provides performance metrics tracking functionality for the AgentLifecycleManager.
Extracted to reduce complexity and improve maintainability.
"""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .agent_lifecycle_manager import LifecycleOperationResult


class LifecyclePerformanceTracker:
    """Handles performance metrics tracking for the lifecycle manager."""

    def __init__(self, performance_metrics: Dict[str, Any]):
        """Initialize the performance tracker."""
        self.performance_metrics = performance_metrics

    def update_metrics(self, result: "LifecycleOperationResult") -> None:
        """Update performance metrics with operation result.

        METRICS COLLECTION:
        This method demonstrates a simple ETL pipeline for operational metrics:

        1. EXTRACT: Pull raw data from operation results
           - Success/failure status
           - Operation duration
           - Cache invalidation events
           - Operation type and agent tier

        2. TRANSFORM: Calculate derived metrics
           - Success rates and failure percentages
           - Rolling averages for performance
           - Operation distribution by type
           - Performance by agent tier

        3. LOAD: Store in metrics structure
           - In-memory storage for real-time access
           - Could be extended to push to:
             * Time-series databases (Prometheus, InfluxDB)
             * AI observability platforms (Datadog, New Relic)
             * Custom analytics pipelines

        OPTIMIZATION OPPORTUNITIES:
        - Add percentile calculations (p50, p95, p99)
        - Track operation queuing times
        - Monitor resource usage per operation
        - Implement sliding window metrics
        """
        self.performance_metrics["total_operations"] += 1

        if result.success:
            self.performance_metrics["successful_operations"] += 1
        else:
            self.performance_metrics["failed_operations"] += 1

        # Update average duration using incremental calculation
        # This avoids storing all durations in memory
        total_ops = self.performance_metrics["total_operations"]
        current_avg = self.performance_metrics["average_duration_ms"]
        new_avg = ((current_avg * (total_ops - 1)) + result.duration_ms) / total_ops
        self.performance_metrics["average_duration_ms"] = new_avg

        # METRICS: Track operation type distribution
        # This helps identify which operations are most common
        op_type = result.operation.value
        if "operation_distribution" not in self.performance_metrics:
            self.performance_metrics["operation_distribution"] = {}
        self.performance_metrics["operation_distribution"][op_type] = (
            self.performance_metrics["operation_distribution"].get(op_type, 0) + 1
        )

        # METRICS: Track performance by agent tier
        # Useful for identifying tier-specific performance issues
        if hasattr(result, "tier") and result.tier:
            if "tier_performance" not in self.performance_metrics:
                self.performance_metrics["tier_performance"] = {}
            tier_name = (
                result.tier.value if hasattr(result.tier, "value") else str(result.tier)
            )
            if tier_name not in self.performance_metrics["tier_performance"]:
                self.performance_metrics["tier_performance"][tier_name] = {
                    "count": 0,
                    "total_duration_ms": 0,
                    "average_duration_ms": 0,
                }
            tier_metrics = self.performance_metrics["tier_performance"][tier_name]
            tier_metrics["count"] += 1
            tier_metrics["total_duration_ms"] += result.duration_ms
            tier_metrics["average_duration_ms"] = (
                tier_metrics["total_duration_ms"] / tier_metrics["count"]
            )

        # Update cache hit rate if cache was involved
        if result.cache_invalidated:
            # Track cache invalidation frequency
            if "cache_invalidations" not in self.performance_metrics:
                self.performance_metrics["cache_invalidations"] = 0
            self.performance_metrics["cache_invalidations"] += 1
