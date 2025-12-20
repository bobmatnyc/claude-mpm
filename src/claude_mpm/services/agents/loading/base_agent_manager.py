#!/usr/bin/env python3
"""
Base Agent Manager
==================

Specialized manager for base_agent.md with structured update capabilities.
Enforces template structure and provides section-specific update methods.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache
from claude_mpm.services.shared import ConfigServiceBase

logger = get_logger(__name__)


class BaseAgentSection(str, Enum):
    """Base agent markdown sections."""

    FRAMEWORK_CONTEXT = "Agent Framework Context"
    BEHAVIORAL_RULES = "Common Behavioral Rules"
    TEMPORAL_CONTEXT = "Temporal Context Integration"
    QUALITY_STANDARDS = "Quality Standards"
    TOOL_USAGE = "Tool Usage Guidelines"
    COLLABORATION = "Collaboration Protocols"
    PERFORMANCE = "Performance Optimization"
    ESCALATION = "Escalation Triggers"
    OUTPUT_FORMATS = "Output Formatting Standards"
    FRAMEWORK_INTEGRATION = "Framework Integration"
    CONSTRAINTS = "Universal Constraints"
    SUCCESS_CRITERIA = "Success Criteria"


@dataclass
class BaseAgentStructure:
    """Structured representation of base_agent.md content."""

    # Header
    title: str = "Base Agent Instructions"
    description: str = "These instructions are prepended to EVERY agent prompt."

    # Main sections
    framework_context: Dict[str, Any] = field(default_factory=dict)
    behavioral_rules: Dict[str, List[str]] = field(default_factory=dict)
    temporal_context: str = ""
    quality_standards: Dict[str, List[str]] = field(default_factory=dict)
    tool_usage: Dict[str, List[str]] = field(default_factory=dict)
    collaboration_protocols: Dict[str, str] = field(default_factory=dict)
    performance_optimization: Dict[str, str] = field(default_factory=dict)
    escalation_triggers: List[str] = field(default_factory=list)
    output_formats: Dict[str, str] = field(default_factory=dict)
    framework_integration: Dict[str, List[str]] = field(default_factory=dict)
    universal_constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    # Raw sections for preservation
    raw_sections: Dict[str, str] = field(default_factory=dict)


class BaseAgentManager(ConfigServiceBase):
    """Manages base_agent.md with structured updates and validation."""

    def __init__(
        self, agents_dir: Optional[Path] = None, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize BaseAgentManager."""
        super().__init__("base_agent_manager", config=config)

        # Initialize paths using configuration
        self.agents_dir = self.get_config_value(
            "agents_dir",
            default=agents_dir or Path(__file__).parent.parent / "agents",
            config_type=Path,
        )
        self.base_agent_path = self.agents_dir / "BASE_AGENT_TEMPLATE.md"
        self.cache = SharedPromptCache.get_instance()

    def read_base_agent(self) -> Optional[BaseAgentStructure]:
        """
        Read and parse base_agent.md into structured format.

        Returns:
            BaseAgentStructure or None if file doesn't exist
        """
        if not self.base_agent_path.exists():
            logger.error(f"base_agent.md not found at {self.base_agent_path}")
            return None

        try:
            content = self.base_agent_path.read_text(encoding="utf-8")
            return self._parse_base_agent(content)
        except Exception as e:
            logger.error(f"Error reading base_agent.md: {e}")
            return None

    def update_base_agent(
        self, updates: Dict[str, Any], backup: bool = True
    ) -> Optional[BaseAgentStructure]:
        """
        Update base_agent.md with structured updates.

        Args:
            updates: Dictionary of updates to apply
            backup: Whether to create backup before updating

        Returns:
            Updated BaseAgentStructure or None if failed
        """
        # Read current structure
        current = self.read_base_agent()
        if not current:
            logger.error("Cannot update - base_agent.md not found")
            return None

        # Create backup if requested
        if backup:
            self._create_backup()

        # Apply updates
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)
            else:
                logger.warning(f"Unknown base agent attribute: {key}")

        # Convert back to markdown and save
        content = self._structure_to_markdown(current)
        self.base_agent_path.write_text(content, encoding="utf-8")

        # Clear cache
        self.cache.invalidate("base_agent:instructions")

        logger.info("Base agent updated successfully")
        return current

    def update_section(
        self, section: BaseAgentSection, content: str, backup: bool = True
    ) -> Optional[BaseAgentStructure]:
        """
        Update a specific section of base_agent.md.

        Args:
            section: Section to update
            content: New section content
            backup: Whether to create backup

        Returns:
            Updated BaseAgentStructure or None
        """
        current = self.read_base_agent()
        if not current:
            return None

        # Map sections to structure attributes
        section_map = {
            BaseAgentSection.FRAMEWORK_CONTEXT: "framework_context",
            BaseAgentSection.BEHAVIORAL_RULES: "behavioral_rules",
            BaseAgentSection.TEMPORAL_CONTEXT: "temporal_context",
            BaseAgentSection.QUALITY_STANDARDS: "quality_standards",
            BaseAgentSection.TOOL_USAGE: "tool_usage",
            BaseAgentSection.COLLABORATION: "collaboration_protocols",
            BaseAgentSection.PERFORMANCE: "performance_optimization",
            BaseAgentSection.ESCALATION: "escalation_triggers",
            BaseAgentSection.OUTPUT_FORMATS: "output_formats",
            BaseAgentSection.FRAMEWORK_INTEGRATION: "framework_integration",
            BaseAgentSection.CONSTRAINTS: "universal_constraints",
            BaseAgentSection.SUCCESS_CRITERIA: "success_criteria",
        }

        if section in section_map:
            attr_name = section_map[section]

            # Parse content based on section type
            if section in [
                BaseAgentSection.ESCALATION,
                BaseAgentSection.CONSTRAINTS,
                BaseAgentSection.SUCCESS_CRITERIA,
            ]:
                # List sections
                parsed_content = self._parse_list_content(content)
                setattr(current, attr_name, parsed_content)
            elif section == BaseAgentSection.TEMPORAL_CONTEXT:
                # String section
                setattr(current, attr_name, content.strip())
            else:
                # Dictionary sections - preserve raw for now
                current.raw_sections[section.value] = content

        # Update and return
        return self.update_base_agent({}, backup=backup)

    def add_behavioral_rule(self, category: str, rule: str) -> bool:
        """Add a new behavioral rule to a specific category."""
        current = self.read_base_agent()
        if not current:
            return False

        if category not in current.behavioral_rules:
            current.behavioral_rules[category] = []

        if rule not in current.behavioral_rules[category]:
            current.behavioral_rules[category].append(rule)
            self.update_base_agent({"behavioral_rules": current.behavioral_rules})
            return True

        return False

    def add_quality_standard(self, category: str, standard: str) -> bool:
        """Add a new quality standard to a specific category."""
        current = self.read_base_agent()
        if not current:
            return False

        if category not in current.quality_standards:
            current.quality_standards[category] = []

        if standard not in current.quality_standards[category]:
            current.quality_standards[category].append(standard)
            self.update_base_agent({"quality_standards": current.quality_standards})
            return True

        return False

    def add_escalation_trigger(self, trigger: str) -> bool:
        """Add a new escalation trigger."""
        current = self.read_base_agent()
        if not current:
            return False

        if trigger not in current.escalation_triggers:
            current.escalation_triggers.append(trigger)
            self.update_base_agent({"escalation_triggers": current.escalation_triggers})
            return True

        return False

    def validate_structure(self) -> Dict[str, bool]:
        """
        Validate that base_agent.md has all required sections.

        Returns:
            Dictionary of section names to validation status
        """
        current = self.read_base_agent()
        if not current:
            return {section.value: False for section in BaseAgentSection}

        validation = {}

        # Check each section
        for section in BaseAgentSection:
            if section == BaseAgentSection.FRAMEWORK_CONTEXT:
                validation[section.value] = bool(current.framework_context)
            elif section == BaseAgentSection.BEHAVIORAL_RULES:
                validation[section.value] = bool(current.behavioral_rules)
            elif section == BaseAgentSection.TEMPORAL_CONTEXT:
                validation[section.value] = bool(current.temporal_context)
            elif section == BaseAgentSection.QUALITY_STANDARDS:
                validation[section.value] = bool(current.quality_standards)
            elif section == BaseAgentSection.TOOL_USAGE:
                validation[section.value] = bool(current.tool_usage)
            elif section == BaseAgentSection.COLLABORATION:
                validation[section.value] = bool(current.collaboration_protocols)
            elif section == BaseAgentSection.PERFORMANCE:
                validation[section.value] = bool(current.performance_optimization)
            elif section == BaseAgentSection.ESCALATION:
                validation[section.value] = bool(current.escalation_triggers)
            elif section == BaseAgentSection.OUTPUT_FORMATS:
                validation[section.value] = bool(current.output_formats)
            elif section == BaseAgentSection.FRAMEWORK_INTEGRATION:
                validation[section.value] = bool(current.framework_integration)
            elif section == BaseAgentSection.CONSTRAINTS:
                validation[section.value] = bool(current.universal_constraints)
            elif section == BaseAgentSection.SUCCESS_CRITERIA:
                validation[section.value] = bool(current.success_criteria)

        return validation

    # Private helper methods

    def _parse_base_agent(self, content: str) -> BaseAgentStructure:
        """Parse base_agent.md content into structured format."""
        structure = BaseAgentStructure()

        # For now, store raw content in sections
        # Full parsing implementation would extract structured data
        lines = content.split("\n")
        current_section = None
        section_content = []

        for line in lines:
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    structure.raw_sections[current_section] = "\n".join(section_content)

                # Start new section
                current_section = line[3:].strip()
                section_content = []
            elif current_section:
                section_content.append(line)

        # Save last section
        if current_section:
            structure.raw_sections[current_section] = "\n".join(section_content)

        # Parse specific sections
        if BaseAgentSection.ESCALATION.value in structure.raw_sections:
            structure.escalation_triggers = self._parse_list_content(
                structure.raw_sections[BaseAgentSection.ESCALATION.value]
            )

        return structure

    def _structure_to_markdown(self, structure: BaseAgentStructure) -> str:
        """Convert BaseAgentStructure back to markdown format."""
        lines = []

        # Header
        lines.append(f"# {structure.title}")
        lines.append("")
        lines.append("<!-- ")
        lines.append(structure.description)
        lines.append(
            "They contain common rules, behaviors, and constraints that apply to ALL agents."
        )
        lines.append("-->")
        lines.append("")

        # Write sections from raw content (preserves formatting)
        for section in BaseAgentSection:
            if section.value in structure.raw_sections:
                lines.append(f"## {section.value}")
                lines.append(structure.raw_sections[section.value])
                lines.append("")

        return "\n".join(lines)

    def _parse_list_content(self, content: str) -> List[str]:
        """Parse list items from markdown content."""
        items = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ")):
                items.append(line[2:].strip())
            elif line.startswith("**") and line.endswith("**"):
                # Skip bold headers
                continue
        return items

    def _create_backup(self) -> Path:
        """Create a timestamped backup of base_agent.md."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.base_agent_path.parent / f"base_agent_{timestamp}.backup"

        if self.base_agent_path.exists():
            content = self.base_agent_path.read_text(encoding="utf-8")
            backup_path.write_text(content, encoding="utf-8")
            logger.info(f"Created backup at {backup_path}")

        return backup_path


# Convenience functions
def get_base_agent_manager() -> BaseAgentManager:
    """Get a configured BaseAgentManager instance."""
    return BaseAgentManager()


def update_base_agent_section(section: BaseAgentSection, content: str) -> bool:
    """
    Quick function to update a base agent section.

    Args:
        section: Section to update
        content: New content for the section

    Returns:
        True if successful, False otherwise
    """
    manager = get_base_agent_manager()
    result = manager.update_section(section, content)
    return result is not None


def validate_base_agent() -> Dict[str, bool]:
    """Quick function to validate base agent structure."""
    manager = get_base_agent_manager()
    return manager.validate_structure()
