#!/usr/bin/env python3
"""
Agent Memory Manager Service
===========================

Manages agent memory files with size limits and validation.

This service provides:
- Memory file operations (load, save, validate)
- Size limit enforcement (8KB default)
- Auto-truncation when limits exceeded
- Default memory template creation
- Section management with item limits
- Timestamp updates
- Directory initialization with README

Memory files are stored in .claude-mpm/memories/ directory
following the naming convention: {agent_id}_agent.md
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import re
import logging

from claude_mpm.core import LoggerMixin
from claude_mpm.core.config import Config
from claude_mpm.utils.paths import PathResolver
from claude_mpm.services.websocket_server import get_websocket_server


class AgentMemoryManager(LoggerMixin):
    """Manages agent memory files with size limits and validation.
    
    WHY: Agents need to accumulate project-specific knowledge over time to become
    more effective. This service manages persistent memory files that agents can
    read before tasks and update with new learnings.
    
    DESIGN DECISION: Memory files are stored in .claude-mpm/memories/ (not project root)
    to keep them organized and separate from other project files. Files follow a
    standardized markdown format with enforced size limits to prevent unbounded growth.
    
    The 8KB limit (~2000 tokens) balances comprehensive knowledge storage with
    reasonable context size for agent prompts.
    """
    
    # Default limits - will be overridden by configuration
    DEFAULT_MEMORY_LIMITS = {
        'max_file_size_kb': 8,
        'max_sections': 10,
        'max_items_per_section': 15,
        'max_line_length': 120
    }
    
    REQUIRED_SECTIONS = [
        'Project Architecture',
        'Implementation Guidelines', 
        'Common Mistakes to Avoid',
        'Current Technical Context'
    ]
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the memory manager.
        
        Sets up the memories directory and ensures it exists with proper README.
        
        Args:
            config: Optional Config object. If not provided, will create default Config.
        """
        super().__init__()
        self.config = config or Config()
        self.project_root = PathResolver.get_project_root()
        self.memories_dir = self.project_root / ".claude-mpm" / "memories"
        self._ensure_memories_directory()
        
        # Initialize memory limits from configuration
        self._init_memory_limits()
    
    def _init_memory_limits(self):
        """Initialize memory limits from configuration.
        
        WHY: Allows configuration-driven memory limits instead of hardcoded values.
        Supports agent-specific overrides for different memory requirements.
        """
        # Check if memory system is enabled
        self.memory_enabled = self.config.get('memory.enabled', True)
        self.auto_learning = self.config.get('memory.auto_learning', False)
        
        # Load default limits from configuration
        config_limits = self.config.get('memory.limits', {})
        self.memory_limits = {
            'max_file_size_kb': config_limits.get('default_size_kb', 
                                                  self.DEFAULT_MEMORY_LIMITS['max_file_size_kb']),
            'max_sections': config_limits.get('max_sections', 
                                            self.DEFAULT_MEMORY_LIMITS['max_sections']),
            'max_items_per_section': config_limits.get('max_items_per_section', 
                                                      self.DEFAULT_MEMORY_LIMITS['max_items_per_section']),
            'max_line_length': config_limits.get('max_line_length', 
                                               self.DEFAULT_MEMORY_LIMITS['max_line_length'])
        }
        
        # Load agent-specific overrides
        self.agent_overrides = self.config.get('memory.agent_overrides', {})
    
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
            if 'size_kb' in overrides:
                limits['max_file_size_kb'] = overrides['size_kb']
        
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
            return self.agent_overrides[agent_id].get('auto_learning', self.auto_learning)
        
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
            content = memory_file.read_text(encoding='utf-8')
            
            # Emit WebSocket event for memory loaded
            try:
                ws_server = get_websocket_server()
                file_size = len(content.encode('utf-8'))
                # Count sections by looking for lines starting with ##
                sections_count = sum(1 for line in content.split('\n') if line.startswith('## '))
                ws_server.memory_loaded(agent_id, file_size, sections_count)
            except Exception as ws_error:
                self.logger.debug(f"WebSocket notification failed: {ws_error}")
            
            return self._validate_and_repair(content, agent_id)
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
            updated_memory = self._add_item_to_section(current_memory, section, new_item)
            
            # Enforce limits
            if self._exceeds_limits(updated_memory, agent_id):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                updated_memory = self._truncate_to_limits(updated_memory, agent_id)
            
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
            'pattern': 'Coding Patterns Learned',
            'architecture': 'Project Architecture', 
            'guideline': 'Implementation Guidelines',
            'mistake': 'Common Mistakes to Avoid',
            'strategy': 'Effective Strategies',
            'integration': 'Integration Points',
            'performance': 'Performance Considerations',
            'domain': 'Domain-Specific Knowledge',
            'context': 'Current Technical Context'
        }
        
        section = section_mapping.get(learning_type, 'Recent Learnings')
        success = self.update_agent_memory(agent_id, section, content)
        
        # Emit WebSocket event for memory updated
        if success:
            try:
                ws_server = get_websocket_server()
                ws_server.memory_updated(agent_id, learning_type, content, section)
            except Exception as ws_error:
                self.logger.debug(f"WebSocket notification failed: {ws_error}")
        
        return success
    
    def _create_default_memory(self, agent_id: str) -> str:
        """Create default memory file for agent.
        
        WHY: New agents need a starting template with essential project knowledge
        and the correct structure for adding new learnings.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            str: The default memory template content
        """
        # Convert agent_id to proper name, handling cases like "test_agent" -> "Test"
        agent_name = agent_id.replace('_agent', '').replace('_', ' ').title()
        project_name = self.project_root.name
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get limits for this agent
        limits = self._get_agent_limits(agent_id)
        
        template = f"""# {agent_name} Agent Memory - {project_name}

<!-- MEMORY LIMITS: {limits['max_file_size_kb']}KB max | {limits['max_sections']} sections max | {limits['max_items_per_section']} items per section -->
<!-- Last Updated: {timestamp} | Auto-updated by: {agent_id} -->

## Project Architecture (Max: 15 items)
- Service-oriented architecture with clear module boundaries
- Three-tier agent hierarchy: project → user → system
- Agent definitions use standardized JSON schema validation

## Coding Patterns Learned (Max: 15 items)
- Always use PathResolver for path operations, never hardcode paths
- SubprocessRunner utility for external command execution
- LoggerMixin provides consistent logging across all services

## Implementation Guidelines (Max: 15 items)
- Check docs/STRUCTURE.md before creating new files
- Follow existing import patterns: from claude_mpm.module import Class
- Use existing utilities instead of reimplementing functionality

## Domain-Specific Knowledge (Max: 15 items)
<!-- Agent-specific knowledge accumulates here -->

## Effective Strategies (Max: 15 items)
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid (Max: 15 items)
- Don't modify Claude Code core functionality, only extend it
- Avoid duplicating code - check utils/ for existing implementations
- Never hardcode file paths, use PathResolver utilities

## Integration Points (Max: 15 items)
<!-- Key interfaces and integration patterns -->

## Performance Considerations (Max: 15 items)
<!-- Performance insights and optimization patterns -->

## Current Technical Context (Max: 15 items)
- EP-0001: Technical debt reduction in progress
- Target: 80% test coverage (current: 23.6%)
- Integration with Claude Code 1.0.60+ native agent framework

## Recent Learnings (Max: 15 items)
<!-- Most recent discoveries and insights -->
"""
        
        # Save default file
        try:
            memory_file = self.memories_dir / f"{agent_id}_agent.md"
            memory_file.write_text(template, encoding='utf-8')
            self.logger.info(f"Created default memory file for {agent_id}")
            
            # Emit WebSocket event for memory created
            try:
                ws_server = get_websocket_server()
                ws_server.memory_created(agent_id, "default")
            except Exception as ws_error:
                self.logger.debug(f"WebSocket notification failed: {ws_error}")
        except Exception as e:
            self.logger.error(f"Error saving default memory for {agent_id}: {e}")
        
        return template
    
    def _add_item_to_section(self, content: str, section: str, new_item: str) -> str:
        """Add item to specified section, respecting limits.
        
        WHY: Each section has a maximum item limit to prevent information overload
        and maintain readability. When limits are reached, oldest items are removed
        to make room for new learnings (FIFO strategy).
        
        Args:
            content: Current memory file content
            section: Section name to add item to
            new_item: Item to add
            
        Returns:
            str: Updated content with new item added
        """
        lines = content.split('\n')
        section_start = None
        section_end = None
        
        # Find section boundaries
        for i, line in enumerate(lines):
            if line.startswith(f'## {section}'):
                section_start = i
            elif section_start is not None and line.startswith('## '):
                section_end = i
                break
        
        if section_start is None:
            # Section doesn't exist, add it
            return self._add_new_section(content, section, new_item)
        
        if section_end is None:
            section_end = len(lines)
        
        # Count existing items in section and find first item index
        item_count = 0
        first_item_index = None
        for i in range(section_start + 1, section_end):
            if lines[i].strip().startswith('- '):
                if first_item_index is None:
                    first_item_index = i
                item_count += 1
        
        # Check if we can add more items
        if item_count >= self.memory_limits['max_items_per_section']:
            # Remove oldest item (first one) to make room
            if first_item_index is not None:
                lines.pop(first_item_index)
                section_end -= 1  # Adjust section end after removal
        
        # Add new item (find insertion point after any comments)
        insert_point = section_start + 1
        while insert_point < section_end and (
            not lines[insert_point].strip() or 
            lines[insert_point].strip().startswith('<!--')
        ):
            insert_point += 1
        
        # Ensure line length limit
        if len(new_item) > self.memory_limits['max_line_length']:
            new_item = new_item[:self.memory_limits['max_line_length'] - 3] + '...'
        
        lines.insert(insert_point, f"- {new_item}")
        
        # Update timestamp
        updated_content = '\n'.join(lines)
        return self._update_timestamp(updated_content)
    
    def _add_new_section(self, content: str, section: str, new_item: str) -> str:
        """Add a new section with the given item.
        
        WHY: When agents discover learnings that don't fit existing sections,
        we need to create new sections dynamically while respecting the maximum
        section limit.
        
        Args:
            content: Current memory content
            section: New section name
            new_item: First item for the section
            
        Returns:
            str: Updated content with new section
        """
        lines = content.split('\n')
        
        # Count existing sections
        section_count = sum(1 for line in lines if line.startswith('## '))
        
        if section_count >= self.memory_limits['max_sections']:
            self.logger.warning(f"Maximum sections reached, cannot add '{section}'")
            # Try to add to Recent Learnings instead
            return self._add_item_to_section(content, 'Recent Learnings', new_item)
        
        # Find insertion point (before Recent Learnings or at end)
        insert_point = len(lines)
        for i, line in enumerate(lines):
            if line.startswith('## Recent Learnings'):
                insert_point = i
                break
        
        # Insert new section
        new_section = [
            '',
            f'## {section} (Max: 15 items)',
            f'- {new_item}',
            ''
        ]
        
        for j, line in enumerate(new_section):
            lines.insert(insert_point + j, line)
        
        return '\n'.join(lines)
    
    def _exceeds_limits(self, content: str, agent_id: Optional[str] = None) -> bool:
        """Check if content exceeds size limits.
        
        Args:
            content: Content to check
            agent_id: Optional agent ID for agent-specific limits
            
        Returns:
            bool: True if content exceeds limits
        """
        # Get appropriate limits based on agent
        if agent_id:
            limits = self._get_agent_limits(agent_id)
        else:
            limits = self.memory_limits
            
        size_kb = len(content.encode('utf-8')) / 1024
        return size_kb > limits['max_file_size_kb']
    
    def _truncate_to_limits(self, content: str, agent_id: Optional[str] = None) -> str:
        """Truncate content to fit within limits.
        
        WHY: When memory files exceed size limits, we need a strategy to reduce
        size while preserving the most important information. This implementation
        removes items from "Recent Learnings" first as they're typically less
        consolidated than other sections.
        
        Args:
            content: Content to truncate
            
        Returns:
            str: Truncated content within size limits
        """
        lines = content.split('\n')
        
        # Get appropriate limits based on agent
        if agent_id:
            limits = self._get_agent_limits(agent_id)
        else:
            limits = self.memory_limits
            
        # Strategy: Remove items from Recent Learnings first
        while self._exceeds_limits('\n'.join(lines), agent_id):
            removed = False
            
            # First try Recent Learnings
            for i, line in enumerate(lines):
                if line.startswith('## Recent Learnings'):
                    # Find and remove first item in this section
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith('- '):
                            lines.pop(j)
                            removed = True
                            break
                        elif lines[j].startswith('## '):
                            break
                    break
            
            # If no Recent Learnings items, remove from other sections
            if not removed:
                # Remove from sections in reverse order (bottom up)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip().startswith('- '):
                        lines.pop(i)
                        removed = True
                        break
            
            # Safety: If nothing removed, truncate from end
            if not removed:
                lines = lines[:-10]
        
        return '\n'.join(lines)
    
    def _update_timestamp(self, content: str) -> str:
        """Update the timestamp in the file header.
        
        Args:
            content: Content to update
            
        Returns:
            str: Content with updated timestamp
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return re.sub(
            r'<!-- Last Updated: .+ \| Auto-updated by: .+ -->',
            f'<!-- Last Updated: {timestamp} | Auto-updated by: system -->',
            content
        )
    
    def _validate_and_repair(self, content: str, agent_id: str) -> str:
        """Validate memory file and repair if needed.
        
        WHY: Memory files might be manually edited by developers or corrupted.
        This method ensures the file maintains required structure and sections.
        
        Args:
            content: Content to validate
            agent_id: Agent identifier
            
        Returns:
            str: Validated and repaired content
        """
        lines = content.split('\n')
        existing_sections = set()
        
        # Find existing sections
        for line in lines:
            if line.startswith('## '):
                section_name = line[3:].split('(')[0].strip()
                existing_sections.add(section_name)
        
        # Check for required sections
        missing_sections = []
        for required in self.REQUIRED_SECTIONS:
            if required not in existing_sections:
                missing_sections.append(required)
        
        if missing_sections:
            self.logger.info(f"Adding missing sections to {agent_id} memory: {missing_sections}")
            
            # Add missing sections before Recent Learnings
            insert_point = len(lines)
            for i, line in enumerate(lines):
                if line.startswith('## Recent Learnings'):
                    insert_point = i
                    break
            
            for section in missing_sections:
                section_content = [
                    '',
                    f'## {section} (Max: 15 items)',
                    '<!-- Section added by repair -->',
                    ''
                ]
                for j, line in enumerate(section_content):
                    lines.insert(insert_point + j, line)
                insert_point += len(section_content)
        
        return '\n'.join(lines)
    
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
            memory_file.write_text(content, encoding='utf-8')
            self.logger.debug(f"Saved memory for {agent_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving memory for {agent_id}: {e}")
            return False
    
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
- Max file size: 8KB (~2000 tokens)
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
                readme_path.write_text(readme_content, encoding='utf-8')
                self.logger.info("Created README.md in memories directory")
                
        except Exception as e:
            self.logger.error(f"Error ensuring memories directory: {e}")
            # Continue anyway - memory system should not block operations


# Convenience functions for external use
def get_memory_manager(config: Optional[Config] = None) -> AgentMemoryManager:
    """Get a singleton instance of the memory manager.
    
    WHY: The memory manager should be shared across the application to ensure
    consistent file access and avoid multiple instances managing the same files.
    
    Args:
        config: Optional Config object. Only used on first instantiation.
    
    Returns:
        AgentMemoryManager: The memory manager instance
    """
    if not hasattr(get_memory_manager, '_instance'):
        get_memory_manager._instance = AgentMemoryManager(config)
    return get_memory_manager._instance