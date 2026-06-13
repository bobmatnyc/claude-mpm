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
    _safe_hint,
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
    process.stdin.close = MagicMock()
    process.stdin.wait_closed = AsyncMock()

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
# _safe_hint: sanitization helper
# ---------------------------------------------------------------------------


class TestSafeHint:
    """_safe_hint strips newlines, truncates, and passes short strings unchanged."""

    def test_short_string_passes_through_unchanged(self) -> None:
        text = "trusty-memory probe failed: connection refused"
        assert _safe_hint(text) == text

    def test_newline_stripped(self) -> None:
        text = "error line 1\nerror line 2\nerror line 3"
        result = _safe_hint(text)
        assert "\n" not in result
        assert "error line 1" in result

    def test_carriage_return_stripped(self) -> None:
        text = "error\r\nwith CRLF\r\nlinebreaks"
        result = _safe_hint(text)
        assert "\r" not in result
        assert "\n" not in result

    def test_truncation_at_max_len(self) -> None:
        long_text = "x" * 200
        result = _safe_hint(long_text, max_len=120)
        assert len(result) <= 120
        assert result.endswith("...")

    def test_truncation_suffix_present(self) -> None:
        long_text = "a" * 200
        result = _safe_hint(long_text, max_len=50)
        assert result.endswith("...")
        assert len(result) == 50

    def test_exactly_max_len_not_truncated(self) -> None:
        text = "a" * 120
        result = _safe_hint(text, max_len=120)
        # Exactly at limit: no truncation needed
        assert result == text
        assert not result.endswith("...")

    def test_multiline_traceback_sanitized(self) -> None:
        traceback_text = (
            "Traceback (most recent call last):\n"
            '  File "/home/user/.local/lib/python3.13/site-packages/foo.py", line 42\n'
            '    raise ValueError("boom")\n'
            "ValueError: boom"
        )
        result = _safe_hint(traceback_text, max_len=120)
        assert "\n" not in result
        assert len(result) <= 120
        assert result.endswith("...")

    def test_custom_max_len(self) -> None:
        text = "b" * 80
        result = _safe_hint(text, max_len=40)
        assert len(result) == 40
        assert result.endswith("...")

    def test_empty_string_returns_empty(self) -> None:
        assert _safe_hint("") == ""

    def test_leading_trailing_whitespace_stripped(self) -> None:
        text = "  some error message  "
        result = _safe_hint(text)
        assert result == "some error message"

    def test_tiny_max_len_no_overflow(self) -> None:
        result = _safe_hint("abcdefgh", max_len=2)
        assert len(result) <= 2

    def test_tiny_max_len_3_no_overflow(self) -> None:
        result = _safe_hint("abcdefgh", max_len=3)
        assert len(result) <= 3


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
        process.stdin.close = MagicMock()
        process.stdin.wait_closed = AsyncMock()
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
        process.stdin.close = MagicMock()
        process.stdin.wait_closed = AsyncMock()
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

    def test_event_loop_conflict_returns_degraded(self) -> None:
        """RuntimeError from asyncio.run → DEGRADED (not ABSENT) for all services.

        ABSENT means the binary is not on PATH.  An event-loop conflict means
        the probe couldn't run at all — tool availability is unknown, which maps
        to DEGRADED so agents are told to treat the service as unreliable rather
        than uninstalled.
        """
        with patch(
            "claude_mpm.services.tool_service_probe.asyncio.run",
            side_effect=RuntimeError("This event loop is already running."),
        ):
            result = probe_all_services_sync()
        # RuntimeError (event loop conflict) → DEGRADED, never ABSENT.
        for svc, r in result.items():
            assert r.state == "degraded", f"{svc}: expected degraded, got {r.state}"
        # Hint must explain the conflict clearly.
        for r in result.values():
            assert "event loop conflict" in r.hint

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
            # Patch at source module: get_trusty_capabilities_live does a
            # local import, so patching trusty_status.probe_all_services_sync
            # would have no effect.
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
            # Patch at source module: get_trusty_capabilities_live does a
            # local import, so patching trusty_status.probe_all_services_sync
            # would have no effect.
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
        # Simulate ImportError on the next `from claude_mpm.services.tool_service_probe
        # import ...` by patching the module with a sentinel that raises ImportError.
        # patch.dict auto-restores sys.modules after the with-block, making this
        # portable and safe across test-runner isolation strategies.
        with patch.dict(
            sys.modules,
            {"claude_mpm.services.tool_service_probe": None},  # type: ignore[dict-item]
        ):
            caps = trusty_status.get_trusty_capabilities_live()

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
            # Patch at source module: get_trusty_capabilities_live does a
            # local import, so patching trusty_status.probe_all_services_sync
            # would have no effect.
            "claude_mpm.services.tool_service_probe.probe_all_services_sync",
            side_effect=RuntimeError("boom"),
        ):
            caps = trusty_status.get_trusty_capabilities_live()

        assert isinstance(caps, dict)


