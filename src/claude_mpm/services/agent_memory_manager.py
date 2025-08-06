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
import os

from claude_mpm.core.config import Config
from claude_mpm.core.mixins import LoggerMixin
from claude_mpm.utils.paths import PathResolver
from claude_mpm.services.project_analyzer import ProjectAnalyzer
# Socket.IO notifications are optional - we'll skip them if server is not available


class AgentMemoryManager:
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
    
    def __init__(self, config: Optional[Config] = None, working_directory: Optional[Path] = None):
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
        self.project_root = PathResolver.get_project_root()
        # Use current working directory by default, not project root
        self.working_directory = working_directory or Path(os.getcwd())
        self.memories_dir = self.working_directory / ".claude-mpm" / "memories"
        self._ensure_memories_directory()
        
        # Initialize memory limits from configuration
        self._init_memory_limits()
        
        # Initialize project analyzer for context-aware memory creation
        self.project_analyzer = ProjectAnalyzer(self.config, self.working_directory)
    
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
        self.memory_enabled = self.config.get('memory.enabled', True)
        self.auto_learning = self.config.get('memory.auto_learning', True)  # Changed default to True
        
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
            
            # Socket.IO notifications removed - memory manager works independently
            
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
        # Convert agent_id to proper name, handling cases like "test_agent" -> "Test"
        agent_name = agent_id.replace('_agent', '').replace('_', ' ').title()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get limits for this agent
        limits = self._get_agent_limits(agent_id)
        
        # Analyze the project for context-specific content
        try:
            project_characteristics = self.project_analyzer.analyze_project()
            project_context = self.project_analyzer.get_project_context_summary()
            important_files = self.project_analyzer.get_important_files_for_context()
            
            self.logger.info(f"Creating project-specific memory for {agent_id} using analyzed project context")
        except Exception as e:
            self.logger.warning(f"Error analyzing project for {agent_id}, falling back to basic template: {e}")
            return self._create_basic_memory_template(agent_id)
        
        # Create project-specific sections
        architecture_items = self._generate_architecture_section(project_characteristics)
        coding_patterns = self._generate_coding_patterns_section(project_characteristics)
        implementation_guidelines = self._generate_implementation_guidelines(project_characteristics)
        tech_context = self._generate_technical_context(project_characteristics)
        integration_points = self._generate_integration_points(project_characteristics)
        
        template = f"""# {agent_name} Agent Memory - {project_characteristics.project_name}

<!-- MEMORY LIMITS: {limits['max_file_size_kb']}KB max | {limits['max_sections']} sections max | {limits['max_items_per_section']} items per section -->
<!-- Last Updated: {timestamp} | Auto-updated by: {agent_id} -->

## Project Context
{project_context}

## Project Architecture
{self._format_section_items(architecture_items)}

## Coding Patterns Learned
{self._format_section_items(coding_patterns)}

## Implementation Guidelines
{self._format_section_items(implementation_guidelines)}

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for {project_characteristics.project_name} domain -->
{self._generate_domain_knowledge_starters(project_characteristics, agent_id)}

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid
{self._format_section_items(self._generate_common_mistakes(project_characteristics))}

## Integration Points
{self._format_section_items(integration_points)}

## Performance Considerations
{self._format_section_items(self._generate_performance_considerations(project_characteristics))}

## Current Technical Context
{self._format_section_items(tech_context)}

## Recent Learnings
<!-- Most recent discoveries and insights -->
"""
        
        # Save default file
        try:
            memory_file = self.memories_dir / f"{agent_id}_agent.md"
            memory_file.write_text(template, encoding='utf-8')
            self.logger.info(f"Created project-specific memory file for {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Error saving default memory for {agent_id}: {e}")
        
        return template
    
    def _create_basic_memory_template(self, agent_id: str) -> str:
        """Create basic memory template when project analysis fails.
        
        WHY: Fallback template ensures agents always get some memory structure
        even if project analysis encounters errors.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            str: Basic memory template
        """
        agent_name = agent_id.replace('_agent', '').replace('_', ' ').title()
        project_name = self.project_root.name
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        limits = self._get_agent_limits(agent_id)
        
        return f"""# {agent_name} Agent Memory - {project_name}

<!-- MEMORY LIMITS: {limits['max_file_size_kb']}KB max | {limits['max_sections']} sections max | {limits['max_items_per_section']} items per section -->
<!-- Last Updated: {timestamp} | Auto-updated by: {agent_id} -->

## Project Context
{project_name}: Software project requiring analysis

## Project Architecture
- Analyze project structure to understand architecture patterns

## Coding Patterns Learned
- Observe codebase patterns and conventions during tasks

## Implementation Guidelines
- Extract implementation guidelines from project documentation

## Domain-Specific Knowledge
<!-- Agent-specific knowledge accumulates here -->

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid
- Learn from errors encountered during project work

## Integration Points
<!-- Key interfaces and integration patterns -->

## Performance Considerations
<!-- Performance insights and optimization patterns -->

## Current Technical Context
- Project analysis pending - gather context during tasks

## Recent Learnings
<!-- Most recent discoveries and insights -->
"""
    
    def _generate_architecture_section(self, characteristics) -> List[str]:
        """Generate architecture section items based on project analysis."""
        items = []
        
        # Architecture type
        items.append(f"{characteristics.architecture_type} with {characteristics.primary_language or 'mixed'} implementation")
        
        # Key directories structure
        if characteristics.key_directories:
            key_dirs = ", ".join(characteristics.key_directories[:5])
            items.append(f"Main directories: {key_dirs}")
        
        # Main modules
        if characteristics.main_modules:
            modules = ", ".join(characteristics.main_modules[:4])
            items.append(f"Core modules: {modules}")
        
        # Entry points
        if characteristics.entry_points:
            entries = ", ".join(characteristics.entry_points[:3])
            items.append(f"Entry points: {entries}")
        
        # Frameworks affecting architecture
        if characteristics.web_frameworks:
            frameworks = ", ".join(characteristics.web_frameworks[:3])
            items.append(f"Web framework stack: {frameworks}")
        
        return items[:8]  # Limit to prevent overwhelming
    
    def _generate_coding_patterns_section(self, characteristics) -> List[str]:
        """Generate coding patterns section based on project analysis."""
        items = []
        
        # Language-specific patterns
        if characteristics.primary_language == 'python':
            items.append("Python project: use type hints, follow PEP 8 conventions")
            if 'django' in [fw.lower() for fw in characteristics.web_frameworks]:
                items.append("Django patterns: models, views, templates separation")
            elif 'flask' in [fw.lower() for fw in characteristics.web_frameworks]:
                items.append("Flask patterns: blueprint organization, app factory pattern")
        elif characteristics.primary_language == 'node_js':
            items.append("Node.js project: use async/await, ES6+ features")
            if 'express' in [fw.lower() for fw in characteristics.web_frameworks]:
                items.append("Express patterns: middleware usage, route organization")
        
        # Framework-specific patterns
        for framework in characteristics.frameworks[:3]:
            if 'react' in framework.lower():
                items.append("React patterns: component composition, hooks usage")
            elif 'vue' in framework.lower():
                items.append("Vue patterns: single file components, composition API")
        
        # Code conventions found
        for convention in characteristics.code_conventions[:3]:
            items.append(f"Project uses: {convention}")
        
        return items[:8]
    
    def _generate_implementation_guidelines(self, characteristics) -> List[str]:
        """Generate implementation guidelines based on project analysis."""
        items = []
        
        # Package manager guidance
        if characteristics.package_manager:
            items.append(f"Use {characteristics.package_manager} for dependency management")
        
        # Testing guidelines
        if characteristics.testing_framework:
            items.append(f"Write tests using {characteristics.testing_framework}")
        
        # Test patterns
        for pattern in characteristics.test_patterns[:2]:
            items.append(f"Follow {pattern.lower()}")
        
        # Build tools
        if characteristics.build_tools:
            tools = ", ".join(characteristics.build_tools[:2])
            items.append(f"Use build tools: {tools}")
        
        # Configuration patterns
        for config_pattern in characteristics.configuration_patterns[:2]:
            items.append(f"Configuration: {config_pattern}")
        
        # Important files to reference
        important_configs = characteristics.important_configs[:3]
        if important_configs:
            configs = ", ".join(important_configs)
            items.append(f"Key config files: {configs}")
        
        return items[:8]
    
    def _generate_technical_context(self, characteristics) -> List[str]:
        """Generate current technical context based on project analysis."""
        items = []
        
        # Technology stack summary
        tech_stack = []
        if characteristics.primary_language:
            tech_stack.append(characteristics.primary_language)
        tech_stack.extend(characteristics.frameworks[:2])
        if tech_stack:
            items.append(f"Tech stack: {', '.join(tech_stack)}")
        
        # Databases in use
        if characteristics.databases:
            dbs = ", ".join(characteristics.databases[:3])
            items.append(f"Data storage: {dbs}")
        
        # API patterns
        if characteristics.api_patterns:
            apis = ", ".join(characteristics.api_patterns[:2])
            items.append(f"API patterns: {apis}")
        
        # Key dependencies
        if characteristics.key_dependencies:
            deps = ", ".join(characteristics.key_dependencies[:4])
            items.append(f"Key dependencies: {deps}")
        
        # Documentation available
        if characteristics.documentation_files:
            docs = ", ".join(characteristics.documentation_files[:3])
            items.append(f"Documentation: {docs}")
        
        return items[:8]
    
    def _generate_integration_points(self, characteristics) -> List[str]:
        """Generate integration points based on project analysis."""
        items = []
        
        # Database integrations
        for db in characteristics.databases[:3]:
            items.append(f"{db.title()} database integration")
        
        # Web framework integrations
        for framework in characteristics.web_frameworks[:2]:
            items.append(f"{framework} web framework integration")
        
        # API integrations
        for api_pattern in characteristics.api_patterns[:2]:
            items.append(f"{api_pattern} integration pattern")
        
        # Common integration patterns based on dependencies
        integration_deps = [dep for dep in characteristics.key_dependencies 
                          if any(keyword in dep.lower() for keyword in ['redis', 'rabbit', 'celery', 'kafka', 'docker'])]
        for dep in integration_deps[:3]:
            items.append(f"{dep} integration")
        
        return items[:6]
    
    def _generate_common_mistakes(self, characteristics) -> List[str]:
        """Generate common mistakes based on project type and stack."""
        items = []
        
        # Language-specific mistakes
        if characteristics.primary_language == 'python':
            items.append("Avoid circular imports - use late imports when needed")
            items.append("Don't ignore virtual environment - always activate before work")
        elif characteristics.primary_language == 'node_js':
            items.append("Avoid callback hell - use async/await consistently")
            items.append("Don't commit node_modules - ensure .gitignore is correct")
        
        # Framework-specific mistakes
        if 'django' in [fw.lower() for fw in characteristics.web_frameworks]:
            items.append("Don't skip migrations - always create and apply them")
        elif 'flask' in [fw.lower() for fw in characteristics.web_frameworks]:
            items.append("Avoid app context issues - use proper application factory")
        
        # Database-specific mistakes
        if characteristics.databases:
            items.append("Don't ignore database transactions in multi-step operations")
            items.append("Avoid N+1 queries - use proper joins or prefetching")
        
        # Testing mistakes
        if characteristics.testing_framework:
            items.append("Don't skip test isolation - ensure tests can run independently")
        
        return items[:8]
    
    def _generate_performance_considerations(self, characteristics) -> List[str]:
        """Generate performance considerations based on project stack."""
        items = []
        
        # Language-specific performance
        if characteristics.primary_language == 'python':
            items.append("Use list comprehensions over loops where appropriate")
            items.append("Consider caching for expensive operations")
        elif characteristics.primary_language == 'node_js':
            items.append("Leverage event loop - avoid blocking operations")
            items.append("Use streams for large data processing")
        
        # Database performance
        if characteristics.databases:
            items.append("Index frequently queried columns")
            items.append("Use connection pooling for database connections")
        
        # Web framework performance
        if characteristics.web_frameworks:
            items.append("Implement appropriate caching strategies")
            items.append("Optimize static asset delivery")
        
        # Framework-specific performance
        if 'react' in [fw.lower() for fw in characteristics.frameworks]:
            items.append("Use React.memo for expensive component renders")
        
        return items[:6]
    
    def _generate_domain_knowledge_starters(self, characteristics, agent_id: str) -> str:
        """Generate domain-specific knowledge starters based on project and agent type."""
        items = []
        
        # Project terminology
        if characteristics.project_terminology:
            terms = ", ".join(characteristics.project_terminology[:4])
            items.append(f"- Key project terms: {terms}")
        
        # Agent-specific starters
        if 'research' in agent_id.lower():
            items.append("- Focus on code analysis, pattern discovery, and architectural insights")
            if characteristics.documentation_files:
                items.append("- Prioritize documentation analysis for comprehensive understanding")
        elif 'engineer' in agent_id.lower():
            items.append("- Focus on implementation patterns, coding standards, and best practices")
            if characteristics.testing_framework:
                items.append(f"- Ensure test coverage using {characteristics.testing_framework}")
        elif 'pm' in agent_id.lower() or 'manager' in agent_id.lower():
            items.append("- Focus on project coordination, task delegation, and progress tracking")
            items.append("- Monitor integration points and cross-component dependencies")
        
        return '\n'.join(items) if items else "<!-- Domain knowledge will accumulate here -->"
    
    def _format_section_items(self, items: List[str]) -> str:
        """Format list of items as markdown bullet points."""
        if not items:
            return "<!-- Items will be added as knowledge accumulates -->"
        
        formatted_items = []
        for item in items:
            # Ensure each item starts with a dash and is properly formatted
            if not item.startswith('- '):
                item = f"- {item}"
            formatted_items.append(item)
        
        return '\n'.join(formatted_items)
    
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
        
        # Ensure line length limit (account for "- " prefix)
        max_item_length = self.memory_limits['max_line_length'] - 2  # Subtract 2 for "- " prefix
        if len(new_item) > max_item_length:
            new_item = new_item[:max_item_length - 3] + '...'
        
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
            f'## {section}',
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
                    f'## {section}',
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
            from claude_mpm.services.memory_optimizer import MemoryOptimizer
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
            from claude_mpm.services.memory_builder import MemoryBuilder
            builder = MemoryBuilder(self.config, self.working_directory)
            
            result = builder.build_from_documentation(force_rebuild)
            self.logger.info("Built memories from documentation")
            
            return result
        except Exception as e:
            self.logger.error(f"Error building memories from docs: {e}")
            return {"success": False, "error": str(e)}
    
    def route_memory_command(self, content: str, context: Optional[Dict] = None) -> Dict[str, Any]:
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
            from claude_mpm.services.memory_router import MemoryRouter
            router = MemoryRouter(self.config)
            
            routing_result = router.analyze_and_route(content, context)
            self.logger.debug(f"Routed memory command: {routing_result['target_agent']}")
            
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
        try:
            status = {
                "system_enabled": self.memory_enabled,
                "auto_learning": self.auto_learning,
                "memory_directory": str(self.memories_dir),
                "total_agents": 0,
                "total_size_kb": 0,
                "agents": {},
                "optimization_opportunities": [],
                "system_health": "healthy"
            }
            
            if not self.memories_dir.exists():
                status["system_health"] = "no_memory_dir"
                return status
            
            memory_files = list(self.memories_dir.glob("*_agent.md"))
            status["total_agents"] = len(memory_files)
            
            total_size = 0
            for file_path in memory_files:
                stat = file_path.stat()
                size_kb = stat.st_size / 1024
                total_size += stat.st_size
                
                agent_id = file_path.stem.replace('_agent', '')
                limits = self._get_agent_limits(agent_id)
                
                # Analyze file content
                try:
                    content = file_path.read_text()
                    section_count = len([line for line in content.splitlines() if line.startswith('## ')])
                    learning_count = len([line for line in content.splitlines() if line.strip().startswith('- ')])
                    
                    agent_status = {
                        "size_kb": round(size_kb, 2),
                        "size_limit_kb": limits['max_file_size_kb'],
                        "size_utilization": min(100, round((size_kb / limits['max_file_size_kb']) * 100, 1)),
                        "sections": section_count,
                        "items": learning_count,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "auto_learning": self._get_agent_auto_learning(agent_id)
                    }
                    
                    # Check for optimization opportunities
                    if size_kb > limits['max_file_size_kb'] * 0.8:
                        status["optimization_opportunities"].append(f"{agent_id}: High memory usage ({size_kb:.1f}KB)")
                    
                    if section_count > limits['max_sections'] * 0.8:
                        status["optimization_opportunities"].append(f"{agent_id}: Many sections ({section_count})")
                    
                    status["agents"][agent_id] = agent_status
                    
                except Exception as e:
                    status["agents"][agent_id] = {"error": str(e)}
            
            status["total_size_kb"] = round(total_size / 1024, 2)
            
            # Determine overall system health
            if len(status["optimization_opportunities"]) > 3:
                status["system_health"] = "needs_optimization"
            elif status["total_size_kb"] > 100:  # More than 100KB total
                status["system_health"] = "high_usage"
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting memory status: {e}")
            return {"success": False, "error": str(e)}
    
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
        try:
            cross_refs = {
                "common_patterns": [],
                "knowledge_gaps": [],
                "redundancies": [],
                "agent_correlations": {},
                "query_matches": [] if query else None
            }
            
            if not self.memories_dir.exists():
                return cross_refs
            
            memory_files = list(self.memories_dir.glob("*_agent.md"))
            agent_memories = {}
            
            # Load all agent memories
            for file_path in memory_files:
                agent_id = file_path.stem.replace('_agent', '')
                try:
                    content = file_path.read_text()
                    agent_memories[agent_id] = content
                except Exception as e:
                    self.logger.warning(f"Error reading memory for {agent_id}: {e}")
                    continue
            
            # Find common patterns across agents
            all_lines = []
            agent_lines = {}
            
            for agent_id, content in agent_memories.items():
                lines = [line.strip() for line in content.splitlines() 
                        if line.strip().startswith('- ')]
                agent_lines[agent_id] = lines
                all_lines.extend([(line, agent_id) for line in lines])
            
            # Look for similar content (basic similarity check)
            line_counts = {}
            for line, agent_id in all_lines:
                # Normalize line for comparison
                normalized = line.lower().replace('- ', '').strip()
                if len(normalized) > 20:  # Only check substantial lines
                    if normalized not in line_counts:
                        line_counts[normalized] = []
                    line_counts[normalized].append(agent_id)
            
            # Find patterns appearing in multiple agents
            for line, agents in line_counts.items():
                if len(set(agents)) > 1:  # Appears in multiple agents
                    cross_refs["common_patterns"].append({
                        "pattern": line[:100] + "..." if len(line) > 100 else line,
                        "agents": list(set(agents)),
                        "count": len(agents)
                    })
            
            # Query-specific matches
            if query:
                query_lower = query.lower()
                for agent_id, content in agent_memories.items():
                    matches = []
                    for line in content.splitlines():
                        if query_lower in line.lower():
                            matches.append(line.strip())
                    
                    if matches:
                        cross_refs["query_matches"].append({
                            "agent": agent_id,
                            "matches": matches[:5]  # Limit to first 5 matches
                        })
            
            # Calculate agent correlations (agents with similar knowledge domains)
            for agent_a in agent_memories:
                for agent_b in agent_memories:
                    if agent_a < agent_b:  # Avoid duplicates
                        common_count = len([
                            line for line in line_counts.values()
                            if agent_a in line and agent_b in line
                        ])
                        
                        if common_count > 0:
                            correlation_key = f"{agent_a}+{agent_b}"
                            cross_refs["agent_correlations"][correlation_key] = common_count
            
            return cross_refs
            
        except Exception as e:
            self.logger.error(f"Error cross-referencing memories: {e}")
            return {"success": False, "error": str(e)}

    def get_all_memories_raw(self) -> Dict[str, Any]:
        """Get all agent memories in structured JSON format.
        
        WHY: This provides programmatic access to all agent memories, allowing
        external tools, scripts, or APIs to retrieve and process the complete
        memory state of the system.
        
        DESIGN DECISION: Returns structured data with metadata for each agent
        including file stats, sections, and parsed content. This enables both
        content access and system analysis.
        
        Returns:
            Dict containing structured memory data for all agents
        """
        try:
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "total_agents": 0,
                "total_size_bytes": 0,
                "agents": {}
            }
            
            # Ensure directory exists
            if not self.memories_dir.exists():
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "total_agents": 0,
                    "total_size_bytes": 0,
                    "agents": {},
                    "message": "No memory directory found"
                }
            
            # Find all agent memory files
            memory_files = list(self.memories_dir.glob("*_agent.md"))
            result["total_agents"] = len(memory_files)
            
            # Process each agent memory file
            for file_path in sorted(memory_files):
                agent_id = file_path.stem.replace('_agent', '')
                
                try:
                    # Get file stats
                    stat = file_path.stat()
                    file_size = stat.st_size
                    result["total_size_bytes"] += file_size
                    
                    # Load and parse memory content
                    memory_content = self.load_agent_memory(agent_id)
                    
                    if memory_content:
                        sections = self._parse_memory_content_to_dict(memory_content)
                        
                        # Count total items across all sections
                        total_items = sum(len(items) for items in sections.values())
                        
                        result["agents"][agent_id] = {
                            "agent_id": agent_id,
                            "file_path": str(file_path),
                            "file_size_bytes": file_size,
                            "file_size_kb": round(file_size / 1024, 2),
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "sections_count": len(sections),
                            "total_items": total_items,
                            "auto_learning": self._get_agent_auto_learning(agent_id),
                            "size_limits": self._get_agent_limits(agent_id),
                            "sections": sections,
                            "raw_content": memory_content
                        }
                    else:
                        result["agents"][agent_id] = {
                            "agent_id": agent_id,
                            "file_path": str(file_path),
                            "file_size_bytes": file_size,
                            "file_size_kb": round(file_size / 1024, 2),
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "error": "Could not load memory content",
                            "sections": {},
                            "raw_content": ""
                        }
                        
                except Exception as e:
                    self.logger.error(f"Error processing memory for agent {agent_id}: {e}")
                    result["agents"][agent_id] = {
                        "agent_id": agent_id,
                        "file_path": str(file_path),
                        "error": str(e),
                        "sections": {},
                        "raw_content": ""
                    }
            
            result["total_size_kb"] = round(result["total_size_bytes"] / 1024, 2)
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting all memories raw: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _parse_memory_content_to_dict(self, content: str) -> Dict[str, List[str]]:
        """Parse memory content into structured dictionary format.
        
        WHY: Provides consistent parsing of memory content into sections and items
        for both display and programmatic access. This ensures the same parsing
        logic is used across the system.
        
        Args:
            content: Raw memory file content
            
        Returns:
            Dict mapping section names to lists of items
        """
        sections = {}
        current_section = None
        current_items = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and header information
            if not line or line.startswith('#') and 'Memory Usage' in line:
                continue
                
            if line.startswith('## ') and not line.startswith('## Memory Usage'):
                # New section found
                if current_section and current_items:
                    sections[current_section] = current_items.copy()
                
                current_section = line[3:].strip()
                current_items = []
                
            elif line.startswith('- ') and current_section:
                # Item in current section
                item = line[2:].strip()
                if item and len(item) > 3:  # Filter out very short items
                    current_items.append(item)
        
        # Add final section
        if current_section and current_items:
            sections[current_section] = current_items
        
        return sections

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
def get_memory_manager(config: Optional[Config] = None, working_directory: Optional[Path] = None) -> AgentMemoryManager:
    """Get a singleton instance of the memory manager.
    
    WHY: The memory manager should be shared across the application to ensure
    consistent file access and avoid multiple instances managing the same files.
    
    Args:
        config: Optional Config object. Only used on first instantiation.
        working_directory: Optional working directory. Only used on first instantiation.
    
    Returns:
        AgentMemoryManager: The memory manager instance
    """
    if not hasattr(get_memory_manager, '_instance'):
        get_memory_manager._instance = AgentMemoryManager(config, working_directory)
    return get_memory_manager._instance