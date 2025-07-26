#!/usr/bin/env python3
"""
Framework INSTRUCTIONS.md Generator Service - Consolidated Module
===============================================================

This service provides structured generation of the framework INSTRUCTIONS.md template
(legacy: CLAUDE.md) with auto-versioning, section management, and deployment capabilities.

This is a consolidated version combining all functionality from the previous
multi-file implementation for better maintainability.
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SectionContent:
    """Represents a section of the INSTRUCTIONS.md file."""
    id: str
    title: str
    content: str
    order: int
    required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Results from content validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# ============================================================================
# Section Generators
# ============================================================================

class SectionGenerators:
    """All section generators in a single class for maintainability."""
    
    @staticmethod
    def generate_header(version: str, **kwargs) -> str:
        """Generate the header section."""
        return f"""# Multi-Agent Project Management Framework v{version}
## INSTRUCTIONS.md - Claude PM Orchestrator Agent
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    @staticmethod
    def generate_claude_pm_init(**kwargs) -> str:
        """Generate Claude PM initialization section."""
        return """## Claude PM Initialization

You are the Claude PM (Project Manager) orchestrator agent. Your primary role is to:

1. **Orchestrate Multi-Agent Workflows**: Delegate tasks to specialized agents based on their expertise
2. **Maintain Project Context**: Keep track of project state, goals, and progress
3. **Ensure Quality**: Monitor agent outputs and ensure they meet project standards
4. **Coordinate Communication**: Facilitate information flow between agents

### Key Responsibilities:
- Analyze incoming requests and determine appropriate agent delegation
- Monitor subprocess execution and handle results
- Maintain project consistency across agent boundaries
- Provide clear, actionable feedback to users
"""

    @staticmethod
    def generate_role_designation(**kwargs) -> str:
        """Generate role designation section."""
        return """## Role Designation

As the PM orchestrator, you have access to the following specialized agents:

### Core Agents:
- **Engineer**: Code implementation, debugging, refactoring
- **Architect**: System design, technical architecture, scalability
- **QA**: Testing, quality assurance, test automation
- **Security**: Security analysis, vulnerability assessment
- **Documentation**: Technical writing, API docs, user guides
- **Ops**: DevOps, deployment, infrastructure
- **Data**: Data engineering, analytics, database design
- **Research**: Technical research, feasibility studies
- **Version Control**: Git operations, branching strategies

### Specialized Agents:
- Additional domain-specific agents available based on project needs
"""

    @staticmethod
    def generate_core_responsibilities(**kwargs) -> str:
        """Generate core responsibilities section."""
        return """## Core Responsibilities

### 1. Request Analysis
- Parse and understand user requirements
- Identify required expertise and resources
- Determine optimal agent delegation strategy

### 2. Agent Delegation
- Select appropriate agents based on task requirements
- Prepare clear, specific instructions for each agent
- Use subprocess execution for agent tasks

### 3. Result Synthesis
- Collect and validate agent outputs
- Ensure consistency across deliverables
- Present cohesive results to users

### 4. Quality Assurance
- Monitor agent performance
- Validate outputs meet requirements
- Request revisions when necessary
"""

    @staticmethod
    def generate_orchestration_principles(**kwargs) -> str:
        """Generate orchestration principles section."""
        return """## Orchestration Principles

### Delegation Guidelines:
1. **Single Responsibility**: Each agent handles their domain expertise
2. **Clear Instructions**: Provide specific, actionable tasks
3. **Context Preservation**: Pass necessary context between agents
4. **Result Validation**: Verify outputs before presenting to users

### Communication Protocol:
- Use structured task definitions
- Include success criteria in delegations
- Request specific output formats
- Handle errors gracefully
"""

    @staticmethod
    def generate_delegation_constraints(**kwargs) -> str:
        """Generate delegation constraints section."""
        return """## Delegation Constraints

### Never Delegate:
- User authentication/authorization decisions
- Sensitive data handling without oversight
- Direct production deployments
- Financial or legal decisions

### Always Delegate:
- Domain-specific implementation tasks
- Technical analysis requiring expertise
- Large-scale code generation
- Specialized testing scenarios
"""

    @staticmethod
    def generate_subprocess_validation(**kwargs) -> str:
        """Generate subprocess validation section."""
        return """## Subprocess Validation

### Pre-Delegation Checks:
1. Validate agent availability
2. Ensure task is within agent capabilities
3. Verify resource requirements
4. Check for circular dependencies

### Post-Execution Validation:
1. Verify subprocess completed successfully
2. Validate output format and content
3. Check for errors or warnings
4. Ensure deliverables meet requirements

### Error Handling:
- Capture and log subprocess errors
- Provide meaningful error messages
- Suggest alternatives when agents fail
- Maintain graceful degradation
"""

    @staticmethod
    def generate_agents(agent_profiles: Optional[List[Dict]] = None, **kwargs) -> str:
        """Generate comprehensive agents section."""
        if not agent_profiles:
            # Default agent profiles
            agent_profiles = [
                {
                    "name": "Engineer",
                    "role": "Software Engineering Expert",
                    "capabilities": [
                        "Code implementation in multiple languages",
                        "Debugging and troubleshooting",
                        "Performance optimization",
                        "Code refactoring"
                    ]
                },
                {
                    "name": "Architect",
                    "role": "System Architecture Expert",
                    "capabilities": [
                        "System design and architecture",
                        "Technology selection",
                        "Scalability planning",
                        "Integration design"
                    ]
                },
                # Add more default profiles as needed
            ]
        
        content = "## Available Agents\n\n"
        
        for profile in agent_profiles:
            content += f"### {profile['name']} Agent\n"
            content += f"**Role**: {profile['role']}\n\n"
            content += "**Capabilities**:\n"
            for capability in profile.get('capabilities', []):
                content += f"- {capability}\n"
            content += "\n"
        
        return content

    @staticmethod
    def generate_todo_task_tools(**kwargs) -> str:
        """Generate todo/task tools section."""
        return """## Task Management Tools

### TodoWrite Tool
Use the TodoWrite tool to manage task lists and track progress:
- Create structured task lists for complex workflows
- Track task status (pending, in_progress, completed)
- Organize multi-step operations
- Demonstrate thoroughness to users

**CRITICAL TodoWrite Requirement**: 
- **ALWAYS** prefix each todo item with [Agent] to indicate delegation target
- Examples: [Research], [Engineer], [QA], [Security], [Documentation], [Ops], [Version Control]
- This ensures proper task attribution and tracking across the multi-agent system
- The system will automatically validate and enforce this requirement

### Task Tool (Subprocess Execution)
The Task tool enables subprocess delegation:
- Execute specialized agent tasks
- Run isolated operations
- Maintain clean execution contexts
- Handle long-running operations

### Usage Guidelines:
1. Use TodoWrite for task planning and tracking with [Agent] prefixes
2. Use Task tool for actual agent delegation
3. Update todo items as tasks complete
4. Maintain clear task descriptions with proper agent attribution
"""

    @staticmethod
    def generate_environment_config(**kwargs) -> str:
        """Generate environment configuration section."""
        return """## Environment Configuration

### Working Directory Structure:
- Maintain awareness of project structure
- Respect existing file organization
- Create new directories only when necessary
- Follow project conventions

### Resource Management:
- Monitor subprocess resource usage
- Implement timeouts for long operations
- Clean up temporary resources
- Handle resource conflicts gracefully
"""

    @staticmethod
    def generate_troubleshooting(**kwargs) -> str:
        """Generate troubleshooting section."""
        return """## Troubleshooting Guide

### Common Issues:

1. **Agent Not Found**
   - Verify agent name spelling
   - Check agent availability
   - Use fallback strategies

2. **Subprocess Timeout**
   - Increase timeout for complex tasks
   - Break down large operations
   - Monitor resource usage

3. **Output Validation Failure**
   - Review agent instructions
   - Check output format requirements
   - Request clarification if needed

4. **Context Loss**
   - Maintain explicit context passing
   - Use structured data formats
   - Implement checkpoints
"""

    @staticmethod
    def generate_footer(version: str, **kwargs) -> str:
        """Generate footer section."""
        return f"""
---
Framework Version: {version}
Last Updated: {datetime.now().strftime('%Y-%m-%d')}
"""


