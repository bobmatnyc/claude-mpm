"""
Unified Agent Registry System for Claude MPM
============================================

This module consolidates all agent registry functionality from the duplicate modules:
- core/agent_registry.py (AgentRegistryAdapter and legacy functions)
- services/agents/registry/agent_registry.py (Full-featured AgentRegistry)
- agents/core/agent_registry.py (Core AgentRegistry with memory integration)

Design Principles:
- Single source of truth for agent discovery and management
- Consistent API across all agent operations
- Hierarchical tier system (PROJECT > USER > SYSTEM)
- Memory-aware agent creation
- Efficient caching with smart invalidation
- Comprehensive metadata management
- Backward compatibility during migration

Architecture:
- UnifiedAgentRegistry: Main registry class
- AgentMetadata: Standardized agent metadata model
- AgentTier: Hierarchical precedence system
- AgentType: Agent classification system
- Discovery engine with tier-based precedence
"""

import contextlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from claude_mpm.core.logging_utils import get_logger

from .unified_paths import get_path_manager

logger = get_logger(__name__)


class AgentTier(Enum):
    """Agent tier hierarchy for precedence resolution."""

    PROJECT = "project"  # Highest precedence
    USER = "user"  # Medium precedence
    SYSTEM = "system"  # Lowest precedence


class AgentSourceType(Enum):
    """Classification by source/tier, NOT by role.

    This enum classifies agents by WHERE they come from (core framework,
    user-created, project-specific, etc.), not by WHAT they do.
    For role-based classification, see models.agent_definition.AgentType.
    """

    CORE = "core"  # Core framework agents
    SPECIALIZED = "specialized"  # Specialized domain agents
    USER_DEFINED = "user_defined"  # User-created agents
    PROJECT = "project"  # Project-specific agents
    SYSTEM = "system"  # System-level agents (matches models enum, factory needs it)
    CUSTOM = "custom"  # Alias for USER_DEFINED (factory compat, frontmatter compat)


