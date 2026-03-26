"""Abstract base class for channel adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
