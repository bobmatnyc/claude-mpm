"""Memory router — CLAUDE.md CRUD.

Endpoints:
    GET /memory?scope=project|user  — read CLAUDE.md
    PUT /memory                     — write CLAUDE.md
"""

from pathlib import Path
from typing import Literal

import aiofiles
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/memory", tags=["Memory"])


class MemoryWrite(BaseModel):
    """Request body for writing CLAUDE.md.

    Attributes:
        content: Full Markdown content to write.
        scope: 'project' or 'user'.
    """

    model_config = ConfigDict(from_attributes=True)

    content: str
    scope: Literal["project", "user"] = "project"


def _memory_path(scope: str) -> Path:
    """Resolve the CLAUDE.md path for the given scope."""
    if scope == "user":
        return Path.home() / "CLAUDE.md"
    return Path.cwd() / "CLAUDE.md"


@router.get("", summary="Read CLAUDE.md")
async def get_memory(
    scope: Literal["project", "user"] = Query("project"),
):
    """Return the contents of CLAUDE.md at the given scope.

    - ``project`` — ``{cwd}/CLAUDE.md``
    - ``user``    — ``~/CLAUDE.md``
    """
    path = _memory_path(scope)
    if not path.exists():
        return {"scope": scope, "path": str(path), "content": "", "exists": False}

    async with aiofiles.open(path) as f:
        content = await f.read()

    return {"scope": scope, "path": str(path), "content": content, "exists": True}


@router.put("", summary="Write CLAUDE.md")
async def write_memory(body: MemoryWrite):
    """Write (overwrite) CLAUDE.md at the given scope with the provided content."""
    path = _memory_path(body.scope)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(path, "w") as f:
            await f.write(body.content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "scope": body.scope,
        "path": str(path),
        "bytes_written": len(body.content.encode()),
        "updated": True,
    }
