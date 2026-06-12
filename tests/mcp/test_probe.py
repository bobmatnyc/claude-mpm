"""Unit tests for src/claude_mpm/mcp/probe.py.

These tests NEVER spawn a real trusty-review binary.  They use a tiny inline
Python script (passed as ``[sys.executable, "-c", ...]``) as the fake stdio
server so no external installation is required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path  # noqa: TC003 - used at runtime in tmp_path fixture annotation

import pytest

from claude_mpm.mcp.probe import probe_mcp_stdio

# ---------------------------------------------------------------------------
# Helpers — tiny inline stdio servers
# ---------------------------------------------------------------------------

# A minimal valid JSON-RPC initialize response that any real MCP server would
# send.  Written to stdout and then the script exits so the test teardown can
# reap the process quickly.
_VALID_RESPONSE = json.dumps(
    {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "fake-server", "version": "0.0.1"},
        },
        "id": 1,
    }
)

# Python one-liner that reads one line from stdin (the initialize request)
# then writes a valid JSON-RPC response to stdout and exits cleanly.
_FAKE_SERVER_SCRIPT = (
    "import sys, json; "
    "_req = sys.stdin.readline(); "
    f"sys.stdout.write({_VALID_RESPONSE!r} + '\\n'); "
    "sys.stdout.flush()"
)

# Script that reads stdin and then immediately exits without any output.
_SILENT_SERVER_SCRIPT = "import sys; sys.stdin.readline(); sys.exit(0)"

# Script that writes garbage (non-JSON) then exits.
_GARBAGE_SERVER_SCRIPT = (
    "import sys; sys.stdin.readline(); "
    "sys.stdout.write('not json at all\\n'); sys.stdout.flush()"
)

# Script that writes a JSON dict without "result" or "error" keys.
_UNEXPECTED_SHAPE_SCRIPT = (
    "import sys, json; sys.stdin.readline(); "
    "sys.stdout.write(json.dumps({'foo': 'bar'}) + '\\n'); sys.stdout.flush()"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_true_on_valid_initialize_response() -> None:
    """A well-behaved MCP stdio server → probe returns True."""
    result = probe_mcp_stdio(
        [sys.executable, "-c", _FAKE_SERVER_SCRIPT],
        timeout=5.0,
    )
    assert result is True


def test_returns_false_on_timeout() -> None:
    """Server that never responds → probe returns False after timeout."""
    # Use a very short timeout; the script reads stdin then hangs (sleep).
    hang_script = "import sys, time; sys.stdin.readline(); time.sleep(60)"
    result = probe_mcp_stdio(
        [sys.executable, "-c", hang_script],
        timeout=0.5,
    )
    assert result is False


def test_returns_false_on_no_output() -> None:
    """Server that exits without producing any output → False."""
    result = probe_mcp_stdio(
        [sys.executable, "-c", _SILENT_SERVER_SCRIPT],
        timeout=3.0,
    )
    assert result is False


def test_returns_false_on_garbage_output() -> None:
    """Non-JSON response → False."""
    result = probe_mcp_stdio(
        [sys.executable, "-c", _GARBAGE_SERVER_SCRIPT],
        timeout=3.0,
    )
    assert result is False


def test_returns_false_on_unexpected_json_shape() -> None:
    """JSON dict without 'result' or 'error' → False."""
    result = probe_mcp_stdio(
        [sys.executable, "-c", _UNEXPECTED_SHAPE_SCRIPT],
        timeout=3.0,
    )
    assert result is False


def test_returns_false_for_nonexistent_binary() -> None:
    """Non-existent binary → False (no exception raised)."""
    result = probe_mcp_stdio(
        ["__this_binary_does_not_exist__", "--stdio"],
        timeout=2.0,
    )
    assert result is False


def test_returns_false_for_empty_command() -> None:
    """Empty command list → False (no exception raised)."""
    result = probe_mcp_stdio([], timeout=1.0)
    assert result is False


def test_accepts_error_response_as_valid() -> None:
    """A JSON-RPC error response (not result) is still a live server → True."""
    error_response = json.dumps(
        {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
            "id": 1,
        }
    )
    error_script = (
        "import sys, json; sys.stdin.readline(); "
        f"sys.stdout.write({error_response!r} + '\\n'); sys.stdout.flush()"
    )
    result = probe_mcp_stdio(
        [sys.executable, "-c", error_script],
        timeout=3.0,
    )
    # An error response still means the server is alive and speaking the protocol.
    assert result is True


def test_subprocess_always_reaped_on_success(tmp_path: Path) -> None:
    """After a successful probe the server process must be dead (no zombies)."""
    pid_file = tmp_path / "probe_child.pid"

    script = (
        "import sys, os, json; "
        f"open({str(pid_file)!r}, 'w').write(str(os.getpid())); "
        "sys.stdin.readline(); "
        f"sys.stdout.write({_VALID_RESPONSE!r} + '\\n'); "
        "sys.stdout.flush(); "
        "import time; time.sleep(60)"  # hang after responding
    )

    result = probe_mcp_stdio(
        [sys.executable, "-c", script],
        timeout=5.0,
    )
    assert result is True

    # Read the PID that the child wrote.
    child_pid = int(pid_file.read_text().strip())
    pid_file.unlink(missing_ok=True)

    # Verify the process is gone (kill(pid, 0) raises ProcessLookupError if
    # not found, or PermissionError if found but unowned — the latter means
    # it's still running under a different UID which can't happen here).
    import os
    import time

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break  # process is gone — good
        except PermissionError:
            pytest.fail(f"Process {child_pid} is still running after probe returned")
        time.sleep(0.05)
    else:
        # One last check
        try:
            os.kill(child_pid, 0)
            pytest.fail(f"Process {child_pid} was not reaped within 3 s")
        except ProcessLookupError:
            pass  # finally gone
