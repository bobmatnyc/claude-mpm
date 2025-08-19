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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.config import Config
from claude_mpm.core.interfaces import MemoryServiceInterface
from claude_mpm.core.unified_paths import get_path_manager
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
        self.project_root = get_path_manager().project_root
        # Use current working directory by default, not project root
        self.working_directory = working_directory or Path(os.getcwd())
        
        # Set up both user and project memory directories
        self.user_memories_dir = Path.home() / ".claude-mpm" / "memories"
        self.project_memories_dir = self.working_directory / ".claude-mpm" / "memories"
        
        # Primary memories_dir points to project for backward compatibility
        self.memories_dir = self.project_memories_dir
        
        # Ensure both directories exist
        self._ensure_memories_directory()
        self._ensure_user_memories_directory()

        # Initialize memory limits from configuration
        self._init_memory_limits()

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

    def _get_memory_file_with_migration(self, directory: Path, agent_id: str) -> Path:
        """Get memory file path, migrating from old naming if needed.
        
        WHY: Supports backward compatibility by automatically migrating from
        the old {agent_id}_agent.md and {agent_id}.md formats to the new {agent_id}_memories.md format.
        
        Args:
            directory: Directory containing memory files
            agent_id: The agent identifier
            
        Returns:
            Path: Path to the memory file (may not exist)
        """
        new_file = directory / f"{agent_id}_memories.md"
        # Support migration from both old formats
        old_file_agent = directory / f"{agent_id}_agent.md"
        old_file_simple = directory / f"{agent_id}.md"
        
        # Migrate from old formats if needed
        if not new_file.exists():
            # Try migrating from {agent_id}_agent.md first
            if old_file_agent.exists():
                try:
                    content = old_file_agent.read_text(encoding="utf-8")
                    new_file.write_text(content, encoding="utf-8")
                    old_file_agent.unlink()
                    self.logger.info(f"Migrated memory file from {old_file_agent.name} to {new_file.name}")
                except Exception as e:
                    self.logger.error(f"Failed to migrate memory file for {agent_id}: {e}")
                    return old_file_agent
            # Try migrating from {agent_id}.md
            elif old_file_simple.exists():
                try:
                    content = old_file_simple.read_text(encoding="utf-8")
                    new_file.write_text(content, encoding="utf-8")
                    old_file_simple.unlink()
                    self.logger.info(f"Migrated memory file from {old_file_simple.name} to {new_file.name}")
                except Exception as e:
                    self.logger.error(f"Failed to migrate memory file for {agent_id}: {e}")
                    return old_file_simple
        
        return new_file

    def load_agent_memory(self, agent_id: str) -> str:
        """Load agent memory file content from both user and project directories.

        WHY: Agents need to read their accumulated knowledge before starting tasks
        to apply learned patterns and avoid repeated mistakes. This method now
        aggregates memories from both user-level (global) and project-level sources.

        Loading order:
        1. User-level memory (~/.claude-mpm/memories/{agent_id}_memories.md)
        2. Project-level memory (./.claude-mpm/memories/{agent_id}_memories.md)
        3. Project memory overrides/extends user memory

        Args:
            agent_id: The agent identifier (e.g., 'research', 'engineer')

        Returns:
            str: The aggregated memory file content, creating default if doesn't exist
        """
        # Support both old and new naming conventions
        user_memory_file = self._get_memory_file_with_migration(self.user_memories_dir, agent_id)
        project_memory_file = self._get_memory_file_with_migration(self.project_memories_dir, agent_id)
        
        user_memory = None
        project_memory = None
        
        # Load user-level memory if exists
        if user_memory_file.exists():
            try:
                user_memory = user_memory_file.read_text(encoding="utf-8")
                user_memory = self.content_manager.validate_and_repair(user_memory, agent_id)
                self.logger.debug(f"Loaded user-level memory for {agent_id}")
            except Exception as e:
                self.logger.error(f"Error reading user memory file for {agent_id}: {e}")
        
        # Load project-level memory if exists
        if project_memory_file.exists():
            try:
                project_memory = project_memory_file.read_text(encoding="utf-8")
                project_memory = self.content_manager.validate_and_repair(project_memory, agent_id)
                self.logger.debug(f"Loaded project-level memory for {agent_id}")
            except Exception as e:
                self.logger.error(f"Error reading project memory file for {agent_id}: {e}")
        
        # Aggregate memories
        if user_memory and project_memory:
            # Both exist - aggregate them
            aggregated = self._aggregate_agent_memories(user_memory, project_memory, agent_id)
            self.logger.info(f"Aggregated user and project memories for {agent_id}")
            return aggregated
        elif project_memory:
            # Only project memory exists
            return project_memory
        elif user_memory:
            # Only user memory exists
            return user_memory
        else:
            # Neither exists - create default in project directory
            self.logger.info(f"Creating default memory for agent: {agent_id}")
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
            memory_file = self.memories_dir / f"{agent_id}_memories.md"
            memory_file.write_text(template, encoding="utf-8")
            self.logger.info(f"Created project-specific memory file for {agent_id}")

        except Exception as e:
            self.logger.error(f"Error saving default memory for {agent_id}: {e}")

        return template

    def _save_memory_file(self, agent_id: str, content: str, save_to_user: bool = False) -> bool:
        """Save memory content to file.

        WHY: Memory updates need to be persisted atomically to prevent corruption
        and ensure learnings are preserved across agent invocations. By default,
        saves to project directory, but can optionally save to user directory.

        Args:
            agent_id: Agent identifier
            content: Content to save
            save_to_user: If True, saves to user directory instead of project

        Returns:
            bool: True if save succeeded
        """
        try:
            # Choose target directory
            target_dir = self.user_memories_dir if save_to_user else self.project_memories_dir
            memory_file = target_dir / f"{agent_id}_memories.md"
            
            # Ensure directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            memory_file.write_text(content, encoding="utf-8")
            location = "user" if save_to_user else "project"
            self.logger.debug(f"Saved memory for {agent_id} to {location} directory")
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

    def extract_and_update_memory(self, agent_id: str, response: str) -> bool:
        """Extract memory updates from agent response and update memory file.

        WHY: Agents provide memory updates in their responses that need to be
        extracted and persisted. This method looks for "remember" field in JSON
        responses and merges new learnings with existing memory.

        Args:
            agent_id: The agent identifier
            response: The agent's response text (may contain JSON)

        Returns:
            bool: True if memory was updated, False otherwise
        """
        try:
            import json
            import re
            
            # Look for JSON block in the response
            # Pattern matches ```json ... ``` blocks
            json_pattern = r'```json\s*(.*?)\s*```'
            json_matches = re.findall(json_pattern, response, re.DOTALL)
            
            if not json_matches:
                # Also try to find inline JSON objects
                json_pattern2 = r'\{[^{}]*"(?:remember|Remember)"[^{}]*\}'
                json_matches = re.findall(json_pattern2, response, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    
                    # Check for memory updates in "remember" field
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
                                success = self._add_learnings_to_memory(agent_id, valid_items)
                                if success:
                                    self.logger.info(f"Added {len(valid_items)} new memories for {agent_id}")
                                    return True
                    
                except json.JSONDecodeError:
                    # Not valid JSON, continue to next match
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error extracting memory from response for {agent_id}: {e}")
            return False
    
    def _add_learnings_to_memory(self, agent_id: str, learnings: List[str]) -> bool:
        """Add new learnings to existing agent memory.
        
        WHY: Instead of replacing all memory, we want to intelligently merge new
        learnings with existing knowledge, avoiding duplicates and maintaining
        the most relevant information.
        
        Args:
            agent_id: The agent identifier
            learnings: List of new learning strings to add
            
        Returns:
            bool: True if memory was successfully updated
        """
        try:
            # Load existing memory
            current_memory = self.load_agent_memory(agent_id)
            
            # Parse existing memory into sections
            sections = self._parse_memory_sections(current_memory)
            
            # Clean sections - remove template placeholder text
            sections = self._clean_template_placeholders(sections)
            
            # Determine which section to add learnings to based on content
            for learning in learnings:
                if not learning or not isinstance(learning, str):
                    continue
                    
                learning = learning.strip()
                if not learning:
                    continue
                
                # Categorize the learning based on keywords
                section = self._categorize_learning(learning)
                
                # Add to appropriate section if not duplicate
                if section not in sections:
                    sections[section] = []
                
                # Check for duplicates (case-insensitive) - FIXED LOGIC
                normalized_learning = learning.lower()
                # Strip bullet points from existing items for comparison
                existing_normalized = [item.lstrip('- ').strip().lower() for item in sections[section]]
                
                if normalized_learning not in existing_normalized:
                    # Add bullet point if not present
                    if not learning.startswith("-"):
                        learning = f"- {learning}"
                    sections[section].append(learning)
                else:
                    self.logger.debug(f"Skipping duplicate memory: {learning}")
            
            # Rebuild memory content
            new_content = self._build_memory_content(agent_id, sections)
            
            # Validate and save
            agent_limits = self._get_agent_limits(agent_id)
            if self.content_manager.exceeds_limits(new_content, agent_limits):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                new_content = self.content_manager.truncate_to_limits(new_content, agent_limits)
            
            return self._save_memory_file(agent_id, new_content)
            
        except Exception as e:
            self.logger.error(f"Error adding learnings to memory for {agent_id}: {e}")
            return False
    
    def _clean_template_placeholders(self, sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Remove template placeholder text from sections.
        
        Args:
            sections: Dict mapping section names to lists of items
            
        Returns:
            Dict with placeholder text removed
        """
        # Template placeholder patterns to remove
        placeholders = [
            "Analyze project structure to understand architecture patterns",
            "Observe codebase patterns and conventions during tasks",
            "Extract implementation guidelines from project documentation",
            "Learn from errors encountered during project work",
            "Project analysis pending - gather context during tasks",
            "claude-mpm: Software project requiring analysis"
        ]
        
        cleaned = {}
        for section_name, items in sections.items():
            cleaned_items = []
            for item in items:
                # Remove bullet point for comparison
                item_text = item.lstrip("- ").strip()
                # Keep item if it's not a placeholder
                if item_text and item_text not in placeholders:
                    cleaned_items.append(item)
            
            # Only include section if it has real content
            if cleaned_items:
                cleaned[section_name] = cleaned_items
        
        return cleaned
    
    def _categorize_learning(self, learning: str) -> str:
        """Categorize a learning item into appropriate section.
        
        Args:
            learning: The learning string to categorize
            
        Returns:
            str: The section name for this learning
        """
        learning_lower = learning.lower()
        
        # Check for keywords to categorize with improved patterns
        # Order matters - more specific patterns should come first
        
        # Architecture keywords
        if any(word in learning_lower for word in ["architecture", "structure", "design", "module", "component", "microservices", "service-oriented"]):
            return "Project Architecture"
            
        # Integration keywords (check before patterns to avoid "use" conflict)
        elif any(word in learning_lower for word in ["integration", "interface", "api", "connection", "database", "pooling", "via"]):
            return "Integration Points"
            
        # Mistake keywords (check before patterns to avoid conflicts)
        elif any(word in learning_lower for word in ["mistake", "error", "avoid", "don't", "never", "not"]):
            return "Common Mistakes to Avoid"
            
        # Context keywords (check before patterns to avoid "working", "version" conflicts)
        elif any(word in learning_lower for word in ["context", "current", "currently", "working", "version", "release", "candidate"]):
            return "Current Technical Context"
            
        # Guideline keywords (check before patterns to avoid "must", "should" conflicts)
        elif any(word in learning_lower for word in ["guideline", "rule", "standard", "practice", "docstring", "documentation", "must", "should", "include", "comprehensive"]):
            return "Implementation Guidelines"
            
        # Pattern keywords (including dependency injection, conventions)
        elif any(word in learning_lower for word in ["pattern", "convention", "style", "format", "dependency injection", "instantiation", "use", "implement"]):
            return "Coding Patterns Learned"
            
        # Strategy keywords  
        elif any(word in learning_lower for word in ["strategy", "approach", "method", "technique", "effective"]):
            return "Effective Strategies"
            
        # Performance keywords
        elif any(word in learning_lower for word in ["performance", "optimization", "speed", "efficiency"]):
            return "Performance Considerations"
            
        # Domain keywords
        elif any(word in learning_lower for word in ["domain", "business", "specific"]):
            return "Domain-Specific Knowledge"
            
        else:
            return "Recent Learnings"
    
    def _build_memory_content(self, agent_id: str, sections: Dict[str, List[str]]) -> str:
        """Build memory content from sections.
        
        Args:
            agent_id: The agent identifier
            sections: Dict mapping section names to lists of items
            
        Returns:
            str: The formatted memory content
        """
        lines = []
        
        # Add header
        lines.append(f"# {agent_id.capitalize()} Agent Memory")
        lines.append("")
        lines.append(f"<!-- Last Updated: {datetime.now().isoformat()} -->")
        lines.append("")
        
        # Add sections in consistent order
        section_order = [
            "Project Architecture",
            "Implementation Guidelines",
            "Common Mistakes to Avoid",
            "Current Technical Context",
            "Coding Patterns Learned",
            "Effective Strategies",
            "Integration Points",
            "Performance Considerations",
            "Domain-Specific Knowledge",
            "Recent Learnings"
        ]
        
        for section_name in section_order:
            if section_name in sections and sections[section_name]:
                lines.append(f"## {section_name}")
                lines.append("")
                for item in sections[section_name]:
                    if item.strip():
                        lines.append(item)
                lines.append("")
        
        # Add any remaining sections
        remaining = set(sections.keys()) - set(section_order)
        for section_name in sorted(remaining):
            if sections[section_name]:
                lines.append(f"## {section_name}")
                lines.append("")
                for item in sections[section_name]:
                    if item.strip():
                        lines.append(item)
                lines.append("")
        
        return '\n'.join(lines)
    
    def replace_agent_memory(self, agent_id: str, memory_sections: Dict[str, List[str]]) -> bool:
        """Replace agent's memory with new content organized by sections.

        WHY: When agents provide memory updates, they replace the existing memory
        rather than appending to it. This ensures memories stay current and relevant.

        Args:
            agent_id: The agent identifier
            memory_sections: Dict mapping section names to lists of memory items

        Returns:
            bool: True if memory was successfully replaced
        """
        try:
            # Build new memory content
            lines = []
            
            # Add header
            lines.append(f"# {agent_id.capitalize()} Agent Memory")
            lines.append("")
            lines.append(f"<!-- Last Updated: {datetime.now().isoformat()} -->")
            lines.append("")
            
            # Add sections in a consistent order
            section_order = [
                "Project Architecture",
                "Implementation Guidelines", 
                "Common Mistakes to Avoid",
                "Current Technical Context",
                "Coding Patterns Learned",
                "Effective Strategies",
                "Integration Points",
                "Performance Considerations",
                "Domain-Specific Knowledge",
                "Recent Learnings"
            ]
            
            # First add ordered sections that exist in memory_sections
            for section_name in section_order:
                if section_name in memory_sections and memory_sections[section_name]:
                    lines.append(f"## {section_name}")
                    lines.append("")
                    for item in memory_sections[section_name]:
                        if item.strip():  # Skip empty items
                            # Add bullet point if not already present
                            if not item.strip().startswith("-"):
                                lines.append(f"- {item.strip()}")
                            else:
                                lines.append(item.strip())
                    lines.append("")
            
            # Then add any remaining sections not in the order list
            remaining_sections = set(memory_sections.keys()) - set(section_order)
            for section_name in sorted(remaining_sections):
                if memory_sections[section_name]:
                    lines.append(f"## {section_name}")
                    lines.append("")
                    for item in memory_sections[section_name]:
                        if item.strip():
                            if not item.strip().startswith("-"):
                                lines.append(f"- {item.strip()}")
                            else:
                                lines.append(item.strip())
                    lines.append("")
            
            new_content = '\n'.join(lines)
            
            # Validate and save
            agent_limits = self._get_agent_limits(agent_id)
            if self.content_manager.exceeds_limits(new_content, agent_limits):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                new_content = self.content_manager.truncate_to_limits(new_content, agent_limits)
            
            # Save the new memory
            return self._save_memory_file(agent_id, new_content)
            
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
            "system_health": "healthy"
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
                        "size_kb": round(size_kb, 2)
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
            "suggestion": "Use get_memory_status() for memory overview"
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
            "suggestion": "Use load_agent_memory() for specific agent memories"
        }

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

    def _ensure_user_memories_directory(self):
        """Ensure user-level memories directory exists with README.

        WHY: User-level memories provide global defaults that apply across all projects,
        allowing users to maintain common patterns and guidelines.
        """
        try:
            self.user_memories_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured user memories directory exists: {self.user_memories_dir}")

            readme_path = self.user_memories_dir / "README.md"
            if not readme_path.exists():
                readme_content = """# User-Level Agent Memory System

## Purpose
User-level memories provide global defaults that apply to all projects. These memories are 
loaded first, then project-specific memories can override or extend them.

## Directory Hierarchy
1. **User-level memories** (~/.claude-mpm/memories/): Global defaults for all projects
2. **Project-level memories** (./.claude-mpm/memories/): Project-specific overrides

## How Memories Are Aggregated
- User memories are loaded first as the base
- Project memories override or extend user memories
- Duplicate sections are merged with project taking precedence
- Unique sections from both sources are preserved

## Manual Editing
Feel free to edit these files to add:
- Common coding patterns you always use
- Personal style guidelines
- Frequently used architectural patterns
- Global best practices

## File Format
Same as project memories - standard markdown with structured sections:
- Project Architecture
- Implementation Guidelines
- Common Mistakes to Avoid
- Current Technical Context

## Examples of Good User-Level Memories
- "Always use type hints in Python code"
- "Prefer composition over inheritance"
- "Write comprehensive docstrings for public APIs"
- "Use dependency injection for testability"
"""
                readme_path.write_text(readme_content, encoding="utf-8")
                self.logger.info("Created README.md in user memories directory")

        except Exception as e:
            self.logger.error(f"Error ensuring user memories directory: {e}")
            # Continue anyway - memory system should not block operations

    def _aggregate_agent_memories(self, user_memory: str, project_memory: str, agent_id: str) -> str:
        """Aggregate user and project memories for an agent.
        
        WHY: When both user-level and project-level memories exist, they need to be
        intelligently merged to provide comprehensive context while avoiding duplication
        and respecting project-specific overrides.
        
        Strategy:
        - Parse both memories into sections
        - Merge sections with project taking precedence
        - Remove exact duplicates within sections
        - Preserve unique items from both sources
        
        Args:
            user_memory: User-level memory content
            project_memory: Project-level memory content
            agent_id: Agent identifier for context
            
        Returns:
            str: Aggregated memory content
        """
        # Parse memories into sections
        user_sections = self._parse_memory_sections(user_memory)
        project_sections = self._parse_memory_sections(project_memory)
        
        # Start with user sections as base
        merged_sections = {}
        
        # Add all user sections first
        for section_name, items in user_sections.items():
            merged_sections[section_name] = set(items)
        
        # Merge project sections (overrides/extends user)
        for section_name, items in project_sections.items():
            if section_name in merged_sections:
                # Merge items - project items take precedence
                merged_sections[section_name].update(items)
            else:
                # New section from project
                merged_sections[section_name] = set(items)
        
        # Build aggregated memory content
        lines = []
        
        # Add header
        lines.append(f"# {agent_id.capitalize()} Agent Memory")
        lines.append("")
        lines.append("*Aggregated from user-level and project-level memories*")
        lines.append("")
        lines.append(f"<!-- Last Updated: {datetime.now().isoformat()} -->")
        lines.append("")
        
        # Add sections in a consistent order
        section_order = [
            "Project Architecture",
            "Implementation Guidelines",
            "Common Mistakes to Avoid",
            "Current Technical Context",
            "Coding Patterns Learned",
            "Effective Strategies",
            "Integration Points",
            "Performance Considerations",
            "Domain-Specific Knowledge",
            "Recent Learnings"
        ]
        
        # First add ordered sections that exist
        for section_name in section_order:
            if section_name in merged_sections and merged_sections[section_name]:
                lines.append(f"## {section_name}")
                lines.append("")
                # Sort items for consistent output
                for item in sorted(merged_sections[section_name]):
                    if item.strip():  # Skip empty items
                        lines.append(item)
                lines.append("")
        
        # Then add any remaining sections not in the order list
        remaining_sections = set(merged_sections.keys()) - set(section_order)
        for section_name in sorted(remaining_sections):
            if merged_sections[section_name]:
                lines.append(f"## {section_name}")
                lines.append("")
                for item in sorted(merged_sections[section_name]):
                    if item.strip():
                        lines.append(item)
                lines.append("")
        
        return '\n'.join(lines)
    
    def _parse_memory_sections(self, memory_content: str) -> Dict[str, List[str]]:
        """Parse memory content into sections and items.
        
        Args:
            memory_content: Raw memory file content
            
        Returns:
            Dict mapping section names to lists of items
        """
        sections = {}
        current_section = None
        current_items = []
        
        for line in memory_content.split('\n'):
            # Skip metadata lines
            if line.startswith('<!-- ') and line.endswith(' -->'):
                continue
            # Check for section headers (## Level 2 headers)
            elif line.startswith('## '):
                # Save previous section if exists
                if current_section and current_items:
                    sections[current_section] = current_items
                
                # Start new section
                current_section = line[3:].strip()  # Remove "## " prefix
                current_items = []
            # Collect non-empty lines as items (but not HTML comments)
            elif line.strip() and current_section and not line.strip().startswith('<!--'):
                # Keep the full line with its formatting
                current_items.append(line.strip())
        
        # Save last section
        if current_section and current_items:
            sections[current_section] = current_items
        
        return sections

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
        metrics = {
            "total_memory_kb": 0,
            "agent_count": 0,
            "agents": {}
        }
        
        if self.memories_dir.exists():
            if agent_id:
                # Metrics for specific agent
                memory_file = self.memories_dir / f"{agent_id}_memories.md"
                if memory_file.exists():
                    size_kb = memory_file.stat().st_size / 1024
                    metrics["agents"][agent_id] = {
                        "size_kb": round(size_kb, 2),
                        "limit_kb": self._get_agent_limits(agent_id)["max_file_size_kb"],
                        "usage_percent": round((size_kb / self._get_agent_limits(agent_id)["max_file_size_kb"]) * 100, 1)
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
                        limit_kb = self._get_agent_limits(agent_name)["max_file_size_kb"]
                        metrics["agents"][agent_name] = {
                            "size_kb": round(size_kb, 2),
                            "limit_kb": limit_kb,
                            "usage_percent": round((size_kb / limit_kb) * 100, 1)
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
