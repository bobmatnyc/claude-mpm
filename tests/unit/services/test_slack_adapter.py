"""Unit tests for Slack channel adapter (Issues #390-#392).

Coverage targets:
- SlackChannelConfig: default values, use_block_kit, update_interval_ms fields
- SlackAdapter: ImportError raised with helpful message when slack-bolt not installed
- SlackAdapter._is_allowed: workspace/channel/user allowlist enforcement; empty = allow all
- SlackAdapter mention: session created, initial message posted, ts tracked
- SlackAdapter slash command: ack() called first, session created
- SlackAdapter message update: chat_update called with debounce, Block Kit blocks when enabled
- SlackAdapter lifecycle: start_async() called (not start()), close_async() on stop
- SlackAdapter session ownership: /mpm-kill only kills sessions owned by requesting user
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.channels.channel_config import (
    SlackChannelConfig,  # type: ignore[import-not-found]
)

# ============================================================================
# HELPERS
# ============================================================================


def _make_config(**kwargs: object) -> SlackChannelConfig:
    """Build a SlackChannelConfig with sensible test defaults."""
    defaults: dict[str, object] = {
        "enabled": True,
        "bot_token_env": "SLACK_BOT_TOKEN",
        "app_token_env": "SLACK_APP_TOKEN",
        "allowed_workspace_ids": [],
        "allowed_channel_ids": [],
        "allowed_user_ids": [],
        "default_cwd": "~",
        "session_mode": "per_user",
        "auth_required": True,
        "use_block_kit": True,
        "update_interval_ms": 3000,
    }
    defaults.update(kwargs)
    return SlackChannelConfig(**defaults)  # type: ignore[arg-type]


def _make_hub_mock() -> MagicMock:
    """Return a mock ChannelHub with the minimum interface needed."""
    hub = MagicMock()
    hub.registry = MagicMock()
    hub.registry.subscribe = AsyncMock()
    hub.registry.unsubscribe = AsyncMock()
    hub.registry._sessions = {}
    hub.create_session = AsyncMock()
    hub.route_message = AsyncMock()
    hub.stop_session = AsyncMock(return_value=True)
    hub.get_session = AsyncMock(return_value=None)
    hub._workers = {}
    return hub


def _make_slack_app_mock() -> MagicMock:
    """Return a mock AsyncApp with the minimum interface."""
    app = MagicMock()
    app.client = MagicMock()
    app.client.chat_postMessage = AsyncMock(return_value={"ts": "1234567890.123456"})
    app.client.chat_update = AsyncMock()
    app.event = MagicMock(return_value=lambda fn: fn)
    app.command = MagicMock(return_value=lambda fn: fn)
    return app


def _make_fake_slack_modules() -> tuple[dict[str, ModuleType], MagicMock, MagicMock]:
    """Build minimal fake slack_bolt / slack_sdk module tree."""
    slack_bolt_mod = ModuleType("slack_bolt")
    async_app_mod = ModuleType("slack_bolt.async_app")
    adapter_mod = ModuleType("slack_bolt.adapter")
    socket_mode_mod = ModuleType("slack_bolt.adapter.socket_mode")
    async_handler_mod = ModuleType("slack_bolt.adapter.socket_mode.async_handler")

    app_mock = _make_slack_app_mock()
    async_app_cls = MagicMock(return_value=app_mock)
    async_app_mod.AsyncApp = async_app_cls

    handler_mock = MagicMock()
    handler_mock.start_async = AsyncMock()
    handler_mock.close_async = AsyncMock()
    async_handler_cls = MagicMock(return_value=handler_mock)
    async_handler_mod.AsyncSocketModeHandler = async_handler_cls

    modules = {
        "slack_bolt": slack_bolt_mod,
        "slack_bolt.async_app": async_app_mod,
        "slack_bolt.adapter": adapter_mod,
        "slack_bolt.adapter.socket_mode": socket_mode_mod,
        "slack_bolt.adapter.socket_mode.async_handler": async_handler_mod,
    }
    return modules, app_mock, handler_mock


# ============================================================================
# TestSlackChannelConfig
# ============================================================================


class TestSlackChannelConfig:
    def test_defaults(self) -> None:
        cfg = SlackChannelConfig()
        assert cfg.enabled is False
        assert cfg.bot_token_env == "SLACK_BOT_TOKEN"
        assert cfg.app_token_env == "SLACK_APP_TOKEN"
        assert cfg.allowed_workspace_ids == []
        assert cfg.allowed_channel_ids == []
        assert cfg.allowed_user_ids == []
        assert cfg.default_cwd == "~"
        assert cfg.session_mode == "per_user"
        assert cfg.auth_required is True

    def test_use_block_kit_default_true(self) -> None:
        cfg = SlackChannelConfig()
        assert cfg.use_block_kit is True

    def test_update_interval_ms_default_3000(self) -> None:
        cfg = SlackChannelConfig()
        assert cfg.update_interval_ms == 3000

    def test_custom_values(self) -> None:
        cfg = SlackChannelConfig(
            enabled=True,
            allowed_workspace_ids=["T123"],
            allowed_channel_ids=["C456"],
            allowed_user_ids=["U789"],
            use_block_kit=False,
            update_interval_ms=5000,
        )
        assert cfg.enabled is True
        assert "T123" in cfg.allowed_workspace_ids
        assert "C456" in cfg.allowed_channel_ids
        assert "U789" in cfg.allowed_user_ids
        assert cfg.use_block_kit is False
        assert cfg.update_interval_ms == 5000


# ============================================================================
# TestSlackAdapterImportGuard
# ============================================================================


class TestSlackAdapterImportGuard:
    @pytest.mark.asyncio
    async def test_import_error_raised_without_library(self) -> None:
        """start() raises ImportError with helpful message when slack-bolt not installed."""
        saved = {k: v for k, v in sys.modules.items() if k.startswith("slack_bolt")}
        for k in list(saved):
            del sys.modules[k]

        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)

        with patch.dict(
            sys.modules,
            {
                "slack_bolt": None,
                "slack_bolt.async_app": None,
                "slack_bolt.adapter": None,
                "slack_bolt.adapter.socket_mode": None,
                "slack_bolt.adapter.socket_mode.async_handler": None,
            },
        ):
            with pytest.raises(ImportError) as exc_info:
                await adapter.start()

        assert "slack-bolt" in str(exc_info.value)

        # Restore
        sys.modules.update(saved)


# ============================================================================
# TestSlackAdapterPermissions
# ============================================================================


class TestSlackAdapterPermissions:
    def test_empty_allowlists_permit_all(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(
            allowed_workspace_ids=[],
            allowed_channel_ids=[],
            allowed_user_ids=[],
        )
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U999", channel_id="C999", team_id="T999")
            is True
        )

    def test_workspace_restriction_allows_matching(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_workspace_ids=["T123", "T456"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U1", channel_id="C1", team_id="T123") is True
        )

    def test_workspace_restriction_rejects_non_matching(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_workspace_ids=["T123"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U1", channel_id="C1", team_id="T999") is False
        )

    def test_channel_restriction_allows_matching(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_channel_ids=["C123"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U1", channel_id="C123", team_id="T1") is True
        )

    def test_channel_restriction_rejects_non_matching(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_channel_ids=["C123"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U1", channel_id="C999", team_id="T1") is False
        )

    def test_user_restriction_allows_matching(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=["U123"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U123", channel_id="C1", team_id="T1") is True
        )

    def test_user_restriction_rejects_non_matching(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=["U123"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        assert (
            adapter._is_allowed(user_id="U999", channel_id="C1", team_id="T1") is False
        )

    def test_combined_restrictions_all_must_pass(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(
            allowed_workspace_ids=["T123"],
            allowed_channel_ids=["C456"],
            allowed_user_ids=["U789"],
        )
        adapter = SlackAdapter(hub=hub, config=cfg)
        # All match
        assert (
            adapter._is_allowed(user_id="U789", channel_id="C456", team_id="T123")
            is True
        )
        # User mismatch
        assert (
            adapter._is_allowed(user_id="U000", channel_id="C456", team_id="T123")
            is False
        )
        # Channel mismatch
        assert (
            adapter._is_allowed(user_id="U789", channel_id="C000", team_id="T123")
            is False
        )
        # Workspace mismatch
        assert (
            adapter._is_allowed(user_id="U789", channel_id="C456", team_id="T000")
            is False
        )


# ============================================================================
# TestSlackAdapterMention
# ============================================================================


class TestSlackAdapterMention:
    @pytest.mark.asyncio
    async def test_mention_creates_session_and_posts_message(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)

        app_mock = _make_slack_app_mock()
        adapter._app = app_mock

        event = {
            "user": "U100",
            "channel": "C200",
            "team": "T300",
            "text": "<@UBOT> hello world",
            "ts": "1234567890.000001",
        }
        say = AsyncMock()

        await adapter._handle_mention(event, say)

        # chat_postMessage should have been called with initial message
        app_mock.client.chat_postMessage.assert_called_once()
        call_kwargs = app_mock.client.chat_postMessage.call_args[1]
        assert call_kwargs["channel"] == "C200"
        assert "Processing" in call_kwargs["text"]

        # Session tracking should be populated
        session_name = "slack-U100"
        assert session_name in adapter._session_messages
        assert adapter._session_messages[session_name]["channel"] == "C200"
        assert adapter._session_messages[session_name]["ts"] == "1234567890.123456"
        assert adapter._session_owners[session_name] == "U100"

        # Hub should have received the message
        hub.route_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_mention_rejects_unauthorized_user(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(allowed_user_ids=["U111"])
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        event = {
            "user": "U999",
            "channel": "C200",
            "team": "T300",
            "text": "<@UBOT> hello",
            "ts": "1234567890.000001",
        }
        say = AsyncMock()

        await adapter._handle_mention(event, say)

        say.assert_called_once()
        assert "Not authorized" in say.call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_mention_empty_prompt_shows_usage(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        event = {
            "user": "U100",
            "channel": "C200",
            "team": "T300",
            "text": "<@UBOT>",
            "ts": "1234567890.000001",
        }
        say = AsyncMock()

        await adapter._handle_mention(event, say)

        say.assert_called_once()
        assert "Usage" in say.call_args[1]["text"]


# ============================================================================
# TestSlackAdapterRunCommand
# ============================================================================


class TestSlackAdapterRunCommand:
    @pytest.mark.asyncio
    async def test_run_command_calls_ack_first(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        ack = AsyncMock()
        body = {
            "user_id": "U100",
            "channel_id": "C200",
            "team_id": "T300",
            "text": "run some task",
        }
        say = AsyncMock()

        await adapter._handle_run_command(ack, body, say)

        ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command_creates_session(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        ack = AsyncMock()
        body = {
            "user_id": "U100",
            "channel_id": "C200",
            "team_id": "T300",
            "text": "fix linting errors",
        }
        say = AsyncMock()

        await adapter._handle_run_command(ack, body, say)

        session_name = "slack-U100"
        assert session_name in adapter._session_messages
        assert adapter._session_owners[session_name] == "U100"
        hub.create_session.assert_called_once()
        hub.route_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command_empty_prompt_shows_usage(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        ack = AsyncMock()
        body = {
            "user_id": "U100",
            "channel_id": "C200",
            "team_id": "T300",
            "text": "",
        }
        say = AsyncMock()

        await adapter._handle_run_command(ack, body, say)

        ack.assert_called_once()
        say.assert_called_once()
        assert "Usage" in say.call_args[1]["text"]


# ============================================================================
# TestSlackAdapterMessageUpdate
# ============================================================================


class TestSlackAdapterMessageUpdate:
    @pytest.mark.asyncio
    async def test_flush_output_calls_chat_update(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(use_block_kit=False)
        adapter = SlackAdapter(hub=hub, config=cfg)

        app_mock = _make_slack_app_mock()
        adapter._app = app_mock

        session_name = "slack-U100"
        adapter._session_messages[session_name] = {
            "channel": "C200",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }
        adapter._output_buffers[session_name] = "Hello from Claude"

        await adapter._flush_output(session_name, final=True, is_error=False)

        app_mock.client.chat_update.assert_called_once()
        kwargs = app_mock.client.chat_update.call_args[1]
        assert kwargs["channel"] == "C200"
        assert kwargs["ts"] == "1234567890.123456"
        assert "Hello from Claude" in kwargs["text"]
        assert "\u2705" in kwargs["text"]  # checkmark

    @pytest.mark.asyncio
    async def test_flush_output_block_kit_generates_blocks(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(use_block_kit=True)
        adapter = SlackAdapter(hub=hub, config=cfg)

        app_mock = _make_slack_app_mock()
        adapter._app = app_mock

        session_name = "slack-U100"
        adapter._session_messages[session_name] = {
            "channel": "C200",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }
        adapter._output_buffers[session_name] = "Some output"

        await adapter._flush_output(session_name, final=True, is_error=False)

        app_mock.client.chat_update.assert_called_once()
        kwargs = app_mock.client.chat_update.call_args[1]
        assert "blocks" in kwargs
        blocks = kwargs["blocks"]
        assert len(blocks) == 2  # section + context
        assert blocks[0]["type"] == "section"
        assert blocks[1]["type"] == "context"
        assert "\u2705" in blocks[1]["elements"][0]["text"]

    @pytest.mark.asyncio
    async def test_flush_output_error_marker_on_error(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config(use_block_kit=True)
        adapter = SlackAdapter(hub=hub, config=cfg)

        app_mock = _make_slack_app_mock()
        adapter._app = app_mock

        session_name = "slack-U100"
        adapter._session_messages[session_name] = {
            "channel": "C200",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }
        adapter._output_buffers[session_name] = ""

        await adapter._flush_output(session_name, final=True, is_error=True)

        kwargs = app_mock.client.chat_update.call_args[1]
        blocks = kwargs["blocks"]
        context_text = blocks[1]["elements"][0]["text"]
        assert "\u274c" in context_text

    @pytest.mark.asyncio
    async def test_on_event_assistant_message_accumulates_buffer(self) -> None:
        from claude_mpm.services.channels.models import SessionEvent
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        session_name = "slack-U100"
        adapter._session_messages[session_name] = {
            "channel": "C200",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }
        adapter._output_buffers[session_name] = ""

        event = SessionEvent(
            session_name=session_name,
            event_type="assistant_message",
            data={"text": "Hello "},
        )
        await adapter.on_event(event)

        assert adapter._output_buffers[session_name] == "Hello "

        # Cancel any debounce task created
        task = adapter._debounce_tasks.get(session_name)
        if task and not task.done():
            task.cancel()

    @pytest.mark.asyncio
    async def test_on_event_state_change_completed_cleans_up(self) -> None:
        from claude_mpm.services.channels.models import SessionEvent
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._app = _make_slack_app_mock()

        session_name = "slack-U100"
        adapter._session_messages[session_name] = {
            "channel": "C200",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }
        adapter._output_buffers[session_name] = "output text"
        adapter._session_owners[session_name] = "U100"

        event = SessionEvent(
            session_name=session_name,
            event_type="state_change",
            data={"state": "completed"},
        )
        await adapter.on_event(event)

        assert session_name not in adapter._session_messages
        assert session_name not in adapter._output_buffers
        assert session_name not in adapter._session_owners


# ============================================================================
# TestSlackAdapterLifecycle
# ============================================================================


class TestSlackAdapterLifecycle:
    @pytest.mark.asyncio
    async def test_start_calls_start_async_not_start(self) -> None:
        fake_modules, _app_mock, handler_mock = _make_fake_slack_modules()
        with patch.dict(sys.modules, fake_modules):
            with patch.dict(
                "os.environ",
                {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_APP_TOKEN": "xapp-test"},
            ):
                from claude_mpm.services.channels.slack_adapter import SlackAdapter

                hub = _make_hub_mock()
                cfg = _make_config()
                adapter = SlackAdapter(hub=hub, config=cfg)

                await adapter.start()

                handler_mock.start_async.assert_called_once()
                hub.registry.subscribe.assert_called_once_with(adapter.on_event)
                assert adapter._running is True

    @pytest.mark.asyncio
    async def test_start_skips_when_tokens_missing(self) -> None:
        fake_modules, _app_mock, handler_mock = _make_fake_slack_modules()
        with patch.dict(sys.modules, fake_modules):
            with patch.dict("os.environ", {}, clear=False):
                import os

                os.environ.pop("SLACK_BOT_TOKEN", None)
                os.environ.pop("SLACK_APP_TOKEN", None)

                from claude_mpm.services.channels.slack_adapter import SlackAdapter

                hub = _make_hub_mock()
                cfg = _make_config()
                adapter = SlackAdapter(hub=hub, config=cfg)

                await adapter.start()

                handler_mock.start_async.assert_not_called()
                assert adapter._running is False

    @pytest.mark.asyncio
    async def test_stop_calls_close_async(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)

        handler_mock = MagicMock()
        handler_mock.close_async = AsyncMock()
        adapter._handler = handler_mock
        adapter._running = True

        await adapter.stop()

        handler_mock.close_async.assert_called_once()
        hub.registry.unsubscribe.assert_called_once_with(adapter.on_event)
        assert adapter._running is False

    @pytest.mark.asyncio
    async def test_stop_cancels_pending_debounce_tasks(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        adapter._handler = None  # No handler to close

        async def _pending() -> None:
            await asyncio.sleep(100)

        task = asyncio.create_task(_pending())
        adapter._debounce_tasks["slack-U100"] = task

        await adapter.stop()
        await asyncio.sleep(0)

        assert task.cancelled()
        assert len(adapter._debounce_tasks) == 0

    @pytest.mark.asyncio
    async def test_stop_without_handler_does_not_raise(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)
        # _handler is None (never started)

        # Should not raise
        await adapter.stop()


# ============================================================================
# TestSlackAdapterSessionOwnership
# ============================================================================


class TestSlackAdapterSessionOwnership:
    @pytest.mark.asyncio
    async def test_kill_rejects_wrong_owner(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)

        session_name = "slack-U999"
        adapter._session_owners[session_name] = "U999"

        ack = AsyncMock()
        body = {
            "user_id": "U100",  # different user
            "text": session_name,
        }
        say = AsyncMock()

        await adapter._handle_kill_command(ack, body, say)

        ack.assert_called_once()
        say.assert_called_once()
        assert "not owned by you" in say.call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_kill_stops_owned_session(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)

        session_name = "slack-U100"
        adapter._session_owners[session_name] = "U100"
        adapter._session_messages[session_name] = {
            "channel": "C200",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }

        ack = AsyncMock()
        body = {
            "user_id": "U100",
            "text": session_name,
        }
        say = AsyncMock()

        await adapter._handle_kill_command(ack, body, say)

        ack.assert_called_once()
        hub.stop_session.assert_called_once_with(session_name)
        assert session_name not in adapter._session_owners

    @pytest.mark.asyncio
    async def test_kill_session_not_found(self) -> None:
        from claude_mpm.services.channels.slack_adapter import SlackAdapter

        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = SlackAdapter(hub=hub, config=cfg)

        ack = AsyncMock()
        body = {
            "user_id": "U100",
            "text": "nonexistent-session",
        }
        say = AsyncMock()

        await adapter._handle_kill_command(ack, body, say)

        ack.assert_called_once()
        say.assert_called_once()
        assert "not found" in say.call_args[1]["text"]
