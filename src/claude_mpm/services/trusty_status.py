"""Trusty daemon connection status for the startup banner (GitHub #598).

Self-contained, dependency-light status probe for the ``trusty-memory`` and
``trusty-search`` daemons. The startup banner imports :func:`get_trusty_status`
to render a one-line connection indicator per service.

Design (scoped per #598)
-------------------------
* **Cold-path short-circuit** — if the user has not opted in to the service we
  render NOTHING for it (zero HTTP cost, no banner clutter). Opt-in is detected
  via a robust, latency-free filesystem check (see :func:`_is_present`): the
  service appears in the CWD ``.mcp.json`` ``mcpServers`` map, OR a per-user
  ``~/.trusty-<service>/http_addr`` discovery file exists. We deliberately do
  NOT gate on the binary name (``shutil.which``): the launched binary may be a
  bridge/wrapper (e.g. ``trusty-memory-mcp-bridge``) whose name does not match
  the service key, which previously suppressed healthy daemons entirely.
* **Bounded, cached health probe** — when the service is present we probe
  ``{base}/health`` with a hard ≤200ms timeout. The probe result is cached
  keyed by the ``http_addr`` discovery file's mtime (mirroring how
  ``_get_ztk_status`` caches by binary mtime), so repeat startups within an
  unchanged session are free. The probe never raises — it fails safe to
  "not running".
* **Palace existence verification (#598 option 1)** — when ``trusty-memory``
  is ``on``, we additionally GET ``{base}/api/v1/palaces`` (the same hard
  ≤200ms timeout, also mtime-cached) to verify the resolved palace name
  actually exists in the daemon. ``/health`` only proves the daemon is up,
  NOT that the palace was ever created — so without this check the banner can
  show ``palace: <name>`` for a palace that does not exist. When the palace is
  missing we append ``(not created)``. This is the ONLY extra HTTP call and it
  fires ONLY after a successful health check (zero added cost when down/absent).
  It fails SAFE toward NOT appending the suffix: only a successful response
  that definitively lacks the palace yields ``(not created)``; any
  error/timeout/non-2xx/parse failure shows the bare name (no false negatives).
* **No ``/ui`` path** — the connected line shows ONLY the base ``host:port``;
  the ``/ui`` dashboard route does not exist in this codebase.
* **Self-contained** — this module intentionally keeps its own tiny copy of
  the URL/health/palace logic so the banner does not import the mixin-heavy
  setup handler. We deliberately do NOT refactor the other existing copies in
  ``handlers/trusty.py`` / ``memory_capture.py`` here (blast-radius limiting).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Hard cap on the health probe. Kept ≤200ms so the banner never stalls startup.
_HEALTH_TIMEOUT_S = 0.2

# Default ports when the http_addr discovery file is missing/unreadable.
# trusty-review has no http_addr discovery file of its own, so it ALWAYS falls
# back to this default port (127.0.0.1:7880) for its /health probe.
_DEFAULT_PORTS: dict[str, int] = {
    "trusty-memory": 7070,
    "trusty-search": 7878,
    "trusty-review": 7880,
}

# Display emoji per service.
_SERVICE_EMOJI: dict[str, str] = {
    "trusty-memory": "🧠",
    "trusty-search": "🔍",
    "trusty-review": "📝",
}

# Cache: { http_addr_file_path: (mtime, is_healthy) }. Keyed by the discovery
# file so a daemon restart (which rewrites http_addr) invalidates the cache.
_HEALTH_CACHE: dict[str, tuple[float, bool]] = {}

# Cache: { "<addr_file_path>::<palace>": (mtime, exists) }. SEPARATE from
# _HEALTH_CACHE (compound key) so the palace-existence result never collides
# with the health result. Keyed by the discovery file mtime + palace name so a
# daemon restart (which rewrites http_addr) invalidates it.
_PALACE_CACHE: dict[str, tuple[float, bool]] = {}


def _addr_file(service: str) -> Path:
    """Path to the daemon's ``http_addr`` discovery file."""
    return Path.home() / f".{service}" / "http_addr"


