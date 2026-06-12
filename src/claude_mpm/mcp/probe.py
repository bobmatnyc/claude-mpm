"""Lightweight JSON-RPC handshake probe for stdio MCP servers.

WHAT: Spawn a stdio MCP server process, send an ``initialize`` JSON-RPC
request, and return True iff a valid JSON-RPC response arrives within
``timeout`` seconds.  Always tears down the subprocess; never raises.

WHY: The trusty-autodetect migration needs to detect review-on-demand stdio
servers (e.g. ``trusty-review``) that have no persistent HTTP daemon.  A
tight-timeout initialize handshake is the canonical way to verify that an
MCP stdio binary is installed and functional without leaving a process behind.
This helper is intentionally small and sync-callable so the migration hot path
does not require an asyncio event loop.

References
----------
SPEC-INTEGRATIONS-03~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-03~1
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
from typing import Any

logger = logging.getLogger(__name__)

# MCP protocol initialize request (JSON-RPC 2.0).
_INITIALIZE_REQUEST: dict[str, Any] = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "claude-mpm-probe", "version": "1.0.0"},
    },
    "id": 1,
}


def probe_mcp_stdio(command: list[str], *, timeout: float = 4.0) -> bool:
    """Return True iff ``command`` responds to a JSON-RPC initialize handshake.

    WHAT: Spawns ``command`` as a subprocess with stdio pipes, writes a
    JSON-RPC ``initialize`` request to its stdin, and waits up to ``timeout``
    seconds for a line on stdout that parses as a valid JSON-RPC response
    (i.e. a dict containing ``"result"`` or ``"error"``).  The subprocess is
    always killed and reaped before returning, regardless of outcome.

    WHY: On-demand stdio MCP servers (e.g. ``trusty-review serve --stdio``)
    have no persistent HTTP daemon to health-probe.  The standard MCP wire
    protocol requires an ``initialize`` exchange before any other method, so a
    successful response is a reliable signal that the binary is installed and
    functional.

    Args:
        command: argv list, e.g. ``["trusty-review", "serve", "--stdio"]``.
        timeout: Seconds to wait for a response line from stdout (default 4.0).
            Keep this tight — it runs on the startup hot path.

    Returns:
        True if the process produced a valid JSON-RPC response within
        ``timeout``; False on any error, timeout, or malformed output.

    :spec: SPEC-INTEGRATIONS-03~1
    """
    if not command:
        return False

    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # silence startup noise
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        logger.debug("probe_mcp_stdio: could not spawn %s: %s", command[0], exc)
        return False

    try:
        # Write the initialize request.
        request_bytes = (json.dumps(_INITIALIZE_REQUEST) + "\n").encode()
        try:
            assert process.stdin is not None  # always set with PIPE
            process.stdin.write(request_bytes)
            process.stdin.flush()
            process.stdin.close()
        except OSError as exc:
            logger.debug(
                "probe_mcp_stdio: stdin write failed for %s: %s", command[0], exc
            )
            return False

        # Read one line from stdout with a wall-clock timeout via a thread.
        assert process.stdout is not None
        result_holder: list[bytes] = []

        def _read_line() -> None:
            try:
                line = process.stdout.readline()  # type: ignore[union-attr]
                result_holder.append(line)
            except OSError:
                pass

        reader = threading.Thread(target=_read_line, daemon=True)
        reader.start()
        reader.join(timeout)

        if not result_holder:
            logger.debug(
                "probe_mcp_stdio: timeout waiting for response from %s", command[0]
            )
            return False

        line = result_holder[0].strip()
        if not line:
            return False

        try:
            response = json.loads(line.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            logger.debug(
                "probe_mcp_stdio: non-JSON response from %s: %s", command[0], exc
            )
            return False

        # Accept any valid JSON-RPC response (result OR error) — either
        # indicates the server is alive and speaking the protocol.
        is_valid = isinstance(response, dict) and (
            "result" in response or "error" in response
        )
        if not is_valid:
            logger.debug(
                "probe_mcp_stdio: unexpected JSON-RPC shape from %s: %s",
                command[0],
                list(response.keys()) if isinstance(response, dict) else type(response),
            )
        return is_valid

    finally:
        # Always reap the subprocess — never leave it behind.
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass
        except OSError:
            pass
