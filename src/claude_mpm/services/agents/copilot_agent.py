"""GitHub Copilot CLI agent integration for Claude MPM.

Provides a lightweight agent backed by ``gh copilot`` for simple tasks such as
local filesystem operations, git operations, and GitHub API interactions.
Copilot CLI is cheaper and faster than a full Claude invocation for many
routine tasks.

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

    gh copilot -p "<prompt>" --model <model> --output-format json -s --no-ask-user
              [--allow-tool <tool> ...] [--deny-tool <tool> ...] | [--allow-all]

Each line of stdout is a JSON object with at minimum ``type`` and ``data``
fields.  The final response text lives in ``assistant.message`` events where
``data.content`` is non-empty, and a ``result`` event captures exit-code and
timing metadata.
"""

from __future__ import annotations

import asyncio
import json
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
        response: The final assistant message text (concatenated if multiple).
        exit_code: Raw process exit code (0 = success).
        duration_ms: Wall-clock milliseconds for the full invocation.
        model: The model that was requested / used.
        raw_events: All parsed JSONL event objects for debugging.
    """

    success: bool
    response: str
    exit_code: int
    duration_ms: int
    model: str
    raw_events: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JSONL parser
# ---------------------------------------------------------------------------


def _parse_copilot_jsonl(output: str) -> tuple[str, dict[str, Any]]:
    """Parse JSONL output from ``gh copilot --output-format json``.

    Each non-empty line is expected to be a JSON object with at least a
    ``type`` field and a ``data`` field.  This function collects:

    * ``assistant.message`` events whose ``data.content`` is non-empty to
      build the full response text.
    * The ``result`` event for exit-code / timing metadata.

    Args:
        output: Raw stdout string from the subprocess.

    Returns:
        A tuple of ``(response_text, result_event)`` where ``result_event``
        is an empty dict when no ``result`` event was found.
    """
    response_parts: list[str] = []
    result_event: dict[str, Any] = {}
    all_events: list[dict[str, Any]] = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Skipping non-JSON line: %r", line)
            continue

        all_events.append(event)
        event_type = event.get("type", "")

        if event_type == "assistant.message":
            data = event.get("data", {})
            content = data.get("content", "")
            if content:
                response_parts.append(content)

        elif event_type == "result":
            result_event = event

    response_text = "".join(response_parts)
    return response_text, result_event


# ---------------------------------------------------------------------------
# Main execution function
# ---------------------------------------------------------------------------


async def run_copilot_task(
    prompt: str,
    *,
    model: str = "claude-haiku-4.5",
    allowed_tools: list[str] | None = None,
    denied_tools: list[str] | None = None,
    timeout: int = 60,
    working_dir: str | None = None,
) -> CopilotResult:
    """Execute a task via GitHub Copilot CLI.

    Builds the ``gh copilot`` command, runs it as an async subprocess, parses
    the JSONL output, and returns a structured :class:`CopilotResult`.

    When neither *allowed_tools* nor *denied_tools* are specified the
    ``--allow-all`` flag is added so that Copilot can use shell commands,
    GitHub APIs, and any enabled MCP servers.

    Args:
        prompt: The user prompt to send to Copilot.
        model: Copilot model to use (e.g. ``"claude-haiku-4.5"``).
            GPT models have a 128-tool cap that conflicts with ``--allow-all``
            (which exposes ~228 tools); Claude models do not have this limit.
        allowed_tools: Explicit list of tool names to allow (passed as
            ``--allow-tool <name>`` once per entry).
        denied_tools: Explicit list of tool names to deny (passed as
            ``--deny-tool <name>`` once per entry).
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

    # Build command
    cmd: list[str] = [
        "gh",
        "copilot",
        "-p",
        prompt,
        "--model",
        model,
        "--output-format",
        "json",
        "-s",  # suppress spinner
        "--no-ask-user",
    ]

    # Tool control flags
    if allowed_tools:
        for tool in allowed_tools:
            cmd += ["--allow-tool", tool]
    elif not denied_tools:
        # No restrictions specified — allow everything
        cmd.append("--allow-all")

    if denied_tools:
        for tool in denied_tools:
            cmd += ["--deny-tool", tool]

    # Environment: set COPILOT_ALLOW_ALL as a fallback hint
    env = os.environ.copy()
    env["COPILOT_ALLOW_ALL"] = "1"

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

    response_text, result_event = _parse_copilot_jsonl(stdout_text)

    # Derive duration from result event when available
    event_duration = result_event.get("data", {}).get("duration_ms")
    duration_ms = int(event_duration) if event_duration is not None else elapsed

    # Collect all raw events for callers that want to inspect them
    raw_events: list[dict[str, Any]] = []
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw_events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    # Determine success: exit 0 AND we got some response text
    success = exit_code == 0 and bool(response_text.strip())

    if not response_text and exit_code == 0:
        # Copilot exited cleanly but produced no text — treat as partial success
        response_text = "(Copilot returned no text response)"
        success = False

    return CopilotResult(
        success=success,
        response=response_text,
        exit_code=exit_code,
        duration_ms=duration_ms,
        model=model,
        raw_events=raw_events,
    )
