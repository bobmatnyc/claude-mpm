"""SDK-based agent runtime for Claude MPM.

This module provides an alternative to subprocess-based agent execution
by using the claude-agent-sdk Python package for direct, in-process
communication with Claude Code.  It implements the :class:`AgentRuntime`
ABC so that higher-level orchestration code can remain backend-agnostic.

Usage:
    runner = SDKAgentRunner(
        system_prompt="You are a helpful assistant.",
        model="claude-sonnet-4-20250514",
    )
    result = await runner.run("Explain dependency injection.")

    # From an AgentConfig
    from claude_mpm.services.agents.agent_runtime import AgentConfig
    runner2 = SDKAgentRunner.from_config(AgentConfig(model="sonnet"))

    # From an MPM agent template JSON
    runner3 = SDKAgentRunner.from_agent_template("path/to/agent.json")

    # Resume a previous session
    result2 = await runner.resume(result.session_id, "Follow-up question.")

    # Streaming with callbacks
    result3 = await runner.run_streaming(
        "Explain DI.",
        on_text=my_text_handler,
        on_tool_call=my_tool_handler,
    )

    # Interruptible session
    async with runner.interruptible() as session:
        r = await session.query("Do something long-running.")
        await session.interrupt()  # cancel if needed
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_mpm.services.agents.agent_runtime import (
    AgentResult,
    AgentRuntime,
    resolve_model_to_sdk,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from claude_agent_sdk import PermissionResult

    from claude_mpm.services.agents.agent_runtime import AgentConfig

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


class SDKAgentRunner(AgentRuntime):
    """Execute agent prompts via the claude-agent-sdk Python package.

    Implements the :class:`AgentRuntime` ABC so that higher-level MPM
    orchestration code can treat SDK and CLI runtimes interchangeably.

    Three execution modes are supported:

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
        mcp_servers: dict[str, Any] | None = None,
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
        self.mcp_servers = mcp_servers

    # -- class constructors ---------------------------------------------------

    @classmethod
    def from_config(cls, config: AgentConfig) -> SDKAgentRunner:
        """Create an ``SDKAgentRunner`` from a runtime-agnostic ``AgentConfig``.

        Model names are resolved from MPM short names (e.g. ``"sonnet"``) to
        full SDK identifiers automatically.
        """
        model = resolve_model_to_sdk(config.model) if config.model else None
        return cls(
            system_prompt=config.system_prompt,
            model=model,
            allowed_tools=config.allowed_tools,
            permission_mode=config.permission_mode,
            cwd=config.cwd,
            max_turns=config.max_turns,
            max_budget_usd=config.max_budget_usd,
            mcp_servers=config.mcp_servers,
        )

    @classmethod
    def from_agent_template(
        cls,
        template_path: str | Path,
        *,
        mcp_servers: dict[str, Any] | None = None,
    ) -> SDKAgentRunner:
        """Create an ``SDKAgentRunner`` from an MPM agent template JSON file.

        Loads the template, extracts system prompt / instructions, model,
        allowed tools, and other configuration fields.

        Args:
            template_path: Path to the agent template JSON file.
            mcp_servers: Optional MCP server configuration to pass through.

        Returns:
            A configured ``SDKAgentRunner``.

        Raises:
            FileNotFoundError: If *template_path* does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        path = Path(template_path)
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

        # Extract system prompt / instructions
        system_prompt: str | None = data.get("narrative_fields", {}).get(
            "instructions"
        ) or data.get("system_prompt")

        # Extract model from several known locations and resolve to SDK name
        raw_model: str | None = (
            data.get("capabilities", {}).get("model")
            or data.get("configuration_fields", {}).get("model")
            or data.get("model")
        )
        model = resolve_model_to_sdk(raw_model) if raw_model else None

        # Extract allowed tools
        allowed_tools: list[str] | None = None
        raw_tools = data.get("capabilities", {}).get("tools")
        if isinstance(raw_tools, list):
            allowed_tools = raw_tools
        elif isinstance(raw_tools, str) and raw_tools != "*":
            allowed_tools = [raw_tools]

        # Extract configuration fields
        config_fields = data.get("configuration_fields", {})
        permission_mode: str | None = config_fields.get("permission_mode")
        cwd: str | None = config_fields.get("cwd")
        max_turns: int | None = config_fields.get("max_turns")
        timeout = config_fields.get("timeout")
        max_budget_usd: float | None = config_fields.get("max_budget_usd")

        # Use timeout as max_turns fallback if max_turns is not set
        if max_turns is None and isinstance(timeout, int):
            max_turns = timeout

        return cls(
            system_prompt=system_prompt,
            model=model,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            cwd=cwd,
            max_turns=max_turns,
            max_budget_usd=max_budget_usd,
            mcp_servers=mcp_servers,
        )

    # -- properties ----------------------------------------------------------

    @property
    def runtime_name(self) -> str:
        """Return the runtime identifier."""
        return "sdk"

    # -- helpers -------------------------------------------------------------

    # Reverse mapping from outputStyle IDs (settings.json) to OutputStyleType keys
    _STYLE_ID_TO_TYPE: dict[str, str] = {
        "claude_mpm": "professional",
        "claude_mpm_teacher": "teaching",
        "claude_mpm_research": "research",
    }

    def _get_output_style_content(self) -> str | None:
        """Load the configured output style content for injection into system prompt.

        Reads ``outputStyle`` from ``~/.claude/settings.json``, then loads the
        corresponding style file via
        ``OutputStyleManager.get_injectable_content()``.

        Returns:
            The style content without YAML frontmatter, or ``None`` if no style
            is configured or the style file cannot be read.
        """
        try:
            from claude_mpm.core.output_style_manager import OutputStyleManager

            settings_path = Path.home() / ".claude" / "settings.json"
            if not settings_path.exists():
                return None

            settings = json.loads(settings_path.read_text())
            style_id = settings.get("outputStyle")
            if not style_id:
                return None

            style_type = self._STYLE_ID_TO_TYPE.get(style_id)
            if style_type is None:
                logger.debug("Unknown output style '%s', skipping injection", style_id)
                return None

            manager = OutputStyleManager()
            content = manager.get_injectable_content(style=style_type)  # type: ignore[arg-type]
            if content:
                logger.debug(
                    "Injecting output style '%s' (%s) into SDK system prompt",
                    style_id,
                    style_type,
                )
            return content
        except Exception:
            logger.debug("Could not load output style, skipping", exc_info=True)
            return None

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
        if self.mcp_servers is not None:
            kwargs["mcp_servers"] = self.mcp_servers
        kwargs.update(overrides)

        # Inject output style into system prompt if configured.
        # SDK sessions don't load user settings, so outputStyle from
        # ~/.claude/settings.json must be injected manually.
        system_prompt = kwargs.get("system_prompt", "")
        style_content = self._get_output_style_content()
        if style_content:
            kwargs["system_prompt"] = (
                f"{style_content}\n\n{system_prompt}"
                if system_prompt
                else style_content
            )

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

    def _config_to_overrides(self, config: AgentConfig | None) -> dict[str, Any]:
        """Convert an ``AgentConfig`` to keyword overrides for ``_build_options``."""
        if config is None:
            return {}
        overrides: dict[str, Any] = {}
        if config.system_prompt is not None:
            overrides["system_prompt"] = config.system_prompt
        if config.model is not None:
            overrides["model"] = resolve_model_to_sdk(config.model)
        if config.allowed_tools is not None:
            overrides["allowed_tools"] = config.allowed_tools
        if config.permission_mode is not None:
            overrides["permission_mode"] = config.permission_mode
        if config.cwd is not None:
            overrides["cwd"] = config.cwd
        if config.max_turns is not None:
            overrides["max_turns"] = config.max_turns
        if config.max_budget_usd is not None:
            overrides["max_budget_usd"] = config.max_budget_usd
        if config.mcp_servers is not None:
            overrides["mcp_servers"] = config.mcp_servers
        return overrides

    @staticmethod
    def _static_to_agent_result(sdk_result: SDKAgentResult) -> AgentResult:
        """Convert an ``SDKAgentResult`` to the runtime-agnostic ``AgentResult``."""
        return AgentResult(
            text=sdk_result.text,
            session_id=sdk_result.session_id,
            tool_calls=[
                {
                    "tool_name": tc.tool_name,
                    "input": tc.input,
                    "output": tc.output,
                    "approved": tc.approved,
                }
                for tc in sdk_result.tool_calls
            ],
            cost_usd=sdk_result.cost_usd,
            num_turns=sdk_result.num_turns,
            duration_ms=sdk_result.duration_ms,
            is_error=sdk_result.is_error,
        )

    # -- public API ----------------------------------------------------------

    async def run(
        self,
        prompt: str,
        config: AgentConfig | None = None,
        **option_overrides: Any,
    ) -> AgentResult:
        """One-shot query via ``sdk_query()``.

        This is the simplest execution mode: send a prompt, collect all
        response messages, and return a structured result.

        The optional *config* parameter satisfies the ``AgentRuntime`` ABC.
        Additional ``**option_overrides`` are forwarded to ``ClaudeAgentOptions``
        for backward compatibility.
        """
        merged = {**self._config_to_overrides(config), **option_overrides}
        options = self._build_options(**merged)
        messages: list[Any] = []

        async for msg in sdk_query(prompt=prompt, options=options):
            messages.append(msg)
            logger.debug("sdk_query message: %s", type(msg).__name__)

        return self._static_to_agent_result(self._extract_result(messages))

    async def run_with_hooks(
        self,
        prompt: str,
        tool_guard: Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool]]
        | None = None,
        blocked_tools: set[str] | None = None,
        config: AgentConfig | None = None,
        **option_overrides: Any,
    ) -> AgentResult:
        """Run with a ``can_use_tool`` callback for tool interception.

        Args:
            prompt: The user prompt.
            tool_guard: An async callable ``(tool_name, tool_input) -> bool``.
                Return ``True`` to allow the tool, ``False`` to deny.
            blocked_tools: A convenience set of tool names to block outright.
            config: Optional ``AgentConfig`` (ABC compliance).
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

        merged = {**self._config_to_overrides(config), **option_overrides}
        options = self._build_options(can_use_tool=_can_use_tool, **merged)
        messages: list[Any] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for msg in client.receive_response():
                messages.append(msg)
                logger.debug("client message: %s", type(msg).__name__)

        sdk_result = self._extract_result(messages)
        # Merge denied tool records that were captured by the callback
        for denied in denied_tools:
            if denied not in sdk_result.tool_calls:
                sdk_result.tool_calls.append(denied)
        return self._static_to_agent_result(sdk_result)

    async def inject(
        self,
        prompts: list[str],
        config: AgentConfig | None = None,
        **option_overrides: Any,
    ) -> AgentResult:
        """Multi-turn conversation: send multiple prompts sequentially.

        Each prompt waits for its response before sending the next one.
        """
        merged = {**self._config_to_overrides(config), **option_overrides}
        options = self._build_options(**merged)
        all_messages: list[Any] = []

        async with ClaudeSDKClient(options=options) as client:
            for prompt in prompts:
                await client.query(prompt)
                async for msg in client.receive_response():
                    all_messages.append(msg)
                    logger.debug("inject message: %s", type(msg).__name__)

        return self._static_to_agent_result(self._extract_result(all_messages))

    # -- session resume / fork -----------------------------------------------

    async def resume(
        self,
        session_id: str,
        prompt: str,
        config: AgentConfig | None = None,
        **option_overrides: Any,
    ) -> AgentResult:
        """Resume a previous session by ID and send a new prompt.

        The conversation history from *session_id* is restored and the new
        *prompt* is appended as the next user turn.
        """
        merged = {**self._config_to_overrides(config), **option_overrides}
        options = self._build_options(resume=session_id, **merged)
        messages: list[Any] = []

        async for msg in sdk_query(prompt=prompt, options=options):
            messages.append(msg)
            logger.debug("resume message: %s", type(msg).__name__)

        return self._static_to_agent_result(self._extract_result(messages))

    async def fork(
        self,
        session_id: str,
        prompt: str,
        config: AgentConfig | None = None,
        **option_overrides: Any,
    ) -> AgentResult:
        """Fork from a previous session and send a new prompt (branches history).

        This creates a new branch of the conversation starting from
        *session_id* without modifying the original session.
        """
        merged = {**self._config_to_overrides(config), **option_overrides}
        options = self._build_options(resume=session_id, fork_session=True, **merged)
        messages: list[Any] = []

        async for msg in sdk_query(prompt=prompt, options=options):
            messages.append(msg)
            logger.debug("fork message: %s", type(msg).__name__)

        return self._static_to_agent_result(self._extract_result(messages))

    # -- streaming output ----------------------------------------------------

    async def run_streaming(
        self,
        prompt: str,
        on_text: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        on_tool_call: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]
        | None = None,
        config: AgentConfig | None = None,
        **option_overrides: Any,
    ) -> AgentResult:
        """Run with real-time callbacks for text and tool-call events.

        Args:
            prompt: The user prompt.
            on_text: Async callback invoked for each ``TextBlock`` as it
                arrives.  Receives the text content as its sole argument.
            on_tool_call: Async callback invoked for each ``ToolUseBlock``.
                Receives ``(tool_name, tool_input)`` as arguments.
            config: Optional ``AgentConfig`` for per-call overrides.
            **option_overrides: Extra options forwarded to ``ClaudeAgentOptions``.

        Returns:
            The final aggregated ``AgentResult``.
        """
        merged = {**self._config_to_overrides(config), **option_overrides}
        options = self._build_options(**merged)
        messages: list[Any] = []

        async for msg in sdk_query(prompt=prompt, options=options):
            messages.append(msg)
            logger.debug("stream message: %s", type(msg).__name__)

            # Fire callbacks for assistant content blocks as they arrive
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and on_text is not None:
                        await on_text(block.text)
                    elif isinstance(block, ToolUseBlock) and on_tool_call is not None:
                        tool_input = (
                            block.input if isinstance(block.input, dict) else {}
                        )
                        await on_tool_call(block.name, tool_input)

        return self._static_to_agent_result(self._extract_result(messages))

    # -- interrupt support ---------------------------------------------------

    def interruptible(self, **option_overrides: Any) -> InterruptibleSession:
        """Create an interruptible session context manager."""
        return InterruptibleSession(self, **option_overrides)


