"""MCP stdio-server process tracking for session lifecycle cleanup (issue #927).

WHAT: Discovers the stdio-mode MCP server subprocesses that Claude Code spawns
for a session (``trusty-memory serve --stdio``, ``trusty-search serve --index
<name>``, ``trusty-review serve --stdio``, and any other stdio server declared
in ``.mcp.json``) and records their PIDs + live command lines so
``claude-mpm session pause`` can terminate them cleanly later.

WHY: ``claude-mpm session pause`` is a standalone CLI invocation — no Claude
Code Stop/SessionEnd hooks fire during it, and Claude Code owns the stdio MCP
subprocesses as its own children.  Without explicit PID tracking those servers
are never terminated on pause and accumulate indefinitely, each pinned to
whatever binary version was current when the session started (some observed
running for weeks).

SAFETY (critical):
- We ONLY ever record/terminate processes whose live command line matches a
  stdio-server invocation declared in the project's ``.mcp.json``.  Matching is
  by full command-line signature (command basename + configured args), never by
  process name alone.
- The shared trusty-search HTTP daemon (``trusty-search start --foreground
  --port 7878``) and the trusty-memory HTTP daemon (``trusty-memory serve
  --foreground``) use DIFFERENT invocations and are therefore never matched.
  As belt-and-suspenders we additionally exclude any candidate whose command
  line contains ``--foreground`` or ``--port 7878``.
- stdio invocations (e.g. ``trusty-memory serve --stdio``) are identical across
  every project/session, so discovery additionally scopes to processes spawned
  by THIS session's ``claude`` process via PPID ancestry — capturing another
  concurrent session's identically-invoked server would let one project's pause
  kill it.
- Every function here is fail-open: missing ``pgrep``, malformed ``.mcp.json``,
  or subprocess errors return empty/None rather than raising.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - used only for pgrep/ps process discovery
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Command-line markers that identify the SHARED, long-lived HTTP daemons which
# must NEVER be terminated by session cleanup.  Any candidate whose live cmdline
# contains one of these is skipped regardless of signature match.
_DAEMON_EXCLUSION_MARKERS = ("--foreground", "--port 7878")

# Prefix for the per-session PID record files written under
# ``<project>/.claude-mpm/``.
_PID_FILE_PREFIX = "mcp-pids-"


def _mcp_config_path(project_dir: Path) -> Path:
    """Return the path to the project's ``.mcp.json`` file."""
    return project_dir / ".mcp.json"


def _pid_dir(project_dir: Path) -> Path:
    """Return the ``.claude-mpm`` directory where PID records are stored."""
    return project_dir / ".claude-mpm"


def load_stdio_server_signatures(project_dir: Path) -> list[str]:
    """Load command-line signatures for every stdio MCP server in ``.mcp.json``.

    WHAT: Parses ``<project_dir>/.mcp.json`` and, for each server that runs in
    stdio mode, builds a signature string of the form
    ``"<command-basename> <arg1> <arg2> ..."`` (e.g.
    ``"trusty-search serve --index tm-claude-mpm-01"``).  A server is treated as
    stdio when its ``type`` is ``"stdio"``, or when ``type`` is absent but it
    declares a ``command`` and no ``url`` (http/sse servers declare a ``url``).

    WHY: The signature is the precise gate used to distinguish the short-lived
    stdio MCP children (which we clean up) from the shared HTTP daemons and any
    other process — a live process must contain this exact signature substring
    to be considered a match.

    Args:
        project_dir: Project root containing ``.mcp.json``.

    Returns:
        List of signature strings.  Empty if the file is missing/unreadable or
        no stdio servers are declared.
    """
    config_path = _mcp_config_path(project_dir)
    try:
        raw = config_path.read_text()
    except OSError:
        return []

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return []

    signatures: list[str] = []
    for server in servers.values():
        if not isinstance(server, dict):
            continue
        server_type = server.get("type")
        # Skip explicit non-stdio transports.
        if server_type in ("http", "sse") or "url" in server:
            continue
        # Accept "stdio" or an untyped server that declares a command.
        command = server.get("command")
        if not command or not isinstance(command, str):
            continue
        if server_type not in (None, "stdio"):
            continue

        args = server.get("args") or []
        if not isinstance(args, list):
            args = []
        tokens = [Path(command).name, *[str(a) for a in args]]
        signatures.append(" ".join(tokens))

    return signatures


