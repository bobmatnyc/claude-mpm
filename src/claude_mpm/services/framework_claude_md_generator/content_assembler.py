"""
Content assembly for framework CLAUDE.md templates.

Assembles sections and applies template variable substitution.
"""

import hashlib
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.agents.management import AgentCapabilitiesGenerator
from claude_mpm.services.agents.registry import DeployedAgentDiscovery

logger = get_logger(__name__)


class ContentAssembler:
    """Assembles framework CLAUDE.md content from sections."""

    def __init__(self):
        """Initialize content assembler."""
        self.template_variables = {}
        self.agent_discovery = DeployedAgentDiscovery()
        self.capabilities_generator = AgentCapabilitiesGenerator()
        logger.debug(
            "Initialized ContentAssembler with dynamic agent capabilities support"
        )

    def generate_content_hash(self) -> str:
        """
        Generate a content hash for integrity verification.

        Returns:
            str: 16-character hash of content
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        hash_obj = hashlib.sha256(timestamp.encode())
        return hash_obj.hexdigest()[:16]

    def assemble_content(
        self, sections: OrderedDict, template_variables: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Assemble complete content from sections.

        Args:
            sections: OrderedDict of section_name -> (generator_func, section_data)
            template_variables: Variables to substitute in the template

        Returns:
            str: Complete assembled content
        """
        # Store template variables
        if template_variables:
            self.template_variables = template_variables

        # Generate all sections
        content_parts = []
        for _section_name, (generator_func, section_data) in sections.items():
            section_content = generator_func(section_data)
            content_parts.append(section_content)

        # Join all sections
        full_content = "\n".join(content_parts)

        # Apply template variable substitution
        return self.apply_template_variables(full_content)

    def apply_template_variables(self, content: str) -> str:
        """
        Apply template variable substitution to content.

        WHY: Enhanced to support dynamic agent capabilities generation.
        - Generates fresh agent capabilities on each call
        - Provides graceful fallback if generation fails
        - Ensures INSTRUCTIONS.md always reflects current deployed agents

        Args:
            content: Content with template variables

        Returns:
            str: Content with variables substituted
        """
        # Check if we need to generate dynamic capabilities
        if "{{capabilities-list}}" in content:
            try:
                # Discover deployed agents
                deployed_agents = self.agent_discovery.discover_deployed_agents()
                # Generate capabilities content
                capabilities_content = (
                    self.capabilities_generator.generate_capabilities_section(
                        deployed_agents
                    )
                )
                # Add to template variables
                self.template_variables["capabilities-list"] = capabilities_content
                logger.info(
                    f"Generated dynamic capabilities for {len(deployed_agents)} agents"
                )
            except Exception as e:
                logger.error(f"Failed to generate dynamic capabilities: {e}")
                # Fallback is handled by the generator's internal fallback mechanism

        # Apply all template variables
        for var_name, var_value in self.template_variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, var_value)

        return content

    def merge_sections(
        self, base_sections: OrderedDict, custom_sections: Dict[str, tuple]
    ) -> OrderedDict:
        """
        Merge custom sections with base sections.

        Args:
            base_sections: Base section definitions
            custom_sections: Custom sections to merge

        Returns:
            OrderedDict: Merged sections
        """
        merged = OrderedDict(base_sections)

        for section_name, section_def in custom_sections.items():
            merged[section_name] = section_def

        return merged

    def insert_section_after(
        self,
        sections: OrderedDict,
        new_section_name: str,
        new_section_def: tuple,
        after_section: str,
    ) -> OrderedDict:
        """
        Insert a new section after a specified section.

        Args:
            sections: Current sections
            new_section_name: Name of new section
            new_section_def: Definition tuple for new section
            after_section: Section to insert after

        Returns:
            OrderedDict: Updated sections
        """
        if after_section not in sections:
            # If target section doesn't exist, just append
            sections[new_section_name] = new_section_def
            return sections

        new_sections = OrderedDict()
        for key, value in sections.items():
            new_sections[key] = value
            if key == after_section:
                new_sections[new_section_name] = new_section_def

        return new_sections

    def create_metadata_dict(
        self, version: str, framework_version: str, content_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create metadata dictionary for header generation.

        Args:
            version: CLAUDE_MD_VERSION string
            framework_version: Framework version
            content_hash: Optional content hash

        Returns:
            Dict: Metadata for header
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "version": version,
            "framework_version": framework_version,
            "deployment_date": timestamp,
            "last_updated": timestamp,
            "content_hash": content_hash or self.generate_content_hash(),
        }