def _base_url(service: str) -> tuple[str, str]:
    """Resolve the daemon base URL.

    Returns a tuple of ``(base_url, host_port)`` where ``base_url`` is the
    ``http://host:port`` form used for probing and ``host_port`` is the bare
    ``host:port`` shown in the banner. Falls back to the default port when the
    discovery file is missing or unreadable.
    """
    try:
        addr = _addr_file(service).read_text(encoding="utf-8").strip()
        if addr:
            return f"http://{addr}", addr
    except OSError:
        pass
    host_port = f"127.0.0.1:{_DEFAULT_PORTS.get(service, 7070)}"
    return f"http://{host_port}", host_port


def _load_config() -> dict[str, Any]:
    """Best-effort load of ``~/.claude-mpm/config.yaml``. Returns ``{}`` on any failure."""
    path = Path.home() / ".claude-mpm" / "config.yaml"
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _palace_name() -> str:
    """Palace name: ``trusty_memory.palace`` config override, else cwd basename."""
    config = _load_config()
    section = config.get("trusty_memory", {})
    if isinstance(section, dict):
        configured = section.get("palace") or ""
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
    return Path.cwd().name


def _health_check(base_url: str) -> bool:
    """Probe ``{base_url}/health`` with a hard ≤200ms timeout.

    Never raises — any non-2xx, network error, or timeout is treated as
    "not healthy". urllib is imported lazily so the banner module keeps a
    minimal import surface.
    """
    import urllib.error
    import urllib.request

    url = f"{base_url}/health"
    try:
        req = urllib.request.Request(url, method="GET")  # nosec B310 - localhost
        with urllib.request.urlopen(  # nosec B310 - localhost
            req, timeout=_HEALTH_TIMEOUT_S
        ) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _cached_health_check(service: str, base_url: str) -> bool:
    """Health check cached by the http_addr discovery file's mtime.

    Repeat startups within an unchanged session are free. A daemon restart
    rewrites ``http_addr`` (changing its mtime) and invalidates the cache.
    When the discovery file is absent we use mtime ``-1.0`` as a sentinel so
    the cache still keys consistently on "no file".
    """
    addr_file = _addr_file(service)
    try:
        mtime = addr_file.stat().st_mtime
    except OSError:
        mtime = -1.0

    key = str(addr_file)
    cached = _HEALTH_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    healthy = _health_check(base_url)
    _HEALTH_CACHE[key] = (mtime, healthy)
    return healthy


def _palace_exists(base_url: str, palace: str) -> bool:
    """Whether ``palace`` exists in the daemon at ``base_url``.

    GETs ``{base_url}/api/v1/palaces`` with the SAME hard ≤200ms timeout as the
    health probe. urllib is imported lazily, matching :func:`_health_check`.

    Response shape (confirmed against the trusty-memory daemon source,
    ``GET /api/v1/palaces`` → ``Json<Vec<PalaceInfo>>``): a top-level JSON array
    of objects, each with ``id`` and ``name`` string fields. We also defensively
    accept an ``{"palaces": [...]}`` wrapper and bare-string entries (the form
    the MCP ``palace_list`` projection emits), and match the resolved palace
    name case-insensitively against BOTH ``id`` and ``name`` (the daemon derives
    ``id`` from ``name`` via ``PalaceId::new(&name)``, so either may carry the
    user-facing identifier).

    Fail-SAFE semantics (#598): never raises. Returns ``True`` on ANY
    error/timeout/non-2xx/parse failure so the caller does NOT append
    ``(not created)`` on a probe failure (avoids false negatives). Returns
    ``False`` ONLY when we got a successful, parseable response that
    definitively does not contain ``palace``.
    """
    import json
    import urllib.error
    import urllib.request

    url = f"{base_url}/api/v1/palaces"
    try:
        req = urllib.request.Request(url, method="GET")  # nosec B310 - localhost
        with urllib.request.urlopen(  # nosec B310 - localhost
            req, timeout=_HEALTH_TIMEOUT_S
        ) as resp:
            if not (200 <= resp.status < 300):
                return True  # fail-safe: unknown → do not claim "not created"
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return True  # fail-safe: probe failure → do not claim "not created"

    # Normalize to a list of palace entries.
    if isinstance(data, dict):
        entries = data.get("palaces", [])
    elif isinstance(data, list):
        entries = data
    else:
        return True  # unexpected shape → fail-safe

    target = palace.strip().lower()
    names: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            names.add(entry.strip().lower())
        elif isinstance(entry, dict):
            for field in ("name", "id"):
                value = entry.get(field)
                if isinstance(value, str):
                    names.add(value.strip().lower())
    return target in names


