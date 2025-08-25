#!/usr/bin/env python3
"""
Hook Handler with Event Bus Integration
=======================================

Example showing how to integrate the event bus with the existing
hook handler, removing direct Socket.IO dependencies.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.events import (
    EventBus,
    HookEventProducer,
    LoggingConsumer,
    SocketIOConsumer,
)


class SimplifiedHookHandler:
    """
    Simplified hook handler that uses EventBus instead of direct Socket.IO.

    This demonstrates how the actual hook handler can be refactored to use
    the event bus, removing all Socket.IO dependencies.
    """

    def __init__(self, event_producer: HookEventProducer):
        """
        Initialize hook handler with event producer.

        Args:
            event_producer: Event producer for publishing hook events
        """
        self.logger = get_logger("HookHandler")
        self.event_producer = event_producer

        # Track current conversation context
        self.current_correlation_id: Optional[str] = None
        self.conversation_context: Dict[str, Any] = {}

    async def handle_hook_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle a hook event from Claude.

        This is called when Claude sends a hook event (response, tool use, etc.)
        """
        event_type = event_data.get("type", "unknown")

        self.logger.debug(f"Handling hook event: {event_type}")

        # Route to appropriate handler
        if event_type == "AssistantResponse":
            await self._handle_assistant_response(event_data)
        elif event_type == "ToolUse":
            await self._handle_tool_use(event_data)
        elif event_type == "SubagentStart":
            await self._handle_subagent_start(event_data)
        elif event_type == "SubagentStop":
            await self._handle_subagent_stop(event_data)
        elif event_type == "Error":
            await self._handle_error(event_data)
        else:
            # Generic hook event
            await self._handle_generic(event_type, event_data)

    async def _handle_assistant_response(self, data: Dict[str, Any]) -> None:
        """Handle assistant response events."""
        # Extract response content
        content = data.get("content", "")
        model = data.get("model", "unknown")

        # Publish to event bus
        await self.event_producer.publish_response(
            response_data={
                "content": content,
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "context": self.conversation_context,
            },
            correlation_id=self.current_correlation_id,
        )

        self.logger.info(f"Published assistant response ({len(content)} chars)")

    async def _handle_tool_use(self, data: Dict[str, Any]) -> None:
        """Handle tool usage events."""
        tool_name = data.get("tool", "unknown")
        tool_params = data.get("params", {})
        tool_result = data.get("result")

        # Publish to event bus
        await self.event_producer.publish_tool_use(
            tool_name=tool_name,
            tool_params=tool_params,
            tool_result=tool_result,
            correlation_id=self.current_correlation_id,
        )

        self.logger.info(f"Published tool use: {tool_name}")

    async def _handle_subagent_start(self, data: Dict[str, Any]) -> None:
        """Handle subagent start events."""
        subagent_name = data.get("name", "unknown")
        task = data.get("task", "")

        # Publish to event bus
        await self.event_producer.publish_subagent_event(
            subagent_name=subagent_name,
            event_type="Start",
            event_data={
                "task": task,
                "started_at": datetime.now().isoformat(),
            },
            correlation_id=self.current_correlation_id,
        )

        self.logger.info(f"Published subagent start: {subagent_name}")

    async def _handle_subagent_stop(self, data: Dict[str, Any]) -> None:
        """Handle subagent stop events."""
        subagent_name = data.get("name", "unknown")
        result = data.get("result", "")

        # Publish to event bus
        await self.event_producer.publish_subagent_event(
            subagent_name=subagent_name,
            event_type="Stop",
            event_data={
                "result": result,
                "stopped_at": datetime.now().isoformat(),
            },
            correlation_id=self.current_correlation_id,
        )

        self.logger.info(f"Published subagent stop: {subagent_name}")

    async def _handle_error(self, data: Dict[str, Any]) -> None:
        """Handle error events."""
        error_type = data.get("error_type", "unknown")
        message = data.get("message", "")
        details = data.get("details", {})

        # Publish to event bus
        await self.event_producer.publish_error(
            error_type=error_type,
            error_message=message,
            error_details=details,
            correlation_id=self.current_correlation_id,
        )

        self.logger.error(f"Published error: {error_type} - {message}")

    async def _handle_generic(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle generic hook events."""
        # Publish raw hook event
        await self.event_producer.publish_raw_hook_event(
            hook_type=event_type,
            hook_data=data,
            correlation_id=self.current_correlation_id,
        )

        self.logger.debug(f"Published generic hook event: {event_type}")


async def simulate_claude_hook_events(handler: SimplifiedHookHandler):
    """Simulate Claude sending various hook events."""
    print("\n🎭 Simulating Claude hook events...")

    # Simulate conversation start
    handler.current_correlation_id = "conv-001"
    handler.conversation_context = {
        "user": "developer",
        "project": "claude-mpm",
    }

    # Assistant response
    await handler.handle_hook_event(
        {
            "type": "AssistantResponse",
            "content": "I'll help you analyze the codebase. Let me start by examining the project structure.",
            "model": "claude-3-opus",
        }
    )

    await asyncio.sleep(0.1)

    # Tool usage
    await handler.handle_hook_event(
        {
            "type": "ToolUse",
            "tool": "Read",
            "params": {"file_path": "/src/main.py"},
            "result": "# Main application file\nimport sys\n...",
        }
    )

    await asyncio.sleep(0.1)

    # Subagent start
    await handler.handle_hook_event(
        {
            "type": "SubagentStart",
            "name": "CodeAnalyzer",
            "task": "Analyze Python code quality",
        }
    )

    await asyncio.sleep(0.5)

    # Subagent stop
    await handler.handle_hook_event(
        {
            "type": "SubagentStop",
            "name": "CodeAnalyzer",
            "result": "Analysis complete: 95% code coverage, no critical issues",
        }
    )

    await asyncio.sleep(0.1)

    # Another response
    await handler.handle_hook_event(
        {
            "type": "AssistantResponse",
            "content": "The code analysis is complete. The codebase has good test coverage and follows best practices.",
            "model": "claude-3-opus",
        }
    )

    # Simulate an error
    await handler.handle_hook_event(
        {
            "type": "Error",
            "error_type": "FileNotFound",
            "message": "Could not find requested file",
            "details": {"file": "/missing/file.py"},
        }
    )

    print("✅ Hook events simulated")


async def main():
    """Main demonstration."""
    print("=" * 60)
    print("Hook Handler with Event Bus Integration")
    print("=" * 60)

    # Create event bus
    print("\n🚌 Setting up event bus...")
    bus = EventBus()
    await bus.start()

    # Create consumers
    print("\n👥 Setting up consumers...")

    # Logging consumer for debugging
    logging_consumer = LoggingConsumer(
        log_level="INFO",
        topics=["hook.**"],  # Only hook events
        include_data=True,
    )
    await bus.subscribe(logging_consumer)
    print("  ✅ LoggingConsumer subscribed")

    # Socket.IO consumer (would emit to dashboard in production)
    socketio_consumer = SocketIOConsumer(
        socketio_server=None,  # Would be actual server
        batch_size=3,
    )
    await bus.subscribe(socketio_consumer)
    print("  ✅ SocketIOConsumer subscribed")

    # Create hook event producer
    print("\n🏭 Creating hook event producer...")
    hook_producer = HookEventProducer(bus)

    # Create simplified hook handler
    print("\n🪝 Creating hook handler...")
    hook_handler = SimplifiedHookHandler(hook_producer)

    # Simulate Claude hook events
    await simulate_claude_hook_events(hook_handler)

    # Wait for processing
    print("\n⏳ Processing events...")
    await asyncio.sleep(2)

    # Show metrics
    print("\n📊 Event Bus Metrics:")
    print("-" * 40)
    metrics = bus.get_metrics()
    print(f"  Events Published: {metrics['events_published']}")
    print(f"  Events Processed: {metrics['events_processed']}")
    print(f"  Queue Size: {metrics['queue_size']}")

    print("\n📊 Producer Metrics:")
    print("-" * 40)
    producer_metrics = hook_producer.get_metrics()
    print(f"  Events Published: {producer_metrics['events_published']}")
    print(f"  Events Failed: {producer_metrics['events_failed']}")

    # Shutdown
    print("\n🛑 Shutting down...")
    await bus.stop()

    print("\n" + "=" * 60)
    print("Integration Demonstration Complete!")
    print("=" * 60)
    print("\n✨ Key Improvements:")
    print("  • Hook handler has NO Socket.IO dependency")
    print("  • Events flow through central bus")
    print("  • Socket.IO is just another consumer")
    print("  • Easy to add new consumers (metrics, logging, etc.)")
    print("  • Hook handler is simpler and more testable")
    print("  • Connection failures don't affect hook processing")


if __name__ == "__main__":
    asyncio.run(main())
