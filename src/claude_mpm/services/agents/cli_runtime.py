"""CLI subprocess-based AgentRuntime adapter.

Wraps the existing ClaudeAdapter subprocess execution to implement
the AgentRuntime ABC, providing a drop-in alternative to SDKAgentRunner.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from claude_mpm.services.agents.agent_runtime import (
    AgentResult,
    AgentRuntime,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from claude_mpm.services.agents.agent_runtime import AgentConfig

logger = logging.getLogger(__name__)


class CLIAgentRunner(AgentRuntime):
    """Execute agent prompts via the Claude CLI subprocess.

    Wraps :class:`~claude_mpm.adapters.cli_adapters.ClaudeAdapter` to
    implement the :class:`AgentRuntime` ABC, allowing the factory and
    runtime-config layer to treat CLI and SDK backends interchangeably.
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        model: str | None = None,
        cwd: str | None = None,
        max_turns: int | None = None,
    ) -> None:
        self._system_prompt = system_prompt
        self._model = model
        self._cwd = cwd
        self._max_turns = max_turns

    # -- class constructors ---------------------------------------------------

    @classmethod
    def from_config(cls, config: AgentConfig) -> CLIAgentRunner:
        """Create a ``CLIAgentRunner`` from a runtime-agnostic ``AgentConfig``."""
        return cls(
            system_prompt=config.system_prompt,
            model=config.model,
            cwd=config.cwd,
            max_turns=config.max_turns,
        )

    # -- properties -----------------------------------------------------------

    @property
    def runtime_name(self) -> str:
        """Return the runtime identifier."""
        return "cli"

    # -- helpers --------------------------------------------------------------

    def _build_cli_args(
        self,
        prompt: str,
        *,
        resume_session: str | None = None,
        fork: bool = False,
        output_json: bool = True,
    ) -> list[str]:
        """Build the ``claude`` CLI argument list."""
        args: list[str] = ["claude", "-p"]

        if output_json:
            args.extend(["--output-format", "json"])

        if self._model:
            args.extend(["--model", self._model])

        if self._max_turns is not None:
            args.extend(["--max-turns", str(self._max_turns)])

        if resume_session:
            args.extend(["--resume", resume_session])
            if fork:
                args.append("--fork-session")

        if self._system_prompt:
            args.extend(["--system-prompt", self._system_prompt])

        args.append(prompt)
        return args

    async def _invoke(
        self,
        prompt: str,
        *,
        resume_session: str | None = None,
        fork: bool = False,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Run the CLI subprocess and convert output to ``AgentResult``."""
        # Apply per-call config overrides
        original = (self._system_prompt, self._model, self._cwd, self._max_turns)
        if config is not None:
            if config.system_prompt is not None:
                self._system_prompt = config.system_prompt
            if config.model is not None:
                self._model = config.model
            if config.cwd is not None:
                self._cwd = config.cwd
            if config.max_turns is not None:
                self._max_turns = config.max_turns

        args = self._build_cli_args(
            prompt,
            resume_session=resume_session,
            fork=fork,
        )

        start = time.monotonic()

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._cwd,
            )
            stdout_bytes, stderr_bytes = await process.communicate()
        finally:
            # Restore originals
            self._system_prompt, self._model, self._cwd, self._max_turns = original

        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = stdout_bytes.decode() if stdout_bytes else ""
        stderr = stderr_bytes.decode() if stderr_bytes else ""

        if process.returncode != 0:
            logger.error("CLI process failed (rc=%s): %s", process.returncode, stderr)
            return AgentResult(
                text=stderr or f"CLI exited with code {process.returncode}",
                is_error=True,
                duration_ms=duration_ms,
            )

        return self._parse_output(stdout, duration_ms=duration_ms)

    @staticmethod
    def _parse_output(raw: str, *, duration_ms: int | None = None) -> AgentResult:
        """Parse CLI JSON output into an ``AgentResult``."""
        try:
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # Fall back to raw text output
            return AgentResult(
                text=raw.strip(),
                duration_ms=duration_ms,
            )

        # The JSON output format from ``claude -p --output-format json``
        text = data.get("result", data.get("text", raw.strip()))
        session_id = data.get("session_id")
        cost_usd = data.get("cost_usd") or data.get("total_cost_usd")
        num_turns = data.get("num_turns")
        is_error = bool(data.get("is_error", False))

        return AgentResult(
            text=str(text),
            session_id=session_id,
            cost_usd=cost_usd,
            num_turns=num_turns,
            duration_ms=duration_ms,
            is_error=is_error,
        )

    # -- AgentRuntime ABC implementation --------------------------------------

    async def run(
        self,
        prompt: str,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Execute a one-shot prompt via the CLI."""
        return await self._invoke(prompt, config=config)

    async def run_with_hooks(
        self,
        prompt: str,
        tool_guard: Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool]]
        | None = None,
        blocked_tools: set[str] | None = None,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Not supported by CLI runtime.

        The CLI subprocess does not expose tool interception hooks.
        Use the SDK runtime (``SDKAgentRunner``) for tool-level control.
        """
        raise NotImplementedError(
            "Tool interception is not supported by the CLI runtime. "
            "Use the SDK runtime ('sdk') for run_with_hooks() support."
        )

    async def resume(
        self,
        session_id: str,
        prompt: str,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Resume a previous session via ``--resume``."""
        return await self._invoke(prompt, resume_session=session_id, config=config)

    async def fork(
        self,
        session_id: str,
        prompt: str,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Fork from a previous session via ``--resume`` + ``--fork-session``."""
        return await self._invoke(
            prompt, resume_session=session_id, fork=True, config=config
        )
