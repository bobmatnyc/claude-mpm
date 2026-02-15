"""
Consolidated Agent Registry for Claude MPM.

This module provides the primary interface for agent discovery and management.
All functionality has been consolidated into the unified agent registry system.

This module provides:
- Agent discovery from the framework
- Agent listing and selection
- Compatibility with both sync and async interfaces
- Legacy function names for backwards compatibility
"""

import contextlib
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

# Import from the unified agent registry system
from .unified_agent_registry import (
    AgentMetadata as UnifiedAgentMetadata,
    AgentTier,
    AgentType,
    discover_agents as unified_discover_agents,
    get_agent as unified_get_agent,
    get_agent_registry,
    get_core_agents as unified_get_core_agents,
    get_registry_stats as unified_get_registry_stats,
    get_specialized_agents as unified_get_specialized_agents,
    list_agents as unified_list_agents,
)

try:
    from ..core.logger import get_logger
except ImportError:
    from core.logger import get_logger


# ============================================================================
# Compatibility Classes - Delegate to Unified Agent Registry
# ============================================================================


@dataclass
class AgentMetadata:
    """
    COMPATIBILITY WRAPPER for agent metadata.

    This class now delegates to the UnifiedAgentRegistry system.
    """

    name: str
    type: str
    path: str
    tier: str = "system"
    last_modified: float = 0.0
    specializations: List[str] = None
    description: str = ""

    def __post_init__(self):
        if self.specializations is None:
            self.specializations = []

    @classmethod
    def from_unified(cls, unified_metadata: UnifiedAgentMetadata) -> "AgentMetadata":
        """Create compatibility metadata from unified metadata."""
        return cls(
            name=unified_metadata.name,
            type=unified_metadata.agent_type.value,
            path=unified_metadata.path,
            tier=unified_metadata.tier.value,
            last_modified=unified_metadata.last_modified,
            specializations=unified_metadata.specializations,
            description=unified_metadata.description,
        )


