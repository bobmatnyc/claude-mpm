"""Abstract base class for channel adapters."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .channel_hub import ChannelHub
    from .models import ChannelMessage, SessionEvent


class BaseAdapter(ABC):
    """Base class for all channel adapters (terminal, telegram, slack)."""

    channel_name: str = "base"

    def __init__(self, hub: ChannelHub) -> None:
        self.hub = hub

    @abstractmethod
    async def start(self) -> None:
        """Start the adapter (begin listening for input)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the adapter."""
        ...

    @abstractmethod
    async def on_event(self, event: SessionEvent) -> None:
        """Called when a session event is broadcast. Override to display to this channel."""

    async def route_message(self, message: ChannelMessage) -> None:
        """Send a message to the hub for routing to the target session."""
        await self.hub.route_message(message)


class BufferedOutputMixin:
    """Shared output buffering, debounce scheduling, and session cleanup logic.

    Adapters that stream assistant output back to a platform (GitHub, Telegram,
    Slack) all need:
    * An output buffer per session (new chunks since last flush)
    * A debounce task per session (coalesce rapid updates)
    * Ownership tracking (session_name -> platform-specific owner id)
    * Message tracking (session_name -> platform-specific message locator)
    * A cleanup helper that tears down all per-session state

    Subclasses keep their platform-specific ``_flush_output()`` method;
    this mixin provides the shared plumbing.
    """

    def _init_buffered_output(self) -> None:
        """Initialise the shared buffer/debounce state.

        Call from the adapter ``__init__`` *after* ``super().__init__(...)``.
        """
        self._output_buffers: dict[str, str] = {}
        self._debounce_tasks: dict[str, asyncio.Task[None]] = {}
        self._session_owners: dict[str, Any] = {}
        self._session_messages: dict[str, Any] = {}

    # -- buffer helpers --------------------------------------------------------

    def _append_output(self, session_name: str, text: str) -> None:
        """Append *text* to the session's output buffer."""
        self._output_buffers[session_name] = (
            self._output_buffers.get(session_name, "") + text
        )

    def _get_buffered_output(self, session_name: str) -> str:
        """Return the full accumulated buffer for *session_name*."""
        return self._output_buffers.get(session_name, "")

    # -- debounce scheduling ---------------------------------------------------

    async def _schedule_debounce(
        self,
        session_name: str,
        interval_s: float,
        flush_fn: Any,
    ) -> None:
        """Schedule a debounced flush.  At most one pending task per session.

        Args:
            session_name: Session key.
            interval_s: Delay in seconds before the flush fires.
            flush_fn: An async callable ``(session_name, final=False) -> None``.
        """
        existing = self._debounce_tasks.get(session_name)
        if existing and not existing.done():
            return  # Already scheduled

        async def _debounced() -> None:
            await asyncio.sleep(interval_s)
            await flush_fn(session_name, final=False)

        task: asyncio.Task[None] = asyncio.create_task(
            _debounced(), name=f"debounce-{session_name}"
        )
        self._debounce_tasks[session_name] = task

    # -- cleanup ---------------------------------------------------------------

    def _cleanup_session_buffers(self, session_name: str) -> None:
        """Remove all shared tracking state for a finished session."""
        self._output_buffers.pop(session_name, None)
        self._session_owners.pop(session_name, None)
        self._session_messages.pop(session_name, None)
        task = self._debounce_tasks.pop(session_name, None)
        if task and not task.done():
            task.cancel()

    def _cancel_all_debounce_tasks(self) -> None:
        """Cancel every pending debounce task (called during adapter stop)."""
        for task in list(self._debounce_tasks.values()):
            if not task.done():
                task.cancel()
        self._debounce_tasks.clear()
