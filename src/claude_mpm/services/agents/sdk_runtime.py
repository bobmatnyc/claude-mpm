"""Prototype SDK-based agent launcher for Claude MPM.

This module provides an alternative to subprocess-based agent execution
by using the claude-agent-sdk Python package for direct, in-process
communication with Claude Code.

Usage:
    runner = SDKAgentRunner(
        system_prompt="You are a helpful assistant.",
        model="claude-sonnet-4-20250514",
    )
    result = await runner.run("Explain dependency injection.")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from claude_agent_sdk import PermissionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful SDK import - the SDK is optional at runtime so that tests and
# environments without Claude Code installed can still import this module.
# ---------------------------------------------------------------------------
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        PermissionResultAllow,
        PermissionResultDeny,
        ResultMessage,
        TextBlock,
        ToolResultBlock,
        ToolUseBlock,
        query as sdk_query,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRecord:
    """Record of a single tool invocation observed during a run."""

    tool_name: str
    input: dict[str, Any]
    output: str | None = None
    approved: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class SDKAgentResult:
    """Structured result returned by SDKAgentRunner after a run completes."""

    text: str
    session_id: str | None = None
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    cost_usd: float | None = None
    num_turns: int | None = None
    duration_ms: int | None = None
    is_error: bool = False
    raw_messages: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class SDKAgentRunner:
    """Execute agent prompts via the claude-agent-sdk Python package.

    Two execution modes are supported:

    * ``run()`` - fire-and-forget via ``query()`` (one-shot, stateless).
    * ``run_with_hooks()`` - persistent session via ``ClaudeSDKClient`` with
      optional ``can_use_tool`` callback for tool interception.
    * ``inject()`` - multi-turn conversation using ``ClaudeSDKClient``.
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        model: str | None = None,
        allowed_tools: list[str] | None = None,
        permission_mode: str | None = None,
        cwd: str | None = None,
        max_turns: int | None = None,
        max_budget_usd: float | None = None,
    ) -> None:
        if not SDK_AVAILABLE:
            raise RuntimeError(
                "claude-agent-sdk is not installed. "
                "Install it with: pip install claude-agent-sdk"
            )

        self.system_prompt = system_prompt
        self.model = model
        self.allowed_tools = allowed_tools
        self.permission_mode = permission_mode
        self.cwd = cwd
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd

    # -- helpers -------------------------------------------------------------

    def _build_options(self, **overrides: Any) -> ClaudeAgentOptions:
        """Build a ``ClaudeAgentOptions`` from stored config + overrides."""
        kwargs: dict[str, Any] = {}
        if self.system_prompt is not None:
            kwargs["system_prompt"] = self.system_prompt
        if self.model is not None:
            kwargs["model"] = self.model
        if self.allowed_tools is not None:
            kwargs["allowed_tools"] = self.allowed_tools
        if self.permission_mode is not None:
            kwargs["permission_mode"] = self.permission_mode
        if self.cwd is not None:
            kwargs["cwd"] = self.cwd
        if self.max_turns is not None:
            kwargs["max_turns"] = self.max_turns
        if self.max_budget_usd is not None:
            kwargs["max_budget_usd"] = self.max_budget_usd
        kwargs.update(overrides)
        return ClaudeAgentOptions(**kwargs)

    @staticmethod
    def _extract_result(messages: list[Any]) -> SDKAgentResult:
        """Walk the collected messages and build an ``SDKAgentResult``."""
        text_parts: list[str] = []
        tool_calls: list[ToolCallRecord] = []
        session_id: str | None = None
        cost_usd: float | None = None
        num_turns: int | None = None
        duration_ms: int | None = None
        is_error = False

        # Track pending tool uses so we can pair them with results
        pending_tools: dict[str, ToolCallRecord] = {}

        for msg in messages:
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        record = ToolCallRecord(
                            tool_name=block.name,
                            input=block.input if isinstance(block.input, dict) else {},
                        )
                        pending_tools[block.id] = record
                        tool_calls.append(record)
                    elif isinstance(block, ToolResultBlock):
                        tool_use_id = block.tool_use_id
                        if tool_use_id in pending_tools:
                            content = block.content
                            if isinstance(content, list):
                                parts = []
                                for item in content:
                                    if isinstance(item, TextBlock):
                                        parts.append(item.text)
                                    elif isinstance(item, dict) and "text" in item:
                                        parts.append(item["text"])
                                content = "\n".join(parts) if parts else str(content)
                            pending_tools[tool_use_id].output = (
                                str(content) if content else None
                            )
                            if block.is_error:
                                pending_tools[tool_use_id].approved = False

            elif isinstance(msg, ResultMessage):
                session_id = msg.session_id
                cost_usd = msg.total_cost_usd
                num_turns = msg.num_turns
                duration_ms = msg.duration_ms
                is_error = bool(msg.is_error)
                # ResultMessage may contain final text in .result
                if msg.result:
                    text_parts.append(str(msg.result))

        return SDKAgentResult(
            text="\n".join(text_parts),
            session_id=session_id,
            tool_calls=tool_calls,
            cost_usd=cost_usd,
            num_turns=num_turns,
            duration_ms=duration_ms,
            is_error=is_error,
            raw_messages=messages,
        )

    # -- public API ----------------------------------------------------------

    async def run(self, prompt: str, **option_overrides: Any) -> SDKAgentResult:
        """One-shot query via ``sdk_query()``.

        This is the simplest execution mode: send a prompt, collect all
        response messages, and return a structured result.
        """
        options = self._build_options(**option_overrides)
        messages: list[Any] = []

        async for msg in sdk_query(prompt=prompt, options=options):
            messages.append(msg)
            logger.debug("sdk_query message: %s", type(msg).__name__)

        return self._extract_result(messages)

    async def run_with_hooks(
        self,
        prompt: str,
        tool_guard: Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool]]
        | None = None,
        blocked_tools: set[str] | None = None,
        **option_overrides: Any,
    ) -> SDKAgentResult:
        """Run with a ``can_use_tool`` callback for tool interception.

        Args:
            prompt: The user prompt.
            tool_guard: An async callable ``(tool_name, tool_input) -> bool``.
                Return ``True`` to allow the tool, ``False`` to deny.
            blocked_tools: A convenience set of tool names to block outright.
            **option_overrides: Extra options forwarded to ``ClaudeAgentOptions``.
        """
        denied_tools: list[ToolCallRecord] = []

        async def _can_use_tool(
            tool_name: str,
            tool_input: dict[str, Any],
            _context: Any,
        ) -> PermissionResult:
            # Check explicit blocklist first
            if blocked_tools and tool_name in blocked_tools:
                denied_tools.append(
                    ToolCallRecord(
                        tool_name=tool_name,
                        input=tool_input,
                        approved=False,
                    )
                )
                return PermissionResultDeny(
                    reason=f"Tool '{tool_name}' is blocked by policy."
                )

            # Then delegate to the custom guard
            if tool_guard is not None:
                allowed = await tool_guard(tool_name, tool_input)
                if not allowed:
                    denied_tools.append(
                        ToolCallRecord(
                            tool_name=tool_name,
                            input=tool_input,
                            approved=False,
                        )
                    )
                    return PermissionResultDeny(
                        reason=f"Tool '{tool_name}' denied by guard."
                    )

            return PermissionResultAllow()

        options = self._build_options(can_use_tool=_can_use_tool, **option_overrides)
        messages: list[Any] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for msg in client.receive_response():
                messages.append(msg)
                logger.debug("client message: %s", type(msg).__name__)

        result = self._extract_result(messages)
        # Merge denied tool records that were captured by the callback
        for denied in denied_tools:
            if denied not in result.tool_calls:
                result.tool_calls.append(denied)
        return result

    async def inject(
        self,
        prompts: list[str],
        **option_overrides: Any,
    ) -> SDKAgentResult:
        """Multi-turn conversation: send multiple prompts sequentially.

        Each prompt waits for its response before sending the next one.
        """
        options = self._build_options(**option_overrides)
        all_messages: list[Any] = []

        async with ClaudeSDKClient(options=options) as client:
            for prompt in prompts:
                await client.query(prompt)
                async for msg in client.receive_response():
                    all_messages.append(msg)
                    logger.debug("inject message: %s", type(msg).__name__)

        return self._extract_result(all_messages)


# ---------------------------------------------------------------------------
# Demo helpers - illustrate usage patterns
# ---------------------------------------------------------------------------


async def demo_simple_query() -> SDKAgentResult:
    """Demonstrate a basic one-shot query."""
    runner = SDKAgentRunner(
        system_prompt="You are a concise assistant. Reply in one sentence.",
    )
    return await runner.run("What is dependency injection in three words?")


async def demo_tool_interception() -> SDKAgentResult:
    """Demonstrate tool interception via can_use_tool callback."""
    runner = SDKAgentRunner(
        system_prompt="You are a code assistant.",
        permission_mode="bypassPermissions",
    )

    async def _guard(tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Allow reads, block writes."""
        if tool_name in {"Write", "Edit"}:
            logger.warning("Blocked write tool: %s", tool_name)
            return False
        return True

    return await runner.run_with_hooks(
        prompt="List files in the current directory.",
        tool_guard=_guard,
    )


async def demo_command_guard() -> SDKAgentResult:
    """Demonstrate blocking dangerous tools by name."""
    runner = SDKAgentRunner(
        system_prompt="You are a safe assistant.",
    )
    return await runner.run_with_hooks(
        prompt="Show me the contents of /etc/passwd",
        blocked_tools={"Bash", "Read"},
    )
