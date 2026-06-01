"""Trusty daemon connection status for the startup banner (GitHub #598).

Self-contained, dependency-light status probe for the ``trusty-memory`` and
``trusty-search`` daemons. The startup banner imports :func:`get_trusty_status`
to render a one-line connection indicator per service.

Design (scoped per #598)
-------------------------
* **Cold-path short-circuit** — if the service binary is NOT on ``PATH``
  (``shutil.which``), we render NOTHING for that service. Only opted-in users
  who installed the binary ever see the indicator, so there is zero HTTP cost
  for everyone else and no banner clutter.
* **Bounded, cached health probe** — when the binary IS present we probe
  ``{base}/health`` with a hard ≤200ms timeout. The probe result is cached
  keyed by the ``http_addr`` discovery file's mtime (mirroring how
  ``_get_ztk_status`` caches by binary mtime), so repeat startups within an
  unchanged session are free. The probe never raises — it fails safe to
  "not running".
* **No ``/ui`` path** — the connected line shows ONLY the base ``host:port``;
  the ``/ui`` dashboard route does not exist in this codebase.
* **Self-contained** — this module intentionally keeps its own tiny copy of
  the URL/health/palace logic so the banner does not import the mixin-heavy
  setup handler. We deliberately do NOT refactor the other existing copies in
  ``handlers/trusty.py`` / ``memory_capture.py`` here (blast-radius limiting).
"""

from __future__ import annotations

import shutil
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

        * ``("absent", "")`` — binary not on PATH; render NOTHING. (The empty
          line lets the caller suppress this service with a truthiness guard.)
        * ``("on", "🧠 trusty-memory: on   palace: <name>   host:port")`` —
          binary present and ``/health`` returned 2xx. Palace name only for
          ``trusty-memory``. The connected form shows ONLY ``host:port`` —
          never a ``/ui`` path.
        * ``("configured", "... not running  (start: ...)")`` — binary present,
          ``/health`` failed, and the service is in CWD ``.mcp.json``.
        * ``("not_running", "... not running  (start: ...)")`` — binary present,
          ``/health`` failed, NOT in ``.mcp.json``. (Binary-on-PATH means the
          user opted in, so we still show ``not running`` rather than a bare
          ``off`` line; ``.mcp.json`` only tweaks the hint text.)

    Never raises — every failure path falls back to a safe value.
    """
    try:
        # Cold-path short-circuit: not installed → render nothing.
        if shutil.which(service) is None:
            return ("absent", "")

        emoji = _SERVICE_EMOJI.get(service, "")
        base_url, host_port = _base_url(service)

        if _cached_health_check(service, base_url):
            if service == "trusty-memory":
                line = f"{emoji} {service}: on   palace: {_palace_name()}   {host_port}"
            else:
                line = f"{emoji} {service}: on   {host_port}"
            return ("on", line)

        # /health failed but binary is installed (opted in) → not running.
        hint = _start_hint(service)
        line = f"{emoji} {service}: not running  {hint}"
        state = "configured" if _is_configured_in_mcp(service) else "not_running"
        return (state, line)
    except Exception:
        # Fail-safe: never break the banner over a status probe.
        return ("absent", "")
