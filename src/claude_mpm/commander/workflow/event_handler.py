"""Event handler for pause/resume workflow on blocking events.

This module provides EventHandler which manages blocking events that require
user input and coordinates session pause/resume.
"""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from ..inbox import Inbox
from ..models.events import BLOCKING_EVENTS, Event, EventStatus
from ..project_session import ProjectSession

if TYPE_CHECKING:
    from ..core.block_manager import BlockManager

logger = logging.getLogger(__name__)


class EventHandler:
    """Handles events requiring user resolution and session pause/resume.

    This class detects blocking events (permission requests, errors, confirmations),
    pauses the associated project session, and resumes execution after the event
    is resolved with a user response.

    Attributes:
        inbox: Inbox for event management
        session_manager: Dict mapping project_id to ProjectSession

    Example:
        >>> handler = EventHandler(inbox, sessions)
        >>> await handler.process_event(event)  # Pauses if blocking
        >>> success = await handler.resolve_event(event_id, "User response")
    """

    def __init__(
        self,
        inbox: Inbox,
        session_manager: Dict[str, ProjectSession],
        block_manager: Optional["BlockManager"] = None,
    ) -> None:
        """Initialize event handler.

        Args:
            inbox: Inbox instance for event access
            session_manager: Dict mapping project_id -> ProjectSession
            block_manager: Optional BlockManager for automatic work unblocking

        Raises:
            ValueError: If inbox or session_manager is None
        """
        if inbox is None:
            raise ValueError("Inbox cannot be None")
        if session_manager is None:
            raise ValueError("Session manager cannot be None")

        self.inbox = inbox
        self.session_manager = session_manager
        self._event_manager = inbox.events
        self.block_manager = block_manager

        logger.debug(
            "EventHandler initialized (block_manager: %s)",
            "enabled" if block_manager else "disabled",
        )

    async def process_event(self, event: Event) -> None:
        """Process an event - pause session if blocking.

        If the event is blocking (requires user input), pauses the associated
        project session until the event is resolved.

        Args:
            event: Event to process

        Example:
            >>> await handler.process_event(error_event)
            # Session paused for project
        """
        if not self.is_blocking(event):
            logger.debug(
                "Event %s is non-blocking (%s), no pause needed",
                event.id,
                event.type.value,
            )
            return

        logger.info(
            "Processing blocking event %s for project %s: %s",
            event.id,
            event.project_id,
            event.title,
        )

        # Get the project session
        session = self.session_manager.get(event.project_id)
        if not session:
            logger.warning(
                "No session found for project %s, cannot pause", event.project_id
            )
            return

        # Pause the session
        try:
            await session.pause(f"Event {event.id}: {event.title}")
            logger.info(
                "Paused session for project %s due to event %s",
                event.project_id,
                event.id,
            )
        except Exception as e:
            logger.error(
                "Failed to pause session for project %s: %s", event.project_id, e
            )

    async def resolve_event(self, event_id: str, response: str) -> bool:
        """Resolve an event with user response and resume session if applicable.

        Marks the event as resolved, sends the response to the runtime, and
        resumes the project session if it was paused for this event.

        Args:
            event_id: ID of event to resolve
            response: User's response to the event

        Returns:
            True if resolution successful and session resumed, False otherwise

        Raises:
            KeyError: If event_id not found

        Example:
            >>> success = await handler.resolve_event("evt_123", "Use authlib")
            >>> if success:
            ...     print("Event resolved and session resumed")
        """
        # Get the event
        event = self._event_manager.get(event_id)
        if not event:
            raise KeyError(f"Event not found: {event_id}")

        logger.info("Resolving event %s: %s", event_id, response[:50])

        # Check if event WAS blocking BEFORE resolving
        was_blocking = self.is_blocking(event)

        # Mark event as resolved
        self._event_manager.respond(event_id, response)

        # Automatically unblock work items if BlockManager is available
        if self.block_manager and was_blocking:
            unblocked_work = await self.block_manager.check_and_unblock(event_id)
            if unblocked_work:
                logger.info(
                    "Event %s resolution unblocked %d work items: %s",
                    event_id,
                    len(unblocked_work),
                    unblocked_work,
                )

        # If event was NOT blocking, no need to resume
        if not was_blocking:
            logger.debug("Event %s was non-blocking, no resume needed", event_id)
            return True

        # Get the project session
        session = self.session_manager.get(event.project_id)
        if not session:
            logger.warning(
                "No session found for project %s, cannot resume", event.project_id
            )
            return False

        # Check if session was paused for this event
        if (
            session.pause_reason
            and event_id in session.pause_reason
            and session.state.value == "paused"
        ):
            try:
                # Send response to the runtime
                if session.active_pane and session.executor:
                    await session.executor.send_message(session.active_pane, response)
                    logger.debug("Sent response to pane %s", session.active_pane)

                # Resume the session
                await session.resume()
                logger.info(
                    "Resumed session for project %s after resolving event %s",
                    event.project_id,
                    event_id,
                )
                return True

            except Exception as e:
                logger.error(
                    "Failed to resume session for project %s: %s", event.project_id, e
                )
                return False
        else:
            logger.debug("Session not paused for event %s, no resume needed", event_id)
            return True

    async def get_pending_events(self, project_id: Optional[str] = None) -> List[Event]:
        """Get unresolved events, optionally filtered by project.

        Args:
            project_id: If provided, only return events for this project

        Returns:
            List of pending events sorted by priority and time

        Example:
            >>> all_pending = await handler.get_pending_events()
            >>> project_pending = await handler.get_pending_events("proj_123")
        """
        return self._event_manager.get_pending(project_id)

    def is_blocking(self, event: Event) -> bool:
        """Check if event type requires pausing execution.

        Blocking event types:
        - permission_request: Requires user approval
        - error: Critical error blocking progress
        - confirmation_request: User confirmation needed
        - decision_needed: User must choose option
        - approval: Destructive action needs approval

        Args:
            event: Event to check

        Returns:
            True if event blocks progress, False otherwise

        Example:
            >>> if handler.is_blocking(event):
            ...     await handler.process_event(event)
        """
        # Check if event type is blocking and status is pending
        return event.type in BLOCKING_EVENTS and event.status == EventStatus.PENDING
