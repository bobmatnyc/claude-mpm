"""Commands / skills router.

Endpoints:
    GET    /commands              — list slash commands
    POST   /commands              — create custom command
    GET    /commands/{name}       — read command
    PUT    /commands/{name}       — update command file
    DELETE /commands/{name}       — delete command file
    POST   /commands/{name}/execute — execute command in a session
"""

from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/commands", tags=["Commands"])


class CommandCreate(BaseModel):
    """Request body for creating a custom command.

    Attributes:
        name: Command name (no leading slash).
        content: Markdown content of the command file.
        scope: 'project' writes to .claude/commands/, 'user' to ~/.claude/commands/.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    content: str
    scope: str = "project"


class CommandUpdate(BaseModel):
    """Request body for updating a custom command.

    Attributes:
        content: New Markdown content.
    """

    model_config = ConfigDict(from_attributes=True)

    content: str


class CommandExecute(BaseModel):
    """Request body for executing a command in a session.

    Attributes:
        session_id: The session to send the command to.
        arguments: Optional arguments appended after the slash command.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    arguments: str = ""


def _project_commands_dir() -> Path:
    return Path.cwd() / ".claude" / "commands"


def _user_commands_dir() -> Path:
    return Path.home() / ".claude" / "commands"


def _find_command(name: str) -> Path | None:
    """Search project and user command directories for a named command."""
    for d in (_project_commands_dir(), _user_commands_dir()):
        candidate = d / f"{name}.md"
        if candidate.exists():
            return candidate
    return None


def _list_commands_from_dir(directory: Path, scope: str) -> list[dict]:
    if not directory.exists():
        return []
    return [
        {"name": f.stem, "scope": scope, "path": str(f)}
        for f in sorted(directory.glob("*.md"))
    ]


@router.get("", summary="List available slash commands")
async def list_commands(
    scope: str = Query("all", description="'project', 'user', or 'all'"),
):
    """Return slash commands from .claude/commands/ and/or ~/.claude/commands/."""
    commands = []
    if scope in ("project", "all"):
        commands.extend(_list_commands_from_dir(_project_commands_dir(), "project"))
    if scope in ("user", "all"):
        commands.extend(_list_commands_from_dir(_user_commands_dir(), "user"))
    return {"commands": commands}


@router.post("", status_code=201, summary="Create a custom command")
async def create_command(body: CommandCreate):
    """Write a new .md command file to the appropriate commands directory."""
    target_dir = (
        _project_commands_dir() if body.scope == "project" else _user_commands_dir()
    )
    path = target_dir / f"{body.name}.md"

    if path.exists():
        raise HTTPException(
            status_code=409, detail=f"Command '{body.name}' already exists at {path}"
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "w") as f:
        await f.write(body.content)

    return {"name": body.name, "scope": body.scope, "path": str(path), "created": True}


@router.get("/{name}", summary="Read a command file")
async def get_command(name: str):
    """Return the Markdown content of a named command."""
    path = _find_command(name)
    if not path:
        raise HTTPException(status_code=404, detail=f"Command '{name}' not found")

    async with aiofiles.open(path) as f:
        content = await f.read()

    return {"name": name, "path": str(path), "content": content}


@router.put("/{name}", summary="Update a command file")
async def update_command(name: str, body: CommandUpdate):
    """Overwrite the Markdown content of a named command."""
    path = _find_command(name)
    if not path:
        raise HTTPException(status_code=404, detail=f"Command '{name}' not found")

    async with aiofiles.open(path, "w") as f:
        await f.write(body.content)

    return {"name": name, "path": str(path), "updated": True}


@router.delete("/{name}", status_code=204, summary="Delete a command file")
async def delete_command(name: str):
    """Remove a named command file from disk."""
    path = _find_command(name)
    if not path:
        raise HTTPException(status_code=404, detail=f"Command '{name}' not found")
    path.unlink()


@router.post("/{name}/execute", summary="Execute a command in a session")
async def execute_command(name: str, body: CommandExecute, request: Request):
    """Send ``/{name} {arguments}`` to the specified session's stdin."""
    pm = request.app.state.process_manager
    try:
        pm.get_session(body.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    cmd = f"/{name}"
    if body.arguments:
        cmd = f"{cmd} {body.arguments}"

    await pm.send_command(body.session_id, cmd)
    return {"command": cmd, "session_id": body.session_id, "sent": True}
