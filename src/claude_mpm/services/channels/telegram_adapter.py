"""Telegram channel adapter — delivers prompts and streams output via Bot API."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base_adapter import BaseAdapter
from .models import ChannelMessage

if TYPE_CHECKING:
    from .channel_config import TelegramChannelConfig
    from .channel_hub import ChannelHub
    from .models import SessionEvent

logger = logging.getLogger(__name__)

# Telegram message character limit
_TG_MAX_CHARS = 4096
# Send new message when buffer exceeds this threshold
_TG_OVERFLOW_THRESHOLD = 3800


def _session_name(user_id: int) -> str:
    """Build the MPM session name for a Telegram user (one session per user in V1)."""
    return f"telegram-{user_id}"


class TelegramAdapter(BaseAdapter):
    """Telegram channel adapter.

    Commands:
    - /run <prompt>  — create a session and route the prompt
    - /status        — list active sessions for this user
    - /sessions      — verbose session listing
    - /kill <name>   — stop a named session owned by this user
    - /help          — show available commands

    Output streaming:
    - Subscribes to ChannelHub session events
    - Accumulates assistant_message text and edits the tracked message (debounced)
    - Sends a new message when the buffer exceeds _TG_OVERFLOW_THRESHOLD chars
    - Finalizes with ✅ or ❌ on state_change → idle/completed/error

    Critical: uses Application.initialize() + Application.start() + updater.start_polling()
    instead of run_polling() so it integrates with the existing asyncio event loop.
    """

    channel_name = "telegram"

    def __init__(self, hub: ChannelHub, config: TelegramChannelConfig) -> None:
        super().__init__(hub)
        self.config = config
        self._app: Any = None
        # session_name → (chat_id, message_id)
        self._session_messages: dict[str, tuple[int, int]] = {}
        # session_name → accumulated text
        self._output_buffers: dict[str, str] = {}
        # session_name → asyncio.Task (debounce edit tasks)
        self._debounce_tasks: dict[str, asyncio.Task[None]] = {}
        # session_name → owner user_id
        self._session_owners: dict[str, int] = {}

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the Telegram adapter without blocking the event loop."""
        try:
            from telegram.ext import Application, CommandHandler
        except ImportError as exc:
            raise ImportError(
                "Telegram support requires: pip install 'claude-mpm[telegram]'"
            ) from exc

        token = os.environ.get(self.config.bot_token_env, "")
        if not token:
            logger.warning(
                "TelegramAdapter: bot token env '%s' is empty, adapter not starting",
                self.config.bot_token_env,
            )
            return

        self._app = Application.builder().token(token).build()

        # Register command handlers
        self._app.add_handler(CommandHandler("run", self._cmd_run))
        self._app.add_handler(CommandHandler("status", self._cmd_status))
        self._app.add_handler(CommandHandler("sessions", self._cmd_sessions))
        self._app.add_handler(CommandHandler("kill", self._cmd_kill))
        self._app.add_handler(CommandHandler("help", self._cmd_help))

        # Start the application non-blockingly
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

        # Subscribe to session events
        await self.hub.registry.subscribe(self.on_event)

        logger.info("TelegramAdapter started (polling)")

    async def stop(self) -> None:
        """Stop the Telegram adapter cleanly."""
        if self._app is not None:
            try:
                await self._app.updater.stop()
                await self._app.stop()
                await self._app.shutdown()
            except Exception:
                logger.warning("TelegramAdapter: error during shutdown", exc_info=True)

        # Cancel pending debounce tasks
        for task in list(self._debounce_tasks.values()):
            if not task.done():
                task.cancel()
        self._debounce_tasks.clear()

        try:
            await self.hub.registry.unsubscribe(self.on_event)
        except Exception:
            pass

        logger.info("TelegramAdapter stopped")

    # ── Allowlist check ────────────────────────────────────────────────────

    def _is_allowed(self, user_id: int) -> bool:
        """Return True if the user is in the allowlist (or the allowlist is empty)."""
        if not self.config.allowed_user_ids:
            # Empty list means open access (not recommended for production)
            return True
        return user_id in self.config.allowed_user_ids

    # ── Command handlers ───────────────────────────────────────────────────

    async def _cmd_run(self, update: Any, context: Any) -> None:
        """Handle /run <prompt> — create session and route prompt."""
        user = update.effective_user
        if user is None:
            return
        if not self._is_allowed(user.id):
            await update.message.reply_text("⛔ Not authorized.")
            return

        args = context.args or []
        prompt = " ".join(args).strip()
        if not prompt:
            await update.message.reply_text(
                "Usage: /run <prompt>\nExample: /run fix all linting errors"
            )
            return

        session_name = _session_name(user.id)
        chat_id = update.effective_chat.id

        # Send initial "starting" message and track its ID
        sent = await update.message.reply_text("⏳ Starting session…")
        self._session_messages[session_name] = (chat_id, sent.message_id)
        self._output_buffers[session_name] = ""
        self._session_owners[session_name] = user.id

        # Determine working directory
        cwd = self.config.default_cwd or ""
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
                user_id=str(user.id),
                user_display=user.full_name or str(user.id),
            )
        except ValueError:
            # Session already exists — reuse it
            logger.debug(
                "TelegramAdapter: session '%s' already exists, reusing", session_name
            )

        # Route the prompt as a ChannelMessage
        async def _reply(text: str) -> None:
            """Fallback reply function (not normally used for streaming)."""
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=text[:_TG_MAX_CHARS]
                )
            except Exception:
                logger.warning("TelegramAdapter: fallback reply failed", exc_info=True)

        msg = ChannelMessage(
            text=prompt,
            session_name=session_name,
            channel=self.channel_name,
            user_id=str(user.id),
            user_display=user.full_name or str(user.id),
            reply_fn=_reply,
        )
        await self.route_message(msg)
        logger.info(
            "TelegramAdapter: user %d created session '%s' with prompt: %s",
            user.id,
            session_name,
            prompt[:80],
        )

    async def _cmd_status(self, update: Any, _context: Any) -> None:
        """Handle /status — list active sessions for this user."""
        user = update.effective_user
        if user is None:
            return
        if not self._is_allowed(user.id):
            await update.message.reply_text("⛔ Not authorized.")
            return

        user_sessions = [
            name
            for name, owner_id in self._session_owners.items()
            if owner_id == user.id
        ]
        if not user_sessions:
            await update.message.reply_text("No active sessions.")
        else:
            lines = ["Active sessions:"] + [f"  • {name}" for name in user_sessions]
            await update.message.reply_text("\n".join(lines))

    async def _cmd_sessions(self, update: Any, _context: Any) -> None:
        """Handle /sessions — verbose session listing with start times."""
        user = update.effective_user
        if user is None:
            return
        if not self._is_allowed(user.id):
            await update.message.reply_text("⛔ Not authorized.")
            return

        user_sessions = [
            name
            for name, owner_id in self._session_owners.items()
            if owner_id == user.id
        ]
        if not user_sessions:
            await update.message.reply_text("No active sessions.")
            return

        lines = ["Active sessions:"]
        for name in user_sessions:
            # Look up session info from hub registry
            session = await self.hub.get_session(name)
            if session:
                import datetime

                started = datetime.datetime.fromtimestamp(session.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                lines.append(
                    f"  • {name} (started {started}, state: {session.state.value})"
                )
            else:
                lines.append(f"  • {name}")
        await update.message.reply_text("\n".join(lines))

    async def _cmd_kill(self, update: Any, context: Any) -> None:
        """Handle /kill <session_name> — stop a named session."""
        user = update.effective_user
        if user is None:
            return
        if not self._is_allowed(user.id):
            await update.message.reply_text("⛔ Not authorized.")
            return

        args = context.args or []
        if not args:
            await update.message.reply_text("Usage: /kill <session_name>")
            return

        target = args[0].strip()

        # Only allow killing sessions owned by this user
        owner_id = self._session_owners.get(target)
        if owner_id is None:
            await update.message.reply_text(f"Session '{target}' not found.")
            return
        if owner_id != user.id:
            await update.message.reply_text(f"Session '{target}' is not owned by you.")
            return

        # Stop the worker via public API
        await self.hub.stop_session(target)
        self._cleanup_session(target)
        await update.message.reply_text(f"Session '{target}' stopped.")

    async def _cmd_help(self, update: Any, _context: Any) -> None:
        """Handle /help — show available commands."""
        user = update.effective_user
        if user is None:
            return
        if not self._is_allowed(user.id):
            await update.message.reply_text("⛔ Not authorized.")
            return

        help_text = (
            "Available commands:\n"
            "  /run <prompt>        — Start a new Claude session\n"
            "  /status              — List your active sessions\n"
            "  /sessions            — Verbose session listing\n"
            "  /kill <session_name> — Stop a session\n"
            "  /help                — Show this help message"
        )
        await update.message.reply_text(help_text)

    # ── Session event handler ──────────────────────────────────────────────

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
                await self._schedule_debounced_edit(session_name)

        elif event.event_type == "state_change":
            state = event.data.get("state", "")
            if state in ("idle", "completed", "error", "stopped"):
                # Cancel pending debounce and do final edit
                task = self._debounce_tasks.pop(session_name, None)
                if task and not task.done():
                    task.cancel()
                final_marker = "✅ Done." if state not in ("error",) else "❌ Error."
                await self._flush_output(session_name, final=True, marker=final_marker)
                self._cleanup_session(session_name)

    # ── Debounce / output flushing ─────────────────────────────────────────

    async def _schedule_debounced_edit(self, session_name: str) -> None:
        """Schedule a debounced edit. At most one pending edit per session."""
        existing = self._debounce_tasks.get(session_name)
        if existing and not existing.done():
            return  # Already scheduled

        interval_s = (
            self.config.edit_interval_ms
            if hasattr(self.config, "edit_interval_ms")
            else 2000
        ) / 1000.0

        async def _debounced() -> None:
            await asyncio.sleep(interval_s)
            await self._flush_output(session_name, final=False)

        task: asyncio.Task[None] = asyncio.create_task(
            _debounced(), name=f"tg-debounce-{session_name}"
        )
        self._debounce_tasks[session_name] = task

    async def _flush_output(
        self,
        session_name: str,
        final: bool = False,
        marker: str = "✅ Done.",
    ) -> None:
        """Edit the tracked message with accumulated output, or send a new one on overflow."""
        tracker = self._session_messages.get(session_name)
        if tracker is None:
            return

        chat_id, msg_id = tracker
        buffer = self._output_buffers.get(session_name, "")

        if final:
            text = f"{buffer}\n\n{marker}" if buffer else marker
        else:
            text = buffer if buffer else "⏳ Processing…"

        # Telegram max length guard
        if len(text) > _TG_OVERFLOW_THRESHOLD and self._app is not None:
            # Send overflow as a new message and update tracker
            try:
                overflow_text = text[:_TG_MAX_CHARS]
                new_msg = await self._app.bot.send_message(
                    chat_id=chat_id,
                    text=overflow_text,
                )
                self._session_messages[session_name] = (chat_id, new_msg.message_id)
                self._output_buffers[session_name] = ""
                # Clean up debounce task reference
                self._debounce_tasks.pop(session_name, None)
                return
            except Exception:
                logger.warning(
                    "TelegramAdapter: failed to send overflow message for '%s'",
                    session_name,
                    exc_info=True,
                )

        # Edit existing message
        if self._app is not None:
            try:
                await self._app.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=text[:_TG_MAX_CHARS],
                )
            except Exception:
                # Edit failed (message too old, not modified, etc.) — send new message
                logger.debug(
                    "TelegramAdapter: edit_message_text failed for '%s', sending new message",
                    session_name,
                )
                try:
                    new_msg = await self._app.bot.send_message(
                        chat_id=chat_id,
                        text=text[:_TG_MAX_CHARS],
                    )
                    self._session_messages[session_name] = (chat_id, new_msg.message_id)
                except Exception:
                    logger.warning(
                        "TelegramAdapter: fallback send_message also failed for '%s'",
                        session_name,
                        exc_info=True,
                    )

        # Clear buffer after flush
        self._output_buffers[session_name] = ""
        self._debounce_tasks.pop(session_name, None)

    # ── Cleanup ────────────────────────────────────────────────────────────

    def _cleanup_session(self, session_name: str) -> None:
        """Remove all tracking state for a finished session."""
        self._session_messages.pop(session_name, None)
        self._output_buffers.pop(session_name, None)
        self._session_owners.pop(session_name, None)
        task = self._debounce_tasks.pop(session_name, None)
        if task and not task.done():
            task.cancel()