def _pgrep_pids(pattern: str) -> list[int]:
    """Return PIDs of processes whose full command line matches *pattern*.

    Uses ``pgrep -f <pattern>`` which is portable across Linux and macOS/BSD
    (both emit one PID per line).  We deliberately do NOT rely on ``pgrep -a``
    to print command lines — BSD/macOS ``pgrep`` ignores ``-a`` and prints only
    PIDs — instead the caller re-reads each PID's live command line via
    :func:`get_process_cmdline` and filters on it.

    Exit code 1 (no matches) and a missing ``pgrep`` binary are both treated as
    "no results" rather than errors (fail-open).
    """
    if shutil.which("pgrep") is None:
        return []
    try:
        result = subprocess.run(  # nosec B603, B607 - fixed argv, no shell
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode not in (0, 1):
        return []
    pids: list[int] = []
    for token in result.stdout.split():
        try:
            pids.append(int(token))
        except ValueError:
            continue
    return pids


def _is_excluded(cmdline: str) -> bool:
    """True if *cmdline* looks like a shared HTTP daemon that must be preserved."""
    return any(marker in cmdline for marker in _DAEMON_EXCLUSION_MARKERS)


def _build_ppid_map() -> dict[int, int]:
    """Return a ``{pid: ppid}`` map of every process, or {} on failure.

    Uses ``ps -eo pid=,ppid=`` which is portable across Linux and macOS/BSD.
    """
    if shutil.which("ps") is None:
        return {}
    try:
        result = subprocess.run(  # nosec B603, B607 - fixed argv, no shell
            ["ps", "-eo", "pid=,ppid="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0:
        return {}
    ppid_map: dict[int, int] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            ppid_map[int(parts[0])] = int(parts[1])
        except ValueError:
            continue
    return ppid_map


def _ancestor_pids(pid: int, ppid_map: dict[int, int]) -> set[int]:
    """Return the set of ancestor PIDs of *pid* (parent, grandparent, ...).

    Walks the ``ppid_map`` chain with a cycle/iteration guard.  The universal
    roots 0 and 1 are intentionally EXCLUDED: detached daemons (started with
    ``start_new_session=True``) reparent to init/launchd (ppid 1), so treating
    pid 1 as an "ancestor" would wrongly claim ownership of the shared daemons.
    """
    ancestors: set[int] = set()
    current = pid
    for _ in range(64):  # generous depth cap; guards against cycles
        parent = ppid_map.get(current)
        if parent is None or parent in (0, 1) or parent in ancestors:
            break
        ancestors.add(parent)
        current = parent
    return ancestors


def _session_owned_pids(candidate_pids: set[int]) -> set[int] | None:
    """Return the subset of *candidate_pids* spawned by THIS Claude Code session.

    WHAT: Builds a process table and computes the ancestry of the current
    process (the SessionStart hook runs as a descendant of the session's
    ``claude`` process).  A candidate MCP server belongs to this session iff its
    PARENT is one of our ancestors — the session's ``claude`` process is both
    the direct parent of the stdio MCP servers it spawned AND an ancestor of
    this hook.

    WHY: stdio invocations like ``trusty-memory serve --stdio`` are IDENTICAL
    across every project/session (the palace is selected via an env var, not the
    command line), so a signature match alone would capture other live sessions'
    servers and pausing one project would kill them.  PPID-ancestry scoping
    restricts capture to exactly this session's children.

    Returns:
        The owned subset, or ``None`` if session ownership cannot be determined
        (process table unavailable or no usable ancestry) — the caller then
        falls back to signature-only matching.
    """
    ppid_map = _build_ppid_map()
    if not ppid_map:
        return None
    ancestors = _ancestor_pids(os.getpid(), ppid_map)
    if not ancestors:
        return None
    return {pid for pid in candidate_pids if ppid_map.get(pid) in ancestors}


def discover_stdio_mcp_processes(project_dir: Path) -> list[dict[str, Any]]:
    """Discover live stdio MCP server processes for THIS session.

    WHAT: Loads stdio server signatures from ``.mcp.json`` and, for each, uses
    ``pgrep -f`` on the command basename to find candidate PIDs, then re-reads
    each PID's live command line (via ``ps``) and keeps only those whose command
    line contains the full signature substring and does NOT look like a shared
    HTTP daemon.  Finally, when session ownership can be determined, restricts
    the result to processes spawned by this session's ``claude`` process (see
    :func:`_session_owned_pids`).

    WHY: This is the discovery half of the #927 fix — it produces the exact set
    of PIDs (with their live command lines) that session pause is later allowed
    to terminate.  Re-reading the cmdline per PID (rather than trusting
    ``pgrep -a``) is required for macOS/BSD portability, where ``pgrep`` prints
    only PIDs.  PPID scoping prevents capturing other concurrent sessions'
    identically-invoked stdio servers.

    Args:
        project_dir: Project root containing ``.mcp.json``.

    Returns:
        List of dicts, each with keys ``pid`` (int), ``cmdline`` (str, the live
        command line), and ``signature`` (str, the matched ``.mcp.json``
        signature).  Deduplicated by PID.  Empty on any failure.
    """
    signatures = load_stdio_server_signatures(project_dir)
    if not signatures:
        return []

    self_pid = os.getpid()
    seen_pids: set[int] = set()
    processes: list[dict[str, Any]] = []

    for signature in signatures:
        # Use the first token (command basename) as the pgrep pattern, then
        # confirm the match against the PID's live command line in Python — this
        # avoids treating regex metacharacters in the signature as patterns and
        # behaves identically on Linux and macOS.
        basename = signature.split(" ", 1)[0]
        for pid in _pgrep_pids(basename):
            if pid in seen_pids or pid == self_pid or pid <= 0:
                continue
            cmdline = get_process_cmdline(pid)
            if cmdline is None:
                continue
            if signature not in cmdline:
                continue
            if _is_excluded(cmdline):
                continue
            seen_pids.add(pid)
            processes.append({"pid": pid, "cmdline": cmdline, "signature": signature})

    # Restrict to this session's own children when ownership is determinable.
    owned = _session_owned_pids(seen_pids)
    if owned is not None:
        processes = [p for p in processes if p["pid"] in owned]

    return processes


def write_pid_file(
    project_dir: Path, session_id: str, processes: list[dict[str, Any]]
) -> Path | None:
    """Write discovered *processes* to ``.claude-mpm/mcp-pids-<session_id>.json``.

    Creates ``.claude-mpm/`` if needed.  Returns the written path, or None on
    failure (fail-open).  A record is always written when there are processes;
    with an empty *processes* list this is a no-op returning None so we do not
    litter empty files.
    """
    if not processes:
        return None

    safe_session = _sanitize_session_id(session_id)
    pid_dir = _pid_dir(project_dir)
    try:
        pid_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    record = {
        "session_id": session_id,
        "project_dir": str(project_dir),
        "captured_at": datetime.now(UTC).isoformat(),
        "processes": processes,
    }
    target = pid_dir / f"{_PID_FILE_PREFIX}{safe_session}.json"
    try:
        target.write_text(json.dumps(record, indent=2))
    except OSError:
        return None
    return target


def _sanitize_session_id(session_id: str) -> str:
    """Return a filesystem-safe token derived from *session_id*.

    Keeps alphanumerics, dashes and underscores; replaces everything else with
    ``-``.  Falls back to ``"unknown"`` for an empty id.
    """
    if not session_id:
        return "unknown"
    return "".join(c if (c.isalnum() or c in "-_") else "-" for c in session_id)


def capture_session_pids(project_dir: Path, session_id: str) -> Path | None:
    """Discover stdio MCP processes and persist them for *session_id*.

    Convenience wrapper combining :func:`discover_stdio_mcp_processes` and
    :func:`write_pid_file`.  Returns the written record path or None.
    """
    processes = discover_stdio_mcp_processes(project_dir)
    return write_pid_file(project_dir, session_id, processes)


def iter_pid_files(project_dir: Path) -> list[Path]:
    """Return all ``mcp-pids-*.json`` record files under ``.claude-mpm/``."""
    pid_dir = _pid_dir(project_dir)
    if not pid_dir.is_dir():
        return []
    try:
        return sorted(pid_dir.glob(f"{_PID_FILE_PREFIX}*.json"))
    except OSError:
        return []


def process_is_alive(pid: int) -> bool:
    """Return True if a process with *pid* currently exists.

    Uses ``os.kill(pid, 0)`` which sends no signal but performs the existence +
    permission check.  Returns False for a missing process and True for a
    process we lack permission to signal (EPERM means it exists).
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def get_process_cmdline(pid: int) -> str | None:
    """Return the live command line for *pid*, or None if unavailable.

    Uses ``ps -p <pid> -o command=`` which works on both macOS/BSD and Linux.
    Returns None if the process is gone, ``ps`` is missing, or the call fails.
    """
    if pid <= 0 or shutil.which("ps") is None:
        return None
    try:
        result = subprocess.run(  # nosec B603, B607 - fixed argv, no shell
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    cmdline = result.stdout.strip()
    return cmdline or None
