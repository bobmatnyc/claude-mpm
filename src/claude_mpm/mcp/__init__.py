"""MCP servers for claude-mpm integration.

This module provides MCP (Model Context Protocol) servers that integrate
with claude-mpm's authentication and token management system.
"""

from claude_mpm.mcp.errors import (
    APIError,
    ContextWindowError,
    RateLimitError,
    SessionError,
    parse_error,
)
from claude_mpm.mcp.google_workspace_server import main as google_workspace_main
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
from claude_mpm.mcp.session_server import SessionServer, main as session_server_main
from claude_mpm.mcp.session_server_http import (
    SessionServerHTTP,
    main as session_server_http_main,
)
from claude_mpm.mcp.slack_user_proxy_server import main as slack_user_proxy_main
from claude_mpm.mcp.subprocess_wrapper import ClaudeMPMSubprocess

__all__ = [
    "APIError",
    "ClaudeMPMSubprocess",
    "ContextWindowError",
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
    "google_workspace_main",
    "parse_error",
    "session_server_http_main",
    "session_server_main",
    "slack_user_proxy_main",
]