def _cached_palace_exists(service: str, base_url: str, palace: str) -> bool:
    """Palace-existence check cached by the http_addr file mtime + palace name.

    Uses a SEPARATE cache (compound key ``<addr_file>::<palace>``) from
    :func:`_cached_health_check` so the two results never collide. A daemon
    restart rewrites ``http_addr`` (changing its mtime) and invalidates this
    cache too. Fail-safe: see :func:`_palace_exists`.
    """
    addr_file = _addr_file(service)
    try:
        mtime = addr_file.stat().st_mtime
    except OSError:
        mtime = -1.0

    key = f"{addr_file}::{palace}"
    cached = _PALACE_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    exists = _palace_exists(base_url, palace)
    _PALACE_CACHE[key] = (mtime, exists)
    return exists


def _index_id_candidates(cwd: Path) -> list[str]:
    """Why: There is NO root_path→index lookup endpoint, so we must probe a small
    set of likely index IDs and confirm the one whose ``root_path`` matches CWD.

    What: Returns the ordered candidate index IDs for ``cwd``: an explicit
    ``trusty_search.index_id`` config override first (if set), then the cwd
    basename (e.g. ``claude-mpm``), then the path-derived ``"_".join(...)`` form
    (e.g. ``Volumes_SSD1_Projects_claude-mpm``). De-duplicated, order preserved.

    Test: ``tests/test_trusty_search_index.py::TestIndexIdCandidates`` — asserts
    the override leads, both derived forms appear, and duplicates are dropped.
    """
    candidates: list[str] = []
    config = _load_config()
    section = config.get("trusty_search", {})
    if isinstance(section, dict):
        override = section.get("index_id")
        if isinstance(override, str) and override.strip():
            candidates.append(override.strip())

    candidates.append(cwd.name)
    parts = [p for p in str(cwd).split("/") if p]
    if parts:
        candidates.append("_".join(parts))

    seen: set[str] = set()
    ordered: list[str] = []
    for cid in candidates:
        if cid and cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    return ordered


