"""
Memory CRUD Service
===================

WHY: This service encapsulates all CRUD operations for agent memories, extracting
logic from the CLI commands to follow Single Responsibility Principle. It provides
a clean interface for memory initialization, reading, updating, and deletion operations.

DESIGN DECISIONS:
- Separates memory CRUD logic from CLI command implementation
- Provides structured data returns for programmatic access
- Handles memory validation and error recovery
- Supports both text and structured output formats
- Integrates with AgentMemoryManager for actual operations
- Maintains backward compatibility with existing memory formats
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.logger import get_logger
from ...services.agents.memory.agent_memory_manager import AgentMemoryManager


class IMemoryCRUDService(ABC):
    """Interface for memory CRUD operations."""

    @abstractmethod
    def create_memory(
        self, agent_id: str, template_type: str = "default"
    ) -> Dict[str, Any]:
        """
        Create new memory file for an agent.

        Args:
            agent_id: ID of the agent
            template_type: Type of template to use

        Returns:
            Dictionary with success status and file path
        """

    @abstractmethod
    def read_memory(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Read memory content for one or all agents.

        Args:
            agent_id: Optional agent ID, None for all agents

        Returns:
            Dictionary with memory content and metadata
        """

    @abstractmethod
    def update_memory(
        self, agent_id: str, section: str, content: str
    ) -> Dict[str, Any]:
        """
        Add learning entry to agent memory.

        Args:
            agent_id: ID of the agent
            section: Memory section to update
            content: Learning content to add

        Returns:
            Dictionary with success status and update details
        """

    @abstractmethod
    def delete_memory(self, agent_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete memory file for an agent.

        Args:
            agent_id: ID of the agent
            confirm: Confirmation flag for deletion

        Returns:
            Dictionary with deletion status
        """

    @abstractmethod
    def list_memories(self, include_stats: bool = True) -> Dict[str, Any]:
        """
        List all memory files with optional statistics.

        Args:
            include_stats: Include file statistics

        Returns:
            Dictionary with memory files list and stats
        """

    @abstractmethod
    def clean_memory(
        self, agent_id: Optional[str] = None, dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up memory files (remove old/unused).

        Args:
            agent_id: Optional specific agent to clean
            dry_run: Preview changes without executing

        Returns:
            Dictionary with cleanup results
        """

    @abstractmethod
    def init_project_memories(self) -> Dict[str, Any]:
        """
        Initialize project-specific memories task.

        Returns:
            Dictionary with initialization task details
        """


class MemoryCRUDService(IMemoryCRUDService):
    """Service for managing memory CRUD operations with robust error handling."""

    def __init__(self, memory_manager: Optional[AgentMemoryManager] = None):
        """
        Initialize the memory CRUD service.

        Args:
            memory_manager: Optional memory manager instance
        """
        self.logger = get_logger(__name__)
        self._memory_manager = memory_manager

    def _get_memory_manager(self) -> AgentMemoryManager:
        """Get or create memory manager instance."""
        if self._memory_manager is None:
            from ...core.shared.config_loader import ConfigLoader

            config_loader = ConfigLoader()
            config = config_loader.load_main_config()
            # Use CLAUDE_MPM_USER_PWD if available
            user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD", Path.cwd())
            current_dir = Path(user_pwd)
            self._memory_manager = AgentMemoryManager(config, current_dir)
        return self._memory_manager

    def create_memory(
        self, agent_id: str, template_type: str = "default"
    ) -> Dict[str, Any]:
        """
        Create new memory file for an agent.

        WHY: Initializes a new memory file with appropriate template structure
        for the specified agent, ensuring consistent format across all memories.
        """
        try:
            memory_manager = self._get_memory_manager()

            # Check if memory already exists
            existing_content = memory_manager.load_agent_memory(agent_id)
            if existing_content:
                return {
                    "success": False,
                    "error": f"Memory already exists for agent: {agent_id}",
                    "agent_id": agent_id,
                    "existing_file": str(
                        memory_manager.memories_dir / f"{agent_id}_memories.md"
                    ),
                }

            # Create memory with default template
            template_content = memory_manager.template_generator.generate_template(
                agent_id, template_type
            )

            memory_file = memory_manager.memories_dir / f"{agent_id}_memories.md"
            memory_file.parent.mkdir(parents=True, exist_ok=True)
            memory_file.write_text(template_content)

            self.logger.info(f"Created memory file for agent: {agent_id}")

            return {
                "success": True,
                "agent_id": agent_id,
                "file_path": str(memory_file),
                "template_type": template_type,
                "message": f"Memory created for agent: {agent_id}",
            }

        except Exception as e:
            self.logger.error(
                f"Error creating memory for {agent_id}: {e}", exc_info=True
            )
            return {"success": False, "error": str(e), "agent_id": agent_id}

    def read_memory(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Read memory content for one or all agents.

        WHY: Provides access to memory content for inspection, debugging,
        or integration with other tools.
        """
        try:
            memory_manager = self._get_memory_manager()

            if agent_id:
                # Read single agent memory
                memory_content = memory_manager.load_agent_memory(agent_id)

                if not memory_content:
                    return {
                        "success": False,
                        "error": f"No memory found for agent: {agent_id}",
                        "agent_id": agent_id,
                    }

                memory_file = memory_manager.memories_dir / f"{agent_id}_memories.md"
                file_stats = None
                if memory_file.exists():
                    stat = memory_file.stat()
                    file_stats = {
                        "size_kb": stat.st_size / 1024,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                        "path": str(memory_file),
                    }

                return {
                    "success": True,
                    "agent_id": agent_id,
                    "content": memory_content,
                    "file_stats": file_stats,
                }

            # Read all agent memories
            memory_dir = memory_manager.memories_dir
            if not memory_dir.exists():
                return {
                    "success": True,
                    "agents": {},
                    "memory_directory": str(memory_dir),
                    "exists": False,
                }

            agents = {}
            for memory_file in self._get_memory_files(memory_dir):
                agent_id = self._extract_agent_id(memory_file)
                try:
                    memory_content = memory_manager.load_agent_memory(agent_id)
                    if memory_content:
                        stat = memory_file.stat()
                        agents[agent_id] = {
                            "content": memory_content,
                            "file_stats": {
                                "size_kb": stat.st_size / 1024,
                                "modified": datetime.fromtimestamp(
                                    stat.st_mtime, tz=timezone.utc
                                ).isoformat(),
                                "path": str(memory_file),
                            },
                        }
                except Exception as e:
                    self.logger.warning(f"Error reading memory for {agent_id}: {e}")

            return {
                "success": True,
                "agents": agents,
                "memory_directory": str(memory_dir),
                "exists": True,
                "agent_count": len(agents),
            }

        except Exception as e:
            self.logger.error(f"Error reading memory: {e}", exc_info=True)
            return {"success": False, "error": str(e), "agent_id": agent_id}

    def update_memory(
        self, agent_id: str, section: str, content: str
    ) -> Dict[str, Any]:
        """
        Add learning entry to agent memory.

        WHY: Allows manual injection of learnings for testing, correction,
        or knowledge enhancement purposes.
        """
        try:
            memory_manager = self._get_memory_manager()

            # Map learning types to appropriate sections
            section_map = {
                "pattern": "Project Architecture",
                "error": "Common Mistakes to Avoid",
                "optimization": "Implementation Guidelines",
                "preference": "Implementation Guidelines",
                "context": "Current Technical Context",
            }

            section_name = section_map.get(section, section)

            # Attempt to update memory
            success = memory_manager.update_agent_memory(
                agent_id, section_name, content
            )

            if success:
                self.logger.info(
                    f"Added learning to {agent_id} memory in section: {section_name}"
                )
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "section": section_name,
                    "content_preview": content[:100]
                    + ("..." if len(content) > 100 else ""),
                    "message": f"Learning added to {agent_id} memory",
                }
            return {
                "success": False,
                "agent_id": agent_id,
                "section": section_name,
                "error": "Failed to add learning - memory file may be at size limit or section may be full",
            }

        except Exception as e:
            self.logger.error(
                f"Error updating memory for {agent_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "agent_id": agent_id,
                "section": section,
            }

    def delete_memory(self, agent_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete memory file for an agent.

        WHY: Provides controlled deletion of memory files with safety checks
        to prevent accidental data loss.
        """
        try:
            if not confirm:
                return {
                    "success": False,
                    "error": "Deletion requires confirmation flag",
                    "agent_id": agent_id,
                    "hint": "Use --confirm flag to delete",
                }

            memory_manager = self._get_memory_manager()
            memory_file = memory_manager.memories_dir / f"{agent_id}_memories.md"

            if not memory_file.exists():
                # Check for alternative formats
                alt_files = [
                    memory_manager.memories_dir / f"{agent_id}_agent.md",
                    memory_manager.memories_dir / f"{agent_id}.md",
                ]

                for alt_file in alt_files:
                    if alt_file.exists():
                        memory_file = alt_file
                        break
                else:
                    return {
                        "success": False,
                        "error": f"No memory file found for agent: {agent_id}",
                        "agent_id": agent_id,
                    }

            # Get file size before deletion
            file_size_kb = memory_file.stat().st_size / 1024

            # Delete the file
            memory_file.unlink()
            self.logger.info(f"Deleted memory file for agent: {agent_id}")

            return {
                "success": True,
                "agent_id": agent_id,
                "deleted_file": str(memory_file),
                "file_size_kb": file_size_kb,
                "message": f"Memory deleted for agent: {agent_id}",
            }

        except Exception as e:
            self.logger.error(
                f"Error deleting memory for {agent_id}: {e}", exc_info=True
            )
            return {"success": False, "error": str(e), "agent_id": agent_id}

    def list_memories(self, include_stats: bool = True) -> Dict[str, Any]:
        """
        List all memory files with optional statistics.

        WHY: Provides overview of all memories in the system for management
        and monitoring purposes.
        """
        try:
            memory_manager = self._get_memory_manager()
            memory_dir = memory_manager.memories_dir

            if not memory_dir.exists():
                return {
                    "success": True,
                    "memory_directory": str(memory_dir),
                    "exists": False,
                    "memories": [],
                    "total_size_kb": 0,
                    "total_files": 0,
                }

            memories = []
            total_size = 0

            for memory_file in self._get_memory_files(memory_dir):
                agent_id = self._extract_agent_id(memory_file)

                memory_info = {
                    "agent_id": agent_id,
                    "file": memory_file.name,
                    "path": str(memory_file),
                }

                if include_stats:
                    stat = memory_file.stat()
                    memory_info.update(
                        {
                            "size_kb": stat.st_size / 1024,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime, tz=timezone.utc
                            ).isoformat(),
                            "created": datetime.fromtimestamp(
                                stat.st_ctime, tz=timezone.utc
                            ).isoformat(),
                        }
                    )
                    total_size += stat.st_size

                memories.append(memory_info)

            return {
                "success": True,
                "memory_directory": str(memory_dir),
                "exists": True,
                "memories": sorted(memories, key=lambda x: x["agent_id"]),
                "total_size_kb": total_size / 1024 if include_stats else None,
                "total_files": len(memories),
            }

        except Exception as e:
            self.logger.error(f"Error listing memories: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def clean_memory(
        self, agent_id: Optional[str] = None, dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up memory files (remove old/unused).

        WHY: Memory files can accumulate over time. This provides controlled
        cleanup to save disk space while preserving important data.

        DESIGN DECISION: For Phase 1, this is a stub implementation.
        Full cleanup logic will be implemented based on usage patterns.
        """
        try:
            memory_manager = self._get_memory_manager()
            memory_dir = memory_manager.memories_dir

            if not memory_dir.exists():
                return {
                    "success": True,
                    "message": "No memory directory found - nothing to clean",
                    "cleaned_files": [],
                    "dry_run": dry_run,
                }

            memory_files = list(self._get_memory_files(memory_dir))
            if not memory_files:
                return {
                    "success": True,
                    "message": "No memory files found - nothing to clean",
                    "cleaned_files": [],
                    "dry_run": dry_run,
                }

            # For Phase 1, just identify candidates for cleanup
            cleanup_candidates = []

            for memory_file in memory_files:
                agent_id_file = self._extract_agent_id(memory_file)

                # Skip if specific agent requested and doesn't match
                if agent_id and agent_id_file != agent_id:
                    continue

                stat = memory_file.stat()
                age_days = (
                    datetime.now(timezone.utc)
                    - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                ).days

                # Identify files older than 30 days as candidates
                if age_days > 30:
                    cleanup_candidates.append(
                        {
                            "agent_id": agent_id_file,
                            "file": str(memory_file),
                            "size_kb": stat.st_size / 1024,
                            "age_days": age_days,
                            "reason": "File older than 30 days with no recent access",
                        }
                    )

            if dry_run:
                return {
                    "success": True,
                    "message": "Cleanup preview (dry run)",
                    "cleanup_candidates": cleanup_candidates,
                    "dry_run": True,
                    "note": "Cleanup not yet implemented in Phase 1",
                }
            # Phase 1: Don't actually delete anything
            return {
                "success": True,
                "message": "Cleanup not yet implemented in Phase 1",
                "cleanup_candidates": cleanup_candidates,
                "dry_run": False,
                "cleaned_files": [],
                "note": "Future cleanup will remove old/corrupted files",
            }

        except Exception as e:
            self.logger.error(f"Error cleaning memory: {e}", exc_info=True)
            return {"success": False, "error": str(e), "agent_id": agent_id}

    def init_project_memories(self) -> Dict[str, Any]:
        """
        Initialize project-specific memories task.

        WHY: When starting with a new project, agents need project-specific
        knowledge beyond what automatic analysis provides. This creates a
        task description for comprehensive project scanning.
        """
        try:
            task_data = {
                "task": "Initialize Project-Specific Memories",
                "description": "Analyze project structure and create targeted memories for agents",
                "instructions": [
                    "Scan the project structure, documentation, and source code",
                    "Identify key patterns, conventions, and project-specific knowledge",
                    "Create targeted memories for each agent type",
                    "Use 'claude-mpm memory add <agent> <type> \"<content>\"' commands",
                ],
                "focus_areas": [
                    "Architectural patterns and design decisions",
                    "Coding conventions from actual source code",
                    "Key modules, APIs, and integration points",
                    "Testing patterns and quality standards",
                    "Performance considerations specific to this project",
                    "Common pitfalls based on the codebase",
                    "Domain-specific terminology and concepts",
                ],
                "example_commands": [
                    'claude-mpm memory add engineer pattern "Use dependency injection with @inject"',
                    'claude-mpm memory add qa pattern "Test files follow test_<module>_<feature>.py"',
                    'claude-mpm memory add research context "Project uses microservices architecture"',
                ],
                "analysis_targets": [
                    "Project structure and documentation",
                    "Source code for patterns and conventions",
                    "Testing patterns and quality standards",
                    "Performance considerations",
                    "Domain-specific terminology",
                ],
            }

            return {
                "success": True,
                "task_data": task_data,
                "message": "Memory initialization task created",
            }

        except Exception as e:
            self.logger.error(f"Error creating initialization task: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # Helper methods
    def _get_memory_files(self, memory_dir: Path) -> List[Path]:
        """Get all memory files supporting various formats."""
        memory_files = []

        # Support new format
        memory_files.extend(memory_dir.glob("*_memories.md"))

        # Support old formats for backward compatibility
        memory_files.extend(memory_dir.glob("*_agent.md"))
        memory_files.extend(
            [
                f
                for f in memory_dir.glob("*.md")
                if f.name != "README.md"
                and not f.name.endswith("_memories.md")
                and not f.name.endswith("_agent.md")
            ]
        )

        return sorted(set(memory_files))

    def _extract_agent_id(self, file_path: Path) -> str:
        """Extract agent ID from various file name formats."""
        if file_path.name.endswith("_memories.md"):
            return file_path.stem[:-9]  # Remove "_memories"
        if file_path.name.endswith("_agent.md"):
            return file_path.stem[:-6]  # Remove "_agent"
        return file_path.stem
