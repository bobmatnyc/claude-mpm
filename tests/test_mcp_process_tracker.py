"""Tests for MCP stdio-server process tracking (issue #927).

WHAT: Exercises signature parsing from ``.mcp.json``, live-process discovery
via a mocked ``pgrep``, and the PID-record writer in
``claude_mpm.services.cli.mcp_process_tracker``.

WHY: Discovery is safety-critical — it must record only the short-lived stdio
MCP children and never the shared HTTP daemons.  These tests mock the process
table so the distinction is validated deterministically.

    uv run pytest -p no:xdist tests/test_mcp_process_tracker.py -v
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime in signatures

import pytest  # noqa: TC002 - used at runtime as fixture type annotation

from claude_mpm.services.cli import mcp_process_tracker as tracker

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# A realistic .mcp.json: two stdio servers plus one HTTP server (url-based).
_MCP_JSON = {
    "mcpServers": {
        "trusty-memory": {
            "command": "trusty-memory",
            "args": ["serve", "--stdio"],
            "type": "stdio",
        },
        "trusty-search": {
            "command": "trusty-search",
            "args": ["serve", "--index", "tm-claude-mpm-01"],
            "type": "stdio",
        },
        "some-http": {
            "type": "http",
            "url": "https://example.com/mcp",
        },
    }
}


def _write_mcp_json(project_dir: Path, data: dict) -> None:
    (project_dir / ".mcp.json").write_text(json.dumps(data))


def _install_fake_proc_table(monkeypatch: pytest.MonkeyPatch, lines: list[str]) -> None:
    """Wire the ``pgrep``/``ps`` seam to a fake process table.

    *lines* are ``"<pid> <cmdline>"`` strings.  ``_pgrep_pids`` returns the PIDs
    whose cmdline contains the search pattern (mimicking ``pgrep -f``), and
    ``get_process_cmdline`` maps a PID back to its cmdline (mimicking ``ps``).
    PPID-ancestry scoping is disabled (``_session_owned_pids`` -> None) so these
    fixtures exercise the signature/exclusion logic in isolation; ownership
    scoping has its own dedicated tests.
    """
    table: dict[int, str] = {}
    for line in lines:
        pid_str, cmdline = line.split(" ", 1)
        table[int(pid_str)] = cmdline

    def _fake_pgrep_pids(pattern: str) -> list[int]:
        return [pid for pid, cmd in table.items() if pattern in cmd]

    def _fake_cmdline(pid: int) -> str | None:
        return table.get(pid)

    monkeypatch.setattr(tracker, "_pgrep_pids", _fake_pgrep_pids)
    monkeypatch.setattr(tracker, "get_process_cmdline", _fake_cmdline)
    monkeypatch.setattr(tracker, "_session_owned_pids", lambda _pids: None)


# ---------------------------------------------------------------------------
# Signature parsing
# ---------------------------------------------------------------------------


def test_load_signatures_extracts_stdio_only(tmp_path: Path) -> None:
    _write_mcp_json(tmp_path, _MCP_JSON)
    sigs = tracker.load_stdio_server_signatures(tmp_path)
    assert "trusty-memory serve --stdio" in sigs
    assert "trusty-search serve --index tm-claude-mpm-01" in sigs
    # HTTP (url-based) server is excluded.
    assert all("example.com" not in s for s in sigs)
    assert len(sigs) == 2


def test_load_signatures_uses_command_basename(tmp_path: Path) -> None:
    _write_mcp_json(
        tmp_path,
        {
            "mcpServers": {
                "m": {
                    "command": "/Users/x/.cargo/bin/trusty-memory",
                    "args": ["serve", "--stdio"],
                    "type": "stdio",
                }
            }
        },
    )
    sigs = tracker.load_stdio_server_signatures(tmp_path)
    assert sigs == ["trusty-memory serve --stdio"]


def test_load_signatures_missing_file_returns_empty(tmp_path: Path) -> None:
    assert tracker.load_stdio_server_signatures(tmp_path) == []


def test_load_signatures_malformed_json_returns_empty(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text("{not json")
    assert tracker.load_stdio_server_signatures(tmp_path) == []


# ---------------------------------------------------------------------------
# Discovery — the core safety behavior
# ---------------------------------------------------------------------------


def test_discover_matches_stdio_and_excludes_http_daemon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_mcp_json(tmp_path, _MCP_JSON)

    lines = [
        # stdio children — should be matched.
        "1001 trusty-memory serve --stdio",
        "1002 trusty-search serve --index tm-claude-mpm-01",
        # shared HTTP daemons — must NEVER match.
        "2001 trusty-memory serve --foreground",
        "2002 /Users/x/.cargo/bin/trusty-search start --foreground --no-auto-discover --port 7878",
        # unrelated process sharing a name fragment but not the signature.
        "3001 trusty-search reindex --index other",
    ]
    _install_fake_proc_table(monkeypatch, lines)

    procs = tracker.discover_stdio_mcp_processes(tmp_path)
    pids = {p["pid"] for p in procs}

    assert pids == {1001, 1002}
    # HTTP daemons and unrelated processes excluded.
    assert 2001 not in pids
    assert 2002 not in pids
    assert 3001 not in pids


def test_discover_records_live_cmdline_and_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_mcp_json(tmp_path, _MCP_JSON)
    lines = ["1001 trusty-memory serve --stdio"]
    _install_fake_proc_table(monkeypatch, lines)

    procs = tracker.discover_stdio_mcp_processes(tmp_path)
    assert len(procs) == 1
    assert procs[0]["pid"] == 1001
    assert procs[0]["cmdline"] == "trusty-memory serve --stdio"
    assert procs[0]["signature"] == "trusty-memory serve --stdio"


def test_discover_deduplicates_pids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_mcp_json(tmp_path, _MCP_JSON)
    # Same PID matched by two signature searches — should appear once. The PID's
    # cmdline contains both command names so both basename searches surface it.
    monkeypatch.setattr(tracker, "_pgrep_pids", lambda _pattern: [1001, 1001])
    monkeypatch.setattr(
        tracker,
        "get_process_cmdline",
        lambda _pid: (
            "trusty-memory serve --stdio trusty-search serve --index tm-claude-mpm-01"
        ),
    )
    monkeypatch.setattr(tracker, "_session_owned_pids", lambda _pids: None)

    procs = tracker.discover_stdio_mcp_processes(tmp_path)
    assert len(procs) == 1


# ---------------------------------------------------------------------------
# PPID-ancestry session scoping
# ---------------------------------------------------------------------------


def test_ancestor_pids_excludes_init_roots() -> None:
    # 500 -> 400 -> 300 -> 1 (init).  pid 1 and 0 must NOT be ancestors.
    ppid_map = {500: 400, 400: 300, 300: 1, 1: 0}
    ancestors = tracker._ancestor_pids(500, ppid_map)
    assert ancestors == {400, 300}
    assert 1 not in ancestors
    assert 0 not in ancestors


def test_ancestor_pids_handles_cycle() -> None:
    ppid_map = {10: 20, 20: 10}  # pathological cycle
    # The guard must TERMINATE (no infinite loop) and return a bounded set.
    ancestors = tracker._ancestor_pids(10, ppid_map)
    assert ancestors == {10, 20}


def test_session_owned_pids_scopes_to_our_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Our hook is pid 900, whose ancestor claude is 800.
    # 111 is a sibling session's server (parent 700 — not our ancestor).
    ppid_map = {
        900: 800,  # us -> claude(800)
        800: 1,  # claude -> init
        100: 800,  # our MCP server (child of our claude)
        111: 700,  # other session's MCP server (child of other claude)
        700: 1,
    }
    monkeypatch.setattr(tracker, "_build_ppid_map", lambda: ppid_map)
    monkeypatch.setattr(tracker.os, "getpid", lambda: 900)

    owned = tracker._session_owned_pids({100, 111})
    assert owned == {100}


def test_session_owned_pids_none_when_table_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tracker, "_build_ppid_map", dict)
    assert tracker._session_owned_pids({1, 2, 3}) is None


def test_discover_scopes_out_other_session_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_mcp_json(tmp_path, _MCP_JSON)
    # Two sessions run an identical `trusty-memory serve --stdio`; only 100 is
    # a child of our session.
    table = {100: "trusty-memory serve --stdio", 111: "trusty-memory serve --stdio"}
    monkeypatch.setattr(
        tracker,
        "_pgrep_pids",
        lambda pattern: [p for p, c in table.items() if pattern in c],
    )
    monkeypatch.setattr(tracker, "get_process_cmdline", table.get)
    # Ownership: only 100 is our child.
    monkeypatch.setattr(tracker, "_session_owned_pids", lambda pids: {100} & pids)

    procs = tracker.discover_stdio_mcp_processes(tmp_path)
    assert {p["pid"] for p in procs} == {100}


def test_discover_no_signatures_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No .mcp.json → no signatures → no discovery, pgrep never consulted.
    called = {"hit": False}

    def _boom(_pattern: str) -> list[int]:
        called["hit"] = True
        return []

    monkeypatch.setattr(tracker, "_pgrep_pids", _boom)
    assert tracker.discover_stdio_mcp_processes(tmp_path) == []
    assert called["hit"] is False


def test_pgrep_pids_handles_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tracker.shutil, "which", lambda _name: None)
    # Must never raise even though pgrep is "missing".
    assert tracker._pgrep_pids("trusty-memory") == []


# ---------------------------------------------------------------------------
# PID-record writer
# ---------------------------------------------------------------------------


def test_write_pid_file_creates_record(tmp_path: Path) -> None:
    procs = [
        {"pid": 1001, "cmdline": "trusty-memory serve --stdio", "signature": "sig"}
    ]
    path = tracker.write_pid_file(tmp_path, "abc-123", procs)
    assert path is not None
    assert path.name == "mcp-pids-abc-123.json"

    record = json.loads(path.read_text())
    assert record["session_id"] == "abc-123"
    assert record["processes"][0]["pid"] == 1001
    assert "captured_at" in record


def test_write_pid_file_empty_processes_is_noop(tmp_path: Path) -> None:
    assert tracker.write_pid_file(tmp_path, "abc", []) is None
    assert (
        list((tmp_path / ".claude-mpm").glob("*.json")) == []
        or not (tmp_path / ".claude-mpm").exists()
    )


def test_write_pid_file_sanitizes_session_id(tmp_path: Path) -> None:
    procs = [{"pid": 1, "cmdline": "x", "signature": "x"}]
    path = tracker.write_pid_file(tmp_path, "weird/../id", procs)
    assert path is not None
    # No path separators leak into the filename.
    assert "/" not in path.name
    assert path.parent == tmp_path / ".claude-mpm"


def test_iter_pid_files_finds_records(tmp_path: Path) -> None:
    procs = [{"pid": 1, "cmdline": "x", "signature": "x"}]
    tracker.write_pid_file(tmp_path, "s1", procs)
    tracker.write_pid_file(tmp_path, "s2", procs)
    files = tracker.iter_pid_files(tmp_path)
    assert len(files) == 2
    assert all(f.name.startswith("mcp-pids-") for f in files)


def test_iter_pid_files_missing_dir(tmp_path: Path) -> None:
    assert tracker.iter_pid_files(tmp_path) == []


# ---------------------------------------------------------------------------
# process_is_alive / get_process_cmdline against the current process
# ---------------------------------------------------------------------------


def test_process_is_alive_true_for_self() -> None:
    import os

    assert tracker.process_is_alive(os.getpid()) is True


def test_process_is_alive_false_for_bad_pid() -> None:
    assert tracker.process_is_alive(-1) is False
    # A very high PID is almost certainly not in use.
    assert tracker.process_is_alive(2_000_000_000) is False
