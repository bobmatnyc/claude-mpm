"""Factory for creating SDK hooks wired to the event bus."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .hook_event_bus import HookEventBus

logger = logging.getLogger(__name__)


def create_pretooluse_hook(
    event_bus: HookEventBus,
) -> Any:
    """Create a PreToolUse hook callback that injects pending messages.

    The returned callback is called before every tool use.  It checks the
    event bus for pending messages and returns them as a systemMessage.

    Returns:
        An async callable matching the ``HookCallback`` signature from
        ``claude_agent_sdk.types``.
    """

    async def _pretooluse_hook(
        input_data: Any,
        tool_use_id: str | None,
        context: Any,
    ) -> dict[str, Any]:
        """PreToolUse hook that injects pending sidecar messages."""
        system_message = event_bus.consume_for_hook()

        if system_message:
            logger.info(
                "Injecting %d chars from event bus into PM session",
                len(system_message),
            )
            return {"systemMessage": system_message}

        # No messages -- allow tool use with no injection
        return {}

    return _pretooluse_hook
