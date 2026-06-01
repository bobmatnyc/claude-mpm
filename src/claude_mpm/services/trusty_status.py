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
_DEFAULT_PORTS: dict[str, int] = {
    "trusty-memory": 7070,
    "trusty-search": 7878,
}

# Display emoji per service.
_SERVICE_EMOJI: dict[str, str] = {
    "trusty-memory": "🧠",
    "trusty-search": "🔍",
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


def _is_configured_in_mcp(service: str) -> bool:
    """Whether ``service`` appears in the CWD ``.mcp.json`` ``mcpServers`` map.

    Best-effort: returns ``False`` on any error (missing file, malformed JSON).
    """
    import json

    mcp_path = Path.cwd() / ".mcp.json"
    try:
        with mcp_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return False
    return service in servers


def _is_present(service: str) -> bool:
    """Whether the user has opted in to ``service`` (latency-free, pure filesystem).

    The service is considered present / opted-in if EITHER signal holds:

    1. ``service`` appears in the CWD ``.mcp.json`` ``mcpServers`` map, OR
    2. the per-user ``~/.trusty-<service>/http_addr`` discovery file exists
       (proof the daemon has run for this user).

    Both are pure filesystem reads — no subprocess, no ``shutil.which``. This
    intentionally does NOT depend on the launched binary's name, which may be a
    bridge/wrapper (e.g. ``trusty-memory-mcp-bridge``) that does not match the
    service key.
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
          ``/health`` failed, and the service is in CWD ``.mcp.json``.
        * ``("not_running", "... not running  (start: ...)")`` — present (via an
          ``http_addr`` discovery file), ``/health`` failed, NOT in
          ``.mcp.json``. (Presence means the user opted in, so we still show
          ``not running`` rather than a bare ``off`` line; ``.mcp.json`` only
          tweaks the hint text.)

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

        if _cached_health_check(service, base_url):
            if service == "trusty-memory":
                palace = _palace_name()
                # #598 option 1: /health only proves the daemon is up — verify
                # the palace actually exists before claiming it. Fail-safe:
                # only append "(not created)" on a definitive negative.
                if _cached_palace_exists(service, base_url, palace):
                    palace_display = f"palace: {palace}"
                else:
                    palace_display = f"palace: {palace} (not created)"
                line = f"{emoji} {service}: on   {palace_display}   {host_port}"
            else:
                line = f"{emoji} {service}: on   {host_port}"
            return ("on", line)

        # /health failed but the service is present (opted in) → not running.
        hint = _start_hint(service)
        line = f"{emoji} {service}: not running  {hint}"
        state = "configured" if _is_configured_in_mcp(service) else "not_running"
        return (state, line)
    except Exception:
        # Fail-safe: never break the banner over a status probe.
        return ("absent", "")
