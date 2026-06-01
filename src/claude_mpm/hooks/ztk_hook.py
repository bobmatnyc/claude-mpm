"""PreToolUse hook: rewrite Bash commands through `ztk run` for token compression.

ztk (https://github.com/codejunkie99/ztk, forked at https://github.com/bobmatnyc/ztk)
is a Zig binary that compresses shell command output before it reaches Claude.
Benchmarks show 80-97% token reduction on common commands (git diff, ls, grep,
pytest, etc.) with a 90.6% overall reduction across a 256-command session.

This hook integrates ztk into claude-mpm's existing hook dispatcher rather than
running `ztk init -g` (which would conflict with our own hook setup).

Behavior:
- Resolve ztk via `_resolve_ztk()`: prefers system PATH, falls back to bundled
  binary shipped in the wheel under `claude_mpm/bin/ztk`.
- If ztk is found AND tool is `Bash`: rewrite `command` to `<ztk> run <original>`
- If ztk is NOT found: pass through unchanged (graceful degradation)
- Already-wrapped commands are left alone (idempotency)
- Uses permissionDecision "allow" (transparent — users have already granted Bash perms)

Returns hookSpecificOutput with updatedInput to modify the Bash command parameter.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

# ---------------------------------------------------------------------------
# Disable flag
# ---------------------------------------------------------------------------
# Set CLAUDE_MPM_DISABLE_ZTK=1 (or "true" / "yes") in the environment to skip
# ztk wrapping for the current session.  The hook is ON by default.
#
# Config-file disable (hooks.ztk.enabled: false in configuration.yaml) is
# intentionally NOT supported here: loading PyYAML in a subprocess hook that
# runs on every Bash call would add >10 ms of startup latency per invocation.
# Use the environment variable for persistent disabling (e.g. via shell profile
# or .env file).
_DISABLE_ENV_VAR = "CLAUDE_MPM_DISABLE_ZTK"
_MPM_LOG_DIR = Path.home() / ".claude-mpm"
_MPM_ZTK_LOG = _MPM_LOG_DIR / "ztk-savings.log"

# ---------------------------------------------------------------------------
# Functional verification cache + self-test
# ---------------------------------------------------------------------------
# WHY a functional self-test (not just existence + exec-bit):
#   The bundled binary at `claude_mpm/bin/ztk` is a 0-byte placeholder that is
#   gitignored and only populated at release time by
#   `scripts/download_ztk_binaries.sh`. A 0-byte file still passes `is_file()`
#   and (once chmod'd) the exec-bit check, yet running it produces exit-0 with
#   EMPTY stdout. The hook then rewrites every Bash command to `<ztk> run <cmd>`,
#   so the broken binary silently swallows ALL command output. This is the real
#   root cause of the "#573/#587 Bash stdout-drop" defect (misattributed to the
#   Claude Code harness). Existence + exec-bit are therefore INSUFFICIENT — we
#   must prove the binary round-trips output before trusting it.
_VERIFY_SENTINEL = "ztk_selftest_8f3a2c"
_VERIFY_TIMEOUT_S = 3.0
_VERIFY_CACHE = _MPM_LOG_DIR / "ztk-verify-cache.json"

# Process-local memo so repeated calls within one process don't re-stat/re-read.
_RESOLVE_MEMO: dict[str, str | None] = {}
_WARNED_NONFUNCTIONAL = False
_WARNED_OUTDATED = False

# ---------------------------------------------------------------------------
# Version currency
# ---------------------------------------------------------------------------
# claude-mpm pins the ztk version it ships/expects in a tiny manifest at
# `claude_mpm/bin/ztk_version.txt`. This is the SINGLE SOURCE OF TRUTH read by
# both the Makefile (`download-ztk` target) and this hook, so the bundled
# binary, the reproducible-fetch tag, and the startup currency check can never
# drift apart. We probe the installed binary's actual version and compare.
#
# IMPORTANT (fail-safe): version currency is ADVISORY, never gating. A binary
# that passes the functional self-test is used even if its version is older
# than required or cannot be parsed — we only surface a recommendation to
# update. We never silently disable a working binary over a version mismatch.
_ZTK_VERSION_PROBE_TIMEOUT_S = 3.0
# Candidate version commands, tried in order. ztk's README documents no
# `--version` flag, so we probe several conventional forms and gracefully
# accept "unknown" if none yield a parseable semver.
_ZTK_VERSION_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("--version",),
    ("version",),
    ("-V",),
    ("-v",),
)
_SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def _read_required_version() -> str | None:
    """Read the pinned ztk version from the bundled manifest.

    Returns a normalized ``vX.Y.Z`` string, or None if the manifest is absent
    or unparseable (in which case currency checks degrade to "unknown" — never
    an error). This is the source of truth shared with the Makefile.
    """
    try:
        manifest = resources.files("claude_mpm").joinpath("bin", "ztk_version.txt")
        raw = Path(str(manifest)).read_text(encoding="utf-8").strip()
    except (ModuleNotFoundError, FileNotFoundError, OSError, AttributeError) as exc:
        _log_debug(f"required-version manifest unavailable: {exc}")
        return None
    return _normalize_version(raw)


def _normalize_version(raw: str) -> str | None:
    """Parse a semver out of arbitrary version output → ``vX.Y.Z`` or None."""
    m = _SEMVER_RE.search(raw or "")
    if not m:
        return None
    return f"v{m.group(1)}.{m.group(2)}.{m.group(3)}"


def _version_tuple(version: str | None) -> tuple[int, int, int] | None:
    """Convert ``vX.Y.Z`` → (X, Y, Z) for comparison, or None if unparseable."""
    if not version:
        return None
    m = _SEMVER_RE.search(version)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _binary_fingerprint(path: Path) -> str:
    """Return a cache key derived from path + mtime_ns + size.

    Per the CLAUDE.md stability pattern, expensive verification is keyed by the
    binary's identity so a probe only re-runs when the binary actually changes
    (e.g. populated at release, upgraded, or swapped on PATH).
    """
    st = path.stat()
    raw = f"{path}|{st.st_mtime_ns}|{st.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_verify_cache() -> dict:
    try:
        with _VERIFY_CACHE.open() as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_verify_cache(cache: dict) -> None:
    try:
        _MPM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _VERIFY_CACHE.open("w") as fh:
            json.dump(cache, fh)
    except OSError as exc:
        _log_debug(f"failed to write verify cache: {exc}")


def verify_ztk_binary(path: str, *, use_cache: bool = True) -> bool:
    """Functionally verify that the ztk binary round-trips command output.

    Runs ``<path> run echo <SENTINEL>`` and confirms the sentinel appears in
    stdout. This is the AUTHORITATIVE health check: the failure mode is
    exit-0-with-empty-stdout, so checking the exit code alone is not enough —
    we must observe the binary actually passing output through.

    The boolean result is cached to ``~/.claude-mpm/ztk-verify-cache.json``
    keyed by the binary's path + mtime + size, so the (subprocess) probe runs
    once per binary version rather than on every Bash call.
    """
    try:
        bin_path = Path(path)
        fp = _binary_fingerprint(bin_path)
    except OSError as exc:
        _log_debug(f"verify: cannot stat {path}: {exc}")
        return False

    cache = _read_verify_cache() if use_cache else {}
    if use_cache and fp in cache:
        _log_debug(f"verify: cache hit for {path} -> {cache[fp]}")
        return bool(cache[fp])

    ok = _run_ztk_selftest(path)
    if use_cache:
        cache[fp] = ok
        # Bound the cache: keep only the most recent entries so it never grows
        # unbounded across many binary versions.
        if len(cache) > 16:
            cache = dict(list(cache.items())[-16:])
        _write_verify_cache(cache)
    _log_debug(f"verify: self-test for {path} -> {ok}")
    return ok


def _run_ztk_selftest(path: str) -> bool:
    """Run the sentinel round-trip probe. Returns True only if stdout matches."""
    try:
        proc = subprocess.run(
            [path, "run", "echo", _VERIFY_SENTINEL],
            capture_output=True,
            text=True,
            timeout=_VERIFY_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log_debug(f"verify: self-test raised {exc!r}")
        return False
    # Authoritative check: the sentinel must be present in stdout. An empty/
    # broken binary exits 0 with no output and fails here.
    return _VERIFY_SENTINEL in (proc.stdout or "")


def detect_ztk_version(path: str, *, use_cache: bool = True) -> str | None:
    """Detect the installed ztk binary's version as ``vX.Y.Z``, or None.

    Probes ``_ZTK_VERSION_COMMANDS`` in order, parsing the first conventional
    semver found in stdout/stderr. Returns None when the binary exposes no
    parseable version (ztk documents no ``--version`` flag, so this is an
    expected, gracefully-handled case — NOT an error).

    The result is cached alongside the functional self-test in
    ``ztk-verify-cache.json`` keyed by the binary fingerprint, so the probe
    runs once per binary version rather than on every startup. FAIL-SAFE: any
    OSError/TimeoutExpired during probing yields None (treated as "unknown"),
    never an exception on the hot path.
    """
    try:
        fp = _binary_fingerprint(Path(path))
    except OSError as exc:
        _log_debug(f"version: cannot stat {path}: {exc}")
        return None

    ver_key = f"ver:{fp}"
    cache = _read_verify_cache() if use_cache else {}
    if use_cache and ver_key in cache:
        cached = cache[ver_key]
        _log_debug(f"version: cache hit for {path} -> {cached}")
        return cached if isinstance(cached, str) else None

    version = _run_ztk_version_probe(path)
    if use_cache:
        cache[ver_key] = version
        _write_verify_cache(cache)
    _log_debug(f"version: probed {path} -> {version}")
    return version


def _run_ztk_version_probe(path: str) -> str | None:
    """Try each version command; return the first parseable ``vX.Y.Z`` or None."""
    for argv in _ZTK_VERSION_COMMANDS:
        try:
            proc = subprocess.run(
                [path, *argv],
                capture_output=True,
                text=True,
                timeout=_ZTK_VERSION_PROBE_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            _log_debug(f"version: probe {argv} raised {exc!r}")
            continue
        merged = f"{proc.stdout or ''}\n{proc.stderr or ''}"
        version = _normalize_version(merged)
        if version:
            return version
    return None


def _warn_outdated_once(installed: str | None, required: str | None) -> None:
    """Emit a single warning that ztk is functional but older than expected."""
    global _WARNED_OUTDATED
    if _WARNED_OUTDATED:
        return
    _WARNED_OUTDATED = True
    shown = installed or "unknown"
    print(
        f"[ztk-hook] ztk is functional but outdated ({shown} < {required}) — "
        "still compressing, but run 'claude-mpm ztk update' to refresh the "
        "bundled binary.",
        file=sys.stderr,
        flush=True,
    )


def _log_debug(message: str) -> None:
    """Write a debug line to stderr when CLAUDE_MPM_ZTK_DEBUG=1."""
    if os.environ.get("CLAUDE_MPM_ZTK_DEBUG") == "1":
        print(f"[ztk-hook] {message}", file=sys.stderr, flush=True)


def _passthrough() -> None:
    """Emit a continue response with no input modification."""
    print(json.dumps({"continue": True}))


def _log_intercepted(command: str) -> None:
    """Append a rewritten-command entry to ~/.claude-mpm/ztk-savings.log.

    Format: ISO-timestamp | full command (truncated to 200 chars)

    WHY: ztk's native log (~/.local/share/ztk/savings.log) records only the
    base command name (e.g. "git"), not the full invocation. The MPM log
    captures the full command string so `claude-mpm ztk-stats` can show
    which exact invocations were compressed.
    Savings bytes/pct come from ztk's own log; this file is for audit/debug.
    """
    try:
        _MPM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Truncate long commands so the log stays readable
        cmd_repr = command[:200].replace("\n", " ")
        line = f"{ts} | {cmd_repr}\n"
        with _MPM_ZTK_LOG.open("a") as fh:
            fh.write(line)
    except OSError as exc:
        _log_debug(f"failed to write MPM savings log: {exc}")


def _candidate_is_usable(path: Path) -> bool:
    """Return True only if `path` is a non-empty, executable regular file.

    WHY size > 0: the bundled binary ships as a 0-byte placeholder until a
    release populates it. A 0-byte file is `is_file()` True and can carry an
    exec-bit, but running it yields exit-0 with EMPTY stdout — the binary that
    silently swallows all Bash output (the #573 root cause). Existence and the
    exec-bit are necessary but NOT sufficient; we reject empty files here and
    follow up with a functional round-trip self-test in `_resolve_ztk()`.
    """
    try:
        if not path.is_file():
            return False
        st = path.stat()
        if st.st_size == 0:
            _log_debug(f"ztk candidate {path} is 0 bytes; rejecting")
            return False
        if not st.st_mode & stat.S_IXUSR:
            # Wheels can drop the exec-bit; try to restore it for the bundle.
            try:
                path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                _log_debug(f"chmod +x applied to {path}")
            except OSError as exc:
                _log_debug(f"failed to chmod ztk candidate {path}: {exc}")
                return False
        return True
    except OSError as exc:
        _log_debug(f"ztk candidate {path} stat failed: {exc}")
        return False


def _warn_nonfunctional_once() -> None:
    """Emit a single clear warning that ztk is present but non-functional."""
    global _WARNED_NONFUNCTIONAL
    if _WARNED_NONFUNCTIONAL:
        return
    _WARNED_NONFUNCTIONAL = True
    print(
        "[ztk-hook] ztk binary present but non-functional "
        "(0-byte/invalid/no output) — shell compression DISABLED, "
        "commands pass through unchanged.",
        file=sys.stderr,
        flush=True,
    )


def _resolve_ztk(*, verify: bool = True) -> str | None:
    """Resolve a FUNCTIONAL ztk executable path, or None for passthrough.

    Resolution order:
    1. System PATH (`shutil.which("ztk")`) — user's install takes precedence
    2. Bundled binary at `claude_mpm/bin/ztk` (chmod +x if needed)

    A candidate must pass THREE gates before it is returned:
      (a) non-empty regular file (size > 0),
      (b) executable bit set (restored for the bundle if missing),
      (c) a cached functional round-trip self-test (`verify_ztk_binary`).

    WHY gate (c): existence + exec-bit are insufficient because an empty or
    invalid binary exits 0 with no output, silently swallowing all Bash stdout
    (the #573/#587 root cause). If no candidate verifies, we return None so the
    caller passes the command through UNCHANGED — never rewriting to a binary we
    have not proven works. Pass `verify=False` to skip the self-test (used by
    callers that only need a path candidate for status display).
    """
    memo_key = "1" if verify else "0"
    if memo_key in _RESOLVE_MEMO:
        return _RESOLVE_MEMO[memo_key]

    candidates: list[Path] = []

    # 1. System install
    system_ztk = shutil.which("ztk")
    if system_ztk:
        candidates.append(Path(system_ztk))

    # 2. Bundled binary via importlib.resources
    try:
        bundled = resources.files("claude_mpm").joinpath("bin", "ztk")
        candidates.append(Path(str(bundled)))
    except (ModuleNotFoundError, FileNotFoundError, AttributeError) as exc:
        _log_debug(f"bundled ztk not available: {exc}")

    result: str | None = None
    saw_present_but_broken = False
    for cand in candidates:
        if not _candidate_is_usable(cand):
            continue
        if verify and not verify_ztk_binary(str(cand)):
            saw_present_but_broken = True
            _log_debug(f"ztk candidate {cand} failed functional verification")
            continue
        _log_debug(f"using verified ztk: {cand}")
        result = str(cand)
        break

    if result is None and saw_present_but_broken:
        _warn_nonfunctional_once()

    _RESOLVE_MEMO[memo_key] = result
    return result


def ztk_status() -> tuple[bool, str]:
    """Single source of truth for ztk functional status (for banner/statusline).

    Returns (active, reason). ``active`` is True only when ztk is disabled via
    neither env var nor flag AND a binary verifies functional. The reason string
    explains the off-state so the banner/statusline can be truthful.
    """
    if os.environ.get(_DISABLE_ENV_VAR, "").lower() in ("1", "true", "yes"):
        return (False, "disabled via --no-ztk")
    if _resolve_ztk() is not None:
        return (True, "verified functional")
    # Distinguish "no binary at all" from "present but broken" for the message.
    if _resolve_ztk(verify=False) is not None:
        return (False, "binary present but non-functional")
    return (False, "binary not found")


def ztk_status_detail() -> dict:
    """Rich ztk status including version + currency (for banner/statusline/CLI).

    Returns a dict:
        {
          "active": bool,                  # functional AND not disabled
          "reason": str,                   # off-state explanation (see ztk_status)
          "installed_version": str | None, # vX.Y.Z or None if unknown/unparseable
          "required_version": str | None,  # pinned manifest version or None
          "currency": "current" | "outdated" | "unknown" | "n/a",
          "path": str | None,              # resolved binary path
        }

    FAIL-SAFE: never raises. Version currency is advisory — an ``active`` (i.e.
    functional) binary stays active regardless of currency. If the installed
    version is older than required, ``active`` is still True but ``currency`` is
    ``"outdated"`` and a one-time stderr warning is emitted, so a working but
    older binary is NEVER silently disabled over a version mismatch.
    """
    try:
        active, reason = ztk_status()
        required = _read_required_version()
        # Resolve a path for version detection. Prefer the verified path; fall
        # back to the unverified candidate so we can still report a version for
        # a present-but-nonfunctional binary if it happens to answer --version.
        path = _resolve_ztk() or _resolve_ztk(verify=False)
        installed = detect_ztk_version(path) if path else None

        currency = _compute_currency(installed, required)
        if active and currency == "outdated":
            _warn_outdated_once(installed, required)

        return {
            "active": active,
            "reason": reason,
            "installed_version": installed,
            "required_version": required,
            "currency": currency,
            "path": path,
        }
    except Exception as exc:
        _log_debug(f"ztk_status_detail raised {exc!r}; reporting unknown")
        return {
            "active": False,
            "reason": "status unavailable",
            "installed_version": None,
            "required_version": None,
            "currency": "unknown",
            "path": None,
        }


def _compute_currency(installed: str | None, required: str | None) -> str:
    """Classify installed-vs-required version → currency label."""
    inst_t = _version_tuple(installed)
    req_t = _version_tuple(required)
    if inst_t is None or req_t is None:
        return "unknown"
    if inst_t < req_t:
        return "outdated"
    return "current"


def build_ztk_response(event: dict) -> dict:
    """Build the ztk-rewrite response for a Bash tool call.

    Returns the full ``hookSpecificOutput``-wrapped payload dict when the Bash
    command is rewritten, or ``{"continue": True}`` for any pass-through case
    (disabled, non-Bash tool, already wrapped, excluded pattern, ztk missing).

    Exposed as an importable function so ``pretooluse_dispatcher`` can call it
    directly without spawning a subprocess.

    FAIL-SAFE GUARANTEE: this is the single entry point on the Bash hot path, so
    it must NEVER raise. The whole body is wrapped so that ANY unexpected error
    (a bug here, a resolver/verify edge case, a malformed event) degrades to a
    clean ``{"continue": True}`` passthrough — the command runs UNWRAPPED rather
    than erroring the Bash call. The callers (``pretooluse_dispatcher`` and the
    inline ``tool_handler`` path) also fail-open, but this inner guard makes the
    contract hold even if a future caller forgets to wrap it.
    """
    try:
        return _build_ztk_response_impl(event)
    except Exception as exc:
        _log_debug(f"build_ztk_response raised {exc!r}; passing through")
        return {"continue": True}


def _build_ztk_response_impl(event: dict) -> dict:
    """Core ztk-rewrite logic; see ``build_ztk_response`` for the fail-safe wrapper."""
    # Environment-variable disable: fast, session-level override.
    if os.environ.get(_DISABLE_ENV_VAR, "").lower() in ("1", "true", "yes"):
        _log_debug(f"{_DISABLE_ENV_VAR} is set; ztk disabled")
        return {"continue": True}

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    # Only act on Bash tool calls
    if tool_name != "Bash":
        return {"continue": True}

    command = tool_input.get("command", "")
    if not isinstance(command, str) or not command.strip():
        return {"continue": True}

    # Idempotency: skip commands that are already wrapped
    stripped = command.lstrip()
    if stripped.startswith("ztk ") or stripped.startswith("ztk\t"):
        _log_debug("command already wrapped; skipping")
        return {"continue": True}

    # Exclusions: skip commands that ztk blocks by default
    # Commands with ' -c ' (e.g., python3 -c, bash -c, sh -c, perl -e) are denied by ztk
    if " -c " in command or " -e " in command:
        _log_debug("command contains ' -c ' or ' -e '; ztk blocks these patterns")
        return {"continue": True}

    # Skip multi-statement compound commands.
    # WHY: `ztk run <cmd>` wraps a SINGLE program invocation. The naive rewrite
    # `f"{ztk} run {command}"` parses only the FIRST segment as ztk's target;
    # everything after a shell operator (`&&`, `||`, `;`, `|`) is run by the
    # outer shell OUTSIDE ztk, so only the first segment's output is captured —
    # the partial-output bug. Newlines have the same effect. We therefore pass
    # any compound/piped command through UNCHANGED rather than wrap it.
    if "\n" in command or any(op in command for op in ("&&", "||", ";", "|")):
        _log_debug("command is compound/piped; passing through (avoids partial output)")
        return {"continue": True}

    # Graceful degradation: ztk must be resolvable
    ztk_path = _resolve_ztk()
    if ztk_path is None:
        _log_debug("ztk not found (system or bundled); pass-through")
        return {"continue": True}

    # Rewrite the command using the resolved ztk path
    tool_input["command"] = f"{ztk_path} run {command}"
    _log_debug(f"rewrote Bash command: {command[:80]!r} -> {ztk_path} run ...")
    _log_intercepted(command)

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": tool_input,
        }
    }


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception as exc:
        _log_debug(f"failed to parse event JSON: {exc}")
        _passthrough()
        return

    print(json.dumps(build_ztk_response(event)))


if __name__ == "__main__":
    main()
