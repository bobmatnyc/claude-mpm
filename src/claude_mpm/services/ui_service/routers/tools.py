"""Tools router.

Endpoints:
    GET /tools                      — list tools with permission state
    PUT /tools/{name}/permission    — set tool permission
"""

import json
from pathlib import Path
from typing import Literal

import aiofiles
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/tools", tags=["Tools"])

_USER_SETTINGS = Path.home() / ".claude" / "settings.json"

# Built-in Claude Code tools
_BUILTIN_TOOLS = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    "LS",
    "Task",
    "TodoRead",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "NotebookRead",
    "NotebookEdit",
    "Computer",
    "mcp__*",
]


class ToolPermissionUpdate(BaseModel):
    """Request body for updating a tool's permission.

    Attributes:
        permission: Target permission list ('allow', 'deny', 'ask').
    """

    model_config = ConfigDict(from_attributes=True)

    permission: Literal["allow", "deny", "ask"]


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


@router.get("", summary="List tools with permission state")
async def list_tools():
    """Return all known tools with their current permission state.

    Permission state is derived from the allow/deny/ask arrays in
    ``~/.claude/settings.json``.  Tools not explicitly listed are
    shown with permission ``'default'``.
    """
    settings = await _read_settings()
    perms = settings.get("permissions", {})

    allow_set = set(perms.get("allow", []))
    deny_set = set(perms.get("deny", []))
    ask_set = set(perms.get("ask", []))

    tools = []
    for tool in _BUILTIN_TOOLS:
        if tool in allow_set:
            state = "allow"
        elif tool in deny_set:
            state = "deny"
        elif tool in ask_set:
            state = "ask"
        else:
            state = "default"
        tools.append({"name": tool, "permission": state})

    return {"tools": tools}


@router.put("/{name}/permission", summary="Update tool permission")
async def set_tool_permission(name: str, body: ToolPermissionUpdate):
    """Move a tool into the specified permission list.

    Removes the tool from any other lists to avoid conflicts.
    """
    settings = await _read_settings()
    perms = settings.setdefault("permissions", {})

    # Remove from all lists
    for lst in ("allow", "deny", "ask"):
        lst_data: list = perms.setdefault(lst, [])
        if name in lst_data:
            lst_data.remove(name)

    # Add to target list
    perms[body.permission].append(name)

    await _write_settings(settings)
    return {"tool": name, "permission": body.permission, "updated": True}
