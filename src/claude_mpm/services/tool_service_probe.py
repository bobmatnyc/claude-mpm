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

Test: tests/services/test_tool_service_probe.py — covers ABSENT, ON (with and
without the sentinel tool), DEGRADED (no tools / timeout / crash), concurrency,
process reaping, and fail-safe behaviour.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

# The tool we look for first in the tools/list response to confirm a service
# is fully wired. If absent but other tools are returned we still report ON
# (the sentinel may not be present in every deployment build), documented here
# so future readers understand the intentional fallback.
SENTINEL_TOOL = "console_metrics"

# Service name -> stdio spawn command. These are the EXACT argv lists the
# trusty-* binaries expect when started in stdio MCP server mode:
#   memory  → `serve --stdio`
#   search  → `serve`
#   analyze → `mcp`
#   review  → `serve --stdio`
# These must track the trusty binaries' stdio-MCP CLI. A CLI drift (e.g. a
# renamed subcommand after a trusty release) will surface as DEGRADED probes
# rather than a crash, making the mismatch easy to diagnose and fix here.
SERVICE_PROBE_COMMANDS: dict[str, list[str]] = {
    "trusty-memory": ["trusty-memory", "serve", "--stdio"],
    "trusty-search": ["trusty-search", "serve"],
    "trusty-analyze": ["trusty-analyze", "mcp"],
    "trusty-review": ["trusty-review", "serve", "--stdio"],
}

# JSON-RPC initialize request (MCP protocol 2024-11-05).
_INIT_REQUEST: dict[str, object] = {
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
_INITIALIZED_NOTIFICATION: dict[str, object] = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {},
}

# JSON-RPC tools/list request.
_TOOLS_LIST_REQUEST: dict[str, object] = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2,
}


def _safe_hint(text: str, max_len: int = 120) -> str:
    """Sanitize a probe hint for safe injection into the PM prompt.

    Strips newlines/carriage returns and truncates to ``max_len`` chars so raw
    exception text, multi-line tracebacks, or long absolute paths cannot bloat
    or leak into the framework prompt. Returns the cleaned, bounded string.
    """
    cleaned = text.replace("\n", " ").replace("\r", " ").strip()
    if len(cleaned) <= max_len:
        return cleaned
    # For very small budgets there's no room for the "..." marker; hard-truncate.
    if max_len < 4:
        return cleaned[:max_len]
    return cleaned[: max_len - 3] + "..."


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

        assert process.stdin is not None
        assert process.stdout is not None

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
            # asyncio.TimeoutError (aliased to builtins.TimeoutError on Python 3.11+)
            # is what asyncio.wait_for raises; catching TimeoutError covers both.
            return ProbeResult(
                state="degraded",
                hint=f"{service} initialize handshake timed out after {timeout}s — check daemon / binary",
            )

        if not raw_init:
            return ProbeResult(
                state="degraded",
                hint=f"{service} closed stdout without responding to initialize",
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
                hint=f"{service} initialize response missing 'result' key",
            )

        # --- Step 2: send notifications/initialized (no response expected) ---
        notif_line = (json.dumps(_INITIALIZED_NOTIFICATION) + "\n").encode()
        process.stdin.write(notif_line)
        await process.stdin.drain()

        # --- Step 3: send tools/list request ---
        tools_line = (json.dumps(_TOOLS_LIST_REQUEST) + "\n").encode()
        process.stdin.write(tools_line)
        await process.stdin.drain()
        # Close stdin to signal EOF — some stdio MCP servers buffer stdout until
        # stdin is closed; without this the probe would time out against such a
        # server and falsely report DEGRADED for a healthy service.
        process.stdin.close()
        # wait_closed() is available in Python 3.7+ to wait for the underlying
        # transport to flush. On Python 3.13 (our minimum) this is always present.
        # Ignore OSError in case the transport is already gone (e.g. child exited).
        try:
            await process.stdin.wait_closed()
        except OSError:
            pass

        # Read tools/list response with timeout.
        try:
            raw_tools = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout,
            )
        except TimeoutError:
            # asyncio.TimeoutError (aliased to builtins.TimeoutError on Python 3.11+)
            # is what asyncio.wait_for raises; catching TimeoutError covers both.
            return ProbeResult(
                state="degraded",
                hint=f"{service} tools/list timed out — service may be reachable but not fully wired",
            )

        if not raw_tools:
            return ProbeResult(
                state="degraded",
                hint=f"{service} closed stdout during tools/list — check `serve --stdio` wiring",
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
                hint=f"{service} tools/list response missing 'result' key",
            )

        result_block = tools_resp.get("result") or {}
        tools_list: list[object] = (
            result_block.get("tools", []) if isinstance(result_block, dict) else []
        )
        tool_names: set[str] = {
            str(t["name"]) for t in tools_list if isinstance(t, dict) and "name" in t
        }

        if not tool_names:
            return ProbeResult(
                state="degraded",
                hint=(
                    f"{service} reachable but no tools exposed — "
                    f"check `serve --stdio` wiring / restart daemon"
                ),
            )

        # Both presence of SENTINEL_TOOL ("console_metrics") and "any tools
        # returned" are treated as ON today.  The sentinel check is intentionally
        # loose: if the sentinel is absent but other tools are present the binary
        # is still considered healthy (not every deployment build exposes it).
        # See SENTINEL_TOOL and module docstring for rationale.
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
    timeout_per_probe: float = 1.5,
) -> dict[str, ProbeResult]:
    """Synchronous wrapper around probe_all_services for use in non-async callers.

    Why: trusty_status.py and framework_loader.py are synchronous; this wrapper
    bridges to the async probe without requiring callers to manage event loops.

    What: Calls asyncio.run(probe_all_services(timeout_per_probe)). If an event
    loop is already running (e.g. inside pytest-asyncio), falls back to returning
    all DEGRADED with a hint explaining the conflict — tool availability is
    unknown, not absent. Any other exception → all DEGRADED. Never raises.

    Test: tests/services/test_tool_service_probe.py::TestFailSafe — verifies no
    exception propagates even when asyncio.run raises, and that an event-loop
    conflict yields DEGRADED (not ABSENT) for all services.
    """
    try:
        return asyncio.run(probe_all_services(timeout_per_probe))
    except RuntimeError as exc:
        # "This event loop is already running." — common in test environments
        # or when called from inside an async context.
        # DEGRADED (not ABSENT): the probe couldn't run; we don't know whether
        # the binaries are installed or not.
        hint = _safe_hint(
            f"probe skipped (event loop conflict) — tool availability unknown: {exc}"
        )
        logger.debug("probe_all_services_sync: %s", hint)
        return {
            svc: ProbeResult(state="degraded", hint=hint)
            for svc in SERVICE_PROBE_COMMANDS
        }
    except Exception as exc:  # pragma: no cover - defensive catch-all
        hint = _safe_hint(f"sync probe wrapper failed: {exc}")
        logger.debug("probe_all_services_sync: %s", hint)
        return {
            svc: ProbeResult(state="degraded", hint=hint)
            for svc in SERVICE_PROBE_COMMANDS
        }
