"""Auto-detect running trusty-search and trusty-memory daemons.

When either daemon is detected (binary on PATH + HTTP health probe succeeds),
inject the corresponding MCP server entry into the project's ``.mcp.json`` so
users don't have to run ``claude-mpm setup trusty-*`` manually.

This migration is registered as ``run_always`` in :mod:`registry` because
daemon state can change between invocations — a user might install/start
``trusty-search`` after the first ``claude-mpm`` run, and we want their next
session to pick it up automatically.

Design constraints:

* **Idempotent**: if the ``.mcp.json`` entry already exists, do nothing.
* **Silent on absence**: missing binary or unhealthy daemon = no-op, no logs.
* **Cheap**: ``shutil.which`` + 2s HTTP probe per daemon; skipped entirely
  when the binary isn't installed.
* **Safe writes**: uses :func:`_mcp_config_transaction` so a write failure
  rolls ``.mcp.json`` back to its prior state.

Address discovery:

Both ``trusty-search`` and ``trusty-memory`` use OS-chosen dynamic ports
written to ``~/.trusty-<svc>/http_addr`` (format: ``host:port`` on a single
line). Hardcoded ports (7878 / 7070) would cause the autodetect to silently
fail whenever the daemons picked different ports. We mirror the discovery
logic used by the ``claude-mpm setup trusty-*`` handlers: read the addr file
when present, fall back to the legacy port only when the file is missing or
unreadable.
"""

from __future__ import annotations

import json
import logging
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Service descriptors. Kept inline (not a dataclass) to avoid pulling in
# extra modules during the startup-hot migration path.
#
# ``addr_file`` points at the daemon's discovery file (single-line
# ``host:port``). ``fallback_addr`` is the legacy hardcoded address used only
# when the discovery file is missing/unreadable.
_SERVICES: tuple[dict[str, Any], ...] = (
    {
        "name": "trusty-search",
        "binary": "trusty-search",
        "addr_file": Path.home() / ".trusty-search" / "http_addr",
        "fallback_addr": "127.0.0.1:7878",
        "mcp_entry": {
            "type": "stdio",
            "command": "trusty-search",
            "args": ["serve"],
        },
    },
    {
        "name": "trusty-memory",
        "binary": "trusty-memory",
        "addr_file": Path.home() / ".trusty-memory" / "http_addr",
        "fallback_addr": "127.0.0.1:7070",
        "mcp_entry": {
            "type": "stdio",
            "command": "trusty-memory",
            "args": ["serve", "--mcp"],
        },
    },
)


def _resolve_base_url(addr_file: Path, fallback_addr: str) -> str:
    """Return the daemon's base URL ``http://host:port``.

    Reads ``addr_file`` (canonical dynamic-port discovery file) when present;
    falls back to ``fallback_addr`` otherwise. Mirrors the logic in
    :meth:`TrustyMixin._trusty_search_base_url`.
    """
    try:
        addr = addr_file.read_text(encoding="utf-8").strip()
        if addr:
            return f"http://{addr}"
    except OSError:
        pass
    return f"http://{fallback_addr}"


def _http_health_check(url: str, timeout: float = 2.0) -> bool:
    """Return True iff ``url`` responds 2xx within ``timeout`` seconds.

    Uses stdlib urllib to avoid adding dependencies. Connection refused,
    timeouts, and unexpected status codes all map to ``False``.
    """
    try:
        req = urllib.request.Request(url, method="GET")  # nosec B310 - localhost
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return 200 <= int(resp.status) < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _load_mcp_config(mcp_path: Path) -> dict[str, Any]:
    """Load ``.mcp.json`` or return an empty config skeleton.

    A malformed file returns an empty skeleton so the autodetect path can
    still inject entries without nuking unrelated state (the broader project
    write happens transactionally below).
    """
    if not mcp_path.exists():
        return {"mcpServers": {}}
    try:
        with open(mcp_path, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"mcpServers": {}}
            return data
    except (json.JSONDecodeError, OSError):
        return {"mcpServers": {}}


def _save_mcp_config(mcp_path: Path, config: dict[str, Any]) -> None:
    """Write ``.mcp.json`` with a trailing newline (matches setup handler)."""
    with open(mcp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def run_migration(project_dir: Path | None = None) -> bool:
    """Detect running trusty daemons and inject MCP entries.

    Args:
        project_dir: Directory containing ``.mcp.json`` (defaults to CWD).

    Returns:
        True if any change was made, False if everything was already
        configured or no daemons were detected. Never raises on the absence
        path — only propagates exceptions from disk writes.
    """
    project_dir = project_dir or Path.cwd()
    mcp_path = project_dir / ".mcp.json"

    # Determine which services are detectable BEFORE touching .mcp.json so a
    # cold path (no daemons running) doesn't open the file at all.
    detected: list[dict[str, Any]] = []
    for svc in _SERVICES:
        if shutil.which(svc["binary"]) is None:
            continue
        base_url = _resolve_base_url(svc["addr_file"], svc["fallback_addr"])
        if not _http_health_check(f"{base_url}/health"):
            continue
        detected.append(svc)

    if not detected:
        return False

    # Defer the import to avoid a circular dependency at module-load time
    # (mcp_config lives under cli.commands.setup, which itself may import
    # migration code indirectly during CLI bootstrap).
    from ..cli.commands.setup.mcp_config import _mcp_config_transaction

    config = _load_mcp_config(mcp_path)
    servers = config.setdefault("mcpServers", {})

    to_write: list[dict[str, Any]] = [
        svc for svc in detected if svc["name"] not in servers
    ]

    if not to_write:
        return False

    try:
        with _mcp_config_transaction(project_dir):
            for svc in to_write:
                servers[svc["name"]] = svc["mcp_entry"]
                logger.info(
                    "Auto-configured %s MCP server (daemon detected via %s)",
                    svc["name"],
                    svc["addr_file"],
                )
            _save_mcp_config(mcp_path, config)
    except Exception as exc:
        # Transaction context will roll back; log and report no-op upward.
        logger.warning("trusty autodetect failed to write .mcp.json: %s", exc)
        return False

    return True
