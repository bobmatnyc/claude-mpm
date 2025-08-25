#!/usr/bin/env python3

from pathlib import Path

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
following the naming convention: {agent_id}_memories.md
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.config import Config
from claude_mpm.core.interfaces import MemoryServiceInterface
from claude_mpm.core.unified_paths import get_path_manager

from .content_manager import MemoryContentManager
from .memory_categorization_service import MemoryCategorizationService
from .memory_file_service import MemoryFileService
from .memory_format_service import MemoryFormatService
from .memory_limits_service import MemoryLimitsService
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
        "max_items": 100,  # Maximum total memory items
        "max_line_length": 120,
    }

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
        self.project_root = get_path_manager().project_root
        # Use current working directory by default, not project root
        self.working_directory = working_directory or Path(os.getcwd())

        # Use only project memory directory
        self.project_memories_dir = self.working_directory / ".claude-mpm" / "memories"

        # Primary memories_dir points to project
        self.memories_dir = self.project_memories_dir

        # Initialize services
        self.file_service = MemoryFileService(self.memories_dir)
        self.limits_service = MemoryLimitsService(self.config)
        self.memory_limits = self.limits_service.memory_limits
        self.format_service = MemoryFormatService()
        self.categorization_service = MemoryCategorizationService()

        # Ensure project directory exists
        self.file_service.ensure_memories_directory()

        # Initialize component services
        self.template_generator = MemoryTemplateGenerator(
            self.config, self.working_directory
        )
        self.content_manager = MemoryContentManager(self.memory_limits)

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

    def load_agent_memory(self, agent_id: str) -> str:
        """Load agent memory file content from project directory.

        WHY: Agents need to read their accumulated knowledge before starting tasks
        to apply learned patterns and avoid repeated mistakes. All memories are
        now stored at the project level for consistency.

        Args:
            agent_id: The agent identifier (e.g., 'PM', 'research', 'engineer')

        Returns:
            str: The memory file content, creating default if doesn't exist
        """
        # All agents use project directory
        project_memory_file = self.file_service.get_memory_file_with_migration(
            self.project_memories_dir, agent_id
        )

        # Load project-level memory if exists
        if project_memory_file.exists():
            try:
                project_memory = project_memory_file.read_text(encoding="utf-8")
                project_memory = self.content_manager.validate_and_repair(
                    project_memory, agent_id
                )
                self.logger.debug(f"Loaded project-level memory for {agent_id}")
                return project_memory
            except Exception as e:
                self.logger.error(
                    f"Error reading project memory file for {agent_id}: {e}"
                )

        # Memory doesn't exist - create default in project directory
        self.logger.info(f"Creating default memory for agent: {agent_id}")
        return self._create_default_memory(agent_id)

    def update_agent_memory(self, agent_id: str, new_items: List[str]) -> bool:
        """Add new learning items to agent memory as a simple list.

        WHY: Simplified memory system - all memories are stored as a simple list
        without categorization, making it easier to manage and understand.

        Args:
            agent_id: The agent identifier
            new_items: List of new learning items to add

        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            # Use the simplified _add_learnings_to_memory method
            return self._add_learnings_to_memory(agent_id, new_items)
        except Exception as e:
            self.logger.error(f"Error updating memory for {agent_id}: {e}")
            # Never fail on memory errors
            return False

    def add_learning(self, agent_id: str, content: str) -> bool:
        """Add a learning to agent memory as a simple list item.

        WHY: Simplified interface for adding single learnings without categorization.
        This method wraps the batch update for convenience.

        Args:
            agent_id: The agent identifier
            content: The learning content

        Returns:
            bool: True if learning was added successfully
        """
        return self.update_agent_memory(agent_id, [content])

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
        limits = self.limits_service.get_agent_limits(agent_id)

        # Delegate to template generator
        template = self.template_generator.create_default_memory(agent_id, limits)

        # Save default file to project directory
        try:
            target_dir = self.memories_dir
            memory_file = target_dir / f"{agent_id}_memories.md"
            memory_file.write_text(template, encoding="utf-8")
            self.logger.info(f"Created project-specific memory file for {agent_id}")

        except Exception as e:
            self.logger.error(f"Error saving default memory for {agent_id}: {e}")

        return template

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

    def extract_and_update_memory(self, agent_id: str, response: str) -> bool:
        """Extract memory updates from agent response and update memory file.

        WHY: Agents provide memory updates in their responses that need to be
        extracted and persisted. This method looks for "remember" field for incremental
        updates or "MEMORIES" field for complete replacement.

        Args:
            agent_id: The agent identifier
            response: The agent's response text (may contain JSON)

        Returns:
            bool: True if memory was updated, False otherwise
        """
        try:
            import json
            import re

            # Log that we're processing memory for this agent
            is_pm = agent_id.upper() == "PM"
            self.logger.debug(f"Extracting memory for {agent_id} (is_pm={is_pm})")

            # Look for JSON block in the response
            # Pattern matches ```json ... ``` blocks
            json_pattern = r"```json\s*(.*?)\s*```"
            json_matches = re.findall(json_pattern, response, re.DOTALL)

            if not json_matches:
                # Also try to find inline JSON objects
                json_pattern2 = r'\{[^{}]*"(?:remember|Remember|MEMORIES)"[^{}]*\}'
                json_matches = re.findall(json_pattern2, response, re.DOTALL)

            for json_str in json_matches:
                try:
                    data = json.loads(json_str)

                    # Check for complete memory replacement in "MEMORIES" field
                    if "MEMORIES" in data and data["MEMORIES"] is not None:
                        memories = data["MEMORIES"]
                        if isinstance(memories, list) and len(memories) > 0:
                            # Filter out empty strings and None values
                            valid_items = []
                            for item in memories:
                                if item and isinstance(item, str) and item.strip():
                                    # Ensure item has bullet point for consistency
                                    item_text = item.strip()
                                    if not item_text.startswith("-"):
                                        item_text = f"- {item_text}"
                                    valid_items.append(item_text)

                            if valid_items:
                                self.logger.info(
                                    f"Replacing all memories for {agent_id} with {len(valid_items)} items"
                                )
                                success = self.replace_agent_memory(
                                    agent_id, valid_items
                                )
                                if success:
                                    self.logger.info(
                                        f"Successfully replaced memories for {agent_id}"
                                    )
                                    return True
                                self.logger.error(
                                    f"Failed to replace memories for {agent_id}"
                                )
                        continue  # Skip checking remember field if MEMORIES was processed

                    # Check for incremental memory updates in "remember" field
                    memory_items = None

                    # Check both "remember" and "Remember" fields
                    if "remember" in data:
                        memory_items = data["remember"]
                    elif "Remember" in data:
                        memory_items = data["Remember"]

                    # Process memory items if found and not null
                    if memory_items is not None and memory_items != "null":
                        # Skip if explicitly null or empty list
                        if isinstance(memory_items, list) and len(memory_items) > 0:
                            # Filter out empty strings and None values
                            valid_items = []
                            for item in memory_items:
                                if item and isinstance(item, str) and item.strip():
                                    valid_items.append(item.strip())

                            # Only proceed if we have valid items
                            if valid_items:
                                self.logger.info(
                                    f"Found {len(valid_items)} memory items for {agent_id}: {valid_items[:2]}..."
                                )
                                success = self._add_learnings_to_memory(
                                    agent_id, valid_items
                                )
                                if success:
                                    self.logger.info(
                                        f"Successfully saved {len(valid_items)} memories for {agent_id} to project directory"
                                    )
                                    return True
                                self.logger.error(
                                    f"Failed to save memories for {agent_id}"
                                )

                except json.JSONDecodeError as je:
                    # Not valid JSON, continue to next match
                    self.logger.debug(f"JSON decode error for {agent_id}: {je}")
                    continue

            self.logger.debug(f"No memory items found in response for {agent_id}")
            return False

        except Exception as e:
            self.logger.error(
                f"Error extracting memory from response for {agent_id}: {e}"
            )
            return False

    def _add_learnings_to_memory(self, agent_id: str, learnings: List[str]) -> bool:
        """Add new learnings to agent memory as a simple list.

        WHY: Simplified memory system - all memories are stored as a simple list
        without categorization, making it easier to manage and understand.
        Updates timestamp on every update.

        Args:
            agent_id: The agent identifier
            learnings: List of new learning strings to add

        Returns:
            bool: True if memory was successfully updated
        """
        try:
            # Load existing memory
            current_memory = self.load_agent_memory(agent_id)

            # Parse existing memory into a simple list
            existing_items = self.format_service.parse_memory_list(current_memory)

            # Clean template placeholders if this is a fresh memory
            existing_items = self.format_service.clean_template_placeholders_list(
                existing_items
            )

            # Add new learnings, avoiding duplicates
            updated = False
            for learning in learnings:
                if not learning or not isinstance(learning, str):
                    continue

                learning = learning.strip()
                if not learning:
                    continue

                # Check for duplicates (case-insensitive)
                normalized_learning = learning.lower()
                # Strip bullet points from existing items for comparison
                existing_normalized = [
                    item.lstrip("- ").strip().lower() for item in existing_items
                ]

                if normalized_learning not in existing_normalized:
                    # Add bullet point if not present
                    if not learning.startswith("-"):
                        learning = f"- {learning}"
                    existing_items.append(learning)
                    self.logger.info(
                        f"Added new memory for {agent_id}: {learning[:50]}..."
                    )
                    updated = True
                else:
                    self.logger.debug(
                        f"Skipping duplicate memory for {agent_id}: {learning}"
                    )

            # Only save if we actually added new items
            if not updated:
                self.logger.debug(f"No new memories to add for {agent_id}")
                return True  # Not an error, just nothing new to add

            # Rebuild memory content as simple list with updated timestamp
            new_content = self.format_service.build_simple_memory_content(
                agent_id, existing_items
            )

            # Validate and save
            agent_limits = self.limits_service.get_agent_limits(agent_id)
            if self.content_manager.exceeds_limits(new_content, agent_limits):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                new_content = self.content_manager.truncate_simple_list(
                    new_content, agent_limits
                )

            # All memories go to project directory
            return self._save_memory_file_wrapper(agent_id, new_content)

        except Exception as e:
            self.logger.error(f"Error adding learnings to memory for {agent_id}: {e}")
            return False

    def replace_agent_memory(self, agent_id: str, memory_items: List[str]) -> bool:
        """Replace agent's memory with new content as a simple list.

        WHY: When agents provide complete memory updates through MEMORIES field,
        they replace the existing memory rather than appending to it.
        This ensures memories stay current and relevant.

        Args:
            agent_id: The agent identifier
            memory_items: List of memory items to replace existing memories

        Returns:
            bool: True if memory was successfully replaced
        """
        try:
            # Build new memory content as simple list with updated timestamp
            new_content = self.format_service.build_simple_memory_content(
                agent_id, memory_items
            )

            # Validate and save
            agent_limits = self.limits_service.get_agent_limits(agent_id)
            if self.content_manager.exceeds_limits(new_content, agent_limits):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                new_content = self.content_manager.truncate_simple_list(
                    new_content, agent_limits
                )

            # Save the new memory
            return self._save_memory_file_wrapper(agent_id, new_content)

        except Exception as e:
            self.logger.error(f"Error replacing memory for {agent_id}: {e}")
            return False

    def get_memory_status(self) -> Dict[str, Any]:
        """Get comprehensive memory system status.

        WHY: Provides detailed overview of memory system health, file sizes,
        optimization opportunities, and agent-specific statistics for monitoring
        and maintenance purposes.

        Returns:
            Dict containing comprehensive memory system status
        """
        # Simplified status implementation without analyzer
        status = {
            "system_enabled": self.memory_enabled,
            "auto_learning": self.auto_learning,
            "memory_directory": str(self.memories_dir),
            "total_agents": 0,
            "total_size_kb": 0,
            "agents": {},
            "system_health": "healthy",
        }

        if self.memories_dir.exists():
            memory_files = list(self.memories_dir.glob("*_memories.md"))
            status["total_agents"] = len(memory_files)

            for file_path in memory_files:
                if file_path.name != "README.md":
                    size_kb = file_path.stat().st_size / 1024
                    status["total_size_kb"] += size_kb
                    agent_id = file_path.stem.replace("_memories", "")
                    status["agents"][agent_id] = {
                        "file": file_path.name,
                        "size_kb": round(size_kb, 2),
                    }

        return status

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
        # Deprecated - return informative message
        return {
            "status": "deprecated",
            "message": "Cross-reference analysis has been deprecated in favor of simplified memory management",
            "suggestion": "Use get_memory_status() for memory overview",
        }

    def get_all_memories_raw(self) -> Dict[str, Any]:
        """Get all agent memories in structured JSON format.

        WHY: This provides programmatic access to all agent memories, allowing
        external tools, scripts, or APIs to retrieve and process the complete
        memory state of the system.

        Returns:
            Dict containing structured memory data for all agents
        """
        # Deprecated - return informative message
        return {
            "status": "deprecated",
            "message": "Raw memory access has been deprecated in favor of simplified memory management",
            "suggestion": "Use load_agent_memory() for specific agent memories",
        }

    def _save_memory_file_wrapper(self, agent_id: str, content: str) -> bool:
        """Wrapper for save_memory_file that handles agent_id.

        Args:
            agent_id: Agent identifier
            content: Content to save

        Returns:
            True if saved successfully
        """
        file_path = self.file_service.get_memory_file_with_migration(
            self.memories_dir, agent_id
        )
        return self.file_service.save_memory_file(file_path, content)

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
            memory_path = self.memories_dir / f"{agent_id}_memories.md"

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
        # Minimal implementation for interface compliance
        metrics = {"total_memory_kb": 0, "agent_count": 0, "agents": {}}

        if self.memories_dir.exists():
            if agent_id:
                # Metrics for specific agent
                memory_file = self.memories_dir / f"{agent_id}_memories.md"
                if memory_file.exists():
                    size_kb = memory_file.stat().st_size / 1024
                    metrics["agents"][agent_id] = {
                        "size_kb": round(size_kb, 2),
                        "limit_kb": self.limits_service.get_agent_limits(agent_id)[
                            "max_file_size_kb"
                        ],
                        "usage_percent": round(
                            (
                                size_kb
                                / self.limits_service.get_agent_limits(agent_id)[
                                    "max_file_size_kb"
                                ]
                            )
                            * 100,
                            1,
                        ),
                    }
                    metrics["total_memory_kb"] = round(size_kb, 2)
                    metrics["agent_count"] = 1
            else:
                # Metrics for all agents
                memory_files = list(self.memories_dir.glob("*_memories.md"))
                for file_path in memory_files:
                    if file_path.name != "README.md":
                        agent_name = file_path.stem.replace("_memories", "")
                        size_kb = file_path.stat().st_size / 1024
                        limit_kb = self.limits_service.get_agent_limits(agent_name)[
                            "max_file_size_kb"
                        ]
                        metrics["agents"][agent_name] = {
                            "size_kb": round(size_kb, 2),
                            "limit_kb": limit_kb,
                            "usage_percent": round((size_kb / limit_kb) * 100, 1),
                        }
                        metrics["total_memory_kb"] += size_kb

                metrics["total_memory_kb"] = round(metrics["total_memory_kb"], 2)
                metrics["agent_count"] = len(metrics["agents"])

        return metrics


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
