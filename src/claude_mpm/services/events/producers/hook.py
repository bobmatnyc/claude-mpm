"""
Hook Event Producer
==================

Publishes hook system events to the event bus.
This replaces direct Socket.IO emission in the hook handler.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

from ..core import Event, EventPriority
from ..interfaces import IEventBus, IEventProducer


class HookEventProducer(IEventProducer):
    """
    Publishes hook events to the event bus.

    This producer is used by the hook handler to publish events
    without knowing about Socket.IO or other consumers.
    """

    def __init__(self, event_bus: IEventBus):
        """
        Initialize hook event producer.

        Args:
            event_bus: The event bus to publish to
        """
        self.logger = get_logger("HookEventProducer")
        self.event_bus = event_bus
        self._source_name = "hook_handler"

        # Metrics
        self._metrics = {
            "events_published": 0,
            "events_failed": 0,
            "batch_published": 0,
        }

    async def publish(self, event: Event) -> bool:
        """Publish a hook event to the bus."""
        try:
            success = await self.event_bus.publish(event)

            if success:
                self._metrics["events_published"] += 1
            else:
                self._metrics["events_failed"] += 1

            return success

        except Exception as e:
            self.logger.error(f"Error publishing hook event: {e}")
            self._metrics["events_failed"] += 1
            return False

    async def publish_batch(self, events: List[Event]) -> int:
        """Publish multiple hook events."""
        successful = 0

        for event in events:
            if await self.publish(event):
                successful += 1

        self._metrics["batch_published"] += 1
        return successful

    @property
    def source_name(self) -> str:
        """Get the name of this event source."""
        return self._source_name

    # Convenience methods for common hook events

    async def publish_response(
        self,
        response_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Publish an assistant response event.

        Args:
            response_data: The response data
            correlation_id: Optional correlation ID

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="hook.response",
            type="AssistantResponse",
            timestamp=datetime.now(),
            source=self.source_name,
            data=response_data,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
        )

        return await self.publish(event)

    async def publish_tool_use(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        tool_result: Optional[Any] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Publish a tool usage event.

        Args:
            tool_name: Name of the tool used
            tool_params: Parameters passed to the tool
            tool_result: Optional tool result
            correlation_id: Optional correlation ID

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="hook.tool",
            type="ToolUse",
            timestamp=datetime.now(),
            source=self.source_name,
            data={
                "tool": tool_name,
                "params": tool_params,
                "result": tool_result,
            },
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
        )

        return await self.publish(event)

    async def publish_error(
        self,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Publish an error event.

        Args:
            error_type: Type of error
            error_message: Error message
            error_details: Optional additional details
            correlation_id: Optional correlation ID

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic="hook.error",
            type="Error",
            timestamp=datetime.now(),
            source=self.source_name,
            data={
                "error_type": error_type,
                "message": error_message,
                "details": error_details or {},
            },
            correlation_id=correlation_id,
            priority=EventPriority.CRITICAL,
        )

        return await self.publish(event)

    async def publish_subagent_event(
        self,
        subagent_name: str,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Publish a subagent-related event.

        Args:
            subagent_name: Name of the subagent
            event_type: Type of subagent event
            event_data: Event data
            correlation_id: Optional correlation ID

        Returns:
            True if published successfully
        """
        event = Event(
            id=str(uuid.uuid4()),
            topic=f"hook.subagent.{event_type.lower()}",
            type=f"Subagent{event_type}",
            timestamp=datetime.now(),
            source=self.source_name,
            data={
                "subagent": subagent_name,
                **event_data,
            },
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
        )

        return await self.publish(event)

    async def publish_raw_hook_event(
        self,
        hook_type: str,
        hook_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Publish a raw hook event.

        This is for hook events that don't fit the standard patterns.

        Args:
            hook_type: Type of hook event
            hook_data: Raw hook data
            correlation_id: Optional correlation ID

        Returns:
            True if published successfully
        """
        # Determine topic based on hook type
        if "response" in hook_type.lower():
            topic = "hook.response"
        elif "tool" in hook_type.lower():
            topic = "hook.tool"
        elif "error" in hook_type.lower():
            topic = "hook.error"
        elif "subagent" in hook_type.lower():
            topic = "hook.subagent"
        else:
            topic = "hook.generic"

        # Determine priority
        if "error" in hook_type.lower() or "critical" in hook_type.lower():
            priority = EventPriority.CRITICAL
        elif "response" in hook_type.lower():
            priority = EventPriority.HIGH
        else:
            priority = EventPriority.NORMAL

        event = Event(
            id=str(uuid.uuid4()),
            topic=topic,
            type=hook_type,
            timestamp=datetime.now(),
            source=self.source_name,
            data=hook_data,
            correlation_id=correlation_id,
            priority=priority,
        )

        return await self.publish(event)

    def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics."""
        return self._metrics
