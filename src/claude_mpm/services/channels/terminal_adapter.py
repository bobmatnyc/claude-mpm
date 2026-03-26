"""Terminal adapter: universal log + interactive client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .channel_hub import ChannelHub
    from .models import SessionEvent

from .base_adapter import BaseAdapter
from .models import ChannelMessage


class TerminalAdapter(BaseAdapter):
    """Terminal channel adapter.

    Operates in two modes:
    - Log mode (default): shows all session events with [session] prefix
    - Active mode: /switch <session> to take interactive input ownership of a session
    """

    channel_name = "terminal"

    def __init__(self, hub: ChannelHub) -> None:
        super().__init__(hub)
        self._active_session: str | None = None
        self._running = False
        self._input_task: asyncio.Task | None = None
        self._user_id = "terminal:local"
        self._user_display = "terminal"

    async def start(self) -> None:
        self._running = True
        await self.hub.registry.subscribe(self.on_event)  # global subscriber
        self._input_task = asyncio.create_task(
            self._input_loop(), name="terminal-input"
        )

    async def stop(self) -> None:
        self._running = False
        await self.hub.registry.unsubscribe(self.on_event)
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()

    async def on_event(self, event: SessionEvent) -> None:
        """Display session events with [session] prefix."""
        prefix = f"\r[{event.session_name}]"
        if event.event_type == "user_message":
            src = event.data.get("user_display", event.user_id)
            # Don't echo terminal's own messages back
            if event.channel == "terminal" and event.user_id == self._user_id:
                return
            print(f"{prefix} > {src}: {event.data.get('text', '')}")
        elif event.event_type == "assistant_message":
            print(f"{prefix} {event.data.get('text', '')}")
        elif event.event_type == "tool_call":
            print(f"{prefix}   {event.data.get('label', '')}")
        elif event.event_type == "error":
            print(f"{prefix} Warning: Error: {event.data.get('error', '')}")
        elif event.event_type == "state_change":
            state = event.data.get("state", "")
            if state in ("idle", "stopped"):
                print(f"{prefix} [{state}]")
        # Re-print prompt if in active mode
        if self._active_session:
            print(f"({self._active_session}) > ", end="", flush=True)

    async def _input_loop(self) -> None:
        """Read from stdin asynchronously."""
        loop = asyncio.get_event_loop()
        print(
            "Channel Hub active. Sessions: /new <name> [cwd]  /join <name>  /switch <name>  /sessions  /exit"
        )
        while self._running:
            try:
                prompt = (
                    f"({self._active_session}) > " if self._active_session else "hub> "
                )
                line = await loop.run_in_executor(None, lambda: input(prompt))
                await self._handle_input(line.strip())
            except EOFError:
                break
            except asyncio.CancelledError:
                break

    async def _handle_input(self, text: str) -> None:
        if not text:
            return

        # Hub-level commands (processed locally, not sent to a session)
        if text.startswith("/new "):
            parts = text[5:].split(None, 1)
            name = parts[0]
            cwd = parts[1] if len(parts) > 1 else None
            await self._cmd_new(name, cwd)
            return
        if text.startswith("/join "):
            name = text[6:].strip()
            await self._cmd_join(name)
            return
        if text.startswith("/switch "):
            name = text[8:].strip()
            await self._cmd_switch(name)
            return
        if text in ("/sessions", "/list"):
            await self._cmd_list()
            return
        if text == "/detach":
            self._active_session = None
            print("Detached. Now in log mode.")
            return
        if text == "/exit":
            print("Shutting down hub...")
            await self.hub.stop()
            return

        # Session commands routed to active session
        if self._active_session:

            async def reply(response: str) -> None:
                # Terminal reply is already shown via on_event, skip
                pass

            msg = ChannelMessage(
                text=text,
                session_name=self._active_session,
                channel=self.channel_name,
                user_id=self._user_id,
                user_display=self._user_display,
                reply_fn=reply,
            )
            await self.route_message(msg)
        else:
            print("No active session. Use /new <name> or /switch <name>.")

    async def _cmd_new(self, name: str, cwd: str | None) -> None:
        from pathlib import Path

        resolved_cwd = str(Path(cwd).expanduser()) if cwd else str(Path.cwd())
        try:
            await self.hub.create_session(
                name=name,
                cwd=resolved_cwd,
                channel=self.channel_name,
                user_id=self._user_id,
                user_display=self._user_display,
            )
            self._active_session = name
            print(f"Session '{name}' created in {resolved_cwd}. Now active.")
        except ValueError as e:
            print(f"Error: {e}")

    async def _cmd_join(self, name: str) -> None:
        try:
            await self.hub.join_session(
                name=name,
                channel=self.channel_name,
                user_id=self._user_id,
            )
            self._active_session = name
            print(f"Joined session '{name}'.")
        except (KeyError, ValueError) as e:
            print(f"Error: {e}")

    async def _cmd_switch(self, name: str) -> None:
        session = await self.hub.registry.get(name)
        if session is None:
            print(f"No session named '{name}'. Use /new {name} to create it.")
            return
        self._active_session = name
        print(f"Switched to session '{name}'.")

    async def _cmd_list(self) -> None:
        sessions = await self.hub.registry.list_sessions()
        if not sessions:
            print("No active sessions.")
            return
        print("Active sessions:")
        for s in sessions:
            marker = " <" if s.name == self._active_session else ""
            print(f"  {s.name:20} [{s.state.value:10}]  cwd={s.cwd}{marker}")
