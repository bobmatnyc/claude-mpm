"""Slack channel adapter — delivers prompts and streams output via Socket Mode."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base_adapter import BaseAdapter
from .models import ChannelMessage

if TYPE_CHECKING:
    from .channel_config import SlackChannelConfig
    from .channel_hub import ChannelHub
    from .models import SessionEvent

logger = logging.getLogger(__name__)

# Slack message character limit
_SLACK_MAX_CHARS = 3000
# Default debounce interval for message updates (ms)
_DEFAULT_UPDATE_INTERVAL_MS = 3000


def _session_name(user_id: str) -> str:
    """Build the MPM session name for a Slack user (one session per user)."""
    return f"slack-{user_id}"


class SlackAdapter(BaseAdapter):
    """Slack channel adapter via Socket Mode.

    Commands:
    - @mention <prompt>         -- create a session and route the prompt
    - /mpm-run <prompt>         -- create a session and route the prompt
    - /mpm-status               -- list active sessions for this user
    - /mpm-sessions             -- verbose session listing
    - /mpm-kill <session_name>  -- stop a named session owned by this user
    - /mpm-help                 -- show available commands

    Output streaming:
    - Subscribes to ChannelHub session events
    - Accumulates assistant_message text and updates the tracked message (debounced)
    - Finalizes with completion/error context block on state_change
    - Uses Block Kit formatting when config.use_block_kit is True

    Critical: uses AsyncApp + AsyncSocketModeHandler with start_async()
    instead of blocking start() so it integrates with the existing asyncio event loop.
    """

    channel_name = "slack"

    def __init__(self, hub: ChannelHub, config: SlackChannelConfig) -> None:
        super().__init__(hub)
        self.config = config
        self._app: Any = None
        self._handler: Any = None
        self._running = False
        # session_name -> {"channel": str, "ts": str, "thread_ts": str | None}
        self._session_messages: dict[str, dict[str, Any]] = {}
        # session_name -> accumulated text
        self._output_buffers: dict[str, str] = {}
        # session_name -> asyncio.Task (debounce edit tasks)
        self._debounce_tasks: dict[str, asyncio.Task[None]] = {}
        # session_name -> owner user_id
        self._session_owners: dict[str, str] = {}

    # -- Lifecycle -------------------------------------------------------------

    async def start(self) -> None:
        """Start the Slack adapter without blocking the event loop."""
        try:
            from slack_bolt.adapter.socket_mode.async_handler import (
                AsyncSocketModeHandler,
            )
            from slack_bolt.async_app import AsyncApp
        except ImportError as exc:
            raise ImportError(
                "Slack support requires: pip install slack-bolt slack-sdk"
            ) from exc

        bot_token = os.environ.get(self.config.bot_token_env, "")
        app_token = os.environ.get(self.config.app_token_env, "")
        if not bot_token or not app_token:
            logger.warning("SlackAdapter: bot_token or app_token missing, skipping")
            return

        self._app = AsyncApp(token=bot_token)

        # Register handlers
        self._app.event("app_mention")(self._handle_mention)
        self._app.command("/mpm-run")(self._handle_run_command)
        self._app.command("/mpm-status")(self._handle_status_command)
        self._app.command("/mpm-sessions")(self._handle_sessions_command)
        self._app.command("/mpm-kill")(self._handle_kill_command)
        self._app.command("/mpm-help")(self._handle_help_command)

        self._handler = AsyncSocketModeHandler(self._app, app_token)
        await self._handler.start_async()
        self._running = True

        # Subscribe to session events
        await self.hub.registry.subscribe(self.on_event)

        logger.info("SlackAdapter started via Socket Mode")

    async def stop(self) -> None:
        """Stop the Slack adapter cleanly."""
        self._running = False

        if self._handler is not None:
            try:
                await self._handler.close_async()
            except Exception:
                logger.warning(
                    "SlackAdapter: error during handler shutdown", exc_info=True
                )

        # Cancel pending debounce tasks
        for task in list(self._debounce_tasks.values()):
            if not task.done():
                task.cancel()
        self._debounce_tasks.clear()

        try:
            await self.hub.registry.unsubscribe(self.on_event)
        except Exception:
            pass

        logger.info("SlackAdapter stopped")

    # -- Permission check ------------------------------------------------------

    def _is_allowed(
        self,
        *,
        user_id: str = "",
        channel_id: str = "",
        team_id: str = "",
    ) -> bool:
        """Return True if the request passes permission checks.

        If all allowlists are empty, allow all.
        If any list is non-empty, the corresponding value must match at least one entry.
        """
        ws_ids = self.config.allowed_workspace_ids
        ch_ids = self.config.allowed_channel_ids
        usr_ids = self.config.allowed_user_ids

        # If all lists empty -> allow all
        if not ws_ids and not ch_ids and not usr_ids:
            return True

        # If a list is non-empty, the request value must be in it
        if ws_ids and team_id not in ws_ids:
            return False
        if ch_ids and channel_id not in ch_ids:
            return False
        if usr_ids and user_id not in usr_ids:
            return False

        return True

    # -- Event handlers --------------------------------------------------------

    async def _handle_mention(self, event: dict[str, Any], say: Any) -> None:
        """Handle app_mention events — parse prompt and create session."""
        user_id = event.get("user", "")
        channel = event.get("channel", "")
        team_id = event.get("team", "")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        if not self._is_allowed(user_id=user_id, channel_id=channel, team_id=team_id):
            await say(text="Not authorized.", thread_ts=thread_ts)
            return

        # Strip the bot mention prefix (e.g. "<@U12345> prompt text")
        import re

        prompt = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
        if not prompt:
            await say(
                text="Usage: @bot <prompt>\nExample: @bot fix all linting errors",
                thread_ts=thread_ts,
            )
            return

        await self._create_and_track_session(
            user_id=user_id,
            channel=channel,
            thread_ts=thread_ts,
            prompt=prompt,
        )

    async def _handle_run_command(
        self, ack: Any, body: dict[str, Any], say: Any
    ) -> None:
        """Handle /mpm-run slash command."""
        await ack()

        user_id = body.get("user_id", "")
        channel = body.get("channel_id", "")
        team_id = body.get("team_id", "")
        prompt = body.get("text", "").strip()

        if not self._is_allowed(user_id=user_id, channel_id=channel, team_id=team_id):
            await say(text="Not authorized.")
            return

        if not prompt:
            await say(
                text="Usage: /mpm-run <prompt>\nExample: /mpm-run fix all linting errors"
            )
            return

        await self._create_and_track_session(
            user_id=user_id,
            channel=channel,
            thread_ts=None,
            prompt=prompt,
        )

    async def _handle_status_command(
        self, ack: Any, body: dict[str, Any], say: Any
    ) -> None:
        """Handle /mpm-status — list active sessions for this user."""
        await ack()

        user_id = body.get("user_id", "")
        user_sessions = [
            name
            for name, owner_id in self._session_owners.items()
            if owner_id == user_id
        ]
        if not user_sessions:
            await say(text="No active sessions.")
        else:
            lines = ["Active sessions:"] + [f"  - {name}" for name in user_sessions]
            await say(text="\n".join(lines))

    async def _handle_sessions_command(
        self, ack: Any, body: dict[str, Any], say: Any
    ) -> None:
        """Handle /mpm-sessions — verbose session listing."""
        await ack()

        user_id = body.get("user_id", "")
        user_sessions = [
            name
            for name, owner_id in self._session_owners.items()
            if owner_id == user_id
        ]
        if not user_sessions:
            await say(text="No active sessions.")
            return

        lines = ["Active sessions:"]
        for name in user_sessions:
            session = await self.hub.get_session(name)
            if session:
                import datetime

                started = datetime.datetime.fromtimestamp(session.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                lines.append(
                    f"  - {name} (started {started}, state: {session.state.value})"
                )
            else:
                lines.append(f"  - {name}")
        await say(text="\n".join(lines))

    async def _handle_kill_command(
        self, ack: Any, body: dict[str, Any], say: Any
    ) -> None:
        """Handle /mpm-kill <session_name> — stop a named session."""
        await ack()

        user_id = body.get("user_id", "")
        target = body.get("text", "").strip()

        if not target:
            await say(text="Usage: /mpm-kill <session_name>")
            return

        owner_id = self._session_owners.get(target)
        if owner_id is None:
            await say(text=f"Session '{target}' not found.")
            return
        if owner_id != user_id:
            await say(text=f"Session '{target}' is not owned by you.")
            return

        # Stop the worker via public API
        await self.hub.stop_session(target)
        self._cleanup_session(target)
        await say(text=f"Session '{target}' stopped.")

    async def _handle_help_command(
        self, ack: Any, _body: dict[str, Any], say: Any
    ) -> None:
        """Handle /mpm-help — show available commands."""
        await ack()

        help_text = (
            "Available commands:\n"
            "  @bot <prompt>              - Start a new Claude session\n"
            "  /mpm-run <prompt>          - Start a new Claude session\n"
            "  /mpm-status                - List your active sessions\n"
            "  /mpm-sessions              - Verbose session listing\n"
            "  /mpm-kill <session_name>   - Stop a session\n"
            "  /mpm-help                  - Show this help message"
        )
        await say(text=help_text)

    # -- Session creation helper -----------------------------------------------

    async def _create_and_track_session(
        self,
        *,
        user_id: str,
        channel: str,
        thread_ts: str | None,
        prompt: str,
    ) -> None:
        """Create or reuse a session, post initial message, and route the prompt."""
        session_name = _session_name(user_id)

        # Post initial "Processing..." message
        assert self._app is not None
        response = await self._app.client.chat_postMessage(
            channel=channel,
            text="Processing...",
            thread_ts=thread_ts,
        )
        ts = response["ts"]

        self._session_messages[session_name] = {
            "channel": channel,
            "ts": ts,
            "thread_ts": thread_ts,
        }
        self._output_buffers[session_name] = ""
        self._session_owners[session_name] = user_id

        # Determine working directory
        cwd = getattr(self.config, "default_cwd", "") or ""
        if not cwd or cwd == "~":
            cwd = str(Path.home())
        else:
            cwd = str(Path(cwd).expanduser())

        # Create or reuse session
        try:
            await self.hub.create_session(
                name=session_name,
                cwd=cwd,
                channel=self.channel_name,
                user_id=user_id,
                user_display=user_id,
            )
        except ValueError:
            logger.debug(
                "SlackAdapter: session '%s' already exists, reusing", session_name
            )

        # Route the prompt as a ChannelMessage
        async def _reply(text: str) -> None:
            """Fallback reply function."""
            try:
                await self._app.client.chat_postMessage(
                    channel=channel, text=text[:_SLACK_MAX_CHARS], thread_ts=thread_ts
                )
            except Exception:
                logger.warning("SlackAdapter: fallback reply failed", exc_info=True)

        msg = ChannelMessage(
            text=prompt,
            session_name=session_name,
            channel=self.channel_name,
            user_id=user_id,
            user_display=user_id,
            reply_fn=_reply,
        )
        await self.route_message(msg)
        logger.info(
            "SlackAdapter: user %s created session '%s' with prompt: %s",
            user_id,
            session_name,
            prompt[:80],
        )

    # -- Session event handler -------------------------------------------------

    async def on_event(self, event: SessionEvent) -> None:
        """Handle session events: stream output, finalize on completion."""
        session_name = event.session_name
        if session_name not in self._session_messages:
            return  # Not our session

        if event.event_type == "assistant_message":
            text = event.data.get("text", "")
            if text:
                self._output_buffers[session_name] = (
                    self._output_buffers.get(session_name, "") + text
                )
                await self._schedule_debounced_update(session_name)

        elif event.event_type == "state_change":
            state = event.data.get("state", "")
            if state in ("idle", "completed", "error", "stopped"):
                # Cancel pending debounce and do final update
                task = self._debounce_tasks.pop(session_name, None)
                if task and not task.done():
                    task.cancel()
                is_error = state == "error"
                await self._flush_output(session_name, final=True, is_error=is_error)
                self._cleanup_session(session_name)

    # -- Debounce / output flushing --------------------------------------------

    async def _schedule_debounced_update(self, session_name: str) -> None:
        """Schedule a debounced chat_update. At most one pending update per session."""
        existing = self._debounce_tasks.get(session_name)
        if existing and not existing.done():
            return  # Already scheduled

        interval_s = (
            getattr(self.config, "update_interval_ms", _DEFAULT_UPDATE_INTERVAL_MS)
            / 1000.0
        )

        async def _debounced() -> None:
            await asyncio.sleep(interval_s)
            await self._flush_output(session_name, final=False)

        task: asyncio.Task[None] = asyncio.create_task(
            _debounced(), name=f"slack-debounce-{session_name}"
        )
        self._debounce_tasks[session_name] = task

    async def _flush_output(
        self,
        session_name: str,
        final: bool = False,
        is_error: bool = False,
    ) -> None:
        """Update the tracked Slack message with accumulated output."""
        tracker = self._session_messages.get(session_name)
        if tracker is None or self._app is None:
            return

        channel = tracker["channel"]
        ts = tracker["ts"]
        buffer = self._output_buffers.get(session_name, "")
        output_text = buffer if buffer else "Processing..."

        use_block_kit = getattr(self.config, "use_block_kit", True)

        if use_block_kit:
            blocks: list[dict[str, Any]] = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": output_text[:_SLACK_MAX_CHARS]},
                },
            ]
            if final:
                status_text = "Session error" if is_error else "Session complete"
                status_emoji = "\u274c" if is_error else "\u2705"
                blocks.append(
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"{status_emoji} {status_text}"}
                        ],
                    }
                )
            try:
                await self._app.client.chat_update(
                    channel=channel,
                    ts=ts,
                    text=output_text[:_SLACK_MAX_CHARS],
                    blocks=blocks,
                )
            except Exception:
                logger.warning(
                    "SlackAdapter: chat_update failed for '%s'",
                    session_name,
                    exc_info=True,
                )
        else:
            if final:
                marker = "\u274c Error." if is_error else "\u2705 Done."
                text = f"{output_text}\n\n{marker}" if output_text else marker
            else:
                text = output_text
            try:
                await self._app.client.chat_update(
                    channel=channel,
                    ts=ts,
                    text=text[:_SLACK_MAX_CHARS],
                )
            except Exception:
                logger.warning(
                    "SlackAdapter: chat_update failed for '%s'",
                    session_name,
                    exc_info=True,
                )

        # Clear buffer after flush
        self._output_buffers[session_name] = ""
        self._debounce_tasks.pop(session_name, None)

    # -- Cleanup ---------------------------------------------------------------

    def _cleanup_session(self, session_name: str) -> None:
        """Remove all tracking state for a finished session."""
        self._session_messages.pop(session_name, None)
        self._output_buffers.pop(session_name, None)
        self._session_owners.pop(session_name, None)
        task = self._debounce_tasks.pop(session_name, None)
        if task and not task.done():
            task.cancel()