# ---------------------------------------------------------------------------
# InterruptibleSession
# ---------------------------------------------------------------------------


class InterruptibleSession:
    """Wraps a ``ClaudeSDKClient`` with interrupt capability.

    Usage::

        async with runner.interruptible() as session:
            result = await session.query("Do work.")
            # In another coroutine: await session.interrupt()
    """

    def __init__(self, runner: SDKAgentRunner, **option_overrides: Any) -> None:
        self._runner = runner
        self._option_overrides = option_overrides
        self._client: Any | None = None
        self._session_id: str | None = None

    async def __aenter__(self) -> InterruptibleSession:
        options = self._runner._build_options(**self._option_overrides)
        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.__aexit__(*exc)
            self._client = None

    async def query(self, prompt: str) -> AgentResult:
        """Send a prompt and collect the response."""
        if self._client is None:
            raise RuntimeError("Session is not open. Use 'async with' block.")
        await self._client.query(prompt)
        messages: list[Any] = []
        async for msg in self._client.receive_response():
            messages.append(msg)
            logger.debug("interruptible message: %s", type(msg).__name__)
        sdk_result = SDKAgentRunner._extract_result(messages)
        self._session_id = sdk_result.session_id
        return SDKAgentRunner._static_to_agent_result(sdk_result)

    async def interrupt(self) -> None:
        """Interrupt the currently running agent."""
        if self._client is not None:
            await self._client.interrupt()

    @property
    def session_id(self) -> str | None:
        """Get session ID for later resume/fork."""
        return self._session_id


# ---------------------------------------------------------------------------
# Demo helpers - illustrate usage patterns
# ---------------------------------------------------------------------------


async def demo_simple_query() -> AgentResult:
    """Demonstrate a basic one-shot query."""
    runner = SDKAgentRunner(
        system_prompt="You are a concise assistant. Reply in one sentence.",
    )
    return await runner.run("What is dependency injection in three words?")


async def demo_tool_interception() -> AgentResult:
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


async def demo_command_guard() -> AgentResult:
    """Demonstrate blocking dangerous tools by name."""
    runner = SDKAgentRunner(
        system_prompt="You are a safe assistant.",
    )
    return await runner.run_with_hooks(
        prompt="Show me the contents of /etc/passwd",
        blocked_tools={"Bash", "Read"},
    )
