"""Hooks router.

Endpoints:
    GET    /config/hooks            — list hooks
    POST   /config/hooks            — add hook
    PUT    /config/hooks/{hook_id}  — update hook
    DELETE /config/hooks/{hook_id}  — remove hook
"""

import json
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException

from claude_mpm.services.ui_service.models.config import HookCreate, HookUpdate

router = APIRouter(prefix="/config/hooks", tags=["Hooks"])

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


@router.get("", summary="List configured hooks")
async def list_hooks():
    """Return all hooks defined in user settings."""
    settings = await _read_settings()
    hooks = settings.get("hooks", {})
    # Normalise to list format with IDs
    result = []
    for event_type, hook_list in hooks.items():
        if isinstance(hook_list, list):
            for entry in hook_list:
                hook_id = entry.get("id") or str(uuid.uuid4())
                result.append(
                    {
                        "id": hook_id,
                        "event": event_type,
                        "command": entry.get("command", ""),
                        "matcher": entry.get("matcher"),
                    }
                )
    return {"hooks": result}


@router.post("", status_code=201, summary="Add a hook")
async def add_hook(body: HookCreate):
    """Append a new hook entry to user settings."""
    settings = await _read_settings()
    hooks = settings.setdefault("hooks", {})
    hook_list: list = hooks.setdefault(body.event, [])

    new_hook = {
        "id": str(uuid.uuid4()),
        "command": body.command,
        "matcher": body.matcher,
    }
    hook_list.append(new_hook)
    await _write_settings(settings)
    return {"id": new_hook["id"], "event": body.event, **new_hook}


@router.put("/{hook_id}", summary="Update a hook")
async def update_hook(hook_id: str, body: HookUpdate):
    """Update an existing hook by its ID."""
    settings = await _read_settings()
    hooks = settings.get("hooks", {})
    updated = False

    for event_type, hook_list in hooks.items():
        if isinstance(hook_list, list):
            for entry in hook_list:
                if entry.get("id") == hook_id:
                    if body.event is not None:
                        # Move to new event bucket
                        hook_list.remove(entry)
                        entry["event"] = body.event
                        hooks.setdefault(body.event, []).append(entry)
                    if body.command is not None:
                        entry["command"] = body.command
                    if body.matcher is not None:
                        entry["matcher"] = body.matcher
                    updated = True
                    break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Hook '{hook_id}' not found")

    await _write_settings(settings)
    return {"id": hook_id, "updated": True}


@router.delete("/{hook_id}", status_code=204, summary="Delete a hook")
async def delete_hook(hook_id: str):
    """Remove a hook by its ID from user settings."""
    settings = await _read_settings()
    hooks = settings.get("hooks", {})
    removed = False

    for event_type, hook_list in hooks.items():
        if isinstance(hook_list, list):
            for entry in hook_list:
                if entry.get("id") == hook_id:
                    hook_list.remove(entry)
                    removed = True
                    break

    if not removed:
        raise HTTPException(status_code=404, detail=f"Hook '{hook_id}' not found")

    await _write_settings(settings)
