"""
SocketIO Event Broadcaster for claude-mpm.

WHY: This module contains all the broadcasting methods extracted from the
monolithic socketio_server.py file. It handles sending events to connected
clients for various Claude MPM activities.

DESIGN DECISION: Separated broadcasting logic from core server management
to create focused, testable modules with single responsibilities.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Set

from ..event_normalizer import EventNormalizer


@dataclass
class RetryableEvent:
    """Represents an event that can be retried on failure.

    WHY: Network failures are common and transient. By tracking retry
    attempts, we can recover from temporary issues while avoiding
    infinite retry loops.
    """

    event_type: str
    data: Dict[str, Any]
    attempt_count: int = 0
    max_retries: int = 3
    created_at: float = None
    last_attempt: float = None
    skip_sid: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_attempt is None:
            self.last_attempt = time.time()

    def should_retry(self) -> bool:
        """Check if this event should be retried.

        WHY: We need to balance reliability with resource usage.
        Events older than 30 seconds or with too many attempts
        should be abandoned.
        """
        if self.attempt_count >= self.max_retries:
            return False

        # Don't retry events older than 30 seconds
        return not time.time() - self.created_at > 30

    def get_backoff_delay(self) -> float:
        """Calculate exponential backoff delay.

        WHY: Exponential backoff prevents overwhelming the system
        during recovery from failures.
        """
        base_delay = 1.0  # 1 second
        max_delay = 8.0  # 8 seconds max

        return min(base_delay * (2**self.attempt_count), max_delay)


class RetryQueue:
    """Manages retry queue for failed event broadcasts.

    WHY: Transient network issues shouldn't cause event loss.
    This queue provides resilient event delivery with backoff.
    """

    def __init__(self, max_size: int = 1000):
        self.queue: Deque[RetryableEvent] = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
        self.stats = {"queued": 0, "retried": 0, "succeeded": 0, "abandoned": 0}

    async def add(self, event: RetryableEvent) -> None:
        """Add an event to the retry queue."""
        async with self.lock:
            self.queue.append(event)
            self.stats["queued"] += 1

    async def get_ready_events(self) -> List[RetryableEvent]:
        """Get events that are ready for retry.

        WHY: We need to respect backoff delays to avoid
        overwhelming the system during recovery.
        """
        async with self.lock:
            current_time = time.time()
            ready = []

            # Check each event in queue
            remaining = []
            for event in self.queue:
                if not event.should_retry():
                    self.stats["abandoned"] += 1
                    continue

                # First attempt (attempt_count == 0) should be immediate
                if event.attempt_count == 0:
                    ready.append(event)
                else:
                    # For retries, check backoff delay
                    time_since_attempt = current_time - event.last_attempt
                    if time_since_attempt >= event.get_backoff_delay():
                        ready.append(event)
                    else:
                        remaining.append(event)

            # Update queue with events not ready yet
            self.queue.clear()
            self.queue.extend(remaining)

            return ready

    async def mark_success(self, event: RetryableEvent) -> None:
        """Mark an event as successfully sent."""
        self.stats["succeeded"] += 1

    async def mark_retry(self, event: RetryableEvent) -> None:
        """Mark an event for retry."""
        event.attempt_count += 1
        event.last_attempt = time.time()
        self.stats["retried"] += 1

        if event.should_retry():
            await self.add(event)

    def get_stats(self) -> Dict[str, int]:
        """Get retry queue statistics."""
        return {**self.stats, "queue_size": len(self.queue)}


class SocketIOEventBroadcaster:
    """Handles broadcasting events to connected Socket.IO clients.

    WHY: This class encapsulates all the event broadcasting logic that was
    scattered throughout the monolithic SocketIOServer class.
    """

    def __init__(
        self,
        sio,
        connected_clients: Set[str],
        event_buffer,
        buffer_lock,
        stats: Dict[str, Any],
        logger,
        server=None,  # Add server reference for event history access
        connection_manager=None,  # Add connection manager for robust delivery
    ):
        self.sio = sio
        self.connected_clients = connected_clients
        self.event_buffer = event_buffer
        self.buffer_lock = buffer_lock
        self.stats = stats
        self.logger = logger
        self.loop = None  # Will be set by main server
        self.server = server  # Reference to main server for event history
        self.connection_manager = connection_manager  # For connection tracking

        # Initialize retry queue for resilient delivery
        self.retry_queue = RetryQueue(max_size=1000)
        self.retry_task = None
        self.retry_interval = 2.0  # Process retry queue every 2 seconds

        # Initialize event normalizer for consistent schema
        self.normalizer = EventNormalizer()

    def start_retry_processor(self):
        """Start the background retry processor.

        WHY: Failed broadcasts need to be retried automatically
        to ensure reliable event delivery.

        IMPORTANT: This method must handle being called from a different thread
        than the one running the event loop.
        """
        if self.loop and not self.retry_task:
            try:
                # Check if the loop is running in the current thread
                try:
                    running_loop = asyncio.get_running_loop()
                    if running_loop == self.loop:
                        # Same thread, can use create_task directly
                        self.retry_task = asyncio.create_task(
                            self._process_retry_queue()
                        )
                        self.logger.info(
                            "🔄 Started retry queue processor (same thread)"
                        )
                    else:
                        # Different thread, need to schedule in the target loop
                        self._start_retry_in_loop()
                except RuntimeError:
                    # No running loop in current thread, schedule in target loop
                    self._start_retry_in_loop()
            except Exception as e:
                self.logger.error(f"Failed to start retry processor: {e}")

    def _start_retry_in_loop(self):
        """Helper to start retry processor from a different thread."""

        async def _create_retry_task():
            self.retry_task = asyncio.create_task(self._process_retry_queue())
            self.logger.info("🔄 Started retry queue processor (cross-thread)")

        # Schedule the task creation in the target loop
        future = asyncio.run_coroutine_threadsafe(_create_retry_task(), self.loop)
        try:
            # Wait briefly to ensure it's scheduled
            future.result(timeout=1.0)
        except Exception as e:
            self.logger.error(f"Failed to schedule retry processor: {e}")

    def stop_retry_processor(self):
        """Stop the background retry processor."""
        if self.retry_task:
            self.retry_task.cancel()
            self.retry_task = None
            self.logger.info("🚫 Stopped retry queue processor")

    async def _process_retry_queue(self):
        """Process the retry queue periodically.

        WHY: Regular processing ensures failed events are retried
        with appropriate backoff delays.
        """
        while True:
            try:
                await asyncio.sleep(self.retry_interval)

                # Get events ready for retry
                ready_events = await self.retry_queue.get_ready_events()

                if ready_events:
                    self.logger.debug(
                        f"🔄 Processing {len(ready_events)} events from retry queue"
                    )

                    for event in ready_events:
                        success = await self._retry_broadcast(event)

                        if success:
                            await self.retry_queue.mark_success(event)
                        else:
                            await self.retry_queue.mark_retry(event)

                    # Log stats periodically
                    stats = self.retry_queue.get_stats()
                    if stats["retried"] > 0 or stats["abandoned"] > 0:
                        self.logger.info(
                            f"📊 Retry queue stats - "
                            f"queued: {stats['queued']}, "
                            f"retried: {stats['retried']}, "
                            f"succeeded: {stats['succeeded']}, "
                            f"abandoned: {stats['abandoned']}, "
                            f"current size: {stats['queue_size']}"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing retry queue: {e}")

    async def _retry_broadcast(self, event: RetryableEvent) -> bool:
        """Retry broadcasting a failed event.

        WHY: Isolated retry logic allows for special handling
        and metrics tracking of retry attempts. Uses normalizer
        to ensure consistent schema.
        """
        try:
            self.logger.debug(
                f"🔄 Retrying {event.event_type} (attempt {event.attempt_count + 1}/{event.max_retries})"
            )

            # Reconstruct the raw event
            raw_event = {
                "type": event.event_type,
                "timestamp": datetime.now().isoformat(),
                "data": {**event.data, "retry_attempt": event.attempt_count + 1},
            }

            # Normalize the event
            normalized = self.normalizer.normalize(raw_event)
            full_event = normalized.to_dict()

            # Attempt broadcast
            if event.skip_sid:
                await self.sio.emit("claude_event", full_event, skip_sid=event.skip_sid)
            else:
                await self.sio.emit("claude_event", full_event)

            self.logger.debug(f"✅ Successfully retried {event.event_type}")
            return True

        except Exception as e:
            self.logger.warning(
                f"⚠️ Retry failed for {event.event_type} "
                f"(attempt {event.attempt_count + 1}): {e}"
            )
            return False

    def broadcast_event(
        self, event_type: str, data: Dict[str, Any], skip_sid: Optional[str] = None
    ):
        """Broadcast an event to all connected clients with retry support.

        WHY: Enhanced with retry queue to ensure reliable delivery
        even during transient network issues. Now uses EventNormalizer
        to ensure consistent event schema and ConnectionManager for tracking.
        """
        if not self.sio:
            return

        # Create raw event for normalization
        raw_event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        # Normalize the event to consistent schema
        normalized = self.normalizer.normalize(raw_event)
        event = normalized.to_dict()

        # Buffer the event for reliability AND add to event history for new clients
        with self.buffer_lock:
            self.event_buffer.append(event)
            self.stats["events_buffered"] += 1

            # Also add to event history if available (for client replay)
            # Access through server reference to maintain single history source
            if hasattr(self, "server") and hasattr(self.server, "event_history"):
                self.server.event_history.append(event)
                self.logger.debug(
                    f"Added {event['type']}/{event['subtype']} to history (total: {len(self.server.event_history)})"
                )

        # If we have a connection manager, buffer event for all connected clients
        if self.connection_manager and self.loop:
            # Buffer for each connected client asynchronously
            async def buffer_for_clients():
                for sid in list(self.connected_clients):
                    await self.connection_manager.buffer_event(sid, event)

            try:
                asyncio.run_coroutine_threadsafe(buffer_for_clients(), self.loop)
            except Exception as e:
                self.logger.warning(f"Failed to buffer event for clients: {e}")

        # Broadcast to all connected clients
        broadcast_success = False
        try:
            # Use run_coroutine_threadsafe to safely call from any thread
            if hasattr(self, "loop") and self.loop and not self.loop.is_closed():
                # Create broadcast coroutine
                if skip_sid:
                    coro = self.sio.emit("claude_event", event, skip_sid=skip_sid)
                else:
                    coro = self.sio.emit("claude_event", event)

                future = asyncio.run_coroutine_threadsafe(coro, self.loop)

                # Wait briefly to see if broadcast succeeds
                try:
                    future.result(timeout=0.5)  # 500ms timeout
                    broadcast_success = True
                    self.stats["events_sent"] += 1

                    # Update activity for all connected clients
                    if self.connection_manager:

                        async def update_activities():
                            for sid in list(self.connected_clients):
                                await self.connection_manager.update_activity(
                                    sid, "event"
                                )

                        try:
                            asyncio.run_coroutine_threadsafe(
                                update_activities(), self.loop
                            )
                        except:
                            pass  # Non-critical

                    self.logger.debug(f"Broadcasted event: {event_type}")
                except:
                    # Will be added to retry queue below
                    pass
            else:
                self.logger.warning(
                    f"Cannot broadcast {event_type}: server loop not available"
                )

        except Exception as e:
            self.logger.error(f"Failed to broadcast event {event_type}: {e}")

        # Add to retry queue if broadcast failed
        if not broadcast_success and self.loop:
            retryable_event = RetryableEvent(
                event_type=event_type, data=data, skip_sid=skip_sid
            )

            # Queue for retry
            asyncio.run_coroutine_threadsafe(
                self.retry_queue.add(retryable_event), self.loop
            )

            self.logger.warning(
                f"⚠️ Queued {event_type} for retry (queue size: {len(self.retry_queue.queue)})"
            )

    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Notify that a session has started."""
        self.broadcast_event(
            "session_started",
            {
                "session_id": session_id,
                "launch_method": launch_method,
                "working_dir": working_dir,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def session_ended(self):
        """Notify that a session has ended."""
        self.broadcast_event("session_ended", {"timestamp": datetime.now().isoformat()})

    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ):
        """Notify Claude status change."""
        self.broadcast_event(
            "claude_status", {"status": status, "pid": pid, "message": message}
        )

    def claude_output(self, content: str, stream: str = "stdout"):
        """Broadcast Claude output."""
        self.broadcast_event("claude_output", {"content": content, "stream": stream})

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Notify agent delegation."""
        self.broadcast_event(
            "agent_delegated", {"agent": agent, "task": task, "status": status}
        )

    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Notify todo list update."""
        # Limit the size of todo data to prevent large payloads
        limited_todos = todos[:50] if len(todos) > 50 else todos

        self.broadcast_event(
            "todo_updated",
            {
                "todos": limited_todos,
                "total_count": len(todos),
                "truncated": len(todos) > 50,
            },
        )

    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Notify ticket creation."""
        self.broadcast_event(
            "ticket_created",
            {"ticket_id": ticket_id, "title": title, "priority": priority},
        )

    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Notify when agent memory is loaded from file."""
        self.broadcast_event(
            "memory_loaded",
            {
                "agent_id": agent_id,
                "memory_size": memory_size,
                "sections_count": sections_count,
            },
        )

    def memory_created(self, agent_id: str, template_type: str):
        """Notify when new agent memory is created from template."""
        self.broadcast_event(
            "memory_created", {"agent_id": agent_id, "template_type": template_type}
        )

    def memory_updated(
        self, agent_id: str, learning_type: str, content: str, section: str
    ):
        """Notify when learning is added to agent memory."""
        # Truncate content if too long to prevent large payloads
        truncated_content = content[:500] + "..." if len(content) > 500 else content

        self.broadcast_event(
            "memory_updated",
            {
                "agent_id": agent_id,
                "learning_type": learning_type,
                "content": truncated_content,
                "section": section,
                "content_length": len(content),
                "truncated": len(content) > 500,
            },
        )

    def memory_injected(self, agent_id: str, context_size: int):
        """Notify when agent memory is injected into context."""
        self.broadcast_event(
            "memory_injected", {"agent_id": agent_id, "context_size": context_size}
        )

    def file_changed(
        self, file_path: str, change_type: str, content: Optional[str] = None
    ):
        """Notify file system changes."""
        event_data = {"file_path": file_path, "change_type": change_type}

        # Include content for small files only
        if content and len(content) < 1000:
            event_data["content"] = content
        elif content:
            event_data["content_preview"] = content[:200] + "..."
            event_data["content_length"] = len(content)

        self.broadcast_event("file_changed", event_data)

    def git_operation(self, operation: str, details: Dict[str, Any]):
        """Notify Git operations."""
        self.broadcast_event(
            "git_operation", {"operation": operation, "details": details}
        )

    def error_occurred(
        self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        """Notify when errors occur."""
        self.broadcast_event(
            "error",
            {"error_type": error_type, "message": message, "details": details or {}},
        )

    def performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """Broadcast performance metrics."""
        self.broadcast_event(
            "performance", {"metric": metric_name, "value": value, "unit": unit}
        )

    def system_status(self, status: Dict[str, Any]):
        """Broadcast system status information."""
        self.broadcast_event("system_status", status)

    def broadcast_system_heartbeat(self, heartbeat_data: Dict[str, Any]):
        """Broadcast system heartbeat event.

        WHY: System events are separate from hook events to provide
        server health monitoring independent of Claude activity.
        Now uses broadcast_event for consistency with buffering and normalization.
        """
        # Use the standard broadcast_event method which handles normalization,
        # buffering, and retry logic
        self.broadcast_event("heartbeat", heartbeat_data)
