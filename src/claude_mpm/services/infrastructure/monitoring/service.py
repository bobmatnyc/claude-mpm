"""Service health monitoring for application-level metrics.

Monitors service-specific metrics like client connections, event processing, and error rates.
"""

import time
from typing import Any, Dict, List

from ....core.enums import HealthStatus
from .base import BaseMonitoringService, HealthMetric


class ServiceHealthService(BaseMonitoringService):
    """Service for monitoring application-level health metrics.

    Monitors:
    - Connected clients count
    - Event processing rate
    - Error rates
    - Response times
    - Service activity
    """

    def __init__(
        self,
        service_stats: Dict[str, Any],
        max_clients: int = 1000,
        max_error_rate: float = 0.1,
        stale_activity_seconds: int = 300,
    ):
        """Initialize service health monitoring.

        Args:
            service_stats: Reference to service statistics dictionary
            max_clients: Maximum allowed connected clients
            max_error_rate: Maximum allowed error rate (0.0-1.0)
            stale_activity_seconds: Seconds before activity is considered stale
        """
        super().__init__("ServiceHealth")
        self.service_stats = service_stats
        self.max_clients = max_clients
        self.max_error_rate = max_error_rate
        self.stale_activity_seconds = stale_activity_seconds

        # Rate calculation state
        self.last_check_time = time.time()
        self.last_events_processed = 0
        self.last_errors = 0

    async def check_health(self) -> List[HealthMetric]:
        """Check service-specific health metrics."""
        metrics = []
        current_time = time.time()

        # Connected clients
        metrics.extend(self._check_client_connections())

        # Event processing
        metrics.extend(self._check_event_processing(current_time))

        # Error rates
        metrics.extend(self._check_error_rates())

        # Service activity
        metrics.extend(self._check_service_activity(current_time))

        # Response times (if available)
        metrics.extend(self._check_response_times())

        # Update state for next check
        self.last_check_time = current_time

        return metrics

    def _check_client_connections(self) -> List[HealthMetric]:
        """Check client connection metrics."""
        metrics = []
        try:
            client_count = self.service_stats.get("clients_connected", 0)

            # Determine status based on thresholds
            if client_count > self.max_clients:
                client_status = HealthStatus.UNHEALTHY
            elif client_count > self.max_clients * 0.8:
                client_status = HealthStatus.DEGRADED
            else:
                client_status = HealthStatus.HEALTHY

            metrics.append(
                HealthMetric(
                    name="connected_clients",
                    value=client_count,
                    status=client_status,
                    threshold=self.max_clients,
                )
            )

            # Client connection rate (if available)
            if "connection_rate" in self.service_stats:
                metrics.append(
                    HealthMetric(
                        name="connection_rate",
                        value=self.service_stats["connection_rate"],
                        status=HealthStatus.HEALTHY,
                        unit="connections/sec",
                    )
                )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="connected_clients",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to get client count: {e}",
                )
            )
        return metrics

    def _check_event_processing(self, current_time: float) -> List[HealthMetric]:
        """Check event processing metrics."""
        metrics = []
        try:
            events_processed = self.service_stats.get("events_processed", 0)

            # Calculate processing rate
            time_diff = current_time - self.last_check_time
            if time_diff > 0 and self.last_events_processed > 0:
                event_rate = (events_processed - self.last_events_processed) / time_diff

                # Determine status based on rate
                rate_status = HealthStatus.HEALTHY
                if event_rate == 0 and events_processed > 0:
                    rate_status = HealthStatus.DEGRADED  # Processing stopped

                metrics.append(
                    HealthMetric(
                        name="event_processing_rate",
                        value=round(event_rate, 2),
                        status=rate_status,
                        unit="events/sec",
                    )
                )

            # Update for next calculation
            self.last_events_processed = events_processed

            # Total events processed
            metrics.append(
                HealthMetric(
                    name="total_events_processed",
                    value=events_processed,
                    status=HealthStatus.HEALTHY,
                )
            )

            # Event queue size (if available)
            if "event_queue_size" in self.service_stats:
                queue_size = self.service_stats["event_queue_size"]
                queue_status = HealthStatus.HEALTHY
                if queue_size > 1000:
                    queue_status = HealthStatus.DEGRADED
                if queue_size > 5000:
                    queue_status = HealthStatus.UNHEALTHY

                metrics.append(
                    HealthMetric(
                        name="event_queue_size",
                        value=queue_size,
                        status=queue_status,
                    )
                )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="event_processing_rate",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to calculate event rate: {e}",
                )
            )
        return metrics

    def _check_error_rates(self) -> List[HealthMetric]:
        """Check error rate metrics."""
        metrics = []
        try:
            errors = self.service_stats.get("errors", 0)
            total_events = self.service_stats.get("events_processed", 1)

            # Calculate error rate
            error_rate = errors / max(total_events, 1)

            # Determine status based on rate
            if error_rate > self.max_error_rate:
                error_status = HealthStatus.UNHEALTHY
            elif error_rate > self.max_error_rate * 0.5:
                error_status = HealthStatus.DEGRADED
            else:
                error_status = HealthStatus.HEALTHY

            metrics.append(
                HealthMetric(
                    name="error_rate",
                    value=round(error_rate, 4),
                    status=error_status,
                    threshold=self.max_error_rate,
                    unit="ratio",
                )
            )

            # Total errors
            metrics.append(
                HealthMetric(
                    name="total_errors",
                    value=errors,
                    status=(
                        HealthStatus.HEALTHY if errors == 0 else HealthStatus.DEGRADED
                    ),
                )
            )

            # Recent error rate (errors in last check period)
            if self.last_errors is not None:
                recent_errors = errors - self.last_errors
                metrics.append(
                    HealthMetric(
                        name="recent_errors",
                        value=recent_errors,
                        status=(
                            HealthStatus.HEALTHY
                            if recent_errors == 0
                            else HealthStatus.DEGRADED
                        ),
                    )
                )

            self.last_errors = errors

        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="error_rate",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to calculate error rate: {e}",
                )
            )
        return metrics

    def _check_service_activity(self, current_time: float) -> List[HealthMetric]:
        """Check service activity freshness."""
        metrics = []
        try:
            last_activity = self.service_stats.get("last_activity")

            if last_activity:
                # Parse timestamp if needed
                if isinstance(last_activity, str):
                    last_activity_timestamp = self._parse_timestamp(last_activity)
                else:
                    last_activity_timestamp = float(last_activity)

                time_since_activity = current_time - last_activity_timestamp

                # Determine status based on staleness
                if time_since_activity > self.stale_activity_seconds * 2:
                    activity_status = HealthStatus.UNHEALTHY
                elif time_since_activity > self.stale_activity_seconds:
                    activity_status = HealthStatus.DEGRADED
                else:
                    activity_status = HealthStatus.HEALTHY

                metrics.append(
                    HealthMetric(
                        name="time_since_last_activity",
                        value=round(time_since_activity, 2),
                        status=activity_status,
                        unit="seconds",
                    )
                )
            else:
                metrics.append(
                    HealthMetric(
                        name="time_since_last_activity",
                        value=-1,
                        status=HealthStatus.DEGRADED,
                        message="No last activity recorded",
                    )
                )
        except Exception as e:
            metrics.append(
                HealthMetric(
                    name="time_since_last_activity",
                    value=-1,
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to parse last activity: {e}",
                )
            )
        return metrics

    def _check_response_times(self) -> List[HealthMetric]:
        """Check response time metrics if available."""
        metrics = []

        # Average response time
        if "avg_response_time_ms" in self.service_stats:
            avg_time = self.service_stats["avg_response_time_ms"]

            # Determine status based on response time
            if avg_time > 1000:  # > 1 second
                time_status = HealthStatus.UNHEALTHY
            elif avg_time > 500:  # > 500ms
                time_status = HealthStatus.DEGRADED
            else:
                time_status = HealthStatus.HEALTHY

            metrics.append(
                HealthMetric(
                    name="avg_response_time",
                    value=round(avg_time, 2),
                    status=time_status,
                    unit="ms",
                )
            )

        # P95 response time
        if "p95_response_time_ms" in self.service_stats:
            metrics.append(
                HealthMetric(
                    name="p95_response_time",
                    value=round(self.service_stats["p95_response_time_ms"], 2),
                    status=HealthStatus.HEALTHY,
                    unit="ms",
                )
            )

        return metrics

    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Parse ISO timestamp string to float.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Timestamp as float (seconds since epoch)
        """
        try:
            from dateutil.parser import parse

            dt = parse(timestamp_str)
            return dt.timestamp()
        except ImportError:
            # Fallback: try manual parsing
            from datetime import datetime

            clean_timestamp = timestamp_str.rstrip("Z")
            dt = datetime.fromisoformat(clean_timestamp.replace("T", " "))
            return dt.timestamp()

    def update_stats(self, **kwargs) -> None:
        """Update service statistics.

        Args:
            **kwargs: Statistics to update
        """
        self.service_stats.update(kwargs)
        self.service_stats["last_activity"] = time.time()
