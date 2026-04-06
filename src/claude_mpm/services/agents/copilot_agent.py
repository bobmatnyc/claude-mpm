"""GitHub Copilot CLI agent integration for Claude MPM.

Provides a lightweight agent backed by ``gh copilot`` for simple tasks such as
local filesystem operations, git operations, and GitHub API interactions.
Copilot CLI uses free GPT credits and is cheaper for many routine tasks.

Usage::

    from claude_mpm.services.agents.copilot_agent import (
        is_copilot_available,
        run_copilot_task,
        CopilotResult,
    )

    if is_copilot_available():
        result = await run_copilot_task(
            "List the 5 most recently modified Python files"
        )
        if result.success:
            print(result.response)

CLI contract::

    gh copilot -- -p "<prompt>" --model <model>
               [--allow-tool '<tool>'] [--allow-all-paths]

Flags are passed after ``--`` because they belong to the ``copilot`` sub-command,
not to ``gh`` itself.  Output is plain text on stdout.  There is no
``--output-format json`` flag in the current Copilot CLI.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level availability cache
# ---------------------------------------------------------------------------

_copilot_available: bool | None = None  # None = not yet checked


def is_copilot_available() -> bool:
    """Check whether ``gh copilot`` is installed and callable.

    The result is cached for the lifetime of the process to avoid repeated
    subprocess spawns.

    Returns:
        True when ``gh copilot --version`` exits with code 0, False otherwise.
    """
    global _copilot_available
    if _copilot_available is not None:
        return _copilot_available

    import subprocess

    try:
        result = subprocess.run(
            ["gh", "copilot", "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        _copilot_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        _copilot_available = False

    if _copilot_available:
        logger.debug("gh copilot is available")
    else:
        logger.debug("gh copilot is not available")

    return _copilot_available


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CopilotResult:
    """Structured result from a GitHub Copilot CLI invocation.

    Attributes:
        success: True when Copilot exited cleanly and produced a response.
        response: The plain-text response from Copilot.
        exit_code: Raw process exit code (0 = success).
        duration_ms: Wall-clock milliseconds for the full invocation.
        model: The model that was requested / used.
        raw_events: Kept for API compatibility; always an empty list because
            the current Copilot CLI does not emit structured JSONL.
    """

    success: bool
    response: str
    exit_code: int
    duration_ms: int
    model: str
    raw_events: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main execution function
# ---------------------------------------------------------------------------


async def run_copilot_task(
    prompt: str,
    *,
    model: str = "gpt-4.1",
    allowed_tools: list[str] | None = None,
    allow_all_paths: bool = True,
    timeout: int = 60,
    working_dir: str | None = None,
) -> CopilotResult:
    """Execute a task via GitHub Copilot CLI.

    Builds the ``gh copilot -- -p <prompt>`` command, runs it as an async
    subprocess, and returns a structured :class:`CopilotResult`.

    The default model is ``gpt-4.1`` which draws from the free GPT credits
    included with GitHub Copilot subscriptions.

    Args:
        prompt: The user prompt to send to Copilot.
        model: Copilot model to use.  Defaults to ``"gpt-4.1"`` (free GPT
            credits).  Other examples: ``"gpt-4o"``, ``"claude-sonnet-4"``.
        allowed_tools: Explicit list of tool names to allow (e.g.
            ``["shell(git)"]``).  When omitted, no ``--allow-tool`` flags are
            added so Copilot uses its defaults.
        allow_all_paths: When True (default) the ``--allow-all-paths`` flag is
            added, permitting Copilot to read files outside the workspace root.
        timeout: Maximum seconds to wait for the subprocess to finish.
        working_dir: Optional working directory for the subprocess.

    Returns:
        A :class:`CopilotResult` describing the outcome.  On failures the
        ``success`` field is False and ``response`` contains an error summary.
    """
    if not is_copilot_available():
        logger.warning("gh copilot is not available; returning error result")
        return CopilotResult(
            success=False,
            response="gh copilot is not installed or not authenticated.",
            exit_code=-1,
            duration_ms=0,
            model=model,
        )

    # Build command.  Copilot flags go after `--` so that `gh` does not
    # try to interpret them as its own flags.
    cmd: list[str] = [
        "gh",
        "copilot",
        "--",
        "-p",
        prompt,
        "--model",
        model,
    ]

    if allow_all_paths:
        cmd.append("--allow-all-paths")

    if allowed_tools:
        for tool in allowed_tools:
            cmd += ["--allow-tool", tool]

    env = os.environ.copy()

    logger.debug("Running: %s", " ".join(cmd))
    start_ms = int(time.monotonic() * 1000)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            elapsed = int(time.monotonic() * 1000) - start_ms
            logger.warning("gh copilot timed out after %d ms", elapsed)
            return CopilotResult(
                success=False,
                response=f"Task timed out after {timeout} seconds.",
                exit_code=-1,
                duration_ms=elapsed,
                model=model,
            )

    except OSError as exc:
        elapsed = int(time.monotonic() * 1000) - start_ms
        logger.error("Failed to launch gh copilot: %s", exc)
        return CopilotResult(
            success=False,
            response=f"Failed to launch gh copilot: {exc}",
            exit_code=-1,
            duration_ms=elapsed,
            model=model,
        )

    elapsed = int(time.monotonic() * 1000) - start_ms
    exit_code = proc.returncode if proc.returncode is not None else -1

    stdout_text = stdout_bytes.decode("utf-8", errors="replace")
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")

    if stderr_text:
        logger.debug("gh copilot stderr: %s", stderr_text.strip())

    response_text = stdout_text.strip()

    # Determine success: exit 0 AND we got some response text
    success = exit_code == 0 and bool(response_text)

    if not response_text and exit_code == 0:
        response_text = "(Copilot returned no text response)"
        success = False

    return CopilotResult(
        success=success,
        response=response_text,
        exit_code=exit_code,
        duration_ms=elapsed,
        model=model,
    )
