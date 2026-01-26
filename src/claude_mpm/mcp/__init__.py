"""MCP servers for claude-mpm integration.

This module provides MCP (Model Context Protocol) servers that integrate
with claude-mpm's authentication and token management system.
"""

from claude_mpm.mcp.google_workspace_server import main

__all__ = ["main"]