class TestGetProbeHint:
    """get_probe_hint returns stored hints or empty string."""

    def test_returns_empty_for_unknown_service(self) -> None:
        from claude_mpm.services import trusty_status

        # Clear hints under lock to avoid cross-test interference.
        with trusty_status._PROBE_HINTS_LOCK:
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
            # Patch at source module: get_trusty_capabilities_live does a
            # local import, so patching trusty_status.probe_all_services_sync
            # would have no effect.
            "claude_mpm.services.tool_service_probe.probe_all_services_sync",
            return_value=fake_results,
        ):
            trusty_status.get_trusty_capabilities_live()

        assert trusty_status.get_probe_hint("trusty-memory") == "check wiring"
        assert trusty_status.get_probe_hint("trusty-search") == ""


# ---------------------------------------------------------------------------
# stdin EOF buffering: servers that only respond after stdin is closed
# ---------------------------------------------------------------------------


class TestStdinEOFBuffering:
    """Servers that flush tools/list only after stdin EOF must classify as ON."""

    async def test_buffering_server_returns_on(self) -> None:
        """Simulate a server that only writes its tools/list response after stdin
        is closed. Without stdin.close() the probe would time out → DEGRADED.
        With the fix, closing stdin triggers the flush → ON.
        """
        init_resp_bytes = _make_init_response()
        tools_resp_bytes = _make_tools_response([SENTINEL_TOOL, "other_tool"])

        process = MagicMock()
        process.stdin = MagicMock()
        process.stdin.write = MagicMock()
        process.stdin.drain = AsyncMock()
        process.stdin.close = MagicMock()
        # wait_closed() must be awaitable; returns once stdin is closed.
        process.stdin.wait_closed = AsyncMock()
        process.kill = MagicMock()
        process.wait = AsyncMock(return_value=0)

        # Track whether stdin was closed; only return tools response after close.
        stdin_closed = False

        def _record_stdin_close() -> None:
            nonlocal stdin_closed
            stdin_closed = True

        process.stdin.close = MagicMock(side_effect=_record_stdin_close)

        read_call = 0

        async def _readline() -> bytes:
            nonlocal read_call
            read_call += 1
            if read_call == 1:
                # initialize response — always returned immediately.
                return init_resp_bytes
            # tools/list response — only available after stdin closed.
            # Spin briefly to let the stdin.close() side-effect register.
            for _ in range(50):
                if stdin_closed:
                    return tools_resp_bytes
                await asyncio.sleep(0.01)
            # Stdin was never closed → return empty (simulating buffer-hold).
            return b""

        process.stdout = MagicMock()
        process.stdout.readline = _readline

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

        assert result.state == "on", (
            f"Expected ON but got {result.state!r}: {result.hint}"
        )
        # Verify stdin was closed during the probe.
        process.stdin.close.assert_called_once()
