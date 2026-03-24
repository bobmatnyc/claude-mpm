"""MCP servers router.

Endpoints:
    GET    /mcp              — list MCP servers from ~/.claude/settings.json
    POST   /mcp              — add an MCP server
    DELETE /mcp/{name}       — remove an MCP server
"""

import json
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException

from claude_mpm.services.ui_service.models.config import MCPServerCreate

router = APIRouter(prefix="/mcp", tags=["MCP"])

_USER_SETTINGS = Path.home() / ".claude" / "settings.json"


async def _read_settings() -> dict:
    if not _USER_SETTINGS.exists():
        return {}
    try:
        async with aiofiles.open(_USER_SETTINGS) as f:
            return json.loads(await f.read())
    except Exception:
        return {}


async def _write_settings(data: dict) -> None:
    _USER_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(_USER_SETTINGS, "w") as f:
        await f.write(json.dumps(data, indent=2))


@router.get("", summary="List MCP servers")
async def list_mcp_servers():
    """Return the mcpServers map from ~/.claude/settings.json."""
    settings = await _read_settings()
    mcp_servers = settings.get("mcpServers", {})
    return {"servers": [{"name": name, **cfg} for name, cfg in mcp_servers.items()]}


@router.post("", status_code=201, summary="Add an MCP server")
async def add_mcp_server(body: MCPServerCreate):
    """Add a new MCP server to ~/.claude/settings.json.

    Returns 409 if a server with that name already exists.
    """
    settings = await _read_settings()
    mcp_servers = settings.setdefault("mcpServers", {})

    if body.name in mcp_servers:
        raise HTTPException(
            status_code=409,
            detail=f"MCP server '{body.name}' already exists",
        )

    mcp_servers[body.name] = {
        "command": body.command,
        "args": body.args,
        "env": body.env,
        "transport": body.transport,
    }
    await _write_settings(settings)
    return {"name": body.name, "added": True}


@router.delete("/{server_name}", status_code=204, summary="Remove an MCP server")
async def delete_mcp_server(server_name: str):
    """Remove an MCP server by name from ~/.claude/settings.json."""
    settings = await _read_settings()
    mcp_servers = settings.get("mcpServers", {})

    if server_name not in mcp_servers:
        raise HTTPException(
            status_code=404,
            detail=f"MCP server '{server_name}' not found",
        )

    del mcp_servers[server_name]
    await _write_settings(settings)
