"""Unified external agent routing for Claude MPM.

Provides a single :func:`run_external_task` entry-point that automatically
selects the cheapest available external agent for a given task.  The routing
priority for ``auto`` mode is:

1. **Cursor** (free tier auto-select model, no credits consumed)
2. **GitHub Copilot** (free GPT credits via ``gh copilot``)
3. ``None`` (no external agent available — caller must fall back)

Usage::

    from claude_mpm.services.agents.external_agents import (
        run_external_task,
        get_available_external_agents,
        ExternalAgentResult,
    )

    # Auto-select cheapest available agent
    result = await run_external_task("Summarise the recent git log")
    if result.success:
        print(result.response)
    else:
        print(f"No agent available or task failed: {result.error}")

    # Check what is available before dispatching
    available = get_available_external_agents()
    print("Available:", available)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from claude_mpm.services.agents.copilot_agent import (
    is_copilot_available,
    run_copilot_task,
)
from claude_mpm.services.agents.cursor_agent import (
    is_cursor_available,
    run_cursor_task,
)

if TYPE_CHECKING:
    from claude_mpm.services.agents.copilot_agent import CopilotResult
    from claude_mpm.services.agents.cursor_agent import CursorResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unified result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExternalAgentResult:
    """Unified result from any external agent invocation.

    Attributes:
        success: True when the agent ran and produced a usable response.
        response: The text response from the agent.
        agent: Which agent was used (``"cursor"``, ``"copilot"``, or ``""``
            when no agent was available).
        exit_code: Raw process exit code (0 = success, -1 = not run).
        duration_ms: Wall-clock milliseconds for the invocation.
        model: Model used by the agent (may be empty for auto-select).
        error: Human-readable error description when ``success`` is False.
        raw_events: Low-level event objects from the underlying agent (useful
            for debugging structured output agents such as Cursor).
    """

    success: bool
    response: str
    agent: str
    exit_code: int
    duration_ms: int
    model: str
    error: str = ""
    raw_events: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def _from_copilot(cls, result: CopilotResult) -> ExternalAgentResult:
        return cls(
            success=result.success,
            response=result.response,
            agent="copilot",
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            model=result.model,
            error="" if result.success else result.response,
            raw_events=result.raw_events,
        )

    @classmethod
    def _from_cursor(cls, result: CursorResult) -> ExternalAgentResult:
        return cls(
            success=result.success,
            response=result.response,
            agent="cursor",
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            model=result.model,
            error="" if result.success else result.response,
            raw_events=result.raw_events,
        )

    @classmethod
    def _no_agent(
        cls, reason: str = "No external agent is available."
    ) -> ExternalAgentResult:
        return cls(
            success=False,
            response="",
            agent="",
            exit_code=-1,
            duration_ms=0,
            model="",
            error=reason,
        )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_available_external_agents() -> list[str]:
    """Return a list of external agent names that are currently available.

    Agents are ordered from highest to lowest priority (cheapest first).

    Returns:
        A list of agent name strings, e.g. ``["cursor", "copilot"]``.  Returns
        an empty list when no external agents are installed/authenticated.
    """
    available: list[str] = []
    if is_cursor_available():
        available.append("cursor")
    if is_copilot_available():
        available.append("copilot")
    return available


async def run_external_task(
    prompt: str,
    *,
    preferred_agent: str = "auto",
    working_dir: str | None = None,
    timeout: int = 120,
) -> ExternalAgentResult:
    """Route a task to the cheapest available external agent.

    Agent selection by *preferred_agent*:

    * ``"auto"`` — try Cursor first (free tier), then Copilot (free GPT), then
      return a failure result if neither is available.
    * ``"cursor"`` — use Cursor agent only; fail if unavailable.
    * ``"copilot"`` — use GitHub Copilot only; fail if unavailable.

    Args:
        prompt: Natural-language task description.
        preferred_agent: Which agent to use.  Defaults to ``"auto"``.
        working_dir: Optional working directory passed to the underlying agent.
        timeout: Maximum seconds to allow for the task.

    Returns:
        An :class:`ExternalAgentResult` with the outcome.  ``success`` is
        False when no agent is available or the agent reports failure.
    """
    agent_choice = preferred_agent.lower().strip()

    if agent_choice == "cursor":
        return await _run_cursor(prompt, working_dir=working_dir, timeout=timeout)

    if agent_choice == "copilot":
        return await _run_copilot(prompt, working_dir=working_dir, timeout=timeout)

    if agent_choice == "auto":
        # Priority: cursor (free) → copilot (free GPT) → none
        if is_cursor_available():
            logger.debug("auto: selecting cursor agent")
            result = await _run_cursor(prompt, working_dir=working_dir, timeout=timeout)
            if result.success:
                return result
            logger.warning(
                "cursor agent failed (exit=%d); falling back to copilot",
                result.exit_code,
            )

        if is_copilot_available():
            logger.debug("auto: selecting copilot agent")
            return await _run_copilot(prompt, working_dir=working_dir, timeout=timeout)

        return ExternalAgentResult._no_agent(
            "No external agents are available.  Install cursor-agent or gh copilot."
        )

    return ExternalAgentResult._no_agent(
        f"Unknown preferred_agent value: {preferred_agent!r}.  "
        "Use 'auto', 'cursor', or 'copilot'."
    )


# ---------------------------------------------------------------------------
# Internal agent wrappers
# ---------------------------------------------------------------------------


async def _run_cursor(
    prompt: str,
    *,
    working_dir: str | None,
    timeout: int,
) -> ExternalAgentResult:
    """Run via Cursor agent and wrap the result."""
    if not is_cursor_available():
        return ExternalAgentResult._no_agent(
            "cursor-agent is not installed or not authenticated."
        )
    result = await run_cursor_task(
        prompt,
        workspace=working_dir,
        timeout=timeout,
    )
    return ExternalAgentResult._from_cursor(result)


async def _run_copilot(
    prompt: str,
    *,
    working_dir: str | None,
    timeout: int,
) -> ExternalAgentResult:
    """Run via GitHub Copilot CLI and wrap the result."""
    if not is_copilot_available():
        return ExternalAgentResult._no_agent(
            "gh copilot is not installed or not authenticated."
        )
    result = await run_copilot_task(
        prompt,
        working_dir=working_dir,
        timeout=timeout,
    )
    return ExternalAgentResult._from_copilot(result)