class AgentFormat(Enum):
    """Supported agent file formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"


@dataclass
class AgentMetadata:
    """Standardized agent metadata model."""

    name: str
    agent_type: AgentSourceType
    tier: AgentTier
    path: str
    format: AgentFormat
    last_modified: float
    description: str = ""
    specializations: list[str] = field(default_factory=list)
    memory_files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    is_memory_aware: bool = False
    # NEW: Collection-based identification fields
    collection_id: str | None = None  # Format: owner/repo-name
    source_path: str | None = None  # Relative path in repo
    canonical_id: str | None = None  # Format: collection_id:agent_id or legacy:filename

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.specializations is None:
            self.specializations = []
        if self.memory_files is None:
            self.memory_files = []
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["agent_type"] = self.agent_type.value
        data["tier"] = self.tier.value
        data["format"] = self.format.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMetadata":
        """Create from dictionary representation."""
        data["agent_type"] = AgentSourceType(data["agent_type"])
        data["tier"] = AgentTier(data["tier"])
        data["format"] = AgentFormat(data["format"])
        return cls(**data)


class UnifiedAgentRegistry:
    """
    Unified agent registry system that consolidates all agent-related functionality.

    This class provides a single, authoritative interface for all agent operations
    in Claude MPM, replacing the multiple duplicate agent registry modules.
    """

    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 3600):
        """Initialize the unified agent registry."""
        self.path_manager = get_path_manager()

        # Registry storage
        self.registry: dict[str, AgentMetadata] = {}
        self.discovery_paths: list[Path] = []
        self.discovered_files: set[Path] = set()

        # Cache configuration
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache_prefix = "unified_agent_registry"

        # Discovery configuration
        self.file_extensions = {".md", ".json", ".yaml", ".yml"}
        self.ignore_patterns = {
            "__pycache__",
            ".git",
            "node_modules",
            ".pytest_cache",
            "backup",
        }

        # Statistics
        self.discovery_stats = {
            "last_discovery": None,
            "total_discovered": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "discovery_duration": 0.0,
        }

        # Setup discovery paths
        self._setup_discovery_paths()

        logger.info(
            f"UnifiedAgentRegistry initialized with cache={'enabled' if cache_enabled else 'disabled'}"
        )

    def _setup_discovery_paths(self) -> None:
        """Setup standard discovery paths for agent files."""
        # Project-level agents (highest priority)
        project_path = self.path_manager.get_project_agents_dir()
        if project_path.exists():
            self.discovery_paths.append(project_path)

        # NOTE: .claude-mpm/agents/ is deprecated in the simplified architecture
        # Source agents come from ~/.claude-mpm/cache/agents/
        # Deployed agents go to .claude/agents/

        # User-level agents (deprecated in simplified architecture)
        # Keeping for backward compatibility but not actively used
        user_path = self.path_manager.get_user_agents_dir()
        if user_path.exists():
            self.discovery_paths.append(user_path)

        # System-level agents (includes templates as a subdirectory)
        system_path = self.path_manager.get_system_agents_dir()
        if system_path.exists():
            self.discovery_paths.append(system_path)

        # Deployed agents in .claude/agents/ (highest priority for project context)
        # These are the actual agents in use by the current project
        deployed_path = Path.cwd() / ".claude" / "agents"
        if deployed_path.exists():
            self.discovery_paths.insert(0, deployed_path)  # Highest priority

        # Remote cache agents from GitHub repository
        cache_path = Path.home() / ".claude-mpm" / "cache" / "agents"
        if cache_path.exists():
            self.discovery_paths.append(cache_path)

        # NOTE: Templates directory is NOT added separately because:
        # - templates_path = system_path / "templates"
        # - The rglob("*") in _discover_path will already find templates
        # - Adding it separately causes duplicate discovery

        logger.debug(
            f"Discovery paths configured: {[str(p) for p in self.discovery_paths]}"
        )

    def discover_agents(self, force_refresh: bool = False) -> dict[str, AgentMetadata]:
        """
        Discover all agents from configured paths with tier precedence.

        Args:
            force_refresh: Force re-discovery even if cache is valid

        Returns:
            Dictionary mapping agent names to their metadata
        """
        start_time = time.time()

        # Check cache first (if enabled and not forcing refresh)
        if self.cache_enabled and not force_refresh and self._is_cache_valid():
            self.discovery_stats["cache_hits"] += 1
            logger.debug("Using cached agent registry")
            return self.registry

        self.discovery_stats["cache_misses"] += 1

        # Clear existing registry and discovered files
        self.registry.clear()
        self.discovered_files.clear()

        # Discover agents from all paths
        for discovery_path in self.discovery_paths:
            tier = self._determine_tier(discovery_path)
            self._discover_path(discovery_path, tier)

        # Handle tier precedence
        self._apply_tier_precedence()

        # Discover and integrate memory files
        self._discover_memory_integration()

        # Cache the results
        if self.cache_enabled:
            self._cache_registry()

        # Update statistics
        self.discovery_stats["last_discovery"] = time.time()
        self.discovery_stats["total_discovered"] = len(self.registry)
        self.discovery_stats["discovery_duration"] = time.time() - start_time

        logger.info(
            f"Discovered {len(self.registry)} agents in {self.discovery_stats['discovery_duration']:.2f}s"
        )

        return self.registry

    def _discover_path(self, path: Path, tier: AgentTier) -> None:
        """Discover agents in a specific path."""
        if not path.exists():
            return

        for file_path in path.rglob("*"):
            # Skip directories and ignored patterns
            if file_path.is_dir():
                continue

            if any(pattern in str(file_path) for pattern in self.ignore_patterns):
                continue

            # Check file extension
            if file_path.suffix not in self.file_extensions:
                continue

            # Extract agent name
            agent_name = self._extract_agent_name(file_path)
            if not agent_name:
                continue

            # Create agent metadata
            try:
                metadata = self._create_agent_metadata(file_path, agent_name, tier)
                if metadata:
                    # Store all discovered agents temporarily for tier precedence
                    # Use a unique key that includes tier to prevent overwrites
                    registry_key = f"{agent_name}_{tier.value}"
                    self.registry[registry_key] = metadata
                    self.discovered_files.add(file_path)
                    logger.debug(
                        f"Discovered agent: {agent_name} ({tier.value}) at {file_path}"
                    )
            except Exception as e:
                logger.warning(f"Failed to process agent file {file_path}: {e}")

    def _extract_agent_name(self, file_path: Path) -> str | None:
        """Extract agent name from file path."""
        # Remove extension and use filename as agent name
        name = file_path.stem

        # Skip certain files and non-agent templates
        skip_files = {
            "README",
            "INSTRUCTIONS",
            "template",
            "example",
            "base_agent",
            "base_agent_template",
            "agent_template",
            "agent_schema",
            "base_pm",
            "workflow",
            "output_style",
            "memory",
            "optimization_report",
            "vercel_ops_instructions",
            "agent-template",
            "agent-schema",  # Also handle hyphenated versions
        }
        # Case-insensitive comparison
        if name.replace("-", "_").upper() in {
            s.replace("-", "_").upper() for s in skip_files
        }:
            return None

        # Normalize name
        return name.lower().replace("-", "_").replace(" ", "_")

    def _create_agent_metadata(
        self, file_path: Path, agent_name: str, tier: AgentTier
    ) -> AgentMetadata | None:
        """Create agent metadata from file."""
        try:
            # Determine format
            format_map = {
                ".md": AgentFormat.MARKDOWN,
                ".json": AgentFormat.JSON,
                ".yaml": AgentFormat.YAML,
                ".yml": AgentFormat.YAML,
            }
            agent_format = format_map.get(file_path.suffix, AgentFormat.MARKDOWN)

            # Determine agent type
            agent_type = self._determine_agent_type(file_path, tier)

            # Extract metadata from file content
            description, specializations = self._extract_file_metadata(
                file_path, agent_format
            )

            # For JSON files, extract additional metadata
            version = "1.0.0"
            author = ""
            tags = []

            if agent_format == AgentFormat.JSON:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    data = json.loads(content)

                    # Extract version
                    version = data.get("agent_version", data.get("version", "1.0.0"))

                    # Extract author (use project name for local agents)
                    author = data.get("author", "")
                    if not author and ".claude-mpm" in str(file_path):
                        # For local agents, use project directory name as author
                        project_root = file_path
                        while project_root.parent != project_root:
                            if (project_root / ".claude-mpm").exists():
                                author = project_root.name
                                break
                            project_root = project_root.parent

                    # Extract tags (handle both list and comma-separated string formats)
                    if "metadata" in data:
                        tags_raw = data["metadata"].get("tags", [])
                        if isinstance(tags_raw, str):
                            tags = [
                                tag.strip()
                                for tag in tags_raw.split(",")
                                if tag.strip()
                            ]
                        else:
                            tags = tags_raw if isinstance(tags_raw, list) else []

                except Exception as e:
                    logger.debug(
                        f"Could not extract extra JSON metadata from {file_path}: {e}"
                    )

            metadata = AgentMetadata(
                name=agent_name,
                agent_type=agent_type,
                tier=tier,
                path=str(file_path),
                format=agent_format,
                last_modified=file_path.stat().st_mtime,
                description=description,
                specializations=specializations,
                version=version,
                author=author,
                tags=tags,
            )

            # Set higher priority for local agents
            if ".claude-mpm" in str(file_path):
                if tier == AgentTier.PROJECT:
                    # Highest priority for project-local agents
                    metadata.tags.append("local")
                    metadata.tags.append("project")
                elif tier == AgentTier.USER:
                    # High priority for user-local agents
                    metadata.tags.append("local")
                    metadata.tags.append("user")

            return metadata

        except Exception as e:
            logger.error(f"Failed to create metadata for {file_path}: {e}")
            return None

    def _determine_tier(self, path: Path) -> AgentTier:
        """Determine agent tier based on path."""
        path_str = str(path)

        if (
            "project" in path_str
            or str(self.path_manager.get_project_agents_dir()) in path_str
        ):
            return AgentTier.PROJECT
        if (
            "user" in path_str
            or str(self.path_manager.get_user_agents_dir()) in path_str
        ):
            return AgentTier.USER
        return AgentTier.SYSTEM

    def _determine_agent_type(
        self, file_path: Path, tier: AgentTier
    ) -> AgentSourceType:
        """Determine agent type based on file path and tier."""
        path_str = str(file_path).lower()

        # Project-specific agents
        if tier == AgentTier.PROJECT:
            return AgentSourceType.PROJECT

        # User-defined agents
        if tier == AgentTier.USER:
            return AgentSourceType.USER_DEFINED

        # Core framework agents
        if "templates" in path_str or "core" in path_str:
            return AgentSourceType.CORE

        # Specialized agents
        return AgentSourceType.SPECIALIZED

    def _extract_file_metadata(
        self, file_path: Path, agent_format: AgentFormat
    ) -> tuple[str, list[str]]:
        """Extract description and specializations from agent file."""
        try:
            content = file_path.read_text(encoding="utf-8")

            if agent_format == AgentFormat.JSON:
                data = json.loads(content)

                # Ensure data is a dictionary, not a list
                if not isinstance(data, dict):
                    logger.warning(
                        f"Invalid JSON structure in {file_path}: expected object, got {type(data).__name__}"
                    )
                    return "", []

                # Handle local agent JSON templates with metadata structure
                if "metadata" in data:
                    metadata = data["metadata"]
                    description = metadata.get(
                        "description", data.get("description", "")
                    )
                    specializations = metadata.get(
                        "specializations", data.get("specializations", [])
                    )

                    # Extract tags as specializations if present (handle both formats)
                    tags_raw = metadata.get("tags", [])
                    if isinstance(tags_raw, str):
                        tags = [
                            tag.strip() for tag in tags_raw.split(",") if tag.strip()
                        ]
                    else:
                        tags = tags_raw if isinstance(tags_raw, list) else []
                    if tags and not specializations:
                        specializations = tags
                else:
                    # Fallback to direct fields
                    description = data.get("description", "")
                    specializations = data.get("specializations", [])

            elif agent_format in [AgentFormat.YAML, AgentFormat.YAML]:
                try:
                    import yaml

                    data = yaml.safe_load(content)
                    description = data.get("description", "")
                    specializations = data.get("specializations", [])
                except ImportError:
                    # Fallback if yaml not available
                    description = ""
                    specializations = []
            else:  # Markdown
                # Extract from frontmatter or content
                description = self._extract_markdown_description(content)
                specializations = self._extract_markdown_specializations(content)

            return description, specializations

        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            return "", []

    def _extract_markdown_description(self, content: str) -> str:
        """Extract description from markdown content."""
        lines = content.split("\n")

        # Look for frontmatter
        if lines and lines[0].strip() == "---":
            for _, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    break
                if line.strip().startswith("description:"):
                    return line.strip().split(":", 1)[1].strip().strip("\"'")

        # Look for first paragraph
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                return line

        return ""

    def _extract_markdown_specializations(self, content: str) -> list[str]:
        """Extract specializations from markdown content."""
        specializations = []

        # Look for frontmatter
        lines = content.split("\n")
        if lines and lines[0].strip() == "---":
            for _, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    break
                if line.startswith("specializations:"):
                    # Parse YAML list
                    spec_content = line.split(":", 1)[1].strip()
                    if spec_content.startswith("[") and spec_content.endswith("]"):
                        # JSON-style list
                        with contextlib.suppress(Exception):
                            specializations = json.loads(spec_content)

        return specializations

    def _apply_tier_precedence(self) -> None:
        """Apply tier precedence rules to resolve conflicts."""
        # Group agents by their actual name (without tier suffix)
        agent_groups = {}
        for _, metadata in self.registry.items():
            # Extract the actual agent name (registry_key is "name_tier")
            agent_name = metadata.name  # Use the actual name from metadata
            if agent_name not in agent_groups:
                agent_groups[agent_name] = []
            agent_groups[agent_name].append(metadata)

        # Resolve conflicts using tier precedence
        resolved_registry = {}
        tier_order = [AgentTier.PROJECT, AgentTier.USER, AgentTier.SYSTEM]

        for name, agents in agent_groups.items():
            if len(agents) == 1:
                resolved_registry[name] = agents[0]
            else:
                # Find highest precedence agent
                for tier in tier_order:
                    for agent in agents:
                        if agent.tier == tier:
                            resolved_registry[name] = agent
                            logger.debug(
                                f"Resolved conflict for {name}: using {tier.value} tier"
                            )
                            break
                    if name in resolved_registry:
                        break

        self.registry = resolved_registry

    def _discover_memory_integration(self) -> None:
        """Discover and integrate memory files with agents."""
        memories_dir = self.path_manager.get_memories_dir("project")
        if not memories_dir.exists():
            return

        for memory_file in memories_dir.glob("*.md"):
            memory_name = memory_file.stem

            # Find matching agent
            for agent_name, metadata in self.registry.items():
                if agent_name == memory_name or memory_name in agent_name:
                    metadata.memory_files.append(str(memory_file))
                    metadata.is_memory_aware = True
                    logger.debug(
                        f"Integrated memory file {memory_file} with agent {agent_name}"
                    )

    def _is_cache_valid(self) -> bool:
        """Check if the current cache is still valid."""
        if not self.discovery_stats["last_discovery"]:
            return False

        # Check if cache has expired
        cache_age = time.time() - self.discovery_stats["last_discovery"]
        if cache_age > self.cache_ttl:
            return False

        # Check if any discovered files have been modified
        for file_path in self.discovered_files:
            if file_path.exists():
                if file_path.stat().st_mtime > self.discovery_stats["last_discovery"]:
                    return False
            else:
                # File was deleted
                return False

        return True

    def _cache_registry(self) -> None:
        """Cache the current registry state."""
        # For now, we just store in memory
        # In a full implementation, this could write to disk

    # ========================================================================
    # Public API Methods
    # ========================================================================

    def get_agent(self, name: str) -> AgentMetadata | None:
        """Get agent metadata by name."""
        if not self.registry:
            self.discover_agents()

        return self.registry.get(name)

    def list_agents(
        self,
        tier: AgentTier | None = None,
        agent_type: AgentSourceType | None = None,
        tags: list[str] | None = None,
    ) -> list[AgentMetadata]:
        """List agents with optional filtering."""
        if not self.registry:
            self.discover_agents()

        agents = list(self.registry.values())

        # Apply filters
        if tier:
            agents = [a for a in agents if a.tier == tier]

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]

        if tags:
            agents = [a for a in agents if any(tag in a.tags for tag in tags)]

        return sorted(agents, key=lambda a: (a.tier.value, a.name))

    def get_agent_names(self) -> list[str]:
        """Get list of all agent names."""
        if not self.registry:
            self.discover_agents()

        return sorted(self.registry.keys())

    def get_core_agents(self) -> list[AgentMetadata]:
        """Get all core framework agents."""
        return self.list_agents(agent_type=AgentSourceType.CORE)

    def get_specialized_agents(self) -> list[AgentMetadata]:
        """Get all specialized agents."""
        return self.list_agents(agent_type=AgentSourceType.SPECIALIZED)

    def get_project_agents(self) -> list[AgentMetadata]:
        """Get all project-specific agents."""
        return self.list_agents(tier=AgentTier.PROJECT)

    def get_memory_aware_agents(self) -> list[AgentMetadata]:
        """Get all memory-aware agents."""
        if not self.registry:
            self.discover_agents()
        return [a for a in self.registry.values() if a.is_memory_aware]

    def get_agents_by_collection(self, collection_id: str) -> list[AgentMetadata]:
        """Get all agents from a specific collection.

        NEW: Enables collection-based agent selection.

        Args:
            collection_id: Collection identifier (e.g., "bobmatnyc/claude-mpm-agents")

        Returns:
            List of agents from the specified collection

        Example:
            >>> registry = get_agent_registry()
            >>> agents = registry.get_agents_by_collection("bobmatnyc/claude-mpm-agents")
            >>> len(agents)
            45
        """
        if not self.registry:
            self.discover_agents()

        collection_agents = [
            agent
            for agent in self.registry.values()
            if agent.collection_id == collection_id
        ]

        return sorted(collection_agents, key=lambda a: a.name)

    def list_collections(self) -> list[dict[str, Any]]:
        """List all available collections with agent counts.

        NEW: Provides overview of available collections.

        Returns:
            List of collection info dictionaries with:
            - collection_id: Collection identifier
            - agent_count: Number of agents in collection
            - agents: List of agent names in collection

        Example:
            >>> registry = get_agent_registry()
            >>> collections = registry.list_collections()
            >>> collections
            [
                {
                    "collection_id": "bobmatnyc/claude-mpm-agents",
                    "agent_count": 45,
                    "agents": ["pm", "engineer", "qa", ...]
                }
            ]
        """
        if not self.registry:
            self.discover_agents()

        # Group agents by collection_id
        collections_map: dict[str, list[str]] = {}

        for agent in self.registry.values():
            if not agent.collection_id:
                # Skip agents without collection (legacy or local)
                continue

            if agent.collection_id not in collections_map:
                collections_map[agent.collection_id] = []

            collections_map[agent.collection_id].append(agent.name)

        # Convert to list format
        collections = [
            {
                "collection_id": coll_id,
                "agent_count": len(agent_names),
                "agents": sorted(agent_names),
            }
            for coll_id, agent_names in collections_map.items()
        ]

        return sorted(collections, key=lambda c: c["collection_id"])

    def get_agent_by_canonical_id(self, canonical_id: str) -> AgentMetadata | None:
        """Get agent by canonical ID (primary matching key).

        NEW: Primary matching method using canonical_id.

        Args:
            canonical_id: Canonical identifier (e.g., "bobmatnyc/claude-mpm-agents:pm")

        Returns:
            AgentMetadata if found, None otherwise

        Example:
            >>> registry = get_agent_registry()
            >>> agent = registry.get_agent_by_canonical_id("bobmatnyc/claude-mpm-agents:pm")
            >>> agent.name
            'Project Manager Agent'
        """
        if not self.registry:
            self.discover_agents()

        for agent in self.registry.values():
            if agent.canonical_id == canonical_id:
                return agent

        return None

    def add_discovery_path(self, path: str | Path) -> None:
        """Add a new path for agent discovery."""
        path = Path(path)
        if path.exists() and path not in self.discovery_paths:
            self.discovery_paths.append(path)
            logger.info(f"Added discovery path: {path}")
            # Force re-discovery with new path
            self.discover_agents(force_refresh=True)

    def invalidate_cache(self) -> None:
        """Invalidate the current cache."""
        self.discovery_stats["last_discovery"] = None
        logger.debug("Agent registry cache invalidated")

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            **self.discovery_stats,
            "total_agents": len(self.registry),
            "discovery_paths": [str(p) for p in self.discovery_paths],
            "cache_enabled": self.cache_enabled,
        }

    def export_registry(self, output_path: str | Path) -> None:
        """Export registry to JSON file."""
        output_path = Path(output_path)

        export_data = {
            "metadata": {
                "export_time": datetime.now(UTC).isoformat(),
                "total_agents": len(self.registry),
                "discovery_paths": [str(p) for p in self.discovery_paths],
            },
            "agents": {
                name: metadata.to_dict() for name, metadata in self.registry.items()
            },
        }

        with output_path.open("w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.registry)} agents to {output_path}")

    def import_registry(self, input_path: str | Path) -> None:
        """Import registry from JSON file."""
        input_path = Path(input_path)

        with input_path.open() as f:
            data = json.load(f)

        # Clear current registry
        self.registry.clear()

        # Import agents
        for name, agent_data in data.get("agents", {}).items():
            self.registry[name] = AgentMetadata.from_dict(agent_data)

        logger.info(f"Imported {len(self.registry)} agents from {input_path}")


# ============================================================================
# Singleton Instance and Convenience Functions
# ============================================================================

# Global singleton instance
_agent_registry: UnifiedAgentRegistry | None = None


def get_agent_registry() -> UnifiedAgentRegistry:
    """Get the global UnifiedAgentRegistry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = UnifiedAgentRegistry()
    return _agent_registry


