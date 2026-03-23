"""Bridge between MPM's existing agent execution and the new runtime system.

Provides a unified entry point that routes to SDK or CLI based on config.
This module is intentionally lightweight -- it delegates all heavy lifting
to :mod:`~claude_mpm.services.agents.agent_runtime` and
:mod:`~claude_mpm.services.agents.runtime_config`.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def execute_agent_prompt(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    allowed_tools: list[str] | None = None,
    cwd: str | None = None,
    session_id: str | None = None,
    max_turns: int | None = None,
    mcp_servers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an agent prompt using the configured runtime.

    Returns a dict with keys: ``text``, ``session_id``, ``cost_usd``,
    ``num_turns``, ``duration_ms``, ``is_error``, ``tool_calls``, ``runtime``.
    """
    from claude_mpm.services.agents.agent_runtime import AgentConfig
    from claude_mpm.services.agents.runtime_config import get_runtime, get_runtime_type

    config = AgentConfig(
        system_prompt=system_prompt,
        model=model,
        allowed_tools=allowed_tools,
        cwd=cwd,
        max_turns=max_turns,
        mcp_servers=mcp_servers,
    )

    runtime = get_runtime(config)
    runtime_type = get_runtime_type()
    logger.info("Executing agent prompt via %s runtime", runtime_type)

    if session_id:
        result = await runtime.resume(session_id, prompt, config)
    else:
        result = await runtime.run(prompt, config)

    return {
        "text": result.text,
        "session_id": result.session_id,
        "cost_usd": result.cost_usd,
        "num_turns": result.num_turns,
        "duration_ms": result.duration_ms,
        "is_error": result.is_error,
        "tool_calls": result.tool_calls,
        "runtime": runtime_type,
    }


def print_runtime_status() -> None:
    """Print current runtime selection and SDK availability."""
    from claude_mpm.services.agents.runtime_config import get_runtime_type

    runtime_type = get_runtime_type()
    print(f"Runtime: {runtime_type}")

    try:
        import claude_agent_sdk  # noqa: F401

        print("SDK available: yes")
    except ImportError:
        print("SDK available: no")

    import os

    env_val = os.environ.get("CLAUDE_MPM_RUNTIME", "")
    if env_val:
        print(f"CLAUDE_MPM_RUNTIME env: {env_val}")
    else:
        print("CLAUDE_MPM_RUNTIME env: (not set, using auto-detect)")


if __name__ == "__main__":
    import asyncio
    import sys

    async def main() -> None:
        print_runtime_status()

        if "--run" in sys.argv:
            print("\nExecuting test prompt...")
            result = await execute_agent_prompt(
                prompt="What is 2+2? Reply with just the number.",
                max_turns=2,
            )
            print(f"Result: {result['text']}")
            print(f"Cost: ${result.get('cost_usd', 'N/A')}")
            print(f"Runtime used: {result['runtime']}")
        else:
            print("\nUse --run to execute a test prompt")

    asyncio.run(main())
