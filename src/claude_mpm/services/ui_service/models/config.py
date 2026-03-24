"""Pydantic models for settings and configuration management."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsPatch(BaseModel):
    """Request body for patching settings.json.

    Attributes:
        data: Arbitrary settings keys to merge into the settings file.
    """

    model_config = ConfigDict(from_attributes=True)

    data: dict[str, Any] = Field(
        ..., description="Key-value pairs to merge into settings"
    )


class PermissionRule(BaseModel):
    """A single permission rule entry.

    Attributes:
        rule: Tool name or pattern (e.g. 'Bash', 'Read(**/*)').
        list: Which list to add the rule to.
    """

    model_config = ConfigDict(from_attributes=True)

    rule: str = Field(..., description="Tool name or glob pattern")
    list: Literal["allow", "deny", "ask"] = Field(
        "ask", description="Which permission list to add the rule to"
    )


class PermissionModeUpdate(BaseModel):
    """Request body for updating the default permission mode.

    Attributes:
        mode: The new permission mode.
    """

    model_config = ConfigDict(from_attributes=True)

    mode: Literal["default", "acceptEdits", "bypassPermissions", "plan"] = Field(
        ..., description="New default permission mode"
    )


class HookCreate(BaseModel):
    """Request body for creating a new hook.

    Attributes:
        event: Hook event type (e.g. PreToolUse, PostToolUse).
        command: Shell command to run.
        matcher: Optional tool/pattern matcher.
    """

    model_config = ConfigDict(from_attributes=True)

    event: str = Field(..., description="Hook event type")
    command: str = Field(..., description="Shell command to execute")
    matcher: str | None = Field(None, description="Optional tool or pattern matcher")


class HookUpdate(BaseModel):
    """Request body for updating an existing hook.

    Attributes:
        event: Updated hook event type.
        command: Updated shell command.
        matcher: Updated matcher.
    """

    model_config = ConfigDict(from_attributes=True)

    event: str | None = None
    command: str | None = None
    matcher: str | None = None


class MCPServerCreate(BaseModel):
    """Request body for adding an MCP server.

    Attributes:
        name: Server identifier name.
        command: CLI command to launch the server.
        args: Additional arguments.
        env: Environment variables for the server process.
        transport: Transport type (stdio, sse, etc.).
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Unique server name")
    command: str = Field(..., description="Command to launch the MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    transport: str = Field("stdio", description="Transport type")