def _fetch_index_status(base_url: str, index_id: str) -> dict[str, Any] | None:
    """Why: The startup freshness check needs the daemon's own view of an index
    (chunk_count, root_path, staleness signals) without scanning git/mtimes.

    What: GETs ``{base_url}/indexes/{index_id}/status`` with a hard <=200ms
    timeout and returns the parsed dict, or ``None`` on any non-2xx / network /
    parse error (a missing index is a 404 → ``None``). urllib is imported lazily,
    matching :func:`_health_check`. Never raises.

    Test: ``tests/test_trusty_search_index.py`` — patches urlopen to return a
    status body, a 404, and an error; asserts dict / None / None respectively.
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    url = f"{base_url}/indexes/{urllib.parse.quote(index_id, safe='')}/status"
    try:
        req = urllib.request.Request(url, method="GET")  # nosec B310 - localhost
        with urllib.request.urlopen(  # nosec B310 - localhost
            req, timeout=_HEALTH_TIMEOUT_S
        ) as resp:
            if not (200 <= resp.status < 300):
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def get_trusty_search_index_status(cwd: Path | None = None) -> dict[str, Any] | None:
    """Why: At startup we want the daemon's own status for THIS project's index so
    we can decide whether to fire a background reindex — without git/mtime
    scanning. Index IDs are not derivable from root_path via any endpoint, so we
    probe candidates and confirm by matching ``root_path``.

    What: Resolves ``cwd`` (defaults to ``Path.cwd()``), probes each candidate ID
    from :func:`_index_id_candidates`, and returns the FIRST status dict whose
    ``root_path`` resolves to the same path as ``cwd``. Reuses ``_base_url`` and
    the <=200ms probe. Returns ``None`` on any failure or when no candidate
    matches (fail-safe — the caller then treats the index as missing). Never
    raises and never blocks longer than the bounded probes.

    Test: ``tests/test_trusty_search_index.py`` — fresh index returns the dict;
    a candidate whose root_path differs is skipped; all-miss / daemon-error
    returns ``None``.
    """
    try:
        resolved = (cwd or Path.cwd()).resolve()
    except (OSError, RuntimeError):
        return None

    base_url, _host_port = _base_url("trusty-search")
    for index_id in _index_id_candidates(resolved):
        status = _fetch_index_status(base_url, index_id)
        if not status:
            continue
        root = status.get("root_path")
        if not isinstance(root, str):
            continue
        try:
            if Path(root).resolve() == resolved:
                return status
        except (OSError, RuntimeError):
            continue
    return None


def is_index_missing_or_empty(status: dict[str, Any] | None) -> bool:
    """Why: "Missing or empty" is the primary trigger for a background reindex.

    What: Returns ``True`` when ``status`` is ``None`` (no matching index found)
    or when its ``chunk_count`` is absent / not a positive int (empty index).

    Test: ``tests/test_trusty_search_index.py`` — None → True, chunk_count 0 →
    True, missing key → True, chunk_count 65225 → False.
    """
    if not status:
        return True
    chunk_count = status.get("chunk_count")
    return not (isinstance(chunk_count, int) and chunk_count > 0)


def is_index_stale(status: dict[str, Any] | None) -> bool:
    """Why: Beyond "missing/empty", the daemon exposes its OWN staleness signals;
    we lean on those rather than scanning git HEAD / file mtimes ourselves.

    What: Returns ``True`` when a non-empty index nonetheless shows a
    daemon-reported problem: a non-null ``last_walk_error`` (the last index walk
    failed) OR a ``status`` field that is not a healthy/terminal value
    (anything other than ``"ready"``/``"idle"``/``"complete"`` — e.g. ``"error"``
    or ``"failed"``). Returns ``False`` for a healthy populated index. Empty
    indexes are handled by :func:`is_index_missing_or_empty`, so this returns
    ``False`` for them to avoid double-counting.

    Test: ``tests/test_trusty_search_index.py`` — last_walk_error set → True,
    status "error" → True, status "ready" + no error → False, empty index →
    False (deferred to missing/empty).
    """
    if is_index_missing_or_empty(status):
        return False
    assert status is not None  # narrowed by the guard above
    if status.get("last_walk_error"):
        return True
    state = status.get("status")
    if isinstance(state, str) and state.lower() not in {"ready", "idle", "complete"}:
        return True
    return False


def trigger_trusty_search_reindex(index_id: str, cwd: Path | None = None) -> bool:
    """Why: When the project index is missing/empty/stale we must refresh it
    WITHOUT blocking startup. The daemon already has a background reindex queue
    (``background_reindex_queue_depth``); we just enqueue and return.

    What: Fires a fire-and-forget ``POST {base}/indexes/{index_id}/reindex`` in a
    detached daemon thread so this call returns immediately (the daemon queues
    the work and responds ``{"queued": true}``). Returns ``True`` if the request
    was dispatched, ``False`` on dispatch failure. NEVER raises into the startup
    path — all errors inside the thread are swallowed.

    Test: ``tests/test_trusty_search_index.py`` — asserts a thread is started
    (non-blocking) and the POST URL/method are correct; an error inside the
    thread does not propagate.
    """
    import threading
    import urllib.parse
    import urllib.request

    base_url, _host_port = _base_url("trusty-search")
    url = f"{base_url}/indexes/{urllib.parse.quote(index_id, safe='')}/reindex"

    def _post() -> None:
        try:
            req = urllib.request.Request(  # nosec B310 - localhost
                url, method="POST", data=b""
            )
            with urllib.request.urlopen(  # nosec B310 - localhost
                req, timeout=_HEALTH_TIMEOUT_S
            ):
                pass
        except Exception:
            pass  # fire-and-forget: the daemon may already be reindexing

    try:
        threading.Thread(target=_post, daemon=True).start()
        return True
    except Exception:
        return False


def _mcp_servers_from_file(path: Path) -> frozenset[str]:
    """Why: Centralise the read-one-mcp-json logic so both the project and user
    paths share the same parse/guard/error-handling without duplication.

    What: Reads ``path`` as JSON, returns the set of keys in ``mcpServers``.
    Returns an empty frozenset on missing file, unreadable file, malformed JSON,
    or any other error so callers can safely union-check across multiple paths.

    Test: ``tests/test_trusty_status.py::TestMcpConfigRead`` — covers missing,
    malformed, and valid inputs for both the project and user paths.
    """
    import json

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return frozenset()
    if not isinstance(data, dict):
        return frozenset()
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return frozenset()
    return frozenset(servers.keys())


def _is_stdio_configured(service: str) -> bool:
    """Whether ``service`` is configured as a stdio-type MCP server in any
    ``.mcp.json``.

    Why: For stdio-type MCP servers, Claude Code manages the process — the
    HTTP health check is informational only. A stdio-configured service that
    fails the HTTP probe is still accessible via stdio and should NOT be
    shown as "not running".

    What: Reads both the project-level and user-level ``.mcp.json`` and
    returns ``True`` if ``service`` appears with ``"type": "stdio"`` in
    either. Returns ``False`` on any I/O / parse error (fail-safe).

    Test: ``tests/test_trusty_status_indicators.py`` — see
    ``TestStdioConfiguredDetection``.
    """
    import json

    for path in (
        Path.cwd() / ".mcp.json",
        Path.home() / ".claude" / ".mcp.json",
    ):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            servers = data.get("mcpServers", {})
            entry = servers.get(service)
            if isinstance(entry, dict) and entry.get("type") == "stdio":
                return True
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            pass
    return False


def _is_configured_in_mcp(service: str) -> bool:
    """Whether ``service`` appears in EITHER the project or user-level MCP config.

    Why: trusty-review (and other tools) may be registered at user scope
    (``~/.claude/.mcp.json``) rather than in the project ``.mcp.json``.
    Previously only the CWD file was checked, so user-level registrations were
    silently ignored and the tool showed as "absent" even when present — blocking
    ``/mpm-review`` and ``mcp__trusty-review__*`` gating.

    What: Returns ``True`` if ``service`` appears in ``mcpServers`` of EITHER

    1. ``Path.cwd() / ".mcp.json"`` (project-level, takes precedence), OR
    2. ``Path.home() / ".claude" / ".mcp.json"`` (user-level fallback).

    This mirrors the project-takes-precedence-then-user-fallback semantics
    already used in ``interactive_session.py::_load_mcp_config`` (~line 1062).
    Best-effort: returns ``False`` on missing file, malformed JSON, or any other
    error — consistent with the previous single-file behaviour.

    Test: ``tests/test_trusty_status.py::TestMcpConfigRead`` — covers
    user-only, project-only, both, and neither configurations.
    """
    project_servers = _mcp_servers_from_file(Path.cwd() / ".mcp.json")
    if service in project_servers:
        return True
    user_servers = _mcp_servers_from_file(Path.home() / ".claude" / ".mcp.json")
    return service in user_servers


def _is_present(service: str) -> bool:
    """Whether the user has opted in to ``service`` (latency-free, pure filesystem).

    The service is considered present / opted-in if ANY of these signals holds:

    1. ``service`` appears in the CWD ``.mcp.json`` ``mcpServers`` map
       (project-level MCP config), OR
    2. ``service`` appears in ``~/.claude/.mcp.json`` ``mcpServers`` map
       (user-level MCP config — where tools like ``trusty-review`` are
       registered for all projects), OR
    3. the per-user ``~/.trusty-<service>/http_addr`` discovery file exists
       (proof the daemon has run for this user).

    All signals are pure filesystem reads — no subprocess, no ``shutil.which``.
    This intentionally does NOT depend on the launched binary's name, which may
    be a bridge/wrapper (e.g. ``trusty-memory-mcp-bridge``) that does not match
    the service key.
    """
    if _is_configured_in_mcp(service):
        return True
    try:
        return _addr_file(service).exists()
    except OSError:
        return False


def _start_hint(service: str) -> str:
    """The ``(start: ...)`` hint shown when a service is not running."""
    if service == "trusty-memory":
        return "(start: trusty-memory ...)"
    if service == "trusty-analyze":
        return "(start: trusty-analyze serve)"
    if service == "trusty-review":
        return "(start: trusty-review serve)"
    return "(start: trusty-search serve)"


def get_trusty_status(service: str) -> tuple[str, str]:
    """Return ``(state, display_line)`` for a trusty daemon.

    Args:
        service: ``"trusty-memory"`` or ``"trusty-search"``.

    Returns:
        Tuple of ``(state, display_line)``:

        * ``("absent", "")`` — not opted in (no ``.mcp.json`` entry AND no
          ``http_addr`` discovery file); render NOTHING. (The empty line lets
          the caller suppress this service with a truthiness guard.)
        * ``("on", "🧠 trusty-memory: on   palace: <name>   host:port")`` —
          present and ``/health`` returned 2xx. Palace name only for
          ``trusty-memory``; the name gains a ``(not created)`` suffix when a
          successful ``GET /api/v1/palaces`` definitively shows the palace does
          not exist (#598 option 1). The connected form shows ONLY
          ``host:port`` — never a ``/ui`` path.
        * ``("configured", "... not running  (start: ...)")`` — present,
          ``/health`` failed, and the service is in the project OR user-level
          ``.mcp.json``.
        * ``("not_running", "... not running  (start: ...)")`` — present (via an
          ``http_addr`` discovery file), ``/health`` failed, NOT in any
          ``.mcp.json``. (Presence means the user opted in, so we still show
          ``not running`` rather than a bare ``off`` line; ``.mcp.json``
          membership only tweaks the hint text.)

    Presence is detected by :func:`_is_present` — a latency-free filesystem
    check that never depends on the launched binary's name (bridges/wrappers
    such as ``trusty-memory-mcp-bridge`` no longer suppress a healthy daemon).

    Never raises — every failure path falls back to a safe value.
    """
    try:
        # Cold-path short-circuit: not opted in → render nothing.
        if not _is_present(service):
            return ("absent", "")

        emoji = _SERVICE_EMOJI.get(service, "")
        base_url, host_port = _base_url(service)

        is_healthy = _cached_health_check(service, base_url)
        is_stdio = _is_stdio_configured(service)

        # stdio-configured services: HTTP health failure ≠ not running.
        # Claude Code manages the stdio process — if configured, assume connected.
        if is_healthy or is_stdio:
            if service == "trusty-memory":
                palace = _palace_name()
                if is_healthy:
                    # #598 option 1: /health only proves the daemon is up — verify
                    # the palace actually exists before claiming it. Fail-safe:
                    # only append "(not created)" on a definitive negative.
                    if _cached_palace_exists(service, base_url, palace):
                        palace_display = f"palace: {palace}"
                    else:
                        palace_display = f"palace: {palace} (not created)"
                    line = f"{emoji} {service}: on   {palace_display}   {host_port}"
                else:
                    # stdio connected but HTTP unreachable (port informational only)
                    line = f"{emoji} {service}: on (stdio)   palace: {palace}"
            elif is_healthy:
                line = f"{emoji} {service}: on   {host_port}"
            else:
                line = f"{emoji} {service}: on (stdio)"
            return ("on", line)

        # NOT stdio-configured AND health check failed → truly not running.
        hint = _start_hint(service)
        line = f"{emoji} {service}: not running  {hint}"
        state = "configured" if _is_configured_in_mcp(service) else "not_running"
        return (state, line)
    except Exception:
        # Fail-safe: never break the banner over a status probe.
        return ("absent", "")


# Services whose per-session capability is reported to the PM prompt. Order is
# stable so the injected table renders deterministically.
_CAPABILITY_SERVICES: tuple[str, ...] = (
    "trusty-memory",
    "trusty-search",
    "trusty-analyze",
    "trusty-review",
)


def get_trusty_capabilities() -> dict[str, str]:
    """Why: The PM prompt instructs unconditional use of trusty-* tools, but
    those daemons may be absent/down this session — wasting tool calls/tokens.
    This is the single source of truth for per-session tool availability fed
    into the prompt so the PM can degrade gracefully (skip + inform).

    What: Returns ``{service: state}`` for ``trusty-memory``, ``trusty-search``,
    ``trusty-analyze`` and ``trusty-review`` where ``state`` is one of
    ``"on"`` / ``"configured"`` / ``"not_running"`` / ``"absent"``, computed
    via :func:`get_trusty_status` (filesystem presence + cached ≤200ms
    ``/health`` probes). Cheap and cached; ``trusty-review`` has no
    ``http_addr`` file so it probes ``127.0.0.1:7880/health``. Per service it
    is wrapped in try/except so a single bad probe never poisons the map, and
    the whole call NEVER raises or blocks startup (any top-level failure yields
    an all-``"absent"`` map).

    Test: ``tests/test_trusty_status.py`` — verifies correct states for
    all-on / mixed / all-absent combinations and that a probe that raises is
    reported as ``"absent"`` rather than propagating.
    """
    capabilities: dict[str, str] = {}
    for service in _CAPABILITY_SERVICES:
        try:
            state, _line = get_trusty_status(service)
        except Exception:
            state = "absent"
        capabilities[service] = state
    return capabilities