# Convenience functions for backward compatibility
def discover_agents() -> dict[str, AgentMetadata]:
    """Discover all agents."""
    return get_agent_registry().discover_agents()


def list_agents(
    tier: AgentTier | None = None, agent_type: AgentSourceType | None = None
) -> list[AgentMetadata]:
    """List agents with optional filtering."""
    return get_agent_registry().list_agents(tier=tier, agent_type=agent_type)


def get_agent(name: str) -> AgentMetadata | None:
    """Get agent metadata by name."""
    return get_agent_registry().get_agent(name)


def get_core_agents() -> list[AgentMetadata]:
    """Get all core framework agents."""
    return get_agent_registry().get_core_agents()


def get_specialized_agents() -> list[AgentMetadata]:
    """Get all specialized agents."""
    return get_agent_registry().get_specialized_agents()


def get_project_agents() -> list[AgentMetadata]:
    """Get all project-specific agents."""
    return get_agent_registry().get_project_agents()


def get_agent_names() -> list[str]:
    """Get list of all agent names."""
    return get_agent_registry().get_agent_names()


def get_registry_stats() -> dict[str, Any]:
    """Get registry statistics."""
    return get_agent_registry().get_registry_stats()


def get_agents_by_collection(collection_id: str) -> list[AgentMetadata]:
    """Get all agents from a specific collection."""
    return get_agent_registry().get_agents_by_collection(collection_id)


