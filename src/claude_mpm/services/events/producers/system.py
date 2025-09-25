"""
System Event Producer
====================

Publishes system-level events to the event bus.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

from ..core import Event, EventPriority
from ..interfaces import IEventBus, IEventProducer


class SystemEventProducer(IEventProducer):
    """
    Publishes system events to the event bus.

    Used for:
    - Service lifecycle events
    - Configuration changes
    - Health status updates
    - Performance metrics
    - System errors
    """

    def __init__(self, event_bus: IEventBus, source_name: str = "system"):
        """
        Initialize system event producer.

        Args:
            event_bus: The event bus to publish to
            source_name: Name of the system component
        """
        self.logger = get_logger("SystemEventProducer")
        self.event_bus = event_bus
        self._source_name = source_name

        # Metrics
        self._metrics = {
            "events_published": 0,
            "events_failed": 0,
        }

    async def publish(self, event: Event) -> bool:
        """Publish a system event to the bus."""
        try:
            success = await self.event_bus.publish(event)

            if success:
                self._metrics["events_published"] += 1
            else:
                self._metrics["events_failed"] += 1

            return success

        except Exception as e:
            self.logger.error(f"Error publishing system event: {e}")
            self._metrics["events_failed"] += 1
            return False

    async def publish_batch(self, events: List[Event]) -> int:
        """Publish multiple system events."""
        successful = 0

        for event in events:
            if await self.publish(event):
                successful += 1

        return successful

    @property
    def source_name(self) -> str:
        """Get the name of this event source."""
        return self._source_name

    # Convenience methods for common system events

    async def publish_startup(
        self,
        service_name: str,
        version: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish a service startup event.

        Args:
            service_name: Name of the service
            version: Service version
            config: Optional configuration data

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.lifecycle.startup",
            type="ServiceStartup",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "version": version,
                "config": config or {},
            },
            priority=EventPriority.HIGH,
        )

        return await self.publish(event)

    async def publish_shutdown(
        self,
        service_name: str,
        reason: str = "normal",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish a service shutdown event.

        Args:
            service_name: Name of the service
            reason: Shutdown reason
            details: Optional additional details

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.lifecycle.shutdown",
            type="ServiceShutdown",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "reason": reason,
                "details": details or {},
            },
            priority=EventPriority.HIGH,
        )

        return await self.publish(event)

    async def publish_health_status(
        self,
        service_name: str,
        status: str,
        checks: Dict[str, bool],
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish a health status event.

        Args:
            service_name: Name of the service
            status: Health status (healthy, degraded, unhealthy)
            checks: Individual health checks
            details: Optional additional details

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.health",
            type="HealthStatus",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "status": status,
                "checks": checks,
                "details": details or {},
            },
            priority=(
                EventPriority.NORMAL if status == "healthy" else EventPriority.HIGH
            ),
        )

        return await self.publish(event)

    async def publish_config_change(
        self,
        service_name: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
    ) -> bool:
        """
        Publish a configuration change event.

        Args:
            service_name: Name of the service
            config_key: Configuration key that changed
            old_value: Previous value
            new_value: New value

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.config",
            type="ConfigChange",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "key": config_key,
                "old_value": old_value,
                "new_value": new_value,
            },
            priority=EventPriority.NORMAL,
        )

        return await self.publish(event)

    async def publish_performance_metrics(
        self,
        service_name: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """
        Publish performance metrics.

        Args:
            service_name: Name of the service
            metrics: Performance metrics data

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.performance",
            type="PerformanceMetrics",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "metrics": metrics,
            },
            priority=EventPriority.LOW,
        )

        return await self.publish(event)

    async def publish_error(
        self,
        service_name: str,
        error_type: str,
        error_message: str,
        stacktrace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish a system error event.

        Args:
            service_name: Name of the service
            error_type: Type of error
            error_message: Error message
            stacktrace: Optional stack trace
            context: Optional error context

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.error",
            type="SystemError",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "error_type": error_type,
                "message": error_message,
                "stacktrace": stacktrace,
                "context": context or {},
            },
            priority=EventPriority.CRITICAL,
        )

        return await self.publish(event)

    async def publish_warning(
        self,
        service_name: str,
        warning_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish a system warning event.

        Args:
            service_name: Name of the service
            warning_type: Type of warning
            message: Warning message
            details: Optional additional details

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="system.warning",
            type="SystemWarning",
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            data={
                "service": service_name,
                "warning_type": warning_type,
                "message": message,
                "details": details or {},
            },
            priority=EventPriority.HIGH,
        )

        return await self.publish(event)

    def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics."""
        return self._metrics
