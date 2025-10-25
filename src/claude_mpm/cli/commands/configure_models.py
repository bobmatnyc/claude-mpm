"""Data models for configure command.

This module contains data classes used by the configure command for
agent metadata and configuration state management.
"""

from typing import List, Optional


class AgentConfig:
    """Simple agent configuration model."""

    def __init__(
        self, name: str, description: str = "", dependencies: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.dependencies = dependencies or []
