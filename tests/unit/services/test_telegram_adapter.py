"""Unit tests for Telegram channel adapter (Issue #389).

Coverage targets:
- TelegramChannelConfig: default values, stream_edits, edit_interval_ms fields
- TelegramAdapter: ImportError raised with helpful message when python-telegram-bot missing
- TelegramAdapter._is_allowed: empty allowlist = open, restricted allowlist enforced
- TelegramAdapter session tracking: _session_messages populated, cleaned up on state_change
- TelegramAdapter message editing: edit_message_text called; overflow sends new message
- TelegramAdapter commands: /status no sessions, /kill stops worker
- TelegramAdapter lifecycle: initialize() + start() + start_polling() order, stop sequence
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from claude_mpm.services.channels.channel_config import (
    TelegramChannelConfig,  # type: ignore[import-not-found]
)

# ============================================================================
# HELPERS
# ============================================================================


def _make_config(**kwargs: object) -> TelegramChannelConfig:
    """Build a TelegramChannelConfig with sensible test defaults."""
    defaults: dict[str, object] = {
        "enabled": True,
        "bot_token_env": "CLAUDE_MPM_TELEGRAM_BOT_TOKEN",
        "allowed_user_ids": [],
        "default_cwd": "~",
        "session_mode": "per_user",
        "auth_required": True,
        "stream_edits": True,
        "edit_interval_ms": 2000,
    }
    defaults.update(kwargs)
    return TelegramChannelConfig(**defaults)  # type: ignore[arg-type]


def _make_hub_mock() -> MagicMock:
    """Return a mock ChannelHub with the minimum interface needed."""
    hub = MagicMock()
    hub.registry = MagicMock()
    hub.registry.subscribe = AsyncMock()
    hub.registry.unsubscribe = AsyncMock()
    hub.create_session = AsyncMock()
    hub.route_message = AsyncMock()
    hub.stop_session = AsyncMock(return_value=True)
    hub.get_session = AsyncMock(return_value=None)
    hub._workers = {}
    return hub


def _make_tg_app_mock() -> MagicMock:
    """Return a mock python-telegram-bot Application."""
    app = MagicMock()
    app.initialize = AsyncMock()
    app.start = AsyncMock()
    app.stop = AsyncMock()
    app.shutdown = AsyncMock()
    app.updater = MagicMock()
    app.updater.start_polling = AsyncMock()
    app.updater.stop = AsyncMock()
    app.bot = MagicMock()
    app.bot.send_message = AsyncMock()
    app.bot.edit_message_text = AsyncMock()
    app.add_handler = MagicMock()
    return app


def _make_fake_tg_modules() -> dict[str, ModuleType]:
    """Build minimal fake telegram / telegram.ext module tree."""
    telegram_mod = ModuleType("telegram")
    ext_mod = ModuleType("telegram.ext")

    builder_mock = MagicMock()
    app_mock = _make_tg_app_mock()
    builder_mock.token.return_value = builder_mock
    builder_mock.build.return_value = app_mock

    ext_mod.Application = MagicMock()
    ext_mod.Application.builder = MagicMock(return_value=builder_mock)
    ext_mod.CommandHandler = MagicMock()
    ext_mod.MessageHandler = MagicMock()
    ext_mod.filters = MagicMock()

    telegram_mod.ext = ext_mod
    return {"telegram": telegram_mod, "telegram.ext": ext_mod}, app_mock


# ============================================================================
# TestTelegramChannelConfig
# ============================================================================


class TestTelegramChannelConfig:
    def test_defaults(self) -> None:
        cfg = TelegramChannelConfig()
        assert cfg.enabled is False
        assert cfg.bot_token_env == "CLAUDE_MPM_TELEGRAM_BOT_TOKEN"
        assert cfg.allowed_user_ids == []
        assert cfg.default_cwd == "~"
        assert cfg.session_mode == "per_user"
        assert cfg.auth_required is True

    def test_stream_edits_field_exists(self) -> None:
        cfg = TelegramChannelConfig()
        assert cfg.stream_edits is True

    def test_edit_interval_ms_field_exists(self) -> None:
        cfg = TelegramChannelConfig()
        assert cfg.edit_interval_ms == 2000

    def test_custom_values(self) -> None:
        cfg = TelegramChannelConfig(
            enabled=True,
            allowed_user_ids=[111, 222],
            edit_interval_ms=1000,
            stream_edits=False,
        )
        assert cfg.enabled is True
        assert 111 in cfg.allowed_user_ids
        assert cfg.edit_interval_ms == 1000
        assert cfg.stream_edits is False


# ============================================================================
# TestTelegramAdapterImportGuard
# ============================================================================


class TestTelegramAdapterImportGuard:
    @pytest.mark.asyncio
    async def test_import_error_raised_without_library(self) -> None:
        """start() raises ImportError with helpful message when telegram not installed."""
        # Temporarily remove telegram from sys.modules to simulate missing package
        saved = {k: v for k, v in sys.modules.items() if k.startswith("telegram")}
        for k in list(saved):
            del sys.modules[k]

        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        with patch.dict(sys.modules, {"telegram": None, "telegram.ext": None}):
            with pytest.raises(ImportError) as exc_info:
                await adapter.start()

        assert "claude-mpm[telegram]" in str(exc_info.value)

        # Restore
        sys.modules.update(saved)


# ============================================================================
# TestTelegramAdapterAllowlist
# ============================================================================


class TestTelegramAdapterAllowlist:
    def test_empty_allowlist_permits_all(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=[])
        adapter = TelegramAdapter(hub=hub, config=cfg)
        assert adapter._is_allowed(99999) is True

    def test_allowlist_permits_listed_user(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=[111, 222])
        adapter = TelegramAdapter(hub=hub, config=cfg)
        assert adapter._is_allowed(111) is True
        assert adapter._is_allowed(222) is True

    def test_allowlist_rejects_unlisted_user(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=[111, 222])
        adapter = TelegramAdapter(hub=hub, config=cfg)
        assert adapter._is_allowed(333) is False

    @pytest.mark.asyncio
    async def test_cmd_run_rejects_unauthorized_user(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=[111])
        adapter = TelegramAdapter(hub=hub, config=cfg)

        # Mock update with unauthorized user
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 999
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        await adapter._cmd_run(update, MagicMock())
        update.message.reply_text.assert_called_once()
        assert "Not authorized" in update.message.reply_text.call_args[0][0]


# ============================================================================
# TestTelegramAdapterSessionTracking
# ============================================================================


class TestTelegramAdapterSessionTracking:
    @pytest.mark.asyncio
    async def test_run_command_populates_session_messages(self) -> None:
        fake_modules, app_mock = _make_fake_tg_modules()
        with patch.dict(sys.modules, fake_modules):
            from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

            hub = _make_hub_mock()
            cfg = _make_config()
            adapter = TelegramAdapter(hub=hub, config=cfg)
            adapter._app = app_mock

            sent_msg = MagicMock()
            sent_msg.message_id = 42

            update = MagicMock()
            update.effective_user = MagicMock()
            update.effective_user.id = 100
            update.effective_user.full_name = "Test User"
            update.effective_chat = MagicMock()
            update.effective_chat.id = 200
            update.message = MagicMock()
            update.message.reply_text = AsyncMock(return_value=sent_msg)

            context = MagicMock()
            context.args = ["hello", "world"]

            await adapter._cmd_run(update, context)

            session_name = "telegram-100"
            assert session_name in adapter._session_messages
            assert adapter._session_messages[session_name] == (200, 42)
            assert adapter._session_owners[session_name] == 100

    @pytest.mark.asyncio
    async def test_state_change_completed_cleans_up_session(self) -> None:
        from claude_mpm.services.channels.models import SessionEvent
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        session_name = "telegram-100"
        adapter._session_messages[session_name] = (200, 42)
        adapter._output_buffers[session_name] = "some output"
        adapter._session_owners[session_name] = 100

        event = SessionEvent(
            session_name=session_name,
            event_type="state_change",
            data={"state": "completed"},
        )
        await adapter.on_event(event)

        assert session_name not in adapter._session_messages
        assert session_name not in adapter._output_buffers
        assert session_name not in adapter._session_owners

    @pytest.mark.asyncio
    async def test_state_change_error_uses_error_marker(self) -> None:
        from claude_mpm.services.channels.models import SessionEvent
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        session_name = "telegram-100"
        adapter._session_messages[session_name] = (200, 42)
        adapter._output_buffers[session_name] = ""
        adapter._session_owners[session_name] = 100

        event = SessionEvent(
            session_name=session_name,
            event_type="state_change",
            data={"state": "error"},
        )
        await adapter.on_event(event)

        # edit_message_text should be called with error marker
        call_args_text = fake_app.bot.edit_message_text.call_args[1]["text"]
        assert "❌" in call_args_text


# ============================================================================
# TestTelegramAdapterMessageEdit
# ============================================================================


class TestTelegramAdapterMessageEdit:
    @pytest.mark.asyncio
    async def test_flush_output_calls_edit_message_text(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        session_name = "telegram-100"
        adapter._session_messages[session_name] = (200, 42)
        adapter._output_buffers[session_name] = "Hello from Claude"

        await adapter._flush_output(session_name, final=True, marker="✅ Done.")

        fake_app.bot.edit_message_text.assert_called_once()
        kwargs = fake_app.bot.edit_message_text.call_args[1]
        assert kwargs["chat_id"] == 200
        assert kwargs["message_id"] == 42
        assert "Hello from Claude" in kwargs["text"]
        assert "✅ Done." in kwargs["text"]

    @pytest.mark.asyncio
    async def test_flush_output_overflow_sends_new_message(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import (
            _TG_OVERFLOW_THRESHOLD,
            TelegramAdapter,
        )

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        new_msg = MagicMock()
        new_msg.message_id = 99
        fake_app.bot.send_message = AsyncMock(return_value=new_msg)

        session_name = "telegram-100"
        adapter._session_messages[session_name] = (200, 42)
        # Create a buffer that exceeds the overflow threshold
        adapter._output_buffers[session_name] = "x" * (_TG_OVERFLOW_THRESHOLD + 100)

        await adapter._flush_output(session_name, final=False)

        # Should have sent a new message (overflow path), not edited
        fake_app.bot.send_message.assert_called_once()
        fake_app.bot.edit_message_text.assert_not_called()
        # Tracker should point to new message
        assert adapter._session_messages[session_name] == (200, 99)

    @pytest.mark.asyncio
    async def test_flush_output_edit_failure_falls_back_to_send(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        # edit_message_text raises an exception
        fake_app.bot.edit_message_text = AsyncMock(
            side_effect=Exception("Message not modified")
        )
        new_msg = MagicMock()
        new_msg.message_id = 77
        fake_app.bot.send_message = AsyncMock(return_value=new_msg)

        session_name = "telegram-100"
        adapter._session_messages[session_name] = (200, 42)
        adapter._output_buffers[session_name] = "Some text"

        await adapter._flush_output(session_name, final=True, marker="✅ Done.")

        # Should fall back to send_message
        fake_app.bot.send_message.assert_called_once()
        # Tracker updated to new message
        assert adapter._session_messages[session_name] == (200, 77)


# ============================================================================
# TestTelegramAdapterCommands
# ============================================================================


class TestTelegramAdapterCommands:
    @pytest.mark.asyncio
    async def test_status_no_sessions(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        await adapter._cmd_status(update, MagicMock())

        update.message.reply_text.assert_called_once()
        assert "No active sessions" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_status_lists_user_sessions(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)
        adapter._session_owners["telegram-100"] = 100
        adapter._session_owners["telegram-200"] = 200

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        await adapter._cmd_status(update, MagicMock())

        call_text = update.message.reply_text.call_args[0][0]
        assert "telegram-100" in call_text
        assert "telegram-200" not in call_text

    @pytest.mark.asyncio
    async def test_kill_stops_worker(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        session_name = "telegram-100"
        adapter._session_owners[session_name] = 100
        adapter._session_messages[session_name] = (200, 42)

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = [session_name]

        await adapter._cmd_kill(update, context)

        hub.stop_session.assert_called_once_with(session_name)
        assert session_name not in adapter._session_owners

    @pytest.mark.asyncio
    async def test_kill_rejects_wrong_owner(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        session_name = "telegram-999"
        adapter._session_owners[session_name] = 999  # owned by user 999

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100  # different user trying to kill
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = [session_name]

        await adapter._cmd_kill(update, context)

        update.message.reply_text.assert_called_once()
        assert "not owned by you" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_help_returns_command_list(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        await adapter._cmd_help(update, MagicMock())

        call_text = update.message.reply_text.call_args[0][0]
        for cmd in ["/run", "/status", "/sessions", "/kill", "/help"]:
            assert cmd in call_text


# ============================================================================
# TestTelegramAdapterLifecycle
# ============================================================================


class TestTelegramAdapterLifecycle:
    @pytest.mark.asyncio
    async def test_start_calls_initialize_start_polling_in_order(self) -> None:
        fake_modules, app_mock = _make_fake_tg_modules()
        with patch.dict(sys.modules, fake_modules):
            with patch.dict(
                "os.environ", {"CLAUDE_MPM_TELEGRAM_BOT_TOKEN": "test-token"}
            ):
                from claude_mpm.services.channels.telegram_adapter import (
                    TelegramAdapter,
                )

                hub = _make_hub_mock()
                cfg = _make_config()
                adapter = TelegramAdapter(hub=hub, config=cfg)

                await adapter.start()

                app_mock.initialize.assert_called_once()
                app_mock.start.assert_called_once()
                app_mock.updater.start_polling.assert_called_once()
                hub.registry.subscribe.assert_called_once_with(adapter.on_event)

    @pytest.mark.asyncio
    async def test_start_skips_when_token_missing(self) -> None:
        fake_modules, app_mock = _make_fake_tg_modules()
        with patch.dict(sys.modules, fake_modules):
            with patch.dict("os.environ", {}, clear=False):
                # Ensure token env var is not set
                import os

                os.environ.pop("CLAUDE_MPM_TELEGRAM_BOT_TOKEN", None)

                from claude_mpm.services.channels.telegram_adapter import (
                    TelegramAdapter,
                )

                hub = _make_hub_mock()
                cfg = _make_config(bot_token_env="CLAUDE_MPM_TELEGRAM_BOT_TOKEN")
                adapter = TelegramAdapter(hub=hub, config=cfg)

                await adapter.start()

                # Application should not be initialized if token is missing
                app_mock.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_calls_updater_stop_app_stop_shutdown(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        await adapter.stop()

        fake_app.updater.stop.assert_called_once()
        fake_app.stop.assert_called_once()
        fake_app.shutdown.assert_called_once()
        hub.registry.unsubscribe.assert_called_once_with(adapter.on_event)

    @pytest.mark.asyncio
    async def test_stop_cancels_pending_debounce_tasks(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)

        fake_app = _make_tg_app_mock()
        adapter._app = fake_app

        # Create a real pending task
        async def _pending() -> None:
            await asyncio.sleep(100)

        task = asyncio.create_task(_pending())
        adapter._debounce_tasks["telegram-100"] = task

        await adapter.stop()
        # Give the event loop a tick to process cancellation
        await asyncio.sleep(0)

        assert task.cancelled()
        assert len(adapter._debounce_tasks) == 0

    @pytest.mark.asyncio
    async def test_stop_without_app_does_not_raise(self) -> None:
        from claude_mpm.services.channels.telegram_adapter import TelegramAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = TelegramAdapter(hub=hub, config=cfg)
        # _app is None (never started)

        # Should not raise
        await adapter.stop()
