"""Live stdio MCP probe for Available Tool Services detection (GitHub #814).

Why: The existing trusty_status.py detects services via filesystem signals
(.mcp.json presence, http_addr file) — this is latency-free but cannot confirm
whether a service is actually wired correctly and exposing tools. This module
adds a live probe that spawns each service as a stdio MCP server, performs an
initialize + tools/list handshake, and classifies the service as ON / DEGRADED
/ ABSENT based on the actual tool-list response.

What: Exposes ProbeResult, SERVICE_PROBE_COMMANDS, and three functions —
_probe_single_service (async, internal), probe_all_services (async, public),
and probe_all_services_sync (sync wrapper). All four probes run concurrently
via asyncio.gather so total added latency is bounded by one probe timeout
(~1.5s) rather than 4x timeout. Always reaps child processes in finally blocks.
Service classification uses a non-empty tools list as the ON signal; sentinel
tool checking is not implemented (any tools returned → ON).

Test: tests/services/test_tool_service_probe.py — covers ABSENT, ON (with and
without any tools), DEGRADED (no tools / timeout / crash), concurrency, process
reaping, and fail-safe behaviour.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)


def _safe_hint(text: str, max_len: int = 120) -> str:
    """Truncate hint to max_len chars and strip newlines for safe PM prompt injection."""
    truncated = text.replace("\n", " ").replace("\r", " ")
    if len(truncated) > max_len:
        truncated = truncated[: max_len - 3] + "..."
    return truncated


# Service name -> stdio spawn command. These are the EXACT argv lists the
# trusty-* binaries expect when started in stdio MCP server mode.
SERVICE_PROBE_COMMANDS: dict[str, list[str]] = {
    "trusty-memory": ["trusty-memory", "serve", "--stdio"],
    "trusty-search": ["trusty-search", "serve"],
    "trusty-analyze": ["trusty-analyze", "mcp"],
    "trusty-review": ["trusty-review", "serve", "--stdio"],
}

# JSON-RPC initialize request (MCP protocol 2024-11-05).
_INIT_REQUEST: dict = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "claude-mpm-probe", "version": "1.0.0"},
    },
    "id": 1,
}

# JSON-RPC notifications/initialized notification (no response expected).
_INITIALIZED_NOTIFICATION: dict = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {},
}

# JSON-RPC tools/list request.
_TOOLS_LIST_REQUEST: dict = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2,
}


@dataclass(frozen=True)
class ProbeResult:
    """Result of a single service probe.

    Why: Encapsulates the three-state outcome (ON / DEGRADED / ABSENT) together
    with an optional actionable hint so callers can render the state and the
    remediation advice from one object.

    What: state is one of "on" | "degraded" | "absent". hint is a non-empty
    actionable string when state != "on", empty string otherwise.

    Test: Constructed directly in test assertions; frozen so tests cannot mutate.
    """

    state: Literal["on", "degraded", "absent"]
    hint: str = field(default="")


async def _probe_single_service(
    service: str,
    command: list[str],
    timeout: float,
) -> ProbeResult:
    """Probe one service via its stdio MCP server interface.

    Why: Provides ground-truth service availability by actually performing the
    MCP initialize + tools/list handshake rather than relying on config files.

    What: Checks binary presence via shutil.which, spawns the subprocess with
    asyncio, performs the MCP handshake, reads the tools list, classifies the
    result, and ALWAYS kills + waits the subprocess in a finally block. Never
    raises out of this function — all exceptions become DEGRADED results.

    Test: tests/services/test_tool_service_probe.py — covers each outcome branch
    and verifies the process is always reaped.
    """
    process: asyncio.subprocess.Process | None = None
    try:
        # Fast path: binary not on PATH → ABSENT immediately (no subprocess).
        if not shutil.which(command[0]):
            return ProbeResult(state="absent", hint="")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        if process.stdin is None or process.stdout is None:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(f"{service} subprocess missing stdin/stdout pipes"),
            )

        # --- Step 1: send initialize request ---
        init_line = (json.dumps(_INIT_REQUEST) + "\n").encode()
        process.stdin.write(init_line)
        await process.stdin.drain()

        # Read initialize response with timeout.
        try:
            raw_init = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout,
            )
        except TimeoutError:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} initialize handshake timed out after {timeout}s — check daemon / binary"
                ),
            )

        if not raw_init:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} closed stdout without responding to initialize"
                ),
            )

        try:
            init_resp = json.loads(raw_init.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError as exc:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} returned non-JSON initialize response: {exc}"
                ),
            )

        if not isinstance(init_resp, dict) or "result" not in init_resp:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(f"{service} initialize response missing 'result' key"),
            )

        # --- Step 2: send notifications/initialized (no response expected) ---
        notif_line = (json.dumps(_INITIALIZED_NOTIFICATION) + "\n").encode()
        process.stdin.write(notif_line)
        await process.stdin.drain()

        # --- Step 3: send tools/list request ---
        tools_line = (json.dumps(_TOOLS_LIST_REQUEST) + "\n").encode()
        process.stdin.write(tools_line)
        await process.stdin.drain()

        # Read tools/list response with timeout.
        try:
            raw_tools = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout,
            )
        except TimeoutError:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} tools/list timed out — service may be reachable but not fully wired"
                ),
            )

        if not raw_tools:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} closed stdout during tools/list — check `serve --stdio` wiring"
                ),
            )

        try:
            tools_resp = json.loads(raw_tools.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError as exc:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} returned non-JSON tools/list response: {exc}"
                ),
            )

        if not isinstance(tools_resp, dict) or "result" not in tools_resp:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(f"{service} tools/list response missing 'result' key"),
            )

        tools: list[dict] = tools_resp["result"].get("tools", [])
        tool_names: set[str] = {t.get("name", "") for t in tools if isinstance(t, dict)}

        if not tool_names:
            return ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{service} reachable but no tools exposed — "
                    f"check `serve --stdio` wiring / restart daemon"
                ),
            )

        # Sentinel present → definitively ON.
        # Fallback: any tools returned → ON (sentinel may not be in all builds;
        # documented in module docstring — this is intentional loose-check).
        return ProbeResult(state="on", hint="")

    except Exception as exc:  # pragma: no cover - unexpected catch-all
        logger.debug("_probe_single_service(%s): unexpected error: %s", service, exc)
        return ProbeResult(
            state="degraded",
            hint=_safe_hint(f"{service} probe failed unexpectedly: {exc}"),
        )
    finally:
        # Always reap the subprocess — no orphans, even on timeout or crash.
        if process is not None:
            try:
                process.kill()
            except (OSError, ProcessLookupError):
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except (TimeoutError, OSError, ProcessLookupError):
                pass


async def probe_all_services(
    timeout_per_probe: float = 1.5,
) -> dict[str, ProbeResult]:
    """Probe all four trusty services concurrently.

    Why: Running probes concurrently via asyncio.gather bounds total latency to
    one probe timeout rather than 4x timeout, keeping startup overhead minimal.

    What: Spawns one _probe_single_service coroutine per entry in
    SERVICE_PROBE_COMMANDS, collects results with gather(return_exceptions=True)
    so a single probe failure cannot abort the others, and maps exceptions to
    DEGRADED results before returning the complete dict.

    Test: tests/services/test_tool_service_probe.py::TestConcurrency — verifies
    all four probes complete in ~timeout time, not 4x timeout.
    """
    services = list(SERVICE_PROBE_COMMANDS.items())
    coros = [
        _probe_single_service(svc, cmd, timeout_per_probe) for svc, cmd in services
    ]
    try:
        raw_results = await asyncio.gather(*coros, return_exceptions=True)
    except Exception as exc:  # pragma: no cover - gather itself cannot normally raise
        logger.debug("probe_all_services: gather failed: %s", exc)
        return {
            svc: ProbeResult(
                state="degraded", hint=_safe_hint(f"probe gather failed: {exc}")
            )
            for svc in SERVICE_PROBE_COMMANDS
        }

    results: dict[str, ProbeResult] = {}
    for (svc, _cmd), result in zip(services, raw_results):
        if isinstance(result, BaseException):
            results[svc] = ProbeResult(
                state="degraded",
                hint=_safe_hint(f"{svc} probe raised: {result}"),
            )
        elif isinstance(result, ProbeResult):
            results[svc] = result
        else:
            # Should never happen — _probe_single_service always returns ProbeResult
            results[svc] = ProbeResult(
                state="degraded",
                hint=_safe_hint(
                    f"{svc} probe returned unexpected type: {type(result)}"
                ),
            )
    return results


def probe_all_services_sync(
    timeout: float = 1.5,
) -> dict[str, ProbeResult]:
    """Synchronous wrapper around probe_all_services for use in non-async callers.

    Why: trusty_status.py and framework_loader.py are synchronous; this wrapper
    bridges to the async probe without requiring callers to manage event loops.

    What: Uses asyncio.get_running_loop() to detect an already-running event
    loop (raises RuntimeError when NO loop is running — counterintuitive but
    correct). If a loop IS running, returns all ABSENT with an explanatory hint.
    Otherwise calls asyncio.run(probe_all_services(timeout)). Any other
    exception → all DEGRADED. Never raises.

    Test: tests/services/test_tool_service_probe.py::TestFailSafe — verifies no
    exception propagates even when asyncio.run raises.
    """
    try:
        asyncio.get_running_loop()
        # A loop is already running — cannot use asyncio.run().
        # Return ABSENT for all services with an explanatory hint.
        hint = _safe_hint("event loop already running — probe skipped")
        logger.debug("probe_all_services_sync: %s", hint)
        return {
            svc: ProbeResult(state="absent", hint=hint)
            for svc in SERVICE_PROBE_COMMANDS
        }
    except RuntimeError:
        # No loop running — safe to call asyncio.run().
        pass
    try:
        return asyncio.run(probe_all_services(timeout))
    except Exception as exc:
        hint = _safe_hint(f"sync probe wrapper failed: {exc}")
        logger.debug("probe_all_services_sync: %s", hint)
        return {
            svc: ProbeResult(state="degraded", hint=hint)
            for svc in SERVICE_PROBE_COMMANDS
        }
