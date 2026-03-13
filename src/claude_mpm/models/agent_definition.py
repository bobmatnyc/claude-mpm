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

from claude_mpm.core.unified_agent_registry import AgentSourceType

# AgentType class removed in Phase 4.  Alias defined after AgentRole below.


class AgentRole(str, Enum):
    """Agent classification by functional role.

    Classifies agents by WHAT they do, not WHERE they come from.
    For source classification, see core.unified_agent_registry.AgentSourceType.
    """

    ENGINEER = "engineer"
    QA = "qa"
    OPS = "ops"
    RESEARCH = "research"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    VERSION_CONTROL = "version_control"
    DATA = "data"
    CONTENT = "content"
    MANAGEMENT = "management"
    SPECIALIZED = "specialized"  # Domain-specific (imagemagick, etc.)
    OTHER = "other"  # Default for unrecognized values

    @classmethod
    def from_frontmatter(cls, value: str | None) -> "AgentRole":
        """Parse agent role from frontmatter with normalization and aliases.

        Source-like values ("core", "system", "project", "custom") map to OTHER
        since they describe source, not role.

        Pipe-delimited values take the first recognized token.

        Args:
            value: Raw agent_type string from frontmatter, or None.

        Returns:
            Matching AgentRole member, or AgentRole.OTHER if unknown.
        """
        if not value:
            return cls.OTHER

        # Handle pipe-delimited values: take first token
        if "|" in value:
            value = value.split("|")[0]

        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")

        # Direct match against enum values
        for member in cls:
            if member.value == normalized:
                return member

        # Source values -> OTHER (these describe origin, not role)
        source_values = {"core", "project", "custom", "system"}
        if normalized in source_values:
            return cls.OTHER

        # Aliases
        aliases: dict[str, AgentRole] = {
            # Legacy source-qualified aliases -> OTHER
            "core_agent": cls.OTHER,
            "project_agent": cls.OTHER,
            # Role aliases
            "engineer_agent": cls.ENGINEER,
            "qa_agent": cls.QA,
            "ops_agent": cls.OPS,
            "research_agent": cls.RESEARCH,
            "security_agent": cls.SECURITY,
            "documentation_agent": cls.DOCUMENTATION,
            "version_control_agent": cls.VERSION_CONTROL,
            "data_agent": cls.DATA,
            "content_agent": cls.CONTENT,
            "management_agent": cls.MANAGEMENT,
            "specialized_agent": cls.SPECIALIZED,
            # Semantic aliases
            "code_analysis": cls.RESEARCH,
            "product_management": cls.MANAGEMENT,
            "product": cls.MANAGEMENT,
            "prompt_engineering": cls.ENGINEER,
            "image_processing": cls.SPECIALIZED,
            "analysis": cls.RESEARCH,
            "claude_mpm": cls.OTHER,
            "imagemagick": cls.SPECIALIZED,
            "memory_manager": cls.MANAGEMENT,
            "refactoring": cls.ENGINEER,
        }

        return aliases.get(normalized, cls.OTHER)


# AgentType preserved as deprecated alias for import compatibility.
# AgentType.ENGINEER etc. works via AgentRole members.
# Source-only values (CORE, PROJECT, CUSTOM, SYSTEM) are no longer available.
AgentType = AgentRole


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

    role: AgentRole  # Primary: what the agent does
    source: Optional[AgentSourceType] = None  # Primary: where it comes from
    model_preference: str = "claude-3-sonnet"
    version: str = "1.0.0"
    last_updated: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    # Collection metadata for enhanced agent matching
    collection_id: Optional[str] = None  # Format: owner/repo-name
    source_path: Optional[str] = None  # Relative path in repository
    canonical_id: Optional[str] = None  # Format: collection_id:agent_id

    @property
    def type(self) -> AgentRole:
        """Deprecated: use .role instead."""
        return self.role

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
                "type": self.metadata.role.value,
                "role": self.metadata.role.value,
                "source": self.metadata.source.value if self.metadata.source else None,
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
                "collection_id": self.metadata.collection_id,
                "source_path": self.metadata.source_path,
                "canonical_id": self.metadata.canonical_id,
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
