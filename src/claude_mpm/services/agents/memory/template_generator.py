#!/usr/bin/env python3
"""
Memory Template Generator
========================

Generates project-specific memory templates for agents based on project analysis.

This module provides:
- Project-specific memory template creation
- Section generation based on project characteristics
- Domain-specific knowledge starters
- Fallback templates when project analysis fails
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.config import Config
from claude_mpm.services.project.analyzer import ProjectAnalyzer


class MemoryTemplateGenerator:
    """Generates project-specific memory templates for agents.

    WHY: Instead of generic templates, agents need project-specific knowledge
    from the start. This class analyzes the current project and creates contextual
    memories with actual project characteristics.
    """

    REQUIRED_SECTIONS = [
        "Project Architecture",
        "Implementation Guidelines",
        "Common Mistakes to Avoid",
        "Current Technical Context",
    ]

    def __init__(
        self, config: Config, working_directory: Path, project_analyzer: ProjectAnalyzer
    ):
        """Initialize the template generator.

        Args:
            config: Configuration object
            working_directory: Working directory path
            project_analyzer: Project analyzer instance
        """
        self.config = config
        self.working_directory = working_directory
        self.project_analyzer = project_analyzer
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create_default_memory(self, agent_id: str, limits: Dict[str, Any]) -> str:
        """Create project-specific default memory file for agent.

        Args:
            agent_id: The agent identifier
            limits: Memory limits for this agent

        Returns:
            str: The project-specific memory template content
        """
        # Convert agent_id to proper name, handling cases like "test_agent" -> "Test"
        agent_name = agent_id.replace("_agent", "").replace("_", " ").title()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Analyze the project for context-specific content
        try:
            project_characteristics = self.project_analyzer.analyze_project()
            project_context = self.project_analyzer.get_project_context_summary()

            self.logger.info(
                f"Creating project-specific memory for {agent_id} using analyzed project context"
            )
        except Exception as e:
            self.logger.warning(
                f"Error analyzing project for {agent_id}, falling back to basic template: {e}"
            )
            return self._create_basic_memory_template(agent_id, limits)

        # Create project-specific sections
        architecture_items = self._generate_architecture_section(
            project_characteristics
        )
        coding_patterns = self._generate_coding_patterns_section(
            project_characteristics
        )
        implementation_guidelines = self._generate_implementation_guidelines(
            project_characteristics
        )
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

        return template

    def _create_basic_memory_template(
        self, agent_id: str, limits: Dict[str, Any]
    ) -> str:
        """Create basic memory template when project analysis fails.

        Args:
            agent_id: The agent identifier
            limits: Memory limits for this agent

        Returns:
            str: Basic memory template
        """
        agent_name = agent_id.replace("_agent", "").replace("_", " ").title()
        project_name = self.working_directory.name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        items.append(
            f"{characteristics.architecture_type} with {characteristics.primary_language or 'mixed'} implementation"
        )

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
        if characteristics.primary_language == "python":
            items.append("Python project: use type hints, follow PEP 8 conventions")
            if "django" in [fw.lower() for fw in characteristics.web_frameworks]:
                items.append("Django patterns: models, views, templates separation")
            elif "flask" in [fw.lower() for fw in characteristics.web_frameworks]:
                items.append(
                    "Flask patterns: blueprint organization, app factory pattern"
                )
        elif characteristics.primary_language == "node_js":
            items.append("Node.js project: use async/await, ES6+ features")
            if "express" in [fw.lower() for fw in characteristics.web_frameworks]:
                items.append("Express patterns: middleware usage, route organization")

        # Framework-specific patterns
        for framework in characteristics.frameworks[:3]:
            if "react" in framework.lower():
                items.append("React patterns: component composition, hooks usage")
            elif "vue" in framework.lower():
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
            items.append(
                f"Use {characteristics.package_manager} for dependency management"
            )

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
        integration_deps = [
            dep
            for dep in characteristics.key_dependencies
            if any(
                keyword in dep.lower()
                for keyword in ["redis", "rabbit", "celery", "kafka", "docker"]
            )
        ]
        for dep in integration_deps[:3]:
            items.append(f"{dep} integration")

        return items[:6]

    def _generate_common_mistakes(self, characteristics) -> List[str]:
        """Generate common mistakes based on project type and stack."""
        items = []

        # Language-specific mistakes
        if characteristics.primary_language == "python":
            items.append("Avoid circular imports - use late imports when needed")
            items.append(
                "Don't ignore virtual environment - always activate before work"
            )
        elif characteristics.primary_language == "node_js":
            items.append("Avoid callback hell - use async/await consistently")
            items.append("Don't commit node_modules - ensure .gitignore is correct")

        # Framework-specific mistakes
        if "django" in [fw.lower() for fw in characteristics.web_frameworks]:
            items.append("Don't skip migrations - always create and apply them")
        elif "flask" in [fw.lower() for fw in characteristics.web_frameworks]:
            items.append("Avoid app context issues - use proper application factory")

        # Database-specific mistakes
        if characteristics.databases:
            items.append("Don't ignore database transactions in multi-step operations")
            items.append("Avoid N+1 queries - use proper joins or prefetching")

        # Testing mistakes
        if characteristics.testing_framework:
            items.append(
                "Don't skip test isolation - ensure tests can run independently"
            )

        return items[:8]

    def _generate_performance_considerations(self, characteristics) -> List[str]:
        """Generate performance considerations based on project stack."""
        items = []

        # Language-specific performance
        if characteristics.primary_language == "python":
            items.append("Use list comprehensions over loops where appropriate")
            items.append("Consider caching for expensive operations")
        elif characteristics.primary_language == "node_js":
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
        if "react" in [fw.lower() for fw in characteristics.frameworks]:
            items.append("Use React.memo for expensive component renders")

        return items[:6]

    def _generate_domain_knowledge_starters(
        self, characteristics, agent_id: str
    ) -> str:
        """Generate domain-specific knowledge starters based on project and agent type."""
        items = []

        # Project terminology
        if characteristics.project_terminology:
            terms = ", ".join(characteristics.project_terminology[:4])
            items.append(f"- Key project terms: {terms}")

        # Agent-specific starters
        if "research" in agent_id.lower():
            items.append(
                "- Focus on code analysis, pattern discovery, and architectural insights"
            )
            if characteristics.documentation_files:
                items.append(
                    "- Prioritize documentation analysis for comprehensive understanding"
                )
        elif "engineer" in agent_id.lower():
            items.append(
                "- Focus on implementation patterns, coding standards, and best practices"
            )
            if characteristics.testing_framework:
                items.append(
                    f"- Ensure test coverage using {characteristics.testing_framework}"
                )
        elif "pm" in agent_id.lower() or "manager" in agent_id.lower():
            items.append(
                "- Focus on project coordination, task delegation, and progress tracking"
            )
            items.append(
                "- Monitor integration points and cross-component dependencies"
            )

        return (
            "\n".join(items)
            if items
            else "<!-- Domain knowledge will accumulate here -->"
        )

    def _format_section_items(self, items: List[str]) -> str:
        """Format list of items as markdown bullet points."""
        if not items:
            return "<!-- Items will be added as knowledge accumulates -->"

        formatted_items = []
        for item in items:
            # Ensure each item starts with a dash and is properly formatted
            if not item.startswith("- "):
                item = f"- {item}"
            formatted_items.append(item)

        return "\n".join(formatted_items)