def list_collections() -> list[dict[str, Any]]:
    """List all available collections."""
    return get_agent_registry().list_collections()


def get_agent_by_canonical_id(canonical_id: str) -> AgentMetadata | None:
    """Get agent by canonical ID."""
    return get_agent_registry().get_agent_by_canonical_id(canonical_id)


# ============================================================================
# DynamicAgentRegistry - canonical naming and normalization (Phase 3, #299)
# ============================================================================


class DynamicAgentRegistry:
    """Dynamic agent registry with canonical naming and normalization.

    This class provides consistent agent naming and discovery across the
    codebase. It is the authority for:
    - Agent discovery from deployed locations
    - Canonical name resolution (handles aliases and variants)
    - Agent ID normalization (dash-based convention)

    Usage:
        >>> registry = DynamicAgentRegistry()
        >>> agents = registry.discover_agents()
        >>> canonical = registry.get_canonical_name("python_engineer")
        'python-engineer'
        >>> normalized = registry.normalize_agent_id("Python Engineer")
        'python-engineer'
    """

    # Known agent name aliases (maps variants to canonical names)
    AGENT_ALIASES: dict[str, str] = {
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

    def __init__(self, deployment_dirs: list[Path] | None = None):
        """Initialize dynamic agent registry.

        Args:
            deployment_dirs: List of directories to search for agents.
                           If None, uses default locations:
                           - .claude/agents/ (project)
                           - ~/.claude/agents/ (user)
                           - ~/.claude-mpm/cache/agents/ (cache)
        """
        self._logger = get_logger("dynamic_agent_registry")

        if deployment_dirs is None:
            self.deployment_dirs = [
                Path.cwd() / ".claude" / "agents",
                Path.home() / ".claude" / "agents",
                Path.home() / ".claude-mpm" / "cache" / "agents",
            ]
        else:
            self.deployment_dirs = deployment_dirs

        self._agent_cache: dict[str, dict[str, Any]] = {}
        self._cache_valid = False

    def discover_agents(self, force_refresh: bool = False) -> dict[str, dict[str, Any]]:
        """Discover all deployed agents from configured directories.

        Scans deployment directories for .md files and extracts agent metadata
        from YAML frontmatter. Priority is based on directory order (first wins).

        Args:
            force_refresh: Force re-scan even if cache is valid

        Returns:
            Dictionary mapping canonical agent names to metadata.
        """
        if self._cache_valid and not force_refresh:
            return self._agent_cache

        agents: dict[str, dict[str, Any]] = {}

        for idx, deployment_dir in enumerate(self.deployment_dirs):
            if not deployment_dir.exists():
                self._logger.debug(
                    f"Deployment directory does not exist: {deployment_dir}"
                )
                continue

            if ".claude-mpm/cache" in str(deployment_dir):
                source_type = "cache"
            elif str(Path.home()) in str(deployment_dir):
                source_type = "user"
            else:
                source_type = "project"

            for md_file in deployment_dir.glob("*.md"):
                if md_file.name.startswith(".") or md_file.name.upper() == "README.MD":
                    continue

                agent_id = self.normalize_agent_id(md_file.stem)

                if agent_id in agents:
                    self._logger.debug(
                        f"Skipping {md_file.name} (already found in higher priority location)"
                    )
                    continue

                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata = self._extract_metadata(content, md_file)
                    metadata["source_dir"] = source_type
                    metadata["priority"] = idx
                    agents[agent_id] = metadata
                except Exception as e:
                    self._logger.warning(
                        f"Failed to read agent file {md_file.name}: {e}"
                    )

        self._agent_cache = agents
        self._cache_valid = True

        self._logger.info(
            f"Discovered {len(agents)} agents from {len(self.deployment_dirs)} directories"
        )
        return agents

    def get_canonical_name(self, name: str) -> str:
        """Get canonical agent name from any variant.

        Handles underscore, space, alias, and case normalization.

        Args:
            name: Any agent name variant

        Returns:
            Canonical dash-based agent name
        """
        normalized = self.normalize_agent_id(name)

        if normalized in self.AGENT_ALIASES:
            return self.AGENT_ALIASES[normalized]

        lower_name = name.lower()
        if lower_name in self.AGENT_ALIASES:
            return self.AGENT_ALIASES[lower_name]

        return normalized

    def normalize_agent_id(self, agent_id: str) -> str:
        """Normalize agent ID to dash-based convention.

        Algorithm:
        1. Lowercase
        2. Replace underscores with dashes
        3. Replace spaces with dashes
        4. Strip -agent suffix
        5. Collapse multiple dashes

        Args:
            agent_id: Raw agent ID

        Returns:
            Normalized dash-based agent ID
        """
        normalized = agent_id.lower()
        normalized = normalized.replace("_", "-")
        normalized = normalized.replace(" ", "-")

        while "--" in normalized:
            normalized = normalized.replace("--", "-")

        normalized = normalized.strip("-")

        if normalized.endswith("-agent"):
            normalized = normalized[:-6]

        return normalized

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Get agent metadata by ID or alias.

        Args:
            agent_id: Agent ID or alias

        Returns:
            Agent metadata dictionary or None if not found
        """
        agents = self.discover_agents()

        canonical = self.get_canonical_name(agent_id)
        if canonical in agents:
            return agents[canonical]

        normalized = self.normalize_agent_id(agent_id)
        if normalized in agents:
            return agents[normalized]

        return None

    def _extract_metadata(self, content: str, file_path: Path) -> dict[str, Any]:
        """Extract agent metadata from file content.

        Args:
            content: File content (with optional YAML frontmatter)
            file_path: Path to the file

        Returns:
            Metadata dictionary with name, agent_id, path, has_frontmatter
        """
        try:
            import yaml as _yaml
        except ImportError:
            _yaml = None  # type: ignore[assignment]

        metadata: dict[str, Any] = {
            "name": file_path.stem.replace("-", " ").title(),
            "agent_id": self.normalize_agent_id(file_path.stem),
            "path": str(file_path),
            "has_frontmatter": False,
        }

        if content.startswith("---"):
            metadata["has_frontmatter"] = True
            frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if frontmatter_match and _yaml is not None:
                with contextlib.suppress(Exception):
                    parsed = _yaml.safe_load(frontmatter_match.group(1))
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

        return metadata


# ============================================================================
# AgentRegistryAdapter and SimpleAgentRegistry compatibility classes
# ============================================================================


class SimpleAgentRegistry:
    """Thin wrapper around UnifiedAgentRegistry for backward compatibility.

    Callers that need the old dict-based list_agents() format should use this
    class rather than importing the deleted agent_registry.py shim.
    """

    def __init__(self, framework_path: Path | None = None):
        """Initialize with optional framework path (ignored)."""
        self.framework_path = framework_path
        self._unified_registry = get_agent_registry()
        self.agents: dict[str, Any] = {}
        self._refresh()

    def _refresh(self) -> None:
        """Populate the agents dict from the unified registry."""
        unified_agents = self._unified_registry.discover_agents()
        self.agents = {
            name: {
                "name": meta.name,
                "type": meta.agent_type.value,
                "path": meta.path,
                "last_modified": meta.last_modified,
                "tier": meta.tier.value,
                "specializations": meta.specializations,
                "description": meta.description,
            }
            for name, meta in unified_agents.items()
        }

    def list_agents(self, **_kwargs: Any) -> dict[str, Any]:
        """List all agents as a name->dict mapping."""
        return self.agents

    def get_agent(self, agent_name: str) -> AgentMetadata | None:
        """Get a specific agent's unified metadata."""
        return self._unified_registry.get_agent(agent_name)

    def discover_agents(self, force_refresh: bool = False) -> dict[str, AgentMetadata]:
        """Discover agents and return as name->UnifiedAgentMetadata mapping."""
        return self._unified_registry.discover_agents(force_refresh=force_refresh)


class AgentRegistryAdapter:
    """Adapter providing the AgentRegistryAdapter interface over UnifiedAgentRegistry.

    Drop-in replacement for the deleted agent_registry.py shim's AgentRegistryAdapter.
    """

    def __init__(self, framework_path: Path | None = None):
        """Initialize the adapter."""
        self._logger = get_logger("agent_registry_adapter")
        self.framework_path = framework_path
        self._unified_registry = get_agent_registry()
        # Expose registry attribute that some callers access directly
        self.registry = SimpleAgentRegistry(framework_path)

    def list_agents(self, **kwargs: Any) -> dict[str, Any]:
        """List available agents (compatibility method)."""
        try:
            return self.registry.list_agents(**kwargs)
        except Exception as e:
            self._logger.error(f"Error listing agents: {e}")
            return {}

    def get_agent_definition(self, agent_name: str) -> str | None:
        """Get agent file content by name."""
        try:
            unified_agent = self._unified_registry.get_agent(agent_name)
            if unified_agent:
                agent_path = Path(unified_agent.path)
                if agent_path.exists():
                    return agent_path.read_text()
            return None
        except Exception as e:
            self._logger.error(f"Error getting agent definition: {e}")
            return None

    def get_core_agents(self) -> list[str]:
        """Get list of core system agent names."""
        try:
            return [a.name for a in self._unified_registry.get_core_agents()]
        except Exception as e:
            self._logger.error(f"Error getting core agents: {e}")
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

    def get_agent_hierarchy(self) -> dict[str, list[str]]:
        """Get agent hierarchy grouped by tier."""
        try:
            hierarchy: dict[str, list[str]] = {"project": [], "user": [], "system": []}
            for tier in [AgentTier.PROJECT, AgentTier.USER, AgentTier.SYSTEM]:
                agents = self._unified_registry.list_agents(tier=tier)
                hierarchy[tier.value] = [a.name for a in agents]
            return hierarchy
        except Exception as e:
            self._logger.error(f"Error getting hierarchy: {e}")
            return {"project": [], "user": [], "system": []}

    def select_agent_for_task(
        self,
        task_description: str,
        required_specializations: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Select optimal agent for a task."""
        # Interface parameter - not used by this implementation
        try:
            unified_agents = self._unified_registry.list_agents()

            if required_specializations:
                unified_agents = [
                    a
                    for a in unified_agents
                    if any(s in a.specializations for s in required_specializations)
                ]

            if not unified_agents:
                return None

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
            self._logger.error(f"Error selecting agent: {e}")
            return None

    def format_agent_for_task_tool(
        self, agent_name: str, task: str, context: str = ""
    ) -> str:
        """Format agent delegation for Task Tool."""
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
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return (
            f"**{nickname}**: {task}\n\n"
            f"TEMPORAL CONTEXT: Today is {today}. Apply date awareness to task execution.\n\n"
            f"**Task**: {task}\n\n"
            f"**Context**: {context}\n\n"
            f"**Authority**: Agent has full authority for {agent_name} operations\n"
            f"**Expected Results**: Completed task with operational insights"
        )


# ============================================================================
# Backward-compat: AgentRegistry alias and module-level functions
# ============================================================================

# Alias used by some callers
AgentRegistry = SimpleAgentRegistry


# Legacy function names for backward compatibility
def listAgents() -> list[str]:
    """Legacy function: Get list of agent names."""
    return get_agent_names()


def discover_agents_sync() -> dict[str, AgentMetadata]:
    """Legacy function: Synchronous agent discovery."""
    return discover_agents()


def list_agents_all() -> list[AgentMetadata]:
    """Legacy function: List all agents."""
    return list_agents()


# ============================================================================
# Export All Public Symbols
# ============================================================================

__all__ = [
    "AgentFormat",
    "AgentMetadata",
    "AgentRegistry",
    "AgentRegistryAdapter",
    "AgentSourceType",
    "AgentTier",
    "DynamicAgentRegistry",
    "SimpleAgentRegistry",
    "UnifiedAgentRegistry",
    "discover_agents",
    "discover_agents_sync",
    "get_agent",
    "get_agent_by_canonical_id",
    "get_agent_names",
    "get_agent_registry",
    "get_agents_by_collection",
    "get_core_agents",
    "get_project_agents",
    "get_registry_stats",
    "get_specialized_agents",
    "listAgents",
    "list_agents",
    "list_agents_all",
    "list_collections",
]
