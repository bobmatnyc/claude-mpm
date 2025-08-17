#!/usr/bin/env python3
"""
Agent Definition Models
=======================

Data models for agent definitions used by AgentManager.

WHY: These models provide a structured representation of agent data to ensure
consistency across the system. They separate the data structure from the
business logic, following the separation of concerns principle.

DESIGN DECISION: Using dataclasses for models because:
- They provide automatic __init__, __repr__, and other methods
- Type hints ensure better IDE support and runtime validation
- Easy to serialize/deserialize for persistence
- Less boilerplate than traditional classes
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentType(str, Enum):
    """Agent type classification.

    WHY: Enum ensures only valid agent types are used throughout the system,
    preventing typos and making the code more maintainable.
    """

    CORE = "core"
    PROJECT = "project"
    CUSTOM = "custom"
    SYSTEM = "system"
    SPECIALIZED = "specialized"


class AgentSection(str, Enum):
    """Agent markdown section identifiers.

    WHY: Standardizes section names across the codebase, making it easier
    to parse and update specific sections programmatically.
    """

    PRIMARY_ROLE = "Primary Role"
    WHEN_TO_USE = "When to Use This Agent"
    CAPABILITIES = "Core Capabilities"
    AUTHORITY = "Authority & Permissions"
    WORKFLOWS = "Agent-Specific Workflows"
    ESCALATION = "Unique Escalation Triggers"
    KPI = "Key Performance Indicators"
    DEPENDENCIES = "Critical Dependencies"
    TOOLS = "Specialized Tools/Commands"


@dataclass
class AgentPermissions:
    """Agent authority and permissions.

    WHY: Separating permissions into a dedicated class allows for:
    - Clear permission boundaries
    - Easy permission checking and validation
    - Future extension without modifying the main agent definition
    """

    exclusive_write_access: List[str] = field(default_factory=list)
    forbidden_operations: List[str] = field(default_factory=list)
    read_access: List[str] = field(default_factory=list)


@dataclass
class AgentWorkflow:
    """Agent workflow definition.

    WHY: Workflows are complex structures that benefit from their own model:
    - Ensures consistent workflow structure
    - Makes workflow validation easier
    - Allows workflow-specific operations
    """

    name: str
    trigger: str
    process: List[str]
    output: str
    raw_yaml: Optional[str] = None


@dataclass
class AgentMetadata:
    """Agent metadata information.

    WHY: Metadata is separated from the main definition because:
    - It changes independently of agent behavior
    - It's used for discovery and management, not execution
    - Different services may need different metadata views
    """

    type: AgentType
    model_preference: str = "claude-3-sonnet"
    version: str = "1.0.0"
    last_updated: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)

    def increment_serial_version(self) -> None:
        """Increment the patch version number.

        WHY: Automatic version incrementing ensures every change is tracked
        and follows semantic versioning principles.
        """
        parts = self.version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            self.version = ".".join(parts)
        else:
            # If version format is unexpected, append .1
            self.version = f"{self.version}.1"


@dataclass
class AgentDefinition:
    """Complete agent definition.

    WHY: This is the main model that represents an agent's complete configuration:
    - Combines all aspects of an agent in one place
    - Provides a clear contract for what constitutes an agent
    - Makes serialization/deserialization straightforward

    DESIGN DECISION: Using composition over inheritance:
    - AgentMetadata, AgentPermissions, and AgentWorkflow are separate classes
    - This allows each component to evolve independently
    - Services can work with just the parts they need
    """

    # Core identifiers
    name: str
    title: str
    file_path: str

    # Metadata
    metadata: AgentMetadata

    # Agent behavior definition
    primary_role: str
    when_to_use: Dict[str, List[str]]  # {"select": [...], "do_not_select": [...]}
    capabilities: List[str]
    authority: AgentPermissions
    workflows: List[AgentWorkflow]
    escalation_triggers: List[str]
    kpis: List[str]
    dependencies: List[str]
    tools_commands: str

    # Raw content for preservation
    raw_content: str = ""
    raw_sections: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        WHY: Many parts of the system need agent data as dictionaries:
        - JSON serialization for APIs
        - Configuration storage
        - Integration with other services
        """
        return {
            "name": self.name,
            "title": self.title,
            "file_path": self.file_path,
            "metadata": {
                "type": self.metadata.type.value,
                "model_preference": self.metadata.model_preference,
                "version": self.metadata.version,
                "last_updated": (
                    self.metadata.last_updated.isoformat()
                    if self.metadata.last_updated
                    else None
                ),
                "author": self.metadata.author,
                "tags": self.metadata.tags,
                "specializations": self.metadata.specializations,
            },
            "primary_role": self.primary_role,
            "when_to_use": self.when_to_use,
            "capabilities": self.capabilities,
            "authority": {
                "exclusive_write_access": self.authority.exclusive_write_access,
                "forbidden_operations": self.authority.forbidden_operations,
                "read_access": self.authority.read_access,
            },
            "workflows": [
                {
                    "name": w.name,
                    "trigger": w.trigger,
                    "process": w.process,
                    "output": w.output,
                }
                for w in self.workflows
            ],
            "escalation_triggers": self.escalation_triggers,
            "kpis": self.kpis,
            "dependencies": self.dependencies,
            "tools_commands": self.tools_commands,
        }
