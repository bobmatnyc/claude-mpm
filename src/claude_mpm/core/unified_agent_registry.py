#!/usr/bin/env python3
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
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from claude_mpm.core.logging_utils import get_logger

from .unified_paths import get_path_manager

logger = get_logger(__name__)


class AgentTier(Enum):
    """Agent tier hierarchy for precedence resolution."""

    PROJECT = "project"  # Highest precedence
    USER = "user"  # Medium precedence
    SYSTEM = "system"  # Lowest precedence


class AgentType(Enum):
    """Agent type classification."""

    CORE = "core"  # Core framework agents
    SPECIALIZED = "specialized"  # Specialized domain agents
    USER_DEFINED = "user_defined"  # User-created agents
    PROJECT = "project"  # Project-specific agents
    MEMORY_AWARE = "memory_aware"  # Memory-enhanced agents


class AgentFormat(Enum):
    """Supported agent file formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"


@dataclass
class AgentMetadata:
    """Standardized agent metadata model."""

    name: str
    agent_type: AgentType
    tier: AgentTier
    path: str
    format: AgentFormat
    last_modified: float
    description: str = ""
    specializations: List[str] = None
    memory_files: List[str] = None
    dependencies: List[str] = None
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = None
    # NEW: Collection-based identification fields
    collection_id: Optional[str] = None  # Format: owner/repo-name
    source_path: Optional[str] = None  # Relative path in repo
    canonical_id: Optional[str] = (
        None  # Format: collection_id:agent_id or legacy:filename
    )

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["agent_type"] = self.agent_type.value
        data["tier"] = self.tier.value
        data["format"] = self.format.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMetadata":
        """Create from dictionary representation."""
        data["agent_type"] = AgentType(data["agent_type"])
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
        self.registry: Dict[str, AgentMetadata] = {}
        self.discovery_paths: List[Path] = []
        self.discovered_files: Set[Path] = set()

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

        # NOTE: Templates directory is NOT added separately because:
        # - templates_path = system_path / "templates"
        # - The rglob("*") in _discover_path will already find templates
        # - Adding it separately causes duplicate discovery

        logger.debug(
            f"Discovery paths configured: {[str(p) for p in self.discovery_paths]}"
        )

    def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
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

    def _extract_agent_name(self, file_path: Path) -> Optional[str]:
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
    ) -> Optional[AgentMetadata]:
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

    def _determine_agent_type(self, file_path: Path, tier: AgentTier) -> AgentType:
        """Determine agent type based on file path and tier."""
        path_str = str(file_path).lower()

        # Project-specific agents
        if tier == AgentTier.PROJECT:
            return AgentType.PROJECT

        # User-defined agents
        if tier == AgentTier.USER:
            return AgentType.USER_DEFINED

        # Core framework agents
        if "templates" in path_str or "core" in path_str:
            return AgentType.CORE

        # Specialized agents
        return AgentType.SPECIALIZED

    def _extract_file_metadata(
        self, file_path: Path, agent_format: AgentFormat
    ) -> tuple[str, List[str]]:
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
            for _i, line in enumerate(lines[1:], 1):
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

    def _extract_markdown_specializations(self, content: str) -> List[str]:
        """Extract specializations from markdown content."""
        specializations = []

        # Look for frontmatter
        lines = content.split("\n")
        if lines and lines[0].strip() == "---":
            for _i, line in enumerate(lines[1:], 1):
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
        for _registry_key, metadata in self.registry.items():
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
                    metadata.agent_type = AgentType.MEMORY_AWARE
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

    def get_agent(self, name: str) -> Optional[AgentMetadata]:
        """Get agent metadata by name."""
        if not self.registry:
            self.discover_agents()

        return self.registry.get(name)

    def list_agents(
        self,
        tier: Optional[AgentTier] = None,
        agent_type: Optional[AgentType] = None,
        tags: Optional[List[str]] = None,
    ) -> List[AgentMetadata]:
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

    def get_agent_names(self) -> List[str]:
        """Get list of all agent names."""
        if not self.registry:
            self.discover_agents()

        return sorted(self.registry.keys())

    def get_core_agents(self) -> List[AgentMetadata]:
        """Get all core framework agents."""
        return self.list_agents(agent_type=AgentType.CORE)

    def get_specialized_agents(self) -> List[AgentMetadata]:
        """Get all specialized agents."""
        return self.list_agents(agent_type=AgentType.SPECIALIZED)

    def get_project_agents(self) -> List[AgentMetadata]:
        """Get all project-specific agents."""
        return self.list_agents(tier=AgentTier.PROJECT)

    def get_memory_aware_agents(self) -> List[AgentMetadata]:
        """Get all memory-aware agents."""
        return self.list_agents(agent_type=AgentType.MEMORY_AWARE)

    def get_agents_by_collection(self, collection_id: str) -> List[AgentMetadata]:
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

    def list_collections(self) -> List[Dict[str, Any]]:
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
        collections_map: Dict[str, List[str]] = {}

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

    def get_agent_by_canonical_id(self, canonical_id: str) -> Optional[AgentMetadata]:
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

    def add_discovery_path(self, path: Union[str, Path]) -> None:
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

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            **self.discovery_stats,
            "total_agents": len(self.registry),
            "discovery_paths": [str(p) for p in self.discovery_paths],
            "cache_enabled": self.cache_enabled,
        }

    def export_registry(self, output_path: Union[str, Path]) -> None:
        """Export registry to JSON file."""
        output_path = Path(output_path)

        export_data = {
            "metadata": {
                "export_time": datetime.now(timezone.utc).isoformat(),
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

    def import_registry(self, input_path: Union[str, Path]) -> None:
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
_agent_registry: Optional[UnifiedAgentRegistry] = None


def get_agent_registry() -> UnifiedAgentRegistry:
    """Get the global UnifiedAgentRegistry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = UnifiedAgentRegistry()
    return _agent_registry


