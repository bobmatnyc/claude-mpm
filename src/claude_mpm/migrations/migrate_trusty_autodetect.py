"""Auto-detect running trusty-search, trusty-memory, and trusty-review services.

When a service is detected (binary on PATH + detection probe succeeds),
inject the corresponding MCP server entry into the project's ``.mcp.json`` so
users don't have to run ``claude-mpm setup trusty-*`` manually.

This migration is registered as ``run_always`` in :mod:`registry` because
daemon state can change between invocations — a user might install/start
``trusty-search`` after the first ``claude-mpm`` run, and we want their next
session to pick it up automatically.

Design constraints:

* **Idempotent**: if the ``.mcp.json`` entry already exists, do nothing.
* **Silent on absence**: missing binary or unhealthy daemon = no-op, no logs.
* **Cheap**: ``shutil.which`` + detection probe per service; skipped entirely
  when the binary isn't installed.
* **Safe writes**: uses :func:`_mcp_config_transaction` so a write failure
  rolls ``.mcp.json`` back to its prior state.

Detection modes (``"detect"`` key per service descriptor):

* ``"http"`` (default) — existing behavior for persistent HTTP daemons:
  resolve ``addr_file`` / ``fallback_addr`` then probe ``/health``.
  Used by ``trusty-search`` and ``trusty-memory``.
* ``"jsonrpc"`` — spawn the stdio server, send a JSON-RPC ``initialize``
  request, accept as detected if a valid response arrives within the timeout.
  Used by ``trusty-review`` (review-on-demand, no persistent HTTP daemon).

Address discovery (http-mode only):

Both ``trusty-search`` and ``trusty-memory`` use OS-chosen dynamic ports
written to ``~/.trusty-<svc>/http_addr`` (format: ``host:port`` on a single
line). Hardcoded ports (7878 / 7070) would cause the autodetect to silently
fail whenever the daemons picked different ports. We mirror the discovery
logic used by the ``claude-mpm setup trusty-*`` handlers: read the addr file
when present, fall back to the legacy port only when the file is missing or
unreadable.

References
----------
SPEC-INTEGRATIONS-03~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-03~1
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Env-var kill-switch for the entire auto-link behavior. Mirrors the
# ``CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS`` precedent. Any truthy value
# disables palace creation, hook injection, AND the .mcp.json write.
_OPT_OUT_ENV = "CLAUDE_MPM_NO_TRUSTY_AUTO_LINK"
_TRUTHY = {"1", "true", "yes", "on"}


# Service descriptors. Kept inline (not a dataclass) to avoid pulling in
# extra modules during the startup-hot migration path.
#
# ``detect`` controls the detection strategy:
#   ``"http"``     — binary on PATH + HTTP /health probe (default; used by
#                    persistent daemon-mode servers with an http_addr file).
#   ``"jsonrpc"``  — binary on PATH + JSON-RPC initialize handshake via
#                    ``probe_mcp_stdio`` (used by review-on-demand stdio
#                    servers that have no persistent HTTP daemon).
#
# ``addr_file`` / ``fallback_addr`` are only used when ``detect == "http"``.
_SERVICES: tuple[dict[str, Any], ...] = (
    {
        "name": "trusty-search",
        "binary": "trusty-search",
        "detect": "http",
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
        "detect": "http",
        "addr_file": Path.home() / ".trusty-memory" / "http_addr",
        "fallback_addr": "127.0.0.1:7070",
        "mcp_entry": {
            "type": "stdio",
            "command": "trusty-memory-mcp-bridge",
            "args": [],
        },
    },
    # trusty-review is review-on-demand: it gets an .mcp.json entry so the
    # ``mcp__trusty-review__*`` tools and ``/mpm-review`` are wired, but it
    # has NO per-project palace and NO capture/index hooks (it is not in
    # ``_TRUSTY_HOOK_SPECS``, so ``inject_trusty_hooks`` is a no-op for it).
    #
    # Detection uses ``"jsonrpc"`` mode: we spawn ``trusty-review serve --stdio``
    # and verify it responds to a JSON-RPC initialize handshake.  There is no
    # persistent HTTP daemon, so an HTTP /health probe would always fail.
    #
    # The ``env`` block carries ONLY non-secret config: ``TRUSTY_REVIEW_AUTH_MODE=cli``
    # lets a local GitHub PAT work in serve mode (learned from testing). AWS
    # credentials and ``GITHUB_TOKEN`` are deliberately NOT set here — they are
    # inherited from the Claude Code process environment. ``TRUSTY_SEARCH_INDEX``
    # is intentionally omitted: the default ``main`` may not exist for a given
    # project, so the user sets it explicitly when authoritative review is needed
    # (documented in ``/mpm-review``).
    {
        "name": "trusty-review",
        "binary": "trusty-review",
        "detect": "jsonrpc",
        "mcp_entry": {
            "type": "stdio",
            "command": "trusty-review",
            "args": ["serve", "--stdio"],
            "env": {
                "TRUSTY_REVIEW_AUTH_MODE": "cli",
            },
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


def _probe_mcp_stdio(command: list[str], *, timeout: float = 4.0) -> bool:
    """Thin wrapper around :func:`~claude_mpm.mcp.probe.probe_mcp_stdio`.

    Defers the import so the migration module stays cheap to load when the
    probe isn't needed (i.e. when ``trusty-review`` binary is absent).
    Any import error is swallowed and treated as a failed probe — this must
    never crash startup.
    """
    try:
        from ..mcp.probe import probe_mcp_stdio

        return probe_mcp_stdio(command, timeout=timeout)
    except Exception as exc:
        logger.debug("_probe_mcp_stdio: import or probe error: %s", exc)
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


def _auto_link_disabled(project_dir: Path) -> bool:
    """Return True iff auto-link is opted out (env var or project config).

    Why: users must be able to fully disable trusty auto-linkage — both via a
    quick env-var kill-switch and via a durable project config flag.
    What: returns True if ``CLAUDE_MPM_NO_TRUSTY_AUTO_LINK`` is truthy, or if
    ``.claude-mpm/configuration.yaml`` sets ``trusty.auto_link: false``. The
    config is read best-effort (any error → treated as not-disabled) so a
    malformed file never blocks startup.
    Test: ``tests/migrations/test_trusty_autodetect.py`` covers both paths.
    """
    if os.environ.get(_OPT_OUT_ENV, "").strip().lower() in _TRUTHY:
        return True

    config = _load_project_config(project_dir)
    trusty = config.get("trusty")
    if isinstance(trusty, dict) and trusty.get("auto_link") is False:
        return True
    return False


def _load_project_config(project_dir: Path) -> dict[str, Any]:
    """Load ``.claude-mpm/configuration.yaml`` best-effort.

    Why: the migration runs on the startup hot path and must not depend on the
    full ``UnifiedConfig`` machinery (which loads env, merges sources, etc.).
    What: parses the project's ``configuration.yaml`` and returns the resulting
    dict, or ``{}`` on any error (missing file, parse failure, non-dict root).
    Test: ``tests/migrations/test_trusty_autodetect.py::test_opt_out_via_config``.
    """
    config_path = project_dir / ".claude-mpm" / "configuration.yaml"
    try:
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ensure_palace(
    base_url: str, palace_name: str, project_dir: Path | None = None
) -> None:
    """Idempotently ensure a memory palace named ``palace_name`` exists.

    Why: without a per-project palace, every trusty-memory MCP call silently
    no-ops — registering the MCP server in ``.mcp.json`` is not enough on its
    own. Mirrors the manual ``claude-mpm setup trusty-memory`` behavior so the
    startup path reaches the same end state.
    What: ``GET {base_url}/api/v1/palaces`` (case-insensitive existence check);
    if absent, ``POST`` ``{"name": palace_name, "description": ..., "cwd":
    str(project_dir)}``. The ``cwd`` field is required by trusty-memory
    0.14+ palace-name enforcement (the daemon validates that the name matches
    the project slug derived from the cwd). All failures are warning-level
    and swallowed — never raises.
    Test: ``tests/migrations/test_trusty_autodetect.py`` (created-when-absent,
    skip-when-present, non-fatal-on-failure).
    """
    palaces_url = f"{base_url}/api/v1/palaces"

    # 1. Existence check (case-insensitive). On any error, fall through to the
    #    POST attempt — a 409/duplicate from the daemon is also non-fatal.
    palace_found = False
    try:
        req = urllib.request.Request(palaces_url, method="GET")  # nosec B310
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            palace_list = data if isinstance(data, list) else data.get("palaces", [])
            for p in palace_list:
                if (
                    isinstance(p, dict)
                    and p.get("name", "").lower() == palace_name.lower()
                ):
                    palace_found = True
                    break
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "trusty autodetect could not list palaces (%s); attempting create", exc
        )

    if palace_found:
        logger.info("trusty-memory palace already exists: %s", palace_name)
        return

    # 2. Create the palace.
    # Include ``cwd`` so trusty-memory's palace-name enforcement can derive the
    # expected project slug from the caller's project directory rather than the
    # daemon's own process cwd (which is typically ``~`` or ``/``).
    payload: dict[str, str] = {
        "name": palace_name,
        "description": "Claude Code session memory for project",
    }
    if project_dir is not None:
        payload["cwd"] = str(project_dir)
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # nosec B310
            palaces_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            if 200 <= int(resp.status) < 300:
                logger.info("trusty-memory palace created: %s", palace_name)
            else:
                logger.warning(
                    "trusty-memory palace creation returned HTTP %s", resp.status
                )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning(
            "trusty autodetect could not create palace '%s': %s", palace_name, exc
        )


def run_migration(project_dir: Path | None = None) -> bool:
    """Detect running trusty daemons and auto-link them to this project.

    Beyond the original ``.mcp.json`` wiring, this also (idempotently):

    * creates the per-project memory palace when ``trusty-memory`` is healthy,
    * injects the trusty capture/index hooks into Claude Code settings.

    Args:
        project_dir: Directory containing ``.mcp.json`` (defaults to CWD).

    Returns:
        True if any change was made (``.mcp.json`` write or hook injection),
        False if everything was already configured, no daemons were detected,
        or auto-link is opted out. Never raises on the absence/opt-out path —
        only propagates exceptions from disk writes.

    :spec: SPEC-INTEGRATIONS-03~1
    """
    project_dir = project_dir or Path.cwd()
    mcp_path = project_dir / ".mcp.json"

    # Opt-out short-circuit: env-var kill-switch or project config flag.
    if _auto_link_disabled(project_dir):
        logger.debug("trusty auto-link disabled via env var or project config")
        return False

    # Determine which services are detectable BEFORE touching .mcp.json so a
    # cold path (no daemons running) doesn't open the file at all.
    detected: list[dict[str, Any]] = []
    for svc in _SERVICES:
        if shutil.which(svc["binary"]) is None:
            continue

        detect_mode = svc.get("detect", "http")

        if detect_mode == "jsonrpc":
            # On-demand stdio server: probe via JSON-RPC initialize handshake.
            # The command+args come from the service's mcp_entry so we always
            # probe exactly the binary that will be wired into .mcp.json.
            entry = svc["mcp_entry"]
            probe_cmd = [entry["command"], *entry.get("args", [])]
            if not _probe_mcp_stdio(probe_cmd):
                continue
            detected.append(dict(svc))
        else:
            # Persistent HTTP daemon: resolve address then probe /health.
            base_url = _resolve_base_url(svc["addr_file"], svc["fallback_addr"])
            if not _http_health_check(f"{base_url}/health"):
                continue
            # Stash the resolved base URL so palace creation reuses it.
            detected.append({**svc, "base_url": base_url})

    if not detected:
        return False

    changed = False

    # 1. Wire .mcp.json entries for any not-yet-registered detected services.
    #    Deferred import avoids a circular dependency at module-load time
    #    (mcp_config lives under cli.commands.setup, which itself may import
    #    migration code indirectly during CLI bootstrap).
    from ..cli.commands.setup.mcp_config import _mcp_config_transaction

    config = _load_mcp_config(mcp_path)
    servers = config.setdefault("mcpServers", {})
    to_write: list[dict[str, Any]] = [
        svc for svc in detected if svc["name"] not in servers
    ]
    if to_write:
        try:
            with _mcp_config_transaction(project_dir):
                for svc in to_write:
                    servers[svc["name"]] = svc["mcp_entry"]
                    detect_via = (
                        svc["addr_file"]
                        if svc.get("detect", "http") == "http"
                        else "jsonrpc-handshake"
                    )
                    logger.info(
                        "Auto-configured %s MCP server (daemon detected via %s)",
                        svc["name"],
                        detect_via,
                    )
                _save_mcp_config(mcp_path, config)
            changed = True
        except Exception as exc:
            # Transaction context will roll back; log and continue (palace +
            # hooks are still worth attempting on subsequent detected services).
            logger.warning("trusty autodetect failed to write .mcp.json: %s", exc)

    # 2. Ensure the per-project palace exists for a healthy trusty-memory. This
    #    runs every startup (idempotent GET/POST) regardless of whether the
    #    .mcp.json entry already existed — registering the MCP server is not
    #    enough; the palace must exist for memory calls to persist anything.
    for svc in detected:
        if svc["name"] == "trusty-memory":
            _ensure_palace(svc["base_url"], project_dir.name, project_dir)

    # 3. Inject the capture/index hooks for whatever was detected. Idempotent
    #    via _mpm_service dedup keys; only touches ./.claude/settings.json when
    #    it already exists, always (creates if absent) ~/.claude/settings.json.
    try:
        from ..services.trusty_hooks import inject_trusty_hooks

        hooks_changed = inject_trusty_hooks(
            [svc["name"] for svc in detected],
            project_dir=project_dir,
        )
        changed = changed or hooks_changed
    except Exception as exc:
        logger.warning("trusty autodetect failed to inject hooks: %s", exc)

    return changed
