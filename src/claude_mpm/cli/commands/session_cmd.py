"""
Session API command — programmatic session creation via the serve daemon.

WHAT: Provides ``claude-mpm session create`` which POSTs to the running
serve daemon's REST API and prints the new session_id to stdout, enabling
shell-script usage::

    SESSION_ID=$(claude-mpm session create --prompt "explain this code")

WHY: Issue #771 — operators need a way to create Claude sessions
programmatically without embedding Python. A thin CLI wrapper over the
existing ``POST /api/v1/sessions`` endpoint makes the daemon scriptable
from any language.

DESIGN DECISIONS:
- Uses stdlib ``urllib.request`` to avoid adding httpx as a hard dependency.
- Reads daemon URL from ``~/.claude-mpm/daemon.sock`` (default) or from
  ``--url`` (TCP).  Falls back to ``http://127.0.0.1:7777`` when neither
  socket file nor ``--url`` is present.
- Prints only the session_id on success (clean stdout for shell capture).
- All other output goes to stderr so scripts can redirect cleanly.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Default daemon address helpers
# ---------------------------------------------------------------------------

_DEFAULT_SOCKET = Path.home() / ".claude-mpm" / "daemon.sock"
_DEFAULT_TCP_URL = "http://127.0.0.1:7777"
_API_PATH = "/api/v1/sessions"


def _resolve_daemon_url(url: str | None, socket_path: str | None) -> str:
    """Return the base URL for the serve daemon.

    Priority:
    1. ``--url`` flag (explicit TCP URL)
    2. ``--socket`` flag (Unix domain socket)
    3. Default socket at ``~/.claude-mpm/daemon.sock`` if it exists
    4. Default TCP ``http://127.0.0.1:7777``

    Args:
        url: Explicit HTTP URL from --url flag (may be None).
        socket_path: Unix socket path from --socket flag (may be None).

    Returns:
        Base URL string for the daemon.
    """
    if url:
        return url.rstrip("/")
    if socket_path:
        from urllib.parse import quote

        resolved = str(Path(socket_path).expanduser())
        return f"http+unix://{quote(resolved, safe='')}"
    if _DEFAULT_SOCKET.exists():
        from urllib.parse import quote

        return f"http+unix://{quote(str(_DEFAULT_SOCKET), safe='')}"
    return _DEFAULT_TCP_URL


def _http_post(base_url: str, path: str, payload: dict) -> dict:
    """POST JSON payload to base_url + path and return parsed response.

    Supports standard ``http://`` URLs only (no http+unix:// — that
    requires httpx or aiohttp).  When a Unix socket URL is detected,
    falls back gracefully with an actionable error message.

    Args:
        base_url: Base URL, either ``http://host:port`` or
            ``http+unix://<encoded_path>``.
        path: API path (e.g. ``/api/v1/sessions``).
        payload: Dict to JSON-encode as the request body.

    Returns:
        Parsed JSON response dict.

    Raises:
        SystemExit: On HTTP error or connection failure.
    """
    if base_url.startswith("http+unix://"):
        # httpx supports Unix sockets natively; try it first.
        return _http_post_unix(base_url, path, payload)

    full_url = base_url + path
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        full_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 — URL is always http:// (validated above, never file:// or custom scheme)
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(
            f"Daemon returned HTTP {exc.code}: {body}",
            file=sys.stderr,
        )
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(
            f"Cannot reach daemon at {full_url}: {exc.reason}\n"
            "Is the daemon running? Try: claude-mpm serve status",
            file=sys.stderr,
        )
        sys.exit(1)


def _http_post_unix(base_url: str, path: str, payload: dict) -> dict:
    """POST to a Unix-domain-socket daemon using httpx.

    Args:
        base_url: ``http+unix://<encoded_socket_path>`` URL.
        path: API path (e.g. ``/api/v1/sessions``).
        payload: Dict to JSON-encode as the request body.

    Returns:
        Parsed JSON response dict.

    Raises:
        SystemExit: On import error or HTTP/connection failure.
    """
    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError:
        print(
            "Unix socket transport requires httpx: pip install httpx\n"
            "Alternatively, bypass the auto-detected socket with "
            "--url http://127.0.0.1:<port>",
            file=sys.stderr,
        )
        sys.exit(1)

    from urllib.parse import unquote

    raw_path = unquote(base_url.replace("http+unix://", ""))
    try:
        transport = httpx.HTTPTransport(uds=raw_path)
        with httpx.Client(transport=transport, base_url="http://localhost") as client:
            resp = client.post(path, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        print(f"Cannot reach daemon via Unix socket: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


def handle_session_create(args) -> int:
    """Handle ``claude-mpm session create``.

    WHAT: Resolves the serve daemon's address, assembles a JSON payload from
          the optional ``prompt``/``model``/``cwd``/``permission_mode`` args,
          POSTs it to ``/api/v1/sessions``, then prints the returned
          session_id to stdout (errors and status go to stderr) and returns
          0 on success or 1 when the daemon response carries no session id.
    WHY: Operators need the new session_id captured cleanly via ``$(...)`` in
         shell scripts, so stdout is reserved exclusively for the id while all
         diagnostics are routed to stderr and failures surface as a non-zero
         exit code rather than crashing the CLI.

    POSTs to the running serve daemon to create a new managed session and
    prints the resulting session_id to stdout (clean for shell capture).

    Args:
        args: Parsed argparse Namespace. Expected attributes:
            - ``url`` (str | None): explicit daemon HTTP URL
            - ``socket_path`` (str | None): Unix socket path
            - ``prompt`` (str | None): initial prompt for the session
            - ``model`` (str | None): Claude model identifier
            - ``cwd`` (str | None): working directory for subprocess
            - ``permission_mode`` (str): permission mode (default: "default")

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    daemon_url = _resolve_daemon_url(
        getattr(args, "url", None),
        getattr(args, "socket_path", None),
    )

    payload: dict[str, object] = {
        "permission_mode": getattr(args, "permission_mode", "default") or "default",
    }
    prompt = getattr(args, "prompt", None)
    if prompt:
        payload["prompt"] = prompt
    model = getattr(args, "model", None)
    if model:
        payload["model"] = model
    cwd = getattr(args, "cwd", None)
    if cwd:
        payload["cwd"] = cwd

    print(f"Creating session via {daemon_url}...", file=sys.stderr)

    response = _http_post(daemon_url, _API_PATH, payload)

    session_id = response.get("id") or response.get("session_id")
    if not session_id:
        print(
            f"Unexpected response from daemon (no session id): {response}",
            file=sys.stderr,
        )
        return 1

    # Print session_id to stdout (clean — suitable for $(...) capture).
    print(session_id)
    return 0