# Convenience functions for backward compatibility
def discover_agents() -> Dict[str, AgentMetadata]:
    """Discover all agents."""
    return get_agent_registry().discover_agents()


def list_agents(
    tier: Optional[AgentTier] = None, agent_type: Optional[AgentType] = None
) -> List[AgentMetadata]:
    """List agents with optional filtering."""
    return get_agent_registry().list_agents(tier=tier, agent_type=agent_type)


def get_agent(name: str) -> Optional[AgentMetadata]:
    """Get agent metadata by name."""
    return get_agent_registry().get_agent(name)


def get_core_agents() -> List[AgentMetadata]:
    """Get all core framework agents."""
    return get_agent_registry().get_core_agents()


def get_specialized_agents() -> List[AgentMetadata]:
    """Get all specialized agents."""
    return get_agent_registry().get_specialized_agents()


def get_project_agents() -> List[AgentMetadata]:
    """Get all project-specific agents."""
    return get_agent_registry().get_project_agents()


def get_agent_names() -> List[str]:
    """Get list of all agent names."""
    return get_agent_registry().get_agent_names()


def get_registry_stats() -> Dict[str, Any]:
    """Get registry statistics."""
    return get_agent_registry().get_registry_stats()


def get_agents_by_collection(collection_id: str) -> List[AgentMetadata]:
    """Get all agents from a specific collection."""
    return get_agent_registry().get_agents_by_collection(collection_id)


def list_collections() -> List[Dict[str, Any]]:
    """List all available collections."""
    return get_agent_registry().list_collections()


def get_agent_by_canonical_id(canonical_id: str) -> Optional[AgentMetadata]:
    """Get agent by canonical ID."""
    return get_agent_registry().get_agent_by_canonical_id(canonical_id)


# Legacy function names for backward compatibility
def listAgents() -> List[str]:
    """Legacy function: Get list of agent names."""
    return get_agent_names()


def discover_agents_sync() -> Dict[str, AgentMetadata]:
    """Legacy function: Synchronous agent discovery."""
    return discover_agents()


def list_agents_all() -> List[AgentMetadata]:
    """Legacy function: List all agents."""
    return list_agents()


# ============================================================================
# Export All Public Symbols
# ============================================================================

__all__ = [
    "AgentFormat",
    "AgentMetadata",
    "AgentTier",
    "AgentType",
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
