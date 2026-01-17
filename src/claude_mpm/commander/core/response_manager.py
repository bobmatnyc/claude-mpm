"""ResponseManager for centralized response routing and validation.

This module provides ResponseManager which handles response validation,
routing, and delivery to runtime sessions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..events.manager import EventManager
from ..models.events import Event, EventType
from ..runtime.executor import RuntimeExecutor

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


@dataclass
class ResponseRoute:
    """Encapsulates a validated response ready for delivery.

    Attributes:
        event: Event being responded to
        response: User's response text
        valid: Whether validation passed
        validation_errors: List of validation error messages
        timestamp: When the route was created
        delivered: Whether response has been delivered
        delivery_timestamp: When the response was delivered
    """

    event: Event
    response: str
    valid: bool
    validation_errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=_utc_now)
    delivered: bool = False
    delivery_timestamp: Optional[datetime] = None


class ResponseManager:
    """Centralizes response validation, routing, and delivery.

    Provides centralized response handling with validation and routing
    capabilities for event responses.

    Attributes:
        event_manager: EventManager for retrieving events
        runtime_executor: Optional RuntimeExecutor for response delivery
        _response_history: History of all response attempts per event

    Example:
        >>> manager = ResponseManager(event_manager, runtime_executor)
        >>> valid, errors = manager.validate_response(event, "staging")
        >>> if valid:
        ...     route = manager.validate_and_route(event_id, "staging")
        ...     success = await manager.deliver_response(route)
    """

    def __init__(
        self,
        event_manager: EventManager,
        runtime_executor: Optional[RuntimeExecutor] = None,
    ) -> None:
        """Initialize ResponseManager.

        Args:
            event_manager: EventManager instance for retrieving events
            runtime_executor: Optional RuntimeExecutor for response delivery

        Raises:
            ValueError: If event_manager is None
        """
        if event_manager is None:
            raise ValueError("EventManager cannot be None")

        self.event_manager = event_manager
        self.runtime_executor = runtime_executor
        self._response_history: Dict[str, List[ResponseRoute]] = {}

        logger.debug(
            "ResponseManager initialized (runtime_executor: %s)",
            "enabled" if runtime_executor else "disabled",
        )

    def validate_response(self, event: Event, response: str) -> Tuple[bool, List[str]]:
        """Validate response against event constraints.

        Validation rules:
        1. Empty responses: Not allowed for blocking events
        2. DECISION_NEEDED options: Response must match one of the options
        3. Response whitespace: Stripped before validation

        Args:
            event: Event being responded to
            response: User's response

        Returns:
            Tuple of (is_valid, list_of_error_messages)

        Example:
            >>> valid, errors = manager.validate_response(event, "staging")
            >>> if not valid:
            ...     for error in errors:
            ...         print(f"Validation error: {error}")
        """
        errors: List[str] = []

        # Strip whitespace for validation
        response_stripped = response.strip()

        # Rule 1: Empty responses not allowed for blocking events
        if event.is_blocking and not response_stripped:
            errors.append("Response cannot be empty for blocking events")

        # Rule 2: DECISION_NEEDED events must use one of the provided options
        if event.type == EventType.DECISION_NEEDED and event.options:
            if response_stripped not in event.options:
                errors.append(
                    f"Response must be one of: {', '.join(event.options)}. "
                    f"Got: '{response_stripped}'"
                )

        # Future validation rules can be added here:
        # - Max length check
        # - Format validation (e.g., regex patterns)
        # - Custom validators per event type
        # - Conditional validation based on event context

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_and_route(
        self, event_id: str, response: str
    ) -> Optional[ResponseRoute]:
        """Create a validated ResponseRoute for an event.

        Retrieves the event, validates the response, and creates a ResponseRoute
        with validation results.

        Args:
            event_id: ID of event to respond to
            response: User's response

        Returns:
            ResponseRoute with validation results, or None if event not found

        Example:
            >>> route = manager.validate_and_route("evt_123", "staging")
            >>> if route and route.valid:
            ...     await manager.deliver_response(route)
            >>> elif route:
            ...     print(f"Validation failed: {route.validation_errors}")
        """
        # Get the event
        event = self.event_manager.get(event_id)
        if not event:
            logger.warning("Event not found: %s", event_id)
            return None

        # Validate response
        valid, errors = self.validate_response(event, response)

        # Create route
        route = ResponseRoute(
            event=event,
            response=response,
            valid=valid,
            validation_errors=errors,
        )

        logger.debug(
            "Created route for event %s: valid=%s, errors=%s",
            event_id,
            valid,
            errors,
        )

        return route

    async def deliver_response(self, route: ResponseRoute) -> bool:
        """Deliver a validated response to the runtime.

        Records the response in event history and attempts delivery to the
        runtime executor if available.

        Args:
            route: ResponseRoute to deliver

        Returns:
            True if delivery successful, False otherwise

        Raises:
            ValueError: If route validation failed

        Example:
            >>> route = manager.validate_and_route("evt_123", "yes")
            >>> if route and route.valid:
            ...     success = await manager.deliver_response(route)
            ...     if success:
            ...         print("Response delivered successfully")
        """
        if not route.valid:
            error_msg = "; ".join(route.validation_errors)
            raise ValueError(f"Cannot deliver invalid response: {error_msg}")

        # Mark route as delivered
        route.delivered = True
        route.delivery_timestamp = _utc_now()

        # Track in history
        self._add_to_history(route)

        # For non-blocking events, no runtime delivery needed
        if not route.event.is_blocking:
            logger.debug(
                "Event %s is non-blocking, no runtime delivery needed",
                route.event.id,
            )
            return True

        # Deliver to runtime if executor available
        if not self.runtime_executor:
            logger.warning(
                "No runtime executor available, cannot deliver response for event %s",
                route.event.id,
            )
            return False

        # Note: Actual delivery is handled by EventHandler which has session context
        # ResponseManager just validates and tracks responses
        # The EventHandler will call executor.send_message() with session's active_pane
        logger.info(
            "Response validated and ready for delivery (event %s): %s",
            route.event.id,
            route.response[:50],
        )
        return True

    def _add_to_history(self, route: ResponseRoute) -> None:
        """Add response route to history tracking.

        Args:
            route: ResponseRoute to record
        """
        event_id = route.event.id
        if event_id not in self._response_history:
            self._response_history[event_id] = []

        self._response_history[event_id].append(route)
        logger.debug(
            "Added response to history for event %s (total: %d)",
            event_id,
            len(self._response_history[event_id]),
        )

    def get_response_history(self, event_id: str) -> List[ResponseRoute]:
        """Get all response attempts for an event (for audit trail).

        Args:
            event_id: Event ID to query

        Returns:
            List of ResponseRoute objects for this event (chronological order)

        Example:
            >>> history = manager.get_response_history("evt_123")
            >>> for i, route in enumerate(history, 1):
            ...     status = "valid" if route.valid else "invalid"
            ...     print(f"Attempt {i} ({status}): {route.response}")
        """
        return self._response_history.get(event_id, []).copy()

    def clear_history(self, event_id: str) -> int:
        """Clear response history for an event.

        Args:
            event_id: Event ID to clear

        Returns:
            Number of history entries removed

        Example:
            >>> removed = manager.clear_history("evt_123")
            >>> print(f"Cleared {removed} history entries")
        """
        history = self._response_history.pop(event_id, [])
        count = len(history)
        if count > 0:
            logger.debug("Cleared %d history entries for event %s", count, event_id)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about response history.

        Returns:
            Dict with statistics about tracked responses

        Example:
            >>> stats = manager.get_stats()
            >>> print(f"Total events with history: {stats['total_events']}")
            >>> print(f"Total response attempts: {stats['total_responses']}")
        """
        total_events = len(self._response_history)
        total_responses = sum(len(routes) for routes in self._response_history.values())
        valid_responses = sum(
            sum(1 for route in routes if route.valid)
            for routes in self._response_history.values()
        )
        invalid_responses = total_responses - valid_responses

        return {
            "total_events": total_events,
            "total_responses": total_responses,
            "valid_responses": valid_responses,
            "invalid_responses": invalid_responses,
        }
