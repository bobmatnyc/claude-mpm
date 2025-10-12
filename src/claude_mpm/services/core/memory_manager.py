"""
Memory Management Service
=========================

WHY: Centralizes all memory-related operations that were previously scattered
across the framework_loader.py god class. This service handles loading,
aggregation, deduplication, and migration of agent memories.

DESIGN DECISION:
- Extracted from framework_loader.py to follow Single Responsibility Principle
- Uses dependency injection for ICacheManager and IPathResolver
- Maintains backward compatibility with legacy memory file formats
- Implements proper memory precedence: project > user > system

ARCHITECTURE:
- IMemoryManager interface implementation
- Loads PM memories and agent-specific memories
- Handles memory aggregation and deduplication
- Migrates legacy memory formats automatically
- Uses caching for performance optimization
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ...core.logger import get_logger
from .service_interfaces import ICacheManager, IMemoryManager, IPathResolver


class MemoryManager(IMemoryManager):
    """
    Memory management service for agent memories.

    This service handles:
    1. Loading PM memories from PM_memories.md files
    2. Loading agent-specific memories (only for deployed agents)
    3. Memory aggregation and deduplication
    4. Legacy format migration (e.g., PM.md -> PM_memories.md)
    5. Memory caching for performance

    Memory Scope:
    - Project-level ONLY: ./.claude-mpm/memories/ (project-scoped isolation)
    - User-level memories are NOT loaded to prevent cross-project contamination

    Note: As of v4.7.10+, memories are strictly project-scoped for complete isolation.
    """

    def __init__(
        self,
        cache_manager: ICacheManager,
        path_resolver: IPathResolver,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize memory manager.

        Args:
            cache_manager: Cache manager for memory caching
            path_resolver: Path resolver for finding memory directories
            logger: Optional logger instance
        """
        self._cache_manager = cache_manager
        self._path_resolver = path_resolver
        self.logger = logger or get_logger("memory_manager")

        # Memory statistics
        self._stats = {
            "loaded_count": 0,
            "skipped_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def load_memories(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load memories for an agent or all agents.

        Args:
            agent_name: Specific agent name or None for all

        Returns:
            Dictionary containing:
            - actual_memories: PM memories content
            - agent_memories: Dict of agent-specific memories
        """
        # Try to get from cache first
        cached_memories = self._cache_manager.get_memories()
        if cached_memories is not None:
            self._stats["cache_hits"] += 1
            self.logger.debug("Memory cache hit")

            # Filter for specific agent if requested
            if agent_name and "agent_memories" in cached_memories:
                if agent_name in cached_memories["agent_memories"]:
                    return {
                        "actual_memories": cached_memories.get("actual_memories", ""),
                        "agent_memories": {
                            agent_name: cached_memories["agent_memories"][agent_name]
                        },
                    }
                return {
                    "actual_memories": cached_memories.get("actual_memories", ""),
                    "agent_memories": {},
                }

            return cached_memories

        # Cache miss - perform actual loading
        self._stats["cache_misses"] += 1
        self.logger.debug("Loading memories from disk (cache miss)")

        # Reset statistics for this load
        self._stats["loaded_count"] = 0
        self._stats["skipped_count"] = 0

        # Get deployed agents set (needed to filter agent memories)
        deployed_agents = self._get_deployed_agents()

        # Load memories from both user and project directories
        result = self._load_actual_memories(deployed_agents)

        # Cache the loaded memories
        self._cache_manager.set_memories(result)

        # Filter for specific agent if requested
        if agent_name and "agent_memories" in result:
            if agent_name in result["agent_memories"]:
                return {
                    "actual_memories": result.get("actual_memories", ""),
                    "agent_memories": {
                        agent_name: result["agent_memories"][agent_name]
                    },
                }
            return {
                "actual_memories": result.get("actual_memories", ""),
                "agent_memories": {},
            }

        return result

    def save_memory(
        self, key: str, value: Any, agent_name: Optional[str] = None
    ) -> None:
        """
        Save a memory entry.

        Args:
            key: Memory key
            value: Memory value
            agent_name: Agent name or None for global
        """
        # Determine target file
        project_memories_dir = Path.cwd() / ".claude-mpm" / "memories"
        self._path_resolver.ensure_directory(project_memories_dir)

        if agent_name:
            memory_file = project_memories_dir / f"{agent_name}_memories.md"
        else:
            memory_file = project_memories_dir / "PM_memories.md"

        # Load existing content or create new
        if memory_file.exists():
            content = memory_file.read_text(encoding="utf-8")
            lines = content.split("\n")
        else:
            lines = [
                f"# {'Agent Memory: ' + agent_name if agent_name else 'PM Memory'}",
                "",
            ]

        # Add new memory as a bullet point
        timestamp = datetime.now(timezone.utc).isoformat()
        lines.append(f"- [{timestamp}] {key}: {value}")

        # Write back
        memory_file.write_text("\n".join(lines), encoding="utf-8")

        # Clear cache to force reload on next access
        self._cache_manager.clear_memory_caches()

        self.logger.info(f"Saved memory to {memory_file.name}")

    def search_memories(
        self, query: str, agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query.

        Args:
            query: Search query
            agent_name: Specific agent or None for all

        Returns:
            List of matching memory entries
        """
        memories = self.load_memories(agent_name)
        results = []

        query_lower = query.lower()

        # Search in PM memories
        if memories.get("actual_memories"):
            for line in memories["actual_memories"].split("\n"):
                if line.strip().startswith("-") and query_lower in line.lower():
                    results.append(
                        {"type": "PM", "content": line.strip(), "agent": None}
                    )

        # Search in agent memories
        if "agent_memories" in memories:
            for agent, content in memories["agent_memories"].items():
                if isinstance(content, str):
                    for line in content.split("\n"):
                        if line.strip().startswith("-") and query_lower in line.lower():
                            results.append(
                                {
                                    "type": "Agent",
                                    "content": line.strip(),
                                    "agent": agent,
                                }
                            )

        return results

    def clear_memories(self, agent_name: Optional[str] = None) -> None:
        """
        Clear memories for an agent or all agents.

        Args:
            agent_name: Specific agent or None for all
        """
        # Clear cache
        self._cache_manager.clear_memory_caches()

        # Clear files if requested
        project_memories_dir = Path.cwd() / ".claude-mpm" / "memories"
        if not project_memories_dir.exists():
            return

        if agent_name:
            # Clear specific agent memory
            memory_file = project_memories_dir / f"{agent_name}_memories.md"
            if memory_file.exists():
                memory_file.unlink()
                self.logger.info(f"Cleared memories for agent: {agent_name}")
        else:
            # Clear all memories
            for memory_file in project_memories_dir.glob("*_memories.md"):
                memory_file.unlink()
                self.logger.info(f"Cleared memory file: {memory_file.name}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Dictionary with memory statistics
        """
        memories = self.load_memories()

        stats = dict(self._stats)  # Copy internal stats

        # Add memory content stats
        stats["pm_memory_size"] = len(
            memories.get("actual_memories", "").encode("utf-8")
        )
        stats["agent_count"] = len(memories.get("agent_memories", {}))

        if "agent_memories" in memories:
            total_agent_size = 0
            for content in memories["agent_memories"].values():
                if isinstance(content, str):
                    total_agent_size += len(content.encode("utf-8"))
            stats["total_agent_memory_size"] = total_agent_size

        return stats

    # Internal methods (extracted from framework_loader.py)

    def _load_actual_memories(self, deployed_agents: Set[str]) -> Dict[str, Any]:
        """
        Load actual memories from project directory only.

        Memories are project-scoped to ensure complete isolation between projects.
        User-level memories are no longer supported to prevent cross-project contamination.

        Args:
            deployed_agents: Set of deployed agent names

        Returns:
            Dictionary with actual_memories and agent_memories
        """
        # Define project memory directory (project-scoped only)
        project_memories_dir = Path.cwd() / ".claude-mpm" / "memories"

        # Dictionary to store aggregated memories
        pm_memories = []
        agent_memories_dict = {}

        # Load memories from project directory only
        if project_memories_dir.exists():
            self.logger.info(
                f"Loading project-level memory files from: {project_memories_dir}"
            )
            self._load_memories_from_directory(
                project_memories_dir,
                deployed_agents,
                pm_memories,
                agent_memories_dict,
                "project",
            )
        else:
            self.logger.debug(
                f"No project memories directory found at: {project_memories_dir}"
            )

        result = {}

        # Aggregate PM memories
        if pm_memories:
            aggregated_pm = self._aggregate_memories(pm_memories)
            result["actual_memories"] = aggregated_pm
            # Count actual memory items in aggregated content
            memory_items = [
                line.strip()
                for line in aggregated_pm.split("\n")
                if line.strip().startswith("-")
            ]
            if memory_items:
                self.logger.info(
                    f"Aggregated PM memory: {len(memory_items)} total items from {len(pm_memories)} source(s)"
                )
            else:
                self.logger.debug(
                    f"Aggregated PM memory from {len(pm_memories)} source(s) (no items)"
                )

        # Store agent memories (already aggregated per agent)
        if agent_memories_dict:
            result["agent_memories"] = agent_memories_dict
            for agent_name, memory_content in agent_memories_dict.items():
                # Count actual memory items
                memory_items = [
                    line.strip()
                    for line in memory_content.split("\n")
                    if line.strip().startswith("-")
                ]
                if memory_items:
                    self.logger.debug(
                        f"Aggregated {agent_name} memory: {len(memory_items)} items"
                    )
                else:
                    self.logger.debug(f"Aggregated {agent_name} memory: no items")

        # Log summary
        if self._stats["loaded_count"] > 0 or self._stats["skipped_count"] > 0:
            agent_count = len(agent_memories_dict) if agent_memories_dict else 0
            pm_loaded = bool(result.get("actual_memories"))

            summary_parts = []
            if pm_loaded:
                summary_parts.append("PM memory loaded")
            if agent_count > 0:
                summary_parts.append(f"{agent_count} agent memories loaded")
            if self._stats["skipped_count"] > 0:
                summary_parts.append(
                    f"{self._stats['skipped_count']} non-deployed agent memories skipped"
                )

            self.logger.info(f"Memory loading complete: {' | '.join(summary_parts)}")

            if len(deployed_agents) > 0:
                self.logger.debug(
                    f"Deployed agents available for memory loading: {', '.join(sorted(deployed_agents))}"
                )

        return result

    def _load_memories_from_directory(
        self,
        memories_dir: Path,
        deployed_agents: Set[str],
        pm_memories: List[Dict[str, Any]],
        agent_memories_dict: Dict[str, Any],
        source: str,
    ) -> None:
        """
        Load memories from a specific directory.

        Args:
            memories_dir: Directory to load memories from
            deployed_agents: Set of deployed agent names
            pm_memories: List to append PM memories to
            agent_memories_dict: Dict to store agent memories
            source: Source label ("user" or "project")
        """
        # Load PM memories (always loaded)
        pm_memory_path = memories_dir / "PM_memories.md"
        old_pm_path = memories_dir / "PM.md"

        # Migrate from old PM.md if needed
        if not pm_memory_path.exists() and old_pm_path.exists():
            self._migrate_legacy_file(old_pm_path, pm_memory_path)

        if pm_memory_path.exists():
            try:
                loaded_content = pm_memory_path.read_text(encoding="utf-8")
                if loaded_content:
                    pm_memories.append(
                        {
                            "source": source,
                            "content": loaded_content,
                            "path": pm_memory_path,
                        }
                    )
                    # Count actual memory items (lines starting with "-")
                    memory_items = [
                        line.strip()
                        for line in loaded_content.split("\n")
                        if line.strip().startswith("-")
                    ]
                    if memory_items:
                        self.logger.info(
                            f"Loaded {source} PM memory: {len(memory_items)} items"
                        )
                    else:
                        # Skip logging if no actual memory items
                        self.logger.debug(
                            f"Skipped {source} PM memory: {pm_memory_path} (no memory items)"
                        )
                    self._stats["loaded_count"] += 1
            except Exception as e:
                self.logger.error(
                    f"Failed to load PM memory from {pm_memory_path}: {e}"
                )

        # Migrate old format memory files
        for old_file in memories_dir.glob("*.md"):
            # Skip files already in correct format and special files
            if old_file.name.endswith("_memories.md") or old_file.name in [
                "PM.md",
                "README.md",
            ]:
                continue

            # Determine new name based on old format
            if old_file.stem.endswith("_agent"):
                # Old format: {agent_name}_agent.md -> {agent_name}_memories.md
                agent_name = old_file.stem[:-6]  # Remove "_agent" suffix
                new_path = memories_dir / f"{agent_name}_memories.md"
                if not new_path.exists():
                    self._migrate_legacy_file(old_file, new_path)
            else:
                # Intermediate format: {agent_name}.md -> {agent_name}_memories.md
                agent_name = old_file.stem
                new_path = memories_dir / f"{agent_name}_memories.md"
                if not new_path.exists():
                    self._migrate_legacy_file(old_file, new_path)

        # Load agent memories (only for deployed agents)
        for memory_file in memories_dir.glob("*_memories.md"):
            # Skip PM_memories.md as we already handled it
            if memory_file.name == "PM_memories.md":
                continue

            # Extract agent name from file (remove "_memories" suffix)
            agent_name = memory_file.stem[:-9]  # Remove "_memories" suffix

            # Check if agent is deployed
            if agent_name in deployed_agents:
                try:
                    loaded_content = memory_file.read_text(encoding="utf-8")
                    if loaded_content:
                        # Store or merge agent memories
                        if agent_name not in agent_memories_dict:
                            agent_memories_dict[agent_name] = []

                        # If it's a list, append the new memory entry
                        if isinstance(agent_memories_dict[agent_name], list):
                            agent_memories_dict[agent_name].append(
                                {
                                    "source": source,
                                    "content": loaded_content,
                                    "path": memory_file,
                                }
                            )

                        # Count actual memory items (lines starting with "-")
                        memory_items = [
                            line.strip()
                            for line in loaded_content.split("\n")
                            if line.strip().startswith("-")
                        ]
                        if memory_items:
                            self.logger.info(
                                f"Loaded {source} memory for {agent_name}: {len(memory_items)} items"
                            )
                        else:
                            # Skip logging if no actual memory items
                            self.logger.debug(
                                f"Skipped {source} memory for {agent_name}: {memory_file.name} (no memory items)"
                            )
                        self._stats["loaded_count"] += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to load agent memory from {memory_file}: {e}"
                    )
            else:
                # Log skipped memories only if they contain actual items
                try:
                    loaded_content = memory_file.read_text(encoding="utf-8")
                    memory_items = [
                        line.strip()
                        for line in loaded_content.split("\n")
                        if line.strip().startswith("-")
                    ]
                    if memory_items:
                        self.logger.info(
                            f"Skipped {source} memory: {memory_file.name} (agent '{agent_name}' not deployed, {len(memory_items)} items)"
                        )
                    else:
                        # Don't log if file has no actual memory items
                        self.logger.debug(
                            f"Skipped {source} memory: {memory_file.name} (agent '{agent_name}' not deployed, no items)"
                        )
                except Exception:
                    # If we can't read the file, just skip silently
                    pass

                # Detect naming mismatches
                alt_name = (
                    agent_name.replace("_", "-")
                    if "_" in agent_name
                    else agent_name.replace("-", "_")
                )
                if alt_name in deployed_agents:
                    self.logger.warning(
                        f"Naming mismatch detected: Memory file uses '{agent_name}' but deployed agent is '{alt_name}'. "
                        f"Consider renaming {memory_file.name} to {alt_name}_memories.md"
                    )

                self._stats["skipped_count"] += 1

        # Aggregate agent memories for this directory
        for agent_name in list(agent_memories_dict.keys()):
            if (
                isinstance(agent_memories_dict[agent_name], list)
                and agent_memories_dict[agent_name]
            ):
                # Aggregate memories for this agent
                aggregated = self._aggregate_memories(agent_memories_dict[agent_name])
                agent_memories_dict[agent_name] = aggregated

    def _aggregate_memories(self, memory_entries: List[Dict[str, Any]]) -> str:
        """
        Aggregate multiple memory entries into a single memory string.

        Strategy:
        - Preserve all unique bullet-point items (lines starting with -)
        - Remove exact duplicates
        - Project-level memories take precedence over user-level

        Args:
            memory_entries: List of memory entries with source, content, and path

        Returns:
            Aggregated memory content as a string
        """
        if not memory_entries:
            return ""

        # If only one entry, return it as-is
        if len(memory_entries) == 1:
            return memory_entries[0]["content"]

        # Parse all memories into a simple list
        all_items = {}  # Dict to track items and their source
        metadata_lines = []
        agent_id = None

        for entry in memory_entries:
            content = entry["content"]
            source = entry["source"]

            for line in content.split("\n"):
                # Check for header to extract agent_id
                if line.startswith("# Agent Memory:"):
                    agent_id = line.replace("# Agent Memory:", "").strip()
                # Check for metadata lines
                elif line.startswith("<!-- ") and line.endswith(" -->"):
                    # Only keep metadata from project source or if not already present
                    if source == "project" or line not in metadata_lines:
                        metadata_lines.append(line)
                # Check for list items
                elif line.strip().startswith("-"):
                    # Normalize the item for comparison
                    item_text = line.strip()
                    normalized = item_text.lstrip("- ").strip().lower()

                    # Add item if new or if project source overrides user source
                    if normalized not in all_items or source == "project":
                        all_items[normalized] = (item_text, source)

        # Build aggregated content
        lines = []

        # Add header
        if agent_id:
            lines.append(f"# Agent Memory: {agent_id}")
        else:
            lines.append("# Agent Memory")

        # Add latest timestamp
        lines.append(
            f"<!-- Last Updated: {datetime.now(timezone.utc).isoformat()}Z -->"
        )
        lines.append("")

        # Add all unique items (sorted for consistency)
        for normalized_key in sorted(all_items.keys()):
            item_text, _ = all_items[normalized_key]
            lines.append(item_text)

        return "\n".join(lines)

    def _migrate_legacy_file(self, old_path: Path, new_path: Path) -> None:
        """
        Migrate memory file from old naming convention to new.

        WHY: Supports backward compatibility by automatically migrating from
        the old {agent_id}_agent.md and {agent_id}.md formats to the new
        {agent_id}_memories.md format.

        Args:
            old_path: Path to the old file
            new_path: Path to the new file
        """
        if old_path.exists() and not new_path.exists():
            try:
                # Read content from old file
                content = old_path.read_text(encoding="utf-8")
                # Write to new file
                new_path.write_text(content, encoding="utf-8")
                # Remove old file
                old_path.unlink()
                self.logger.info(
                    f"Migrated memory file from {old_path.name} to {new_path.name}"
                )
            except Exception as e:
                self.logger.error(f"Failed to migrate memory file {old_path.name}: {e}")

    def _get_deployed_agents(self) -> Set[str]:
        """
        Get a set of deployed agent names from .claude/agents/ directories.

        Returns:
            Set of agent names (file stems) that are deployed
        """
        # Try to get from cache first
        cached = self._cache_manager.get_deployed_agents()
        if cached is not None:
            return cached

        # Cache miss - perform actual scan
        self.logger.debug("Scanning for deployed agents (cache miss)")
        deployed = set()

        # Check project-level .claude/agents/
        project_agents_dir = Path.cwd() / ".claude" / "agents"
        if project_agents_dir.exists():
            for agent_file in project_agents_dir.glob("*.md"):
                agent_name = agent_file.stem
                if agent_name.upper() != "README":
                    deployed.add(agent_name)
                    self.logger.debug(f"Found deployed agent: {agent_name}")

        # Cache the result
        self._cache_manager.set_deployed_agents(deployed)

        return deployed
