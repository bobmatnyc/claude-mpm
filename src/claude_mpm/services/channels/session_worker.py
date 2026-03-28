"""SessionWorker: wraps ClaudeSDKClient for a single named ChannelSession."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import ChannelMessage, ChannelSession
    from .session_registry import SessionRegistry

logger = logging.getLogger(__name__)


class SessionWorker:
    """Manages one ClaudeSDKClient session for a ChannelSession.

    Input: asyncio.Queue[ChannelMessage] — channel adapters push messages here.
    Output: broadcasts SessionEvents via SessionRegistry.
    """

    def __init__(
        self,
        session: ChannelSession,
        registry: SessionRegistry,
        runner: Any,  # ClaudeRunnerProtocol
        system_prompt: str | None = None,
        mcp_config: dict | None = None,
        vector_search_ok: bool = False,
        github_context: Any = None,  # GitHubRepoContext | None
        github_mcp_config: Any = None,  # GitHubMCPConfig | None
    ) -> None:
        self.session = session
        self.registry = registry
        self.runner = runner
        self.system_prompt = system_prompt
        self.mcp_config = mcp_config or {}
        self.vector_search_ok = vector_search_ok
        self.github_context = github_context
        self.github_mcp_config = github_mcp_config
        self.input_queue: asyncio.Queue[ChannelMessage] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the session worker as an asyncio task."""
        self._task = asyncio.create_task(
            self._run(), name=f"session-{self.session.name}"
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def send(self, message: ChannelMessage) -> None:
        """Enqueue a message for processing."""
        await self.input_queue.put(message)

    async def _run(self) -> None:
        from .models import SessionEvent, SessionState

        try:
            import claude_agent_sdk as sdk  # type: ignore[import-not-found]
            from claude_agent_sdk import (  # type: ignore[import-not-found]
                AssistantMessage,
                ClaudeAgentOptions,
                ClaudeSDKClient,
                ResultMessage,
                TextBlock,
                ToolUseBlock,
            )
        except ImportError:
            logger.error("claude_agent_sdk not installed")
            return

        from claude_mpm.services.agents.hook_event_bus import HookEventBus
        from claude_mpm.services.agents.hook_factory import create_pretooluse_hook
        from claude_mpm.services.agents.session_state_tracker import (
            SessionStateTracker,
            set_global_tracker,
        )

        event_bus = HookEventBus()
        pretooluse_hook = create_pretooluse_hook(event_bus)
        HookMatcher = getattr(sdk, "HookMatcher", None)

        hooks_config: dict | None = None
        if HookMatcher is not None:
            hooks_config = {
                "PreToolUse": [HookMatcher(matcher=None, hooks=[pretooluse_hook])]
            }

        system_prompt = self.system_prompt or (
            self.runner._create_system_prompt()
            if hasattr(self.runner, "_create_system_prompt")
            else ""
        )

        # Inject output style into system prompt (SDK sessions don't load
        # user settings, so the outputStyle configured in
        # ~/.claude/settings.json is never applied automatically)
        style_content = self._get_output_style_content()
        if style_content:
            system_prompt = (
                f"{style_content}\n\n{system_prompt}"
                if system_prompt
                else style_content
            )

        # Inject GitHub context into system prompt
        if self.github_context is not None:
            try:
                from claude_mpm.services.github.system_prompt_injector import (
                    GitHubSystemPromptInjector,
                )

                system_prompt = GitHubSystemPromptInjector().inject_into_prompt(
                    system_prompt, self.github_context
                )
            except Exception:
                pass

        # Merge GitHub MCP config into mcp_servers
        mcp_servers: dict = dict(self.mcp_config) if self.mcp_config else {}
        if self.github_mcp_config is not None:
            mcp_servers[self.github_mcp_config.server_name] = (
                self.github_mcp_config.config
            )

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=self.session.cwd,
            permission_mode="bypassPermissions"
            if (
                hasattr(self.runner, "permission_mode")
                and self.runner.permission_mode == "bypassPermissions"
            )
            else None,
            hooks=hooks_config,
            mcp_servers=mcp_servers if mcp_servers else {},
        )

        tracker = SessionStateTracker()
        tracker.set_session_id(self.session.name)
        set_global_tracker(tracker)

        await self.registry.update_state(self.session.name, SessionState.IDLE)
        await self.registry.broadcast(
            SessionEvent(
                session_name=self.session.name,
                event_type="state_change",
                data={"state": "idle", "cwd": self.session.cwd},
            )
        )

        tool_id_to_agent: dict[str, str] = {}
        current_agent: str = "PM"

        try:
            async with ClaudeSDKClient(options=options) as client:
                while True:
                    # Wait for next message from any channel adapter
                    msg = await self.input_queue.get()

                    # Handle special commands
                    if msg.text.strip().startswith("/"):
                        await self._handle_command(msg)
                        self.input_queue.task_done()
                        continue

                    # Broadcast user message event
                    await self.registry.broadcast(
                        SessionEvent(
                            session_name=self.session.name,
                            event_type="user_message",
                            data={"text": msg.text, "user_display": msg.user_display},
                            channel=msg.channel,
                            user_id=msg.user_id,
                        )
                    )

                    tracker.record_user_input(msg.text)
                    await self.registry.update_state(
                        self.session.name, SessionState.PROCESSING
                    )

                    response_parts: list[str] = []
                    tool_id_to_agent = {}
                    current_agent = "PM"

                    try:
                        await client.query(msg.text)
                        async for message in client.receive_response():
                            if isinstance(message, AssistantMessage):
                                if hasattr(message, "model") and message.model:
                                    tracker.set_model(message.model)
                                parent_id = getattr(message, "parent_tool_use_id", None)
                                if parent_id and parent_id in tool_id_to_agent:
                                    current_agent = tool_id_to_agent[parent_id]
                                else:
                                    current_agent = "PM"
                                for block in message.content:
                                    if isinstance(block, TextBlock):
                                        response_parts.append(block.text)
                                        tracker.record_assistant_message(
                                            block.text,
                                            usage=getattr(message, "usage", None),
                                        )
                                        await self.registry.broadcast(
                                            SessionEvent(
                                                session_name=self.session.name,
                                                event_type="assistant_message",
                                                data={"text": block.text},
                                            )
                                        )
                                    elif isinstance(block, ToolUseBlock):
                                        tracker.record_tool_call(block.name)
                                        if block.name in ("Agent", "Task"):
                                            subagent = (
                                                block.input.get("subagent_type")
                                                or block.input.get("description", "")[
                                                    :30
                                                ]
                                                or "Agent"
                                            )
                                            tool_id_to_agent[block.id] = subagent
                                            label = f"[{current_agent}:{block.name} -> {subagent}]"
                                        else:
                                            label = f"[{current_agent}:{block.name}]"
                                        await self.registry.broadcast(
                                            SessionEvent(
                                                session_name=self.session.name,
                                                event_type="tool_call",
                                                data={
                                                    "label": label,
                                                    "tool": block.name,
                                                    "agent": current_agent,
                                                },
                                            )
                                        )
                            elif isinstance(message, ResultMessage):
                                if message.session_id:
                                    self.session.session_id = message.session_id
                                tracker.record_result(
                                    session_id=getattr(message, "session_id", None),
                                    cost=getattr(message, "total_cost_usd", None),
                                    num_turns=getattr(message, "num_turns", None),
                                    usage=getattr(message, "usage", None),
                                )
                                await self.registry.update_state(
                                    self.session.name, SessionState.IDLE
                                )
                    except Exception as e:
                        logger.exception("Session '%s' query error", self.session.name)
                        await self.registry.broadcast(
                            SessionEvent(
                                session_name=self.session.name,
                                event_type="error",
                                data={"error": str(e)},
                            )
                        )

                    # Route full response back to originating channel
                    full_response = "\n".join(response_parts)
                    if full_response and msg.reply_fn:
                        try:
                            await msg.reply_fn(full_response)
                        except Exception:
                            logger.exception(
                                "Failed to send reply to channel '%s'", msg.channel
                            )

                    self.input_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Session '%s' worker cancelled", self.session.name)
        finally:
            tracker.record_stopped()
            from .models import SessionState

            await self.registry.update_state(self.session.name, SessionState.STOPPED)
            await self.registry.broadcast(
                SessionEvent(
                    session_name=self.session.name,
                    event_type="state_change",
                    data={"state": "stopped"},
                )
            )

    @staticmethod
    def _get_output_style_content() -> str | None:
        """Load the configured output style content for injection into system prompt."""
        from claude_mpm.core.output_style_manager import get_output_style_for_injection

        return get_output_style_for_injection()

    async def _handle_command(self, msg: ChannelMessage) -> None:
        """Handle /cd and other session-level commands."""
        text = msg.text.strip()
        if text.startswith("/cd "):
            from pathlib import Path

            new_dir = text[4:].strip()
            expanded = str(Path(new_dir).expanduser())
            if os.path.isdir(expanded):
                self.session.cwd = expanded
                if msg.reply_fn:
                    await msg.reply_fn(f"Working directory changed to {expanded}")
            elif msg.reply_fn:
                await msg.reply_fn(f"Directory not found: {new_dir}")
        elif text == "/status":
            info = (
                f"Session: {self.session.name}\n"
                f"CWD: {self.session.cwd}\n"
                f"State: {self.session.state.value}\n"
                f"Participants: {len(self.session.participants)}"
            )
            if msg.reply_fn:
                await msg.reply_fn(info)
