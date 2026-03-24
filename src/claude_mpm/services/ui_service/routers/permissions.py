"""Permissions router.

Endpoints:
    GET    /config/permissions           — combined allow/deny/ask arrays
    POST   /config/permissions           — add a rule
    DELETE /config/permissions/{rule_id} — remove a rule
    PUT    /config/permissions/mode      — set defaultMode
"""

import json
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException

from claude_mpm.services.ui_service.models.config import (
    PermissionModeUpdate,
    PermissionRule,
)

router = APIRouter(prefix="/config/permissions", tags=["Permissions"])

_USER_SETTINGS = Path.home() / ".claude" / "settings.json"


async def _read_settings() -> dict:
    """Read user settings, returning {} on failure."""
    if not _USER_SETTINGS.exists():
        return {}
    try:
        async with aiofiles.open(_USER_SETTINGS) as f:
            return json.loads(await f.read())
    except Exception:
        return {}


async def _write_settings(data: dict) -> None:
    """Write data to user settings.json."""
    _USER_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(_USER_SETTINGS, "w") as f:
        await f.write(json.dumps(data, indent=2))


@router.get("", summary="Get combined permission rules")
async def get_permissions():
    """Return allow, deny, and ask arrays from user settings."""
    settings = await _read_settings()
    perms = settings.get("permissions", {})
    return {
        "allow": perms.get("allow", []),
        "deny": perms.get("deny", []),
        "ask": perms.get("ask", []),
        "defaultMode": settings.get("defaultMode", "default"),
    }


@router.post("", status_code=201, summary="Add a permission rule")
async def add_permission(body: PermissionRule):
    """Add a rule to the allow, deny, or ask list.

    Avoids duplicate entries.
    """
    settings = await _read_settings()
    perms = settings.setdefault("permissions", {})
    target_list: list = perms.setdefault(body.list, [])

    if body.rule not in target_list:
        target_list.append(body.rule)
        await _write_settings(settings)

    return {
        "rule": body.rule,
        "list": body.list,
        "added": body.rule not in target_list,
    }


@router.delete("/{rule_id:path}", status_code=204, summary="Remove a permission rule")
async def delete_permission(rule_id: str):
    """Remove a rule from whichever list it appears in.

    The ``rule_id`` is the URL-encoded rule string itself.
    """
    import urllib.parse

    rule = urllib.parse.unquote(rule_id)
    settings = await _read_settings()
    perms = settings.get("permissions", {})
    removed = False
    for lst in ("allow", "deny", "ask"):
        lst_data: list = perms.get(lst, [])
        if rule in lst_data:
            lst_data.remove(rule)
            removed = True

    if not removed:
        raise HTTPException(status_code=404, detail=f"Rule '{rule}' not found")
    await _write_settings(settings)


@router.put("/mode", summary="Set the default permission mode")
async def set_permission_mode(body: PermissionModeUpdate):
    """Update the ``defaultMode`` field in user settings."""
    settings = await _read_settings()
    settings["defaultMode"] = body.mode
    await _write_settings(settings)
    return {"defaultMode": body.mode}
