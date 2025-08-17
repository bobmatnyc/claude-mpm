from pathlib import Path

#!/usr/bin/env python3
"""
Agent Memory Manager Service
===========================

Manages agent memory files with size limits and validation.

This service provides:
- Memory file operations (load, save, validate)
- Size limit enforcement (80KB default)
- Auto-truncation when limits exceeded
- Default memory template creation
- Section management with item limits
- Timestamp updates
- Directory initialization with README

Memory files are stored in .claude-mpm/memories/ directory
following the naming convention: {agent_id}_agent.md
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.config import Config
from claude_mpm.core.interfaces import MemoryServiceInterface
from claude_mpm.services.project.analyzer import ProjectAnalyzer
from claude_mpm.core.unified_paths import get_path_manager

from .analyzer import MemoryAnalyzer
from .content_manager import MemoryContentManager
from .template_generator import MemoryTemplateGenerator


class AgentMemoryManager(MemoryServiceInterface):
    """Manages agent memory files with size limits and validation.

    WHY: Agents need to accumulate project-specific knowledge over time to become
    more effective. This service manages persistent memory files that agents can
    read before tasks and update with new learnings.

    DESIGN DECISION: Memory files are stored in .claude-mpm/memories/ (not project root)
    to keep them organized and separate from other project files. Files follow a
    standardized markdown format with enforced size limits to prevent unbounded growth.

    The 80KB limit (~20k tokens) balances comprehensive knowledge storage with
    reasonable context size for agent prompts.
    """

    # Default limits - will be overridden by configuration
    # Updated to support 20k tokens (~80KB) for enhanced memory capacity
    DEFAULT_MEMORY_LIMITS = {
        "max_file_size_kb": 80,  # Increased from 8KB to 80KB (20k tokens)
        "max_sections": 10,
        "max_items_per_section": 15,
        "max_line_length": 120,
    }

    REQUIRED_SECTIONS = [
        "Project Architecture",
        "Implementation Guidelines",
        "Common Mistakes to Avoid",
        "Current Technical Context",
    ]

    def __init__(
        self, config: Optional[Config] = None, working_directory: Optional[Path] = None
    ):
        """Initialize the memory manager.

        Sets up the memories directory and ensures it exists with proper README.

        Args:
            config: Optional Config object. If not provided, will create default Config.
            working_directory: Optional working directory. If not provided, uses current working directory.
        """
        # Initialize logger using the same pattern as LoggerMixin
        self._logger_instance = None
        self._logger_name = None

        self.config = config or Config()
        self.project_root = get_path_manager().get_project_root()
        # Use current working directory by default, not project root
        self.working_directory = working_directory or Path(os.getcwd())
        self.memories_dir = self.working_directory / ".claude-mpm" / "memories"
        self._ensure_memories_directory()

        # Initialize memory limits from configuration
        self._init_memory_limits()

        # Initialize project analyzer for context-aware memory creation
        self.project_analyzer = ProjectAnalyzer(self.config, self.working_directory)

        # Initialize component services
        self.template_generator = MemoryTemplateGenerator(
            self.config, self.working_directory, self.project_analyzer
        )
        self.content_manager = MemoryContentManager(self.memory_limits)
        self.analyzer = MemoryAnalyzer(
            self.memories_dir,
            self.memory_limits,
            self.agent_overrides,
            self._get_agent_limits,
            self._get_agent_auto_learning,
            self.content_manager,
        )

    @property
    def logger(self):
        """Get or create the logger instance (like LoggerMixin)."""
        if self._logger_instance is None:
            if self._logger_name:
                logger_name = self._logger_name
            else:
                module = self.__class__.__module__
                class_name = self.__class__.__name__

                if module and module != "__main__":
                    logger_name = f"{module}.{class_name}"
                else:
                    logger_name = class_name

            self._logger_instance = logging.getLogger(logger_name)

        return self._logger_instance

    def _init_memory_limits(self):
        """Initialize memory limits from configuration.

        WHY: Allows configuration-driven memory limits instead of hardcoded values.
        Supports agent-specific overrides for different memory requirements.
        """
        # Check if memory system is enabled
        self.memory_enabled = self.config.get("memory.enabled", True)
        self.auto_learning = self.config.get(
            "memory.auto_learning", True
        )  # Changed default to True

        # Load default limits from configuration
        config_limits = self.config.get("memory.limits", {})
        self.memory_limits = {
            "max_file_size_kb": config_limits.get(
                "default_size_kb", self.DEFAULT_MEMORY_LIMITS["max_file_size_kb"]
            ),
            "max_sections": config_limits.get(
                "max_sections", self.DEFAULT_MEMORY_LIMITS["max_sections"]
            ),
            "max_items_per_section": config_limits.get(
                "max_items_per_section",
                self.DEFAULT_MEMORY_LIMITS["max_items_per_section"],
            ),
            "max_line_length": config_limits.get(
                "max_line_length", self.DEFAULT_MEMORY_LIMITS["max_line_length"]
            ),
        }

        # Load agent-specific overrides
        self.agent_overrides = self.config.get("memory.agent_overrides", {})

    def _get_agent_limits(self, agent_id: str) -> Dict[str, Any]:
        """Get memory limits for specific agent, including overrides.

        WHY: Different agents may need different memory capacities. Research agents
        might need larger memory for comprehensive findings, while simple agents
        can work with smaller limits.

        Args:
            agent_id: The agent identifier

        Returns:
            Dict containing the effective limits for this agent
        """
        # Start with default limits
        limits = self.memory_limits.copy()

        # Apply agent-specific overrides if they exist
        if agent_id in self.agent_overrides:
            overrides = self.agent_overrides[agent_id]
            if "size_kb" in overrides:
                limits["max_file_size_kb"] = overrides["size_kb"]

        return limits

    def _get_agent_auto_learning(self, agent_id: str) -> bool:
        """Check if auto-learning is enabled for specific agent.

        Args:
            agent_id: The agent identifier

        Returns:
            bool: True if auto-learning is enabled for this agent
        """
        # Check agent-specific override first
        if agent_id in self.agent_overrides:
            return self.agent_overrides[agent_id].get(
                "auto_learning", self.auto_learning
            )

        # Fall back to global setting
        return self.auto_learning

    def load_agent_memory(self, agent_id: str) -> str:
        """Load agent memory file content.

        WHY: Agents need to read their accumulated knowledge before starting tasks
        to apply learned patterns and avoid repeated mistakes.

        Args:
            agent_id: The agent identifier (e.g., 'research', 'engineer')

        Returns:
            str: The memory file content, creating default if doesn't exist
        """
        memory_file = self.memories_dir / f"{agent_id}_agent.md"

        if not memory_file.exists():
            self.logger.info(f"Creating default memory for agent: {agent_id}")
            return self._create_default_memory(agent_id)

        try:
            content = memory_file.read_text(encoding="utf-8")
            return self.content_manager.validate_and_repair(content, agent_id)
        except Exception as e:
            self.logger.error(f"Error reading memory file for {agent_id}: {e}")
            # Return default memory on error - never fail
            return self._create_default_memory(agent_id)

    def update_agent_memory(self, agent_id: str, section: str, new_item: str) -> bool:
        """Add new learning item to specified section.

        WHY: Agents discover new patterns and insights during task execution that
        should be preserved for future tasks. This method adds new learnings while
        enforcing size limits to prevent unbounded growth.

        Args:
            agent_id: The agent identifier
            section: The section name to add the item to
            new_item: The learning item to add

        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            current_memory = self.load_agent_memory(agent_id)
            updated_memory = self.content_manager.add_item_to_section(
                current_memory, section, new_item
            )

            # Enforce limits
            agent_limits = self._get_agent_limits(agent_id)
            if self.content_manager.exceeds_limits(updated_memory, agent_limits):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                updated_memory = self.content_manager.truncate_to_limits(
                    updated_memory, agent_limits
                )

            # Save with timestamp
            return self._save_memory_file(agent_id, updated_memory)
        except Exception as e:
            self.logger.error(f"Error updating memory for {agent_id}: {e}")
            # Never fail on memory errors
            return False

    def add_learning(self, agent_id: str, learning_type: str, content: str) -> bool:
        """Add structured learning to appropriate section.

        WHY: Different types of learnings belong in different sections for better
        organization and retrieval. This method maps learning types to appropriate
        sections automatically.

        Args:
            agent_id: The agent identifier
            learning_type: Type of learning (pattern, architecture, guideline, etc.)
            content: The learning content

        Returns:
            bool: True if learning was added successfully
        """
        section_mapping = {
            "pattern": "Coding Patterns Learned",
            "architecture": "Project Architecture",
            "guideline": "Implementation Guidelines",
            "mistake": "Common Mistakes to Avoid",
            "strategy": "Effective Strategies",
            "integration": "Integration Points",
            "performance": "Performance Considerations",
            "domain": "Domain-Specific Knowledge",
            "context": "Current Technical Context",
        }

        section = section_mapping.get(learning_type, "Recent Learnings")
        success = self.update_agent_memory(agent_id, section, content)

        # Socket.IO notifications removed - memory manager works independently

        return success

    def _create_default_memory(self, agent_id: str) -> str:
        """Create project-specific default memory file for agent.

        WHY: Instead of generic templates, agents need project-specific knowledge
        from the start. This analyzes the current project and creates contextual
        memories with actual project characteristics.

        Args:
            agent_id: The agent identifier

        Returns:
            str: The project-specific memory template content
        """
        # Get limits for this agent
        limits = self._get_agent_limits(agent_id)

        # Delegate to template generator
        template = self.template_generator.create_default_memory(agent_id, limits)

        # Save default file
        try:
            memory_file = self.memories_dir / f"{agent_id}_agent.md"
            memory_file.write_text(template, encoding="utf-8")
            self.logger.info(f"Created project-specific memory file for {agent_id}")

        except Exception as e:
            self.logger.error(f"Error saving default memory for {agent_id}: {e}")

        return template

    def _save_memory_file(self, agent_id: str, content: str) -> bool:
        """Save memory content to file.

        WHY: Memory updates need to be persisted atomically to prevent corruption
        and ensure learnings are preserved across agent invocations.

        Args:
            agent_id: Agent identifier
            content: Content to save

        Returns:
            bool: True if save succeeded
        """
        try:
            memory_file = self.memories_dir / f"{agent_id}_agent.md"
            memory_file.write_text(content, encoding="utf-8")
            self.logger.debug(f"Saved memory for {agent_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving memory for {agent_id}: {e}")
            return False

    def optimize_memory(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Optimize agent memory by consolidating/cleaning memories.

        WHY: Over time, memory files accumulate redundant or outdated information.
        This method delegates to the memory optimizer service to clean up and
        consolidate memories while preserving important information.

        Args:
            agent_id: Optional specific agent ID. If None, optimizes all agents.

        Returns:
            Dict containing optimization results and statistics
        """
        try:
            from claude_mpm.services.memory.optimizer import MemoryOptimizer

            optimizer = MemoryOptimizer(self.config, self.working_directory)

            if agent_id:
                result = optimizer.optimize_agent_memory(agent_id)
                self.logger.info(f"Optimized memory for agent: {agent_id}")
            else:
                result = optimizer.optimize_all_memories()
                self.logger.info("Optimized all agent memories")

            return result
        except Exception as e:
            self.logger.error(f"Error optimizing memory: {e}")
            return {"success": False, "error": str(e)}

    def build_memories_from_docs(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build agent memories from project documentation.

        WHY: Project documentation contains valuable knowledge that should be
        extracted and assigned to appropriate agents for better context awareness.

        Args:
            force_rebuild: If True, rebuilds even if docs haven't changed

        Returns:
            Dict containing build results and statistics
        """
        try:
            from claude_mpm.services.memory.builder import MemoryBuilder

            builder = MemoryBuilder(self.config, self.working_directory)

            result = builder.build_from_documentation(force_rebuild)
            self.logger.info("Built memories from documentation")

            return result
        except Exception as e:
            self.logger.error(f"Error building memories from docs: {e}")
            return {"success": False, "error": str(e)}

    def route_memory_command(
        self, content: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Route memory command to appropriate agent via PM delegation.

        WHY: Memory commands like "remember this for next time" need to be analyzed
        to determine which agent should store the information. This method provides
        routing logic for PM agent delegation.

        Args:
            content: The content to be remembered
            context: Optional context for routing decisions

        Returns:
            Dict containing routing decision and reasoning
        """
        try:
            from claude_mpm.services.memory.router import MemoryRouter

            router = MemoryRouter(self.config)

            routing_result = router.analyze_and_route(content, context)
            self.logger.debug(
                f"Routed memory command: {routing_result['target_agent']}"
            )

            return routing_result
        except Exception as e:
            self.logger.error(f"Error routing memory command: {e}")
            return {"success": False, "error": str(e)}

    def get_memory_status(self) -> Dict[str, Any]:
        """Get comprehensive memory system status.

        WHY: Provides detailed overview of memory system health, file sizes,
        optimization opportunities, and agent-specific statistics for monitoring
        and maintenance purposes.

        Returns:
            Dict containing comprehensive memory system status
        """
        return self.analyzer.get_memory_status()

    def cross_reference_memories(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Find common patterns and cross-references across agent memories.

        WHY: Different agents may have learned similar or related information.
        Cross-referencing helps identify knowledge gaps, redundancies, and
        opportunities for knowledge sharing between agents.

        Args:
            query: Optional query to filter cross-references

        Returns:
            Dict containing cross-reference analysis results
        """
        return self.analyzer.cross_reference_memories(query)

    def get_all_memories_raw(self) -> Dict[str, Any]:
        """Get all agent memories in structured JSON format.

        WHY: This provides programmatic access to all agent memories, allowing
        external tools, scripts, or APIs to retrieve and process the complete
        memory state of the system.

        Returns:
            Dict containing structured memory data for all agents
        """
        return self.analyzer.get_all_memories_raw()

    def _ensure_memories_directory(self):
        """Ensure memories directory exists with README.

        WHY: The memories directory needs clear documentation so developers
        understand the purpose of these files and how to interact with them.
        """
        try:
            self.memories_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured memories directory exists: {self.memories_dir}")

            readme_path = self.memories_dir / "README.md"
            if not readme_path.exists():
                readme_content = """# Agent Memory System

## Purpose
Each agent maintains project-specific knowledge in these files. Agents read their memory file before tasks and update it when they learn something new.

## Manual Editing
Feel free to edit these files to:
- Add project-specific guidelines
- Remove outdated information
- Reorganize for better clarity
- Add domain-specific knowledge

## Memory Limits
- Max file size: 80KB (~20k tokens)
- Max sections: 10
- Max items per section: 15
- Files auto-truncate when limits exceeded

## File Format
Standard markdown with structured sections. Agents expect:
- Project Architecture
- Implementation Guidelines
- Common Mistakes to Avoid
- Current Technical Context

## How It Works
1. Agents read their memory file before starting tasks
2. Agents add learnings during or after task completion
3. Files automatically enforce size limits
4. Developers can manually edit for accuracy

## Memory File Lifecycle
- Created automatically when agent first runs
- Updated through hook system after delegations
- Manually editable by developers
- Version controlled with project
"""
                readme_path.write_text(readme_content, encoding="utf-8")
                self.logger.info("Created README.md in memories directory")

        except Exception as e:
            self.logger.error(f"Error ensuring memories directory: {e}")
            # Continue anyway - memory system should not block operations

    # ================================================================================
    # Interface Adapter Methods
    # ================================================================================
    # These methods adapt the existing implementation to comply with MemoryServiceInterface

    def load_memory(self, agent_id: str) -> Optional[str]:
        """Load memory for a specific agent.

        WHY: This adapter method provides interface compliance by wrapping
        the existing load_agent_memory method.

        Args:
            agent_id: Identifier of the agent

        Returns:
            Memory content as string or None if not found
        """
        try:
            content = self.load_agent_memory(agent_id)
            return content if content else None
        except Exception as e:
            self.logger.error(f"Failed to load memory for {agent_id}: {e}")
            return None

    def save_memory(self, agent_id: str, content: str) -> bool:
        """Save memory for a specific agent.

        WHY: This adapter method provides interface compliance. The existing
        implementation uses update_agent_memory for modifications, so we
        implement a full save by writing directly to the file.

        Args:
            agent_id: Identifier of the agent
            content: Memory content to save

        Returns:
            True if save successful
        """
        try:
            memory_path = self.memories_dir / f"{agent_id}_agent.md"

            # Validate size before saving
            is_valid, error_msg = self.validate_memory_size(content)
            if not is_valid:
                self.logger.error(f"Memory validation failed: {error_msg}")
                return False

            # Write the content
            memory_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Saved memory for agent {agent_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save memory for {agent_id}: {e}")
            return False

    def validate_memory_size(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate memory content size and structure.

        WHY: This adapter method provides interface compliance by implementing
        validation based on configured limits.

        Args:
            content: Memory content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.content_manager.validate_memory_size(content)

    def get_memory_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get memory usage metrics.

        WHY: This adapter method provides interface compliance by gathering
        metrics about memory usage.

        Args:
            agent_id: Optional specific agent ID, or None for all

        Returns:
            Dictionary with memory metrics
        """
        return self.analyzer.get_memory_metrics(agent_id)


# Convenience functions for external use
def get_memory_manager(
    config: Optional[Config] = None, working_directory: Optional[Path] = None
) -> AgentMemoryManager:
    """Get a singleton instance of the memory manager.

    WHY: The memory manager should be shared across the application to ensure
    consistent file access and avoid multiple instances managing the same files.

    Args:
        config: Optional Config object. Only used on first instantiation.
        working_directory: Optional working directory. Only used on first instantiation.

    Returns:
        AgentMemoryManager: The memory manager instance
    """
    if not hasattr(get_memory_manager, "_instance"):
        get_memory_manager._instance = AgentMemoryManager(config, working_directory)
    return get_memory_manager._instance