class SimpleAgentRegistry:
    """
    COMPATIBILITY WRAPPER for simple agent registry.

    This class now delegates to the UnifiedAgentRegistry system.
    """

    def __init__(self, framework_path: Optional[Path] = None):
        """Initialize with optional framework path (ignored in new implementation)."""
        self.framework_path = framework_path
        self._unified_registry = get_agent_registry()
        self.agents = {}
        self._discover_agents()

    def _discover_agents(self):
        """Discover agents using the unified registry."""
        unified_agents = self._unified_registry.discover_agents()

        # Convert to old format for compatibility
        self.agents = {}
        for name, unified_metadata in unified_agents.items():
            self.agents[name] = {
                "name": unified_metadata.name,
                "type": unified_metadata.agent_type.value,
                "path": unified_metadata.path,
                "last_modified": unified_metadata.last_modified,
                "tier": unified_metadata.tier.value,
                "specializations": unified_metadata.specializations,
                "description": unified_metadata.description,
            }

    def _determine_tier(self, agent_path: Path) -> str:
        """Determine agent tier based on path (compatibility method)."""
        # Delegate to unified registry logic
        if (
            "project" in str(agent_path)
            or ".claude-mpm" in str(agent_path)
            or ".claude/agents" in str(agent_path)
        ):
            return "project"
        if "user" in str(agent_path) or str(Path.home()) in str(agent_path):
            return "user"
        return "system"

    def _extract_specializations(self, agent_id: str) -> List[str]:
        """Extract specializations based on agent type (compatibility method)."""
        specialization_map = {
            "engineer": ["coding", "architecture", "implementation"],
            "documentation": ["docs", "api", "guides"],
            "qa": ["testing", "quality", "validation"],
            "research": ["analysis", "investigation", "exploration"],
            "ops": ["deployment", "monitoring", "infrastructure"],
            "security": ["security", "audit", "compliance"],
            "version_control": ["git", "versioning", "releases"],
            "data_engineer": ["data", "etl", "analytics"],
        }
        return specialization_map.get(agent_id, [])

    def _extract_description(self, agent_id: str) -> str:
        """Extract description for agent (compatibility method)."""
        descriptions = {
            "engineer": "Software engineering and implementation",
            "documentation": "Documentation creation and maintenance",
            "qa": "Quality assurance and testing",
            "research": "Research and investigation",
            "ops": "Operations and deployment",
            "security": "Security analysis and compliance",
            "version_control": "Version control and release management",
            "data_engineer": "Data engineering and analytics",
        }
        return descriptions.get(agent_id, f"{agent_id.title()} agent")

    def list_agents(self, **kwargs) -> Dict[str, Any]:
        """List all agents (compatibility method)."""
        return self.agents

    def listAgents(self, **kwargs) -> Dict[str, Any]:
        """DEPRECATED: Use list_agents() instead. Kept for backward compatibility."""
        warnings.warn(
            "listAgents() is deprecated, use list_agents() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.list_agents(**kwargs)

    def list_agents_filtered(
        self, agent_type: Optional[str] = None, tier: Optional[str] = None
    ) -> List[AgentMetadata]:
        """List agents with optional filtering (compatibility method)."""
        # Use unified registry for filtering
        unified_tier = None
        unified_agent_type = None

        if tier:
            unified_tier = AgentTier(tier)
        if agent_type:
            try:
                unified_agent_type = AgentType(agent_type)
            except ValueError:
                # Handle legacy agent types
                unified_agent_type = None

        unified_agents = self._unified_registry.list_agents(
            tier=unified_tier, agent_type=unified_agent_type
        )

        return [AgentMetadata.from_unified(agent) for agent in unified_agents]

    def get_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """Get a specific agent (compatibility method)."""
        unified_agent = self._unified_registry.get_agent(agent_name)
        if unified_agent:
            return AgentMetadata.from_unified(unified_agent)
        return None

    def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """Discover agents (compatibility method)."""
        unified_agents = self._unified_registry.discover_agents(
            force_refresh=force_refresh
        )

        # Update internal agents dict for compatibility
        self.agents = {}
        for name, unified_metadata in unified_agents.items():
            self.agents[name] = {
                "name": unified_metadata.name,
                "type": unified_metadata.agent_type.value,
                "path": unified_metadata.path,
                "last_modified": unified_metadata.last_modified,
                "tier": unified_metadata.tier.value,
                "specializations": unified_metadata.specializations,
                "description": unified_metadata.description,
            }

        # Return compatibility format
        return {
            name: AgentMetadata.from_unified(unified_metadata)
            for name, unified_metadata in unified_agents.items()
        }

    @property
    def core_agent_types(self) -> Set[str]:
        """Get core agent types (compatibility property)."""
        return {
            "documentation",
            "engineer",
            "qa",
            "research",
            "ops",
            "security",
            "version_control",
            "data_engineer",
        }

    @property
    def specialized_agent_types(self) -> Set[str]:
        """Get specialized agent types beyond core (compatibility property)."""
        all_types = {metadata["type"] for metadata in self.agents.values()}
        return all_types - self.core_agent_types


class AgentRegistryAdapter:
    """
    COMPATIBILITY WRAPPER for agent registry adapter.

    This adapter now delegates to the UnifiedAgentRegistry system.
    """

    def __init__(self, framework_path: Optional[Path] = None):
        """Initialize the agent registry adapter (framework_path ignored in new implementation)."""
        self.logger = get_logger("agent_registry")
        self.framework_path = framework_path  # Kept for compatibility
        self._unified_registry = get_agent_registry()
        self.registry = SimpleAgentRegistry(framework_path)

    def _find_framework(self) -> Optional[Path]:
        """Find claude-mpm installation (compatibility method)."""
        # Delegate to unified path manager
        from .unified_paths import get_path_manager

        return get_path_manager().framework_root

    def _is_valid_framework_path(self, path: Path) -> bool:
        """Check if a path is a valid claude-mpm installation (compatibility method)."""
        return path.exists() and (path / "src" / "claude_mpm").exists()

    def _initialize_registry(self):
        """Initialize the agent registry (compatibility method)."""
        # Registry is already initialized in __init__

    def list_agents(self, **kwargs) -> Dict[str, Any]:
        """List available agents (compatibility method)."""
        try:
            return self.registry.list_agents(**kwargs)
        except Exception as e:
            self.logger.error(f"Error listing agents: {e}")
            return {}

    def get_agent_definition(self, agent_name: str) -> Optional[str]:
        """Get agent definition by name (compatibility method)."""
        try:
            unified_agent = self._unified_registry.get_agent(agent_name)
            if unified_agent:
                agent_path = Path(unified_agent.path)
                if agent_path.exists():
                    return agent_path.read_text()
            return None
        except Exception as e:
            self.logger.error(f"Error getting agent definition: {e}")
            return None

    def select_agent_for_task(
        self,
        task_description: str,
        required_specializations: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Select optimal agent for a task (compatibility method)."""
        try:
            # Get all agents from unified registry
            unified_agents = self._unified_registry.list_agents()

            if required_specializations:
                # Filter by specializations
                filtered = []
                for agent in unified_agents:
                    agent_specs = set(agent.specializations)
                    if any(spec in agent_specs for spec in required_specializations):
                        filtered.append(agent)
                unified_agents = filtered

            if not unified_agents:
                return None

            # Return the first matching agent in compatibility format
            agent = unified_agents[0]
            return {
                "id": agent.name,
                "metadata": {
                    "name": agent.name,
                    "type": agent.agent_type.value,
                    "path": agent.path,
                    "tier": agent.tier.value,
                    "specializations": agent.specializations,
                    "description": agent.description,
                },
            }

        except Exception as e:
            self.logger.error(f"Error selecting agent: {e}")
            return None

    def get_agent_hierarchy(self) -> Dict[str, List[str]]:
        """Get agent hierarchy (compatibility method)."""
        try:
            hierarchy = {"project": [], "user": [], "system": []}

            # Get agents by tier from unified registry
            for tier in [AgentTier.PROJECT, AgentTier.USER, AgentTier.SYSTEM]:
                agents = self._unified_registry.list_agents(tier=tier)
                hierarchy[tier.value] = [agent.name for agent in agents]

            return hierarchy

        except Exception as e:
            self.logger.error(f"Error getting hierarchy: {e}")
            return {"project": [], "user": [], "system": []}

    def get_core_agents(self) -> List[str]:
        """Get list of core system agents (compatibility method)."""
        try:
            core_agents = self._unified_registry.get_core_agents()
            return [agent.name for agent in core_agents]
        except Exception as e:
            self.logger.error(f"Error getting core agents: {e}")
            return [
                "documentation",
                "engineer",
                "qa",
                "research",
                "ops",
                "security",
                "version_control",
                "data_engineer",
            ]

    def format_agent_for_task_tool(
        self, agent_name: str, task: str, context: str = ""
    ) -> str:
        """Format agent delegation for Task Tool (compatibility method)."""
        # Map agent names to nicknames
        nicknames = {
            "documentation": "Documenter",
            "engineer": "Engineer",
            "qa": "QA",
            "research": "Researcher",
            "ops": "Ops",
            "security": "Security",
            "version_control": "Versioner",
            "data_engineer": "Data Engineer",
        }

        nickname = nicknames.get(agent_name, agent_name.title())
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return f"""**{nickname}**: {task}

TEMPORAL CONTEXT: Today is {today}. Apply date awareness to task execution.

**Task**: {task}

**Context**: {context}

**Authority**: Agent has full authority for {agent_name} operations
**Expected Results**: Completed task with operational insights"""


# ============================================================================
# Phase 3 (Issue #299): Dynamic Agent Registry
# ============================================================================


class DynamicAgentRegistry:
    """Dynamic agent registry with canonical naming and normalization.

    Phase 3 (Issue #299): This class provides consistent agent naming
    and discovery across the entire codebase. It is the authority for:
    - Agent discovery from deployed locations
    - Canonical name resolution (handles aliases and variants)
    - Agent ID normalization (dash-based convention)

    Design Decision: Single source of truth for agent naming

    Rationale: Multiple services need to resolve agent names consistently.
    Rather than duplicating normalization logic, this registry provides
    a central authority that all services can query.

    Usage:
        >>> registry = DynamicAgentRegistry()
        >>> agents = registry.discover_agents()
        >>> canonical = registry.get_canonical_name("python_engineer")  # Returns "python-engineer"
        >>> normalized = registry.normalize_agent_id("Python Engineer")  # Returns "python-engineer"
    """

    # Known agent name aliases (maps variants to canonical names)
    # This handles common naming inconsistencies across repositories
    AGENT_ALIASES: Dict[str, str] = {
        # Underscore variants
        "python_engineer": "python-engineer",
        "qa_engineer": "qa-engineer",
        "data_engineer": "data-engineer",
        "version_control": "version-control",
        "product_owner": "product-owner",
        "project_organizer": "project-organizer",
        # Space variants
        "python engineer": "python-engineer",
        "qa engineer": "qa-engineer",
        "data engineer": "data-engineer",
        "version control": "version-control",
        "product owner": "product-owner",
        "project organizer": "project-organizer",
        # Common short forms
        "eng": "engineer",
        "doc": "documentation",
        "docs": "documentation",
        "sec": "security",
        "vc": "version-control",
        "po": "product-owner",
    }

    def __init__(self, deployment_dirs: Optional[List[Path]] = None):
        """Initialize dynamic agent registry.

        Args:
            deployment_dirs: List of directories to search for agents.
                           If None, uses default locations:
                           - .claude/agents/ (project)
                           - ~/.claude/agents/ (user)
                           - ~/.claude-mpm/cache/agents/ (cache)
        """
        self.logger = get_logger("dynamic_agent_registry")

        if deployment_dirs is None:
            # Default deployment directories in priority order
            self.deployment_dirs = [
                Path.cwd() / ".claude" / "agents",  # Project agents (highest priority)
                Path.home() / ".claude" / "agents",  # User agents
                Path.home()
                / ".claude-mpm"
                / "cache"
                / "agents",  # Cache (lowest priority)
            ]
        else:
            self.deployment_dirs = deployment_dirs

        # Cache for discovered agents
        self._agent_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_valid = False

    def discover_agents(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Discover all deployed agents from configured directories.

        Scans deployment directories for .md files and extracts agent metadata
        from YAML frontmatter. Priority is based on directory order (first wins).

        Args:
            force_refresh: Force re-scan even if cache is valid

        Returns:
            Dictionary mapping canonical agent names to metadata:
            {
                "engineer": {
                    "name": "Engineer",
                    "agent_id": "engineer",
                    "path": "/path/to/.claude/agents/engineer.md",
                    "source_dir": "project",
                    "has_frontmatter": True,
                },
                ...
            }
        """
        if self._cache_valid and not force_refresh:
            return self._agent_cache

        agents: Dict[str, Dict[str, Any]] = {}

        for idx, deployment_dir in enumerate(self.deployment_dirs):
            if not deployment_dir.exists():
                self.logger.debug(
                    f"Deployment directory does not exist: {deployment_dir}"
                )
                continue

            # Determine source type based on path
            if ".claude-mpm/cache" in str(deployment_dir):
                source_type = "cache"
            elif str(Path.home()) in str(deployment_dir):
                source_type = "user"
            else:
                source_type = "project"

            for md_file in deployment_dir.glob("*.md"):
                # Skip hidden files and README
                if md_file.name.startswith(".") or md_file.name.upper() == "README.MD":
                    continue

                # Normalize agent_id from filename
                agent_id = self.normalize_agent_id(md_file.stem)

                # Skip if we already have this agent (earlier dir has priority)
                if agent_id in agents:
                    self.logger.debug(
                        f"Skipping {md_file.name} (already found in higher priority location)"
                    )
                    continue

                # Extract metadata from file
                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata = self._extract_metadata(content, md_file)
                    metadata["source_dir"] = source_type
                    metadata["priority"] = idx  # Lower = higher priority
                    agents[agent_id] = metadata
                except Exception as e:
                    self.logger.warning(
                        f"Failed to read agent file {md_file.name}: {e}"
                    )

        self._agent_cache = agents
        self._cache_valid = True

        self.logger.info(
            f"Discovered {len(agents)} agents from {len(self.deployment_dirs)} directories"
        )
        return agents

    def get_canonical_name(self, name: str) -> str:
        """Get canonical agent name from any variant.

        Handles:
        - Underscore variants: "python_engineer" -> "python-engineer"
        - Space variants: "Python Engineer" -> "python-engineer"
        - Known aliases: "eng" -> "engineer"
        - Case normalization: "ENGINEER" -> "engineer"

        Args:
            name: Any agent name variant

        Returns:
            Canonical dash-based agent name

        Examples:
            >>> registry.get_canonical_name("python_engineer")
            'python-engineer'
            >>> registry.get_canonical_name("Python Engineer")
            'python-engineer'
            >>> registry.get_canonical_name("eng")
            'engineer'
        """
        # First normalize to lowercase with dashes
        normalized = self.normalize_agent_id(name)

        # Check if it's a known alias
        if normalized in self.AGENT_ALIASES:
            return self.AGENT_ALIASES[normalized]

        # Check original input (lowercased) in aliases
        lower_name = name.lower()
        if lower_name in self.AGENT_ALIASES:
            return self.AGENT_ALIASES[lower_name]

        return normalized

    def normalize_agent_id(self, agent_id: str) -> str:
        """Normalize agent ID to dash-based convention.

        This is the canonical normalization function that all services
        should use to ensure consistent agent naming.

        Algorithm:
        1. Lowercase the input
        2. Replace underscores with dashes
        3. Replace spaces with dashes
        4. Strip -agent suffix
        5. Collapse multiple dashes

        Args:
            agent_id: Raw agent ID (may have underscores, spaces, mixed case)

        Returns:
            Normalized dash-based agent ID

        Examples:
            >>> registry.normalize_agent_id("Python_Engineer")
            'python-engineer'
            >>> registry.normalize_agent_id("QA Agent")
            'qa'
            >>> registry.normalize_agent_id("data-engineer")
            'data-engineer'
        """
        # Lowercase
        normalized = agent_id.lower()

        # Replace underscores and spaces with dashes
        normalized = normalized.replace("_", "-")
        normalized = normalized.replace(" ", "-")

        # Collapse multiple dashes
        while "--" in normalized:
            normalized = normalized.replace("--", "-")

        # Strip leading/trailing dashes
        normalized = normalized.strip("-")

        # Strip -agent suffix
        if normalized.endswith("-agent"):
            normalized = normalized[:-6]

        return normalized

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent metadata by ID or alias.

        Args:
            agent_id: Agent ID or alias

        Returns:
            Agent metadata dictionary or None if not found
        """
        # Ensure cache is populated
        agents = self.discover_agents()

        # Try canonical name first
        canonical = self.get_canonical_name(agent_id)
        if canonical in agents:
            return agents[canonical]

        # Try normalized form
        normalized = self.normalize_agent_id(agent_id)
        if normalized in agents:
            return agents[normalized]

        return None

    def _extract_metadata(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Extract agent metadata from file content.

        Args:
            content: File content (with optional YAML frontmatter)
            file_path: Path to the file

        Returns:
            Metadata dictionary with name, agent_id, path, has_frontmatter
        """
        import re

        metadata: Dict[str, Any] = {
            "name": file_path.stem.replace("-", " ").title(),
            "agent_id": self.normalize_agent_id(file_path.stem),
            "path": str(file_path),
            "has_frontmatter": False,
        }

        # Try to extract from YAML frontmatter
        if content.startswith("---"):
            metadata["has_frontmatter"] = True
            frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if frontmatter_match:
                try:
                    parsed = yaml.safe_load(frontmatter_match.group(1))
                    if isinstance(parsed, dict):
                        if "name" in parsed:
                            metadata["name"] = parsed["name"]
                        if "agent_id" in parsed:
                            metadata["agent_id"] = self.normalize_agent_id(
                                parsed["agent_id"]
                            )
                        if "description" in parsed:
                            metadata["description"] = parsed["description"]
                        if "model" in parsed:
                            metadata["model"] = parsed["model"]
                except yaml.YAMLError:
                    pass

        return metadata


# ============================================================================
# Compatibility Functions - Delegate to Unified Agent Registry
# ============================================================================

# Export main class as AgentRegistry for compatibility
AgentRegistry = SimpleAgentRegistry


def create_agent_registry(
    cache_service: Any = None, framework_path: Optional[Path] = None
) -> AgentRegistry:
    """Create a new AgentRegistry instance (compatibility function)."""
    # Ignore parameters and use unified registry
    return AgentRegistry(framework_path)


def discover_agents(force_refresh: bool = False) -> Dict[str, AgentMetadata]:
    """Convenience function for synchronous agent discovery (compatibility function)."""
    return unified_discover_agents()


def get_core_agent_types() -> Set[str]:
    """Get the set of core agent types (compatibility function)."""
    core_agents = unified_get_core_agents()
    return {agent.name for agent in core_agents}


def get_specialized_agent_types() -> Set[str]:
    """Get the set of specialized agent types (compatibility function)."""
    specialized_agents = unified_get_specialized_agents()
    return {agent.name for agent in specialized_agents}


def list_agents_all() -> Dict[str, Dict[str, Any]]:
    """Synchronous function for listing all agents (compatibility function)."""
    unified_agents = unified_discover_agents()
    return {
        name: {
            "name": metadata.name,
            "type": metadata.agent_type.value,
            "path": metadata.path,
            "tier": metadata.tier.value,
            "last_modified": metadata.last_modified,
            "specializations": metadata.specializations,
            "description": metadata.description,
        }
        for name, metadata in unified_agents.items()
    }


def listAgents() -> Dict[str, Dict[str, Any]]:
    """DEPRECATED: Use list_agents_all() instead (compatibility function)."""
    warnings.warn(
        "listAgents() is deprecated, use list_agents_all() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return list_agents_all()


def list_agents(
    agent_type: Optional[str] = None, tier: Optional[str] = None
) -> List[AgentMetadata]:
    """Synchronous function to list agents with optional filtering (compatibility function)."""
    # Convert parameters to unified types
    unified_tier = None
    unified_agent_type = None

    if tier:
        with contextlib.suppress(ValueError):
            unified_tier = AgentTier(tier)

    if agent_type:
        with contextlib.suppress(ValueError):
            unified_agent_type = AgentType(agent_type)

    unified_agents = unified_list_agents(
        tier=unified_tier, agent_type=unified_agent_type
    )
    return [AgentMetadata.from_unified(agent) for agent in unified_agents]


def discover_agents_sync(force_refresh: bool = False) -> Dict[str, AgentMetadata]:
    """Synchronous function for agent discovery (compatibility function)."""
    return discover_agents(force_refresh)


def get_agent(agent_name: str) -> Optional[Dict[str, Any]]:
    """Synchronous function to get a specific agent (compatibility function)."""
    unified_agent = unified_get_agent(agent_name)
    if unified_agent:
        return {
            "name": unified_agent.name,
            "type": unified_agent.agent_type.value,
            "path": unified_agent.path,
            "tier": unified_agent.tier.value,
            "last_modified": unified_agent.last_modified,
            "specializations": unified_agent.specializations,
            "description": unified_agent.description,
        }
    return None


def get_registry_stats() -> Dict[str, Any]:
    """Synchronous function to get registry statistics (compatibility function)."""
    return unified_get_registry_stats()


# Export all public symbols
__all__ = [
    "AgentMetadata",
    "AgentRegistry",
    "AgentRegistryAdapter",
    "DynamicAgentRegistry",  # Phase 3 (Issue #299)
    "SimpleAgentRegistry",
    "create_agent_registry",
    "discover_agents",
    "discover_agents_sync",
    "get_agent",
    "get_core_agent_types",
    "get_registry_stats",
    "get_specialized_agent_types",
    "listAgents",  # Deprecated
    "list_agents",
    "list_agents_all",
]