# ============================================================================
# Main Generator Class
# ============================================================================

class FrameworkClaudeMdGenerator:
    """
    Generates and manages the framework INSTRUCTIONS.md template (legacy: CLAUDE.md) 
    with structured sections, auto-versioning, and deployment capabilities.
    
    This consolidated version combines all functionality into a single module.
    """
    
    def __init__(self):
        """Initialize the generator with current framework version."""
        self.framework_version = self._detect_framework_version()
        self.sections: List[SectionContent] = []
        self.section_generators = SectionGenerators()
        
        # Deployment paths
        self.framework_root = self._find_framework_root()
        self.deployment_targets = {
            'framework': self.framework_root / 'INSTRUCTIONS.md' if self.framework_root else None,
            'user': Path.home() / '.claude-pm' / 'INSTRUCTIONS.md',
            'project': Path.cwd() / 'INSTRUCTIONS.md'
        }
        
        # Initialize default sections
        self._initialize_sections()
        
        logger.info(f"FrameworkClaudeMdGenerator initialized with version {self.framework_version}")
    
    def _detect_framework_version(self) -> str:
        """Detect the current framework version."""
        # Try multiple locations for VERSION file
        version_locations = [
            Path(__file__).parent.parent / 'framework' / 'VERSION',
            Path.cwd() / 'framework' / 'VERSION',
            Path.home() / '.claude-pm' / 'VERSION'
        ]
        
        for version_file in version_locations:
            if version_file.exists():
                try:
                    return version_file.read_text().strip()
                except Exception:
                    pass
        
        # Default version
        return "1.0.0"
    
    def _find_framework_root(self) -> Optional[Path]:
        """Find the framework root directory."""
        possible_roots = [
            Path(__file__).parent.parent / 'framework',
            Path.cwd() / 'framework',
            Path.cwd() / 'src' / 'claude_mpm' / 'framework'
        ]
        
        for root in possible_roots:
            if root.exists():
                return root
        
        return None
    
    def _initialize_sections(self) -> None:
        """Initialize all sections in the required order."""
        section_configs = [
            ("header", "Header", self.section_generators.generate_header, True),
            ("claude_pm_init", "Claude PM Initialization", self.section_generators.generate_claude_pm_init, True),
            ("role_designation", "Role Designation", self.section_generators.generate_role_designation, True),
            ("core_responsibilities", "Core Responsibilities", self.section_generators.generate_core_responsibilities, True),
            ("orchestration_principles", "Orchestration Principles", self.section_generators.generate_orchestration_principles, True),
            ("delegation_constraints", "Delegation Constraints", self.section_generators.generate_delegation_constraints, True),
            ("subprocess_validation", "Subprocess Validation", self.section_generators.generate_subprocess_validation, True),
            ("agents", "Available Agents", self.section_generators.generate_agents, True),
            ("todo_task_tools", "Task Management Tools", self.section_generators.generate_todo_task_tools, True),
            ("environment_config", "Environment Configuration", self.section_generators.generate_environment_config, False),
            ("troubleshooting", "Troubleshooting Guide", self.section_generators.generate_troubleshooting, False),
            ("footer", "Footer", self.section_generators.generate_footer, True)
        ]
        
        for order, (section_id, title, generator, required) in enumerate(section_configs):
            self.add_section(section_id, title, generator, order, required)
    
    def add_section(self, section_id: str, title: str, 
                   generator: Callable, order: int, required: bool = True) -> None:
        """Add a section to the generator."""
        section = SectionContent(
            id=section_id,
            title=title,
            content="",  # Will be generated
            order=order,
            required=required
        )
        self.sections.append(section)
        
        # Store generator reference
        section.metadata['generator'] = generator
    
    def generate_content(self, include_optional: bool = True,
                        custom_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate the complete INSTRUCTIONS.md content."""
        content_parts = []
        custom_data = custom_data or {}
        
        # Sort sections by order
        sorted_sections = sorted(self.sections, key=lambda s: s.order)
        
        for section in sorted_sections:
            # Skip optional sections if not included
            if not section.required and not include_optional:
                continue
            
            # Generate section content
            generator = section.metadata.get('generator')
            if generator:
                section_content = generator(
                    version=self.framework_version,
                    **custom_data
                )
                section.content = section_content
                content_parts.append(section_content)
        
        return "\n".join(content_parts)
    
    def validate_content(self, content: str) -> ValidationResult:
        """Validate generated content."""
        errors = []
        warnings = []
        suggestions = []
        
        # Check minimum length
        if len(content) < 1000:
            errors.append("Content seems too short")
        
        # Check for required sections
        required_sections = [
            "Claude PM Initialization",
            "Role Designation", 
            "Core Responsibilities"
        ]
        
        for required in required_sections:
            if required not in content:
                errors.append(f"Missing required section: {required}")
        
        # Check for version
        if self.framework_version not in content:
            warnings.append("Framework version not found in content")
        
        # Structure validation
        if content.count('#') < 5:
            warnings.append("Content may lack proper structure (too few headers)")
        
        # Suggestions
        if "```" not in content:
            suggestions.append("Consider adding code examples")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def deploy(self, target: str = 'framework', 
              backup: bool = True,
              validate: bool = True) -> Tuple[bool, str]:
        """Deploy generated content to target location."""
        if target not in self.deployment_targets:
            return False, f"Unknown deployment target: {target}"
        
        target_path = self.deployment_targets[target]
        if not target_path:
            return False, f"Target path for '{target}' not configured"
        
        # Generate content
        content = self.generate_content()
        
        # Validate if requested
        if validate:
            validation_result = self.validate_content(content)
            if not validation_result.is_valid:
                return False, f"Validation failed: {', '.join(validation_result.errors)}"
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file if requested
        if backup and target_path.exists():
            backup_path = target_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(target_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Write new content
        try:
            target_path.write_text(content)
            logger.info(f"Deployed to: {target_path}")
            return True, f"Successfully deployed to {target_path}"
        except Exception as e:
            return False, f"Deployment failed: {e}"
    
    def update_version(self, new_version: str) -> None:
        """Update the framework version."""
        self.framework_version = new_version
        logger.info(f"Updated framework version to {new_version}")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get deployment status for all targets."""
        status = {}
        
        for target, path in self.deployment_targets.items():
            if not path:
                status[target] = {'exists': False, 'accessible': False}
                continue
            
            status[target] = {
                'exists': path.exists(),
                'accessible': path.parent.exists() and os.access(path.parent, os.W_OK),
                'path': str(path)
            }
            
            if path.exists():
                stat = path.stat()
                status[target].update({
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return status
    
    def export_template(self, output_path: Path, 
                       format: str = 'markdown') -> bool:
        """Export template to specified path and format."""
        content = self.generate_content()
        
        try:
            if format == 'markdown':
                output_path.write_text(content)
            elif format == 'html':
                # Simple markdown to HTML conversion
                import re
                html_content = content
                # Convert headers
                html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
                # Convert lists
                html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
                # Wrap in basic HTML
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Framework INSTRUCTIONS.md</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1, h2, h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 4px; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
                output_path.write_text(html_content)
            else:
                return False
            
            logger.info(f"Exported template to {output_path} as {format}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def get_section_by_id(self, section_id: str) -> Optional[SectionContent]:
        """Get a specific section by ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None
    
    def update_section_content(self, section_id: str, new_content: str) -> bool:
        """Update content for a specific section."""
        section = self.get_section_by_id(section_id)
        if section:
            section.content = new_content
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics."""
        content = self.generate_content()
        
        return {
            'framework_version': self.framework_version,
            'total_sections': len(self.sections),
            'required_sections': len([s for s in self.sections if s.required]),
            'optional_sections': len([s for s in self.sections if not s.required]),
            'content_length': len(content),
            'line_count': content.count('\n'),
            'deployment_targets': list(self.deployment_targets.keys())
        }