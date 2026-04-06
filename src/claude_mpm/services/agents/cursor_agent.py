"""Cursor agent CLI integration for Claude MPM.

Provides a lightweight agent backed by ``cursor-agent`` for simple tasks such
as local filesystem operations, code understanding, and general programming
tasks.  Cursor agent is an alternative to Copilot that uses Cursor's AI
infrastructure with a free-tier auto-select model.

Usage::

    from claude_mpm.services.agents.cursor_agent import (
        is_cursor_available,
        run_cursor_task,
        CursorResult,
    )

    if is_cursor_available():
        result = await run_cursor_task(
            "List the 5 most recently modified Python files"
        )
        if result.success:
            print(result.response)

CLI contract::

    cursor-agent --print --output-format stream-json --trust
                 [--workspace <path>] [--model <model>]
                 "<prompt>"

Output is a stream of JSONL objects.  Assistant content lives in events where
the type indicates text content from the assistant.  The ``--stream-partial-output``
flag can be added for incremental output (not used by default).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level availability cache
# ---------------------------------------------------------------------------

_cursor_available: bool | None = None  # None = not yet checked


def is_cursor_available() -> bool:
    """Check whether ``cursor-agent`` is installed and authenticated.

    Runs ``cursor-agent --version`` to check installation, then
    ``cursor-agent status`` to verify authentication.  The result is cached
    for the lifetime of the process to avoid repeated subprocess spawns.

    Returns:
        True when cursor-agent is installed and appears authenticated,
        False otherwise.
    """
    global _cursor_available
    if _cursor_available is not None:
        return _cursor_available

    import subprocess

    # Step 1: Check installation
    try:
        result = subprocess.run(
            ["cursor-agent", "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            _cursor_available = False
            logger.debug("cursor-agent --version returned non-zero exit code")
            return _cursor_available
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        _cursor_available = False
        logger.debug("cursor-agent not found on PATH")
        return _cursor_available

    # Step 2: Check authentication
    try:
        status_result = subprocess.run(
            ["cursor-agent", "status"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        stdout = status_result.stdout.decode("utf-8", errors="replace").lower()
        stderr = status_result.stderr.decode("utf-8", errors="replace").lower()
        combined = stdout + stderr

        if "not logged in" in combined or "not authenticated" in combined:
            _cursor_available = False
            logger.debug("cursor-agent is not authenticated")
            return _cursor_available
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        # If status command fails entirely, still try (cursor-agent may not have status)
        logger.debug("cursor-agent status check failed; assuming available")

    _cursor_available = True
    logger.debug("cursor-agent is available")
    return _cursor_available


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CursorResult:
    """Structured result from a Cursor agent CLI invocation.

    Attributes:
        success: True when Cursor agent exited cleanly and produced a response.
        response: The final assistant message text (concatenated from all parts).
        exit_code: Raw process exit code (0 = success).
        duration_ms: Wall-clock milliseconds for the full invocation.
        model: The model that was requested / used (empty string for auto-select).
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


def _parse_cursor_stream_json(output: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse stream-json JSONL output from ``cursor-agent``.

    Each non-empty line is expected to be a JSON object.  This function
    collects text content from assistant message events and returns:

    * Concatenated assistant response text.
    * All parsed event objects for downstream inspection.

    The exact event schema depends on the cursor-agent version.  This parser
    handles common patterns:

    * Objects with a ``type`` field of ``"text"`` or ``"assistant"`` containing
      a ``text`` or ``content`` key.
    * Objects with a top-level ``text`` or ``content`` key.
    * Objects with a ``delta`` sub-object containing ``text`` or ``content``.

    Args:
        output: Raw stdout string from the subprocess.

    Returns:
        A tuple of ``(response_text, all_events)`` where ``response_text`` is
        the concatenated assistant text and ``all_events`` contains all parsed
        JSON objects.
    """
    response_parts: list[str] = []
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

        # Extract text from common event shapes
        text: str | None = None

        if event_type in ("text", "assistant", "assistant.message"):
            # Type-keyed events: look in common text fields
            text = (
                event.get("text")
                or event.get("content")
                or event.get("data", {}).get("content")
                or event.get("data", {}).get("text")
            )
        elif event_type == "delta":
            delta = event.get("delta", {})
            text = delta.get("text") or delta.get("content")
        elif not event_type:
            # No type field — try top-level text/content
            text = event.get("text") or event.get("content")

        if isinstance(text, str) and text:
            response_parts.append(text)

    response_text = "".join(response_parts)
    return response_text, all_events


# ---------------------------------------------------------------------------
# Main execution function
# ---------------------------------------------------------------------------


async def run_cursor_task(
    prompt: str,
    *,
    model: str | None = None,
    workspace: str | None = None,
    timeout: int = 120,
) -> CursorResult:
    """Execute a task via Cursor agent CLI.

    Builds the ``cursor-agent`` command with non-interactive flags, runs it as
    an async subprocess, parses the stream-json output, and returns a
    structured :class:`CursorResult`.

    Args:
        prompt: The user prompt to send to Cursor agent.
        model: Optional model override (e.g. ``"claude-3.5-sonnet"``).
            Omit (``None``) to let Cursor auto-select — this uses the free
            tier and avoids credit consumption.
        workspace: Working directory for the agent (passed as
            ``--workspace <path>``).  Defaults to the current working
            directory if omitted.
        timeout: Maximum seconds to wait for the subprocess to finish.

    Returns:
        A :class:`CursorResult` describing the outcome.  On failures the
        ``success`` field is False and ``response`` contains an error summary.
    """
    if not is_cursor_available():
        logger.warning("cursor-agent is not available; returning error result")
        return CursorResult(
            success=False,
            response="cursor-agent is not installed or not authenticated.",
            exit_code=-1,
            duration_ms=0,
            model=model or "",
        )

    # Build command
    cmd: list[str] = [
        "cursor-agent",
        "--print",
        "--output-format",
        "stream-json",
        "--trust",
    ]

    if workspace:
        cmd += ["--workspace", workspace]

    if model:
        cmd += ["--model", model]

    # Prompt is the positional argument — must be last
    cmd.append(prompt)

    logger.debug("Running: %s", " ".join(cmd))
    start_ms = int(time.monotonic() * 1000)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace,
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
            logger.warning("cursor-agent timed out after %d ms", elapsed)
            return CursorResult(
                success=False,
                response=f"Task timed out after {timeout} seconds.",
                exit_code=-1,
                duration_ms=elapsed,
                model=model or "",
            )

    except OSError as exc:
        elapsed = int(time.monotonic() * 1000) - start_ms
        logger.error("Failed to launch cursor-agent: %s", exc)
        return CursorResult(
            success=False,
            response=f"Failed to launch cursor-agent: {exc}",
            exit_code=-1,
            duration_ms=elapsed,
            model=model or "",
        )

    elapsed = int(time.monotonic() * 1000) - start_ms
    exit_code = proc.returncode if proc.returncode is not None else -1

    stdout_text = stdout_bytes.decode("utf-8", errors="replace")
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")

    if stderr_text:
        logger.debug("cursor-agent stderr: %s", stderr_text.strip())

    response_text, raw_events = _parse_cursor_stream_json(stdout_text)

    # Fall back to plain text if no JSON events were parsed (some cursor-agent
    # versions may not emit structured JSON)
    if not response_text and stdout_text.strip():
        response_text = stdout_text.strip()

    # Determine success: exit 0 AND we got some response text
    success = exit_code == 0 and bool(response_text.strip())

    if not response_text and exit_code == 0:
        # Cursor agent exited cleanly but produced no text
        response_text = "(cursor-agent returned no text response)"
        success = False

    # Try to extract model name from events if not provided
    effective_model = model or ""
    if not effective_model:
        for event in raw_events:
            candidate = event.get("model") or event.get("data", {}).get("model")
            if isinstance(candidate, str) and candidate:
                effective_model = candidate
                break

    return CursorResult(
        success=success,
        response=response_text,
        exit_code=exit_code,
        duration_ms=elapsed,
        model=effective_model,
        raw_events=raw_events,
    )
