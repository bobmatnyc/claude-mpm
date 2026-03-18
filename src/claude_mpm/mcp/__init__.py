"""MCP servers for claude-mpm integration.

This module provides MCP (Model Context Protocol) servers that integrate
with claude-mpm's authentication and token management system.

Modules that depend on the optional ``mcp`` package (session_server,
session_server_http, slack_user_proxy_server) are imported lazily so that
the rest of the package remains importable even when ``mcp`` is not
installed.
"""

from claude_mpm.mcp.errors import (
    APIError,
    ContextWindowError,
    RateLimitError,
    SessionError,
    parse_error,
)
from claude_mpm.mcp.models import SessionInfo, SessionResult, SessionStatus
from claude_mpm.mcp.ndjson_parser import (
    NDJSONStreamParser,
    extract_session_id,
    extract_session_id_from_stream,
)
from claude_mpm.mcp.ngrok_tunnel import NgrokTunnel, TunnelInfo
from claude_mpm.mcp.rclone_manager import (
    RcloneConfig,
    RcloneManager,
    RcloneNotInstalledError,
    RcloneOperationError,
    check_rclone_available,
)
from claude_mpm.mcp.session_manager import SessionManager
from claude_mpm.mcp.subprocess_wrapper import ClaudeMPMSubprocess

# ---------------------------------------------------------------------------
# Optional imports -- these modules depend on the ``mcp`` package which may
# not be installed in every environment (e.g. test, lightweight CLI usage).
# ---------------------------------------------------------------------------
try:
    from claude_mpm.mcp.session_server import (
        SessionServer,
        main as session_server_main,
    )
except ImportError:
    SessionServer = None  # type: ignore[assignment,misc]
    session_server_main = None  # type: ignore[assignment]

try:
    from claude_mpm.mcp.session_server_http import (
        SessionServerHTTP,
        main as session_server_http_main,
    )
except ImportError:
    SessionServerHTTP = None  # type: ignore[assignment,misc]
    session_server_http_main = None  # type: ignore[assignment]

try:
    from claude_mpm.mcp.slack_user_proxy_server import (
        main as slack_user_proxy_main,
    )
except ImportError:
    slack_user_proxy_main = None  # type: ignore[assignment]

try:
    from claude_mpm.mcp.messaging_server import (
        MessagingMCPServer,
        main as messaging_server_main,
    )
except ImportError:
    MessagingMCPServer = None  # type: ignore[assignment,misc]
    messaging_server_main = None  # type: ignore[assignment]

__all__ = [
    "APIError",
    "ClaudeMPMSubprocess",
    "ContextWindowError",
    "MessagingMCPServer",
    "NDJSONStreamParser",
    "NgrokTunnel",
    "RateLimitError",
    "RcloneConfig",
    "RcloneManager",
    "RcloneNotInstalledError",
    "RcloneOperationError",
    "SessionError",
    "SessionInfo",
    "SessionManager",
    "SessionResult",
    "SessionServer",
    "SessionServerHTTP",
    "SessionStatus",
    "TunnelInfo",
    "check_rclone_available",
    "extract_session_id",
    "extract_session_id_from_stream",
    "messaging_server_main",
    "parse_error",
    "session_server_http_main",
    "session_server_main",
    "slack_user_proxy_main",
]
