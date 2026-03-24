"""Config router — settings.json CRUD.

Endpoints:
    GET   /config?level=user|project|local  — read settings
    PATCH /config?level=user|project|local  — merge-update settings
"""

import json
from pathlib import Path
from typing import Literal

import aiofiles
from fastapi import APIRouter, HTTPException, Query, Request

from claude_mpm.services.ui_service.models.config import SettingsPatch

router = APIRouter(prefix="/config", tags=["Config"])


def _settings_path(level: str, cwd: str) -> Path:
    """Resolve the settings.json path for the given level.

    Args:
        level: 'user', 'project', or 'local'.
        cwd: Current working directory (used for project/local levels).

    Returns:
        Resolved Path to the settings file.
    """
    if level == "user":
        return Path.home() / ".claude" / "settings.json"
    if level == "project":
        return Path(cwd) / ".claude" / "settings.json"
    if level == "local":
        return Path(cwd) / ".claude" / "settings.local.json"
    raise ValueError(f"Unknown settings level: {level}")


@router.get("", summary="Read settings.json at given level")
async def get_config(
    request: Request,
    level: Literal["user", "project", "local"] = Query("user"),
):
    """Return the parsed contents of settings.json at the specified level.

    Levels:
    - ``user``    — ``~/.claude/settings.json``
    - ``project`` — ``{cwd}/.claude/settings.json``
    - ``local``   — ``{cwd}/.claude/settings.local.json``
    """
    cwd = getattr(request.app.state, "cwd", str(Path.cwd()))
    try:
        path = _settings_path(level, cwd)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not path.exists():
        return {"level": level, "path": str(path), "settings": {}}

    try:
        async with aiofiles.open(path) as f:
            raw = await f.read()
        settings = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid JSON in {path}: {exc}"
        ) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"level": level, "path": str(path), "settings": settings}


@router.patch("", summary="Merge-update settings.json at given level")
async def patch_config(
    request: Request,
    body: SettingsPatch,
    level: Literal["user", "project", "local"] = Query("user"),
):
    """Merge ``body.data`` into settings.json without clobbering other keys.

    The update is a shallow merge at the top level.  Nested objects are
    replaced entirely if their top-level key is present in the patch.
    """
    cwd = getattr(request.app.state, "cwd", str(Path.cwd()))
    try:
        path = _settings_path(level, cwd)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Read existing settings
    existing: dict = {}
    if path.exists():
        try:
            async with aiofiles.open(path) as f:
                raw = await f.read()
            existing = json.loads(raw)
        except json.JSONDecodeError:
            existing = {}

    # Merge
    existing.update(body.data)

    # Write back
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(existing, indent=2))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"level": level, "path": str(path), "settings": existing}
