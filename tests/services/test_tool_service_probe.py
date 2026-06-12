"""Tests for the live stdio MCP probe (GitHub #814).

Why: tool_service_probe.py performs subprocess-based MCP handshakes. Tests must
cover all outcome branches (ABSENT/ON/DEGRADED), timeout safety, process
reaping, concurrency, and fail-safe behaviour — all without requiring real
trusty daemons.

What: Uses unittest.mock and AsyncMock to simulate subprocess behaviour. Async
tests run via pytest-asyncio (mode=auto).

Test: Run with `pytest tests/services/test_tool_service_probe.py -v --timeout=30`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.tool_service_probe import (
    SENTINEL_TOOL,
    SERVICE_PROBE_COMMANDS,
    ProbeResult,
    _probe_single_service,
    probe_all_services,
    probe_all_services_sync,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_process(
    stdout_lines: list[bytes],
    *,
    kill_side_effect: Exception | None = None,
) -> MagicMock:
    """Build a mock asyncio.subprocess.Process.

    Why: Allows tests to control exactly what the subprocess writes to stdout
    without spawning real processes.

    What: Returns a MagicMock whose stdout.readline is an AsyncMock that pops
    from stdout_lines in order (returns b"" when exhausted), stdin.write is a
    MagicMock, stdin.drain is an AsyncMock, kill() raises kill_side_effect if
    set, and wait() is an AsyncMock returning 0.
    """
    process = MagicMock()
    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()

    remaining = list(stdout_lines)

    async def _readline() -> bytes:
        if remaining:
            return remaining.pop(0)
        return b""

    process.stdout = MagicMock()
    process.stdout.readline = _readline

    if kill_side_effect:
        process.kill = MagicMock(side_effect=kill_side_effect)
    else:
        process.kill = MagicMock()

    process.wait = AsyncMock(return_value=0)
    return process


def _make_init_response(with_error: bool = False) -> bytes:
    """JSON-RPC initialize response line."""
    import json

    if with_error:
        resp = {"jsonrpc": "2.0", "error": {"code": -1, "message": "err"}, "id": 1}
    else:
        resp = {
            "jsonrpc": "2.0",
            "result": {"protocolVersion": "2024-11-05", "capabilities": {}},
            "id": 1,
        }
    return (json.dumps(resp) + "\n").encode()


def _make_tools_response(tool_names: list[str]) -> bytes:
    """JSON-RPC tools/list response line."""
    import json

    tools = [
        {"name": n, "description": f"desc {n}", "inputSchema": {}} for n in tool_names
    ]
    resp = {"jsonrpc": "2.0", "result": {"tools": tools}, "id": 2}
    return (json.dumps(resp) + "\n").encode()


# ---------------------------------------------------------------------------
# ProbeResult dataclass
# ---------------------------------------------------------------------------


class TestProbeResult:
    """Basic structural tests for the ProbeResult dataclass."""

    def test_on_state(self) -> None:
        r = ProbeResult(state="on")
        assert r.state == "on"
        assert r.hint == ""

    def test_degraded_with_hint(self) -> None:
        r = ProbeResult(state="degraded", hint="restart daemon")
        assert r.state == "degraded"
        assert r.hint == "restart daemon"

    def test_absent_no_hint(self) -> None:
        r = ProbeResult(state="absent")
        assert r.hint == ""

    def test_frozen(self) -> None:
        r = ProbeResult(state="on")
        with pytest.raises((AttributeError, TypeError)):
            r.state = "absent"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _probe_single_service: ABSENT
# ---------------------------------------------------------------------------


class TestProbeAbsent:
    """Binary not on PATH → ABSENT, no subprocess spawned."""

    async def test_absent_when_binary_not_found(self) -> None:
        with patch(
            "claude_mpm.services.tool_service_probe.shutil.which", return_value=None
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory", "serve", "--stdio"], timeout=1.0
            )
        assert result.state == "absent"
        assert result.hint == ""

    async def test_absent_does_not_spawn_process(self) -> None:
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which", return_value=None
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec"
            ) as mock_spawn,
        ):
            await _probe_single_service("trusty-memory", ["trusty-memory"], timeout=1.0)
        mock_spawn.assert_not_called()


# ---------------------------------------------------------------------------
# _probe_single_service: ON
# ---------------------------------------------------------------------------


class TestProbeOn:
    """Binary present and handshake succeeds."""

    async def test_on_with_sentinel_tool(self) -> None:
        process = _make_process(
            [_make_init_response(), _make_tools_response([SENTINEL_TOOL, "other_tool"])]
        )
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/usr/local/bin/trusty-memory",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory", "serve", "--stdio"], timeout=2.0
            )
        assert result.state == "on"
        assert result.hint == ""

    async def test_on_without_sentinel_but_tools_present(self) -> None:
        """Looser check: any tools returned → ON (sentinel may not always be present)."""
        process = _make_process(
            [
                _make_init_response(),
                _make_tools_response(["memory_recall", "memory_note"]),
            ]
        )
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/usr/bin/trusty-memory",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory", "serve", "--stdio"], timeout=2.0
            )
        assert result.state == "on"

    async def test_on_hints_empty(self) -> None:
        process = _make_process(
            [_make_init_response(), _make_tools_response([SENTINEL_TOOL])]
        )
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/trusty-search",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-search", ["trusty-search", "serve"], timeout=2.0
            )
        assert result.hint == ""


# ---------------------------------------------------------------------------
# _probe_single_service: DEGRADED
# ---------------------------------------------------------------------------


class TestProbeDegraded:
    """Various failure modes all yield DEGRADED with a non-empty hint."""

    async def test_degraded_empty_tools_list(self) -> None:
        process = _make_process([_make_init_response(), _make_tools_response([])])
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=2.0
            )
        assert result.state == "degraded"
        assert result.hint != ""

    async def test_degraded_garbage_response(self) -> None:
        process = _make_process([b"not json at all\n"])
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=2.0
            )
        assert result.state == "degraded"
        assert result.hint != ""

    async def test_degraded_missing_result_key(self) -> None:
        import json

        bad_init = (json.dumps({"jsonrpc": "2.0", "id": 1}) + "\n").encode()
        process = _make_process([bad_init])
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=2.0
            )
        assert result.state == "degraded"

    async def test_degraded_stdout_closed(self) -> None:
        """Subprocess writes nothing (empty bytes) → DEGRADED."""
        process = _make_process([b""])
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=2.0
            )
        assert result.state == "degraded"

    async def test_degraded_never_raises(self) -> None:
        """Even when the subprocess explodes, no exception should escape."""
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                side_effect=OSError("spawn failed"),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=2.0
            )
        assert result.state in ("degraded", "absent")


# ---------------------------------------------------------------------------
# Timeout safety
# ---------------------------------------------------------------------------


class TestProbeTimeout:
    """Probes that hang must resolve as DEGRADED within the timeout."""

    async def test_timeout_yields_degraded(self) -> None:
        """A subprocess that never writes → DEGRADED after timeout."""

        async def _hang() -> bytes:
            await asyncio.sleep(60)
            return b""  # unreachable in test

        process = MagicMock()
        process.stdin = MagicMock()
        process.stdin.write = MagicMock()
        process.stdin.drain = AsyncMock()
        process.stdout = MagicMock()
        process.stdout.readline = _hang
        process.kill = MagicMock()
        process.wait = AsyncMock(return_value=0)

        start = time.monotonic()
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=0.2
            )
        elapsed = time.monotonic() - start

        assert result.state == "degraded"
        assert elapsed < 3.0, f"Timeout probe took too long: {elapsed:.1f}s"

    async def test_timeout_hint_mentions_service(self) -> None:
        async def _hang() -> bytes:
            await asyncio.sleep(60)
            return b""

        process = MagicMock()
        process.stdin = MagicMock()
        process.stdin.write = MagicMock()
        process.stdin.drain = AsyncMock()
        process.stdout = MagicMock()
        process.stdout.readline = _hang
        process.kill = MagicMock()
        process.wait = AsyncMock(return_value=0)

        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            result = await _probe_single_service(
                "trusty-search", ["trusty-search", "serve"], timeout=0.2
            )
        assert "trusty-search" in result.hint


# ---------------------------------------------------------------------------
# Process reaping
# ---------------------------------------------------------------------------


class TestProcessReaping:
    """After probe completes (success or failure), the subprocess must be reaped."""

    async def test_process_killed_on_success(self) -> None:
        process = _make_process(
            [_make_init_response(), _make_tools_response([SENTINEL_TOOL])]
        )
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            await _probe_single_service("trusty-memory", ["trusty-memory"], timeout=2.0)
        process.kill.assert_called()

    async def test_process_killed_on_degraded(self) -> None:
        process = _make_process([b"garbage\n"])
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            await _probe_single_service("trusty-memory", ["trusty-memory"], timeout=2.0)
        process.kill.assert_called()

    async def test_process_killed_even_if_kill_raises(self) -> None:
        """Even if kill() raises OSError, the probe must not propagate it."""
        process = _make_process(
            [b"garbage\n"],
            kill_side_effect=OSError("already dead"),
        )
        with (
            patch(
                "claude_mpm.services.tool_service_probe.shutil.which",
                return_value="/bin/x",
            ),
            patch(
                "claude_mpm.services.tool_service_probe.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=process),
            ),
        ):
            # Must not raise even though kill raises.
            result = await _probe_single_service(
                "trusty-memory", ["trusty-memory"], timeout=2.0
            )
        assert result.state == "degraded"


# ---------------------------------------------------------------------------
# Concurrency: probe_all_services
# ---------------------------------------------------------------------------


class TestConcurrency:
    """All four probes run concurrently — total time ~ 1x timeout, not 4x."""

    async def test_all_services_returned(self) -> None:
        async def _fast_absent(svc: str, cmd: list[str], t: float) -> ProbeResult:
            return ProbeResult(state="absent")

        with patch(
            "claude_mpm.services.tool_service_probe._probe_single_service",
            side_effect=_fast_absent,
        ):
            results = await probe_all_services(timeout_per_probe=1.0)

        assert set(results) == set(SERVICE_PROBE_COMMANDS)

    async def test_concurrent_execution_bounded_time(self) -> None:
        """Four probes with 0.2s sleep each should finish in < 0.8s total."""
        delay = 0.15

        async def _slow_absent(svc: str, cmd: list[str], t: float) -> ProbeResult:
            await asyncio.sleep(delay)
            return ProbeResult(state="absent")

        start = time.monotonic()
        with patch(
            "claude_mpm.services.tool_service_probe._probe_single_service",
            side_effect=_slow_absent,
        ):
            await probe_all_services(timeout_per_probe=1.0)
        elapsed = time.monotonic() - start

        # Concurrent: should finish in ~delay, not 4x delay.
        assert elapsed < delay * 3, (
            f"Expected concurrent execution but took {elapsed:.2f}s (4x delay = {4 * delay:.2f}s)"
        )

    async def test_one_raise_does_not_abort_others(self) -> None:
        """An exception from one probe should yield DEGRADED, not cancel siblings."""
        call_count = 0

        async def _mixed(svc: str, cmd: list[str], t: float) -> ProbeResult:
            nonlocal call_count
            call_count += 1
            if svc == "trusty-search":
                raise RuntimeError("boom")
            return ProbeResult(state="absent")

        with patch(
            "claude_mpm.services.tool_service_probe._probe_single_service",
            side_effect=_mixed,
        ):
            results = await probe_all_services(timeout_per_probe=1.0)

        assert call_count == 4
        assert results["trusty-search"].state == "degraded"
        assert results["trusty-memory"].state == "absent"


# ---------------------------------------------------------------------------
# probe_all_services_sync: fail-safe
# ---------------------------------------------------------------------------


class TestFailSafe:
    """probe_all_services_sync must never raise, even on event-loop conflicts."""

    def test_sync_wrapper_never_raises(self) -> None:
        with patch(
            "claude_mpm.services.tool_service_probe.asyncio.run",
            side_effect=RuntimeError("boom"),
        ):
            result = probe_all_services_sync()
        # Should return a dict — any state is fine, but no exception.
        assert isinstance(result, dict)
        assert set(result) == set(SERVICE_PROBE_COMMANDS)

    def test_event_loop_conflict_returns_absent(self) -> None:
        with patch(
            "claude_mpm.services.tool_service_probe.asyncio.run",
            side_effect=RuntimeError("This event loop is already running."),
        ):
            result = probe_all_services_sync()
        # RuntimeError → ABSENT (event loop conflict path).
        for svc, r in result.items():
            assert r.state == "absent", f"{svc}: expected absent, got {r.state}"

    def test_unexpected_exception_returns_degraded(self) -> None:
        with patch(
            "claude_mpm.services.tool_service_probe.asyncio.run",
            side_effect=OSError("disk full"),
        ):
            result = probe_all_services_sync()
        # OSError is not RuntimeError → DEGRADED.
        for svc, r in result.items():
            assert r.state == "degraded", f"{svc}: expected degraded, got {r.state}"

    def test_sync_wrapper_returns_all_services(self) -> None:
        with patch(
            "claude_mpm.services.tool_service_probe.asyncio.run",
            return_value={
                svc: ProbeResult(state="absent") for svc in SERVICE_PROBE_COMMANDS
            },
        ):
            result = probe_all_services_sync()
        assert set(result) == set(SERVICE_PROBE_COMMANDS)


# ---------------------------------------------------------------------------
# trusty_status integration: get_trusty_capabilities_live and get_probe_hint
# ---------------------------------------------------------------------------


class TestGetTrustyCapabilitiesLive:
    """Tests for the new trusty_status functions.

    Why: get_trusty_capabilities_live does a local import of probe_all_services_sync
    inside the function body, so we patch at the source module level
    (claude_mpm.services.tool_service_probe) rather than on trusty_status.
    """

    def test_states_mapped_correctly(self) -> None:
        from claude_mpm.services import trusty_status

        fake_results = {
            "trusty-memory": ProbeResult(state="on"),
            "trusty-search": ProbeResult(state="absent"),
            "trusty-analyze": ProbeResult(state="degraded", hint="no tools"),
            "trusty-review": ProbeResult(state="on"),
        }
        with patch(
            "claude_mpm.services.tool_service_probe.probe_all_services_sync",
            return_value=fake_results,
        ):
            caps = trusty_status.get_trusty_capabilities_live()

        assert caps["trusty-memory"] == "on"
        assert caps["trusty-search"] == "absent"
        assert caps["trusty-analyze"] == "degraded"
        assert caps["trusty-review"] == "on"

    def test_hints_stored(self) -> None:
        from claude_mpm.services import trusty_status

        fake_results = {
            "trusty-memory": ProbeResult(state="degraded", hint="restart daemon"),
            "trusty-search": ProbeResult(state="absent"),
            "trusty-analyze": ProbeResult(state="on"),
            "trusty-review": ProbeResult(state="on"),
        }
        with patch(
            "claude_mpm.services.tool_service_probe.probe_all_services_sync",
            return_value=fake_results,
        ):
            trusty_status.get_trusty_capabilities_live()

        assert trusty_status.get_probe_hint("trusty-memory") == "restart daemon"
        assert trusty_status.get_probe_hint("trusty-search") == ""
        assert trusty_status.get_probe_hint("trusty-analyze") == ""

    def test_fallback_on_import_error(self, monkeypatch: Any) -> None:
        """When the probe module raises on import, falls back to config-based detection."""
        import sys

        from claude_mpm.services import trusty_status

        monkeypatch.setattr(
            trusty_status,
            "get_trusty_capabilities",
            lambda: {
                "trusty-memory": "on",
                "trusty-search": "absent",
                "trusty-analyze": "absent",
                "trusty-review": "absent",
            },
        )
        # Remove the module from sys.modules to simulate ImportError on next import.
        saved = sys.modules.pop("claude_mpm.services.tool_service_probe", None)
        # Stash the module in a fake entry that raises.
        sys.modules["claude_mpm.services.tool_service_probe"] = None  # type: ignore[assignment]
        try:
            caps = trusty_status.get_trusty_capabilities_live()
        finally:
            # Restore the module.
            if saved is not None:
                sys.modules["claude_mpm.services.tool_service_probe"] = saved
            else:
                sys.modules.pop("claude_mpm.services.tool_service_probe", None)

        # Should have fallen back without raising.
        assert isinstance(caps, dict)
        assert set(caps) >= {"trusty-memory", "trusty-search"}

    def test_fallback_on_probe_exception(self, monkeypatch: Any) -> None:
        """Any exception from probe_all_services_sync → falls back, does not raise."""
        from claude_mpm.services import trusty_status

        monkeypatch.setattr(
            trusty_status,
            "get_trusty_capabilities",
            lambda: {
                "trusty-memory": "absent",
                "trusty-search": "absent",
                "trusty-analyze": "absent",
                "trusty-review": "absent",
            },
        )
        with patch(
            "claude_mpm.services.tool_service_probe.probe_all_services_sync",
            side_effect=RuntimeError("boom"),
        ):
            caps = trusty_status.get_trusty_capabilities_live()

        assert isinstance(caps, dict)


class TestGetProbeHint:
    """get_probe_hint returns stored hints or empty string."""

    def test_returns_empty_for_unknown_service(self) -> None:
        from claude_mpm.services import trusty_status

        trusty_status._PROBE_HINTS.clear()
        assert trusty_status.get_probe_hint("no-such-service") == ""

    def test_returns_hint_after_live_probe(self) -> None:
        from claude_mpm.services import trusty_status

        fake_results = {
            "trusty-memory": ProbeResult(state="degraded", hint="check wiring"),
            "trusty-search": ProbeResult(state="absent"),
            "trusty-analyze": ProbeResult(state="on"),
            "trusty-review": ProbeResult(state="on"),
        }
        with patch(
            "claude_mpm.services.tool_service_probe.probe_all_services_sync",
            return_value=fake_results,
        ):
            trusty_status.get_trusty_capabilities_live()

        assert trusty_status.get_probe_hint("trusty-memory") == "check wiring"
        assert trusty_status.get_probe_hint("trusty-search") == ""
