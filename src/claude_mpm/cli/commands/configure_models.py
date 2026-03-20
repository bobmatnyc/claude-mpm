"""Data models for configure command.

This module contains data classes used by the configure command for
agent metadata and configuration state management.
"""

from typing import Any


class AgentConfig:
    """Simple agent configuration model."""

    def __init__(
        self, name: str, description: str = "", dependencies: list[str] | None = None
    ):
        self.name = name
        self.description = description
        self.dependencies = dependencies or []
        self.is_deployed: bool = False
        self.source_dict: dict[str, Any] | None = None
        self.full_agent_id: str | None = None
