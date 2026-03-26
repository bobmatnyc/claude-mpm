"""Registry for named channel sessions."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .models import ChannelSession, SessionState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from .models import SessionEvent

logger = logging.getLogger(__name__)


class SessionRegistry:
    """Thread-safe registry of named ChannelSessions."""

    def __init__(self, persist_dir: Path | None = None) -> None:
        self._sessions: dict[str, ChannelSession] = {}
        self._lock = asyncio.Lock()
        # Event subscribers: session_name -> list of async callbacks
        self._subscribers: dict[
            str, list[Callable[[SessionEvent], Awaitable[None]]]
        ] = {}
        # "all sessions" subscribers (terminal log mode)
        self._global_subscribers: list[Callable[[SessionEvent], Awaitable[None]]] = []
        self._persist_dir = persist_dir or (Path.home() / ".claude-mpm" / "channels")

    async def create(
        self,
        name: str,
        cwd: str,
        channel: str,
        user_id: str,
    ) -> ChannelSession:
        """Create a new named session. Raises ValueError if name already exists."""
        async with self._lock:
            if name in self._sessions:
                raise ValueError(
                    f"Session '{name}' already exists. Use /join to attach."
                )
            session = ChannelSession(
                name=name,
                cwd=cwd,
                created_by_channel=channel,
                created_by_user=user_id,
            )
            session.add_participant(channel, user_id)
            self._sessions[name] = session
            logger.info("Created session '%s' (cwd=%s, channel=%s)", name, cwd, channel)
            return session

    async def get(self, name: str) -> ChannelSession | None:
        async with self._lock:
            return self._sessions.get(name)

    async def join(self, name: str, channel: str, user_id: str) -> ChannelSession:
        """Join an existing session. Raises KeyError if session does not exist."""
        async with self._lock:
            session = self._sessions.get(name)
            if session is None:
                raise KeyError(f"Session '{name}' does not exist.")
            if session.state == SessionState.STOPPED:
                raise ValueError(f"Session '{name}' has stopped.")
            session.add_participant(channel, user_id)
            return session

    async def list_sessions(self) -> list[ChannelSession]:
        async with self._lock:
            return list(self._sessions.values())

    async def remove(self, name: str) -> None:
        async with self._lock:
            self._sessions.pop(name, None)

    async def update_state(self, name: str, state: SessionState) -> None:
        async with self._lock:
            if session := self._sessions.get(name):
                session.state = state

    # ── Event pub/sub ──────────────────────────────────────────────────────

    async def subscribe(
        self,
        callback: Callable[[SessionEvent], Awaitable[None]],
        session_name: str | None = None,
    ) -> None:
        """Subscribe to events. session_name=None subscribes to ALL sessions (log mode)."""
        async with self._lock:
            if session_name is None:
                self._global_subscribers.append(callback)
            else:
                self._subscribers.setdefault(session_name, []).append(callback)

    async def unsubscribe(
        self,
        callback: Callable[[SessionEvent], Awaitable[None]],
        session_name: str | None = None,
    ) -> None:
        async with self._lock:
            if session_name is None:
                self._global_subscribers = [
                    s for s in self._global_subscribers if s is not callback
                ]
            else:
                subs = self._subscribers.get(session_name, [])
                self._subscribers[session_name] = [s for s in subs if s is not callback]

    async def broadcast(self, event: SessionEvent) -> None:
        """Broadcast event to all subscribers of the session and global subscribers."""
        callbacks: list[Callable[[SessionEvent], Awaitable[None]]] = []
        async with self._lock:
            callbacks.extend(self._global_subscribers)
            callbacks.extend(self._subscribers.get(event.session_name, []))
        for cb in callbacks:
            try:
                await cb(event)
            except Exception:
                logger.exception("Error in session event subscriber")
