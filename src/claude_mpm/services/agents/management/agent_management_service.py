from pathlib import Path

#!/usr/bin/env python3
"""
Agent Management Service
========================

Comprehensive service for managing agent definitions with CRUD operations,
section extraction/updates, and version management.

Uses python-frontmatter and mistune for markdown parsing as recommended.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import frontmatter
import mistune
import yaml

from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.models.agent_definition import (
    AgentDefinition,
    AgentMetadata,
    AgentPermissions,
    AgentSection,
    AgentType,
    AgentWorkflow,
)
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

from ..deployment.agent_versioning import AgentVersionManager

logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent definitions with CRUD operations and versioning."""

    def __init__(
        self, framework_dir: Optional[Path] = None, project_dir: Optional[Path] = None
    ):
        """
        Initialize AgentManager.

        Args:
            framework_dir: Path to agents templates directory
            project_dir: Path to project-specific agents directory
        """
        # Use get_path_manager() for consistent path discovery
        if framework_dir is None:
            try:
                # Use agents templates directory
                self.framework_dir = (
                    Path(__file__).parent.parent / "agents" / "templates"
                )
            except Exception:
                # Fallback to agents directory
                self.framework_dir = get_path_manager().get_agents_dir()
        else:
            self.framework_dir = framework_dir

        if project_dir is None:
            project_root = get_path_manager().get_project_root()
            # Use direct agents directory without subdirectory to match deployment expectations
            self.project_dir = project_root / get_path_manager().CONFIG_DIR / "agents"
        else:
            self.project_dir = project_dir
        self.version_manager = AgentVersionManager()
        self.cache = SharedPromptCache.get_instance()
        self._markdown = mistune.create_markdown()

    def create_agent(
        self, name: str, definition: AgentDefinition, location: str = "project"
    ) -> Path:
        """
        Create a new agent definition file.

        Args:
            name: Agent name (e.g., "performance-agent")
            definition: Agent definition object
            location: "project" or "framework"

        Returns:
            Path to created file
        """
        # Determine target directory
        target_dir = self.project_dir if location == "project" else self.framework_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        content = self._definition_to_markdown(definition)

        # Write file
        file_path = target_dir / f"{name}.md"
        file_path.write_text(content, encoding="utf-8")

        # Clear cache
        self._clear_agent_cache(name)

        logger.info(f"Created agent '{name}' at {file_path}")
        return file_path

    def read_agent(self, name: str) -> Optional[AgentDefinition]:
        """
        Read an agent definition.

        Args:
            name: Agent name (without .md extension)

        Returns:
            AgentDefinition or None if not found
        """
        # Try to find the agent file
        agent_path = self._find_agent_file(name)
        if not agent_path:
            logger.warning(f"Agent '{name}' not found")
            return None

        try:
            # Read and parse the file
            content = agent_path.read_text(encoding="utf-8")
            return self._parse_agent_markdown(content, name, str(agent_path))
        except Exception as e:
            logger.error(f"Error reading agent '{name}': {e}")
            return None

    def update_agent(
        self, name: str, updates: Dict[str, Any], increment_version: bool = True
    ) -> Optional[AgentDefinition]:
        """
        Update an agent definition.

        Args:
            name: Agent name
            updates: Dictionary of updates to apply
            increment_version: Whether to increment serial version

        Returns:
            Updated AgentDefinition or None if failed
        """
        # Read current definition
        agent_def = self.read_agent(name)
        if not agent_def:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(agent_def, key):
                setattr(agent_def, key, value)
            elif key in ["type", "model_preference", "tags", "specializations"]:
                setattr(agent_def.metadata, key, value)

        # Increment version if requested
        if increment_version:
            agent_def.metadata.increment_serial_version()
            agent_def.metadata.last_updated = datetime.now()

        # Write back
        agent_path = self._find_agent_file(name)
        if agent_path:
            content = self._definition_to_markdown(agent_def)
            agent_path.write_text(content, encoding="utf-8")

            # Clear cache
            self._clear_agent_cache(name)

            logger.info(
                f"Updated agent '{name}' to version {agent_def.metadata.version}"
            )
            return agent_def

        return None

    def update_section(
        self,
        name: str,
        section: AgentSection,
        content: str,
        increment_version: bool = True,
    ) -> Optional[AgentDefinition]:
        """
        Update a specific section of an agent.

        Args:
            name: Agent name
            section: Section to update
            content: New section content
            increment_version: Whether to increment version

        Returns:
            Updated AgentDefinition or None
        """
        agent_def = self.read_agent(name)
        if not agent_def:
            return None

        # Map section to attribute
        section_map = {
            AgentSection.PRIMARY_ROLE: "primary_role",
            AgentSection.CAPABILITIES: "capabilities",
            AgentSection.TOOLS: "tools_commands",
            AgentSection.ESCALATION: "escalation_triggers",
            AgentSection.KPI: "kpis",
            AgentSection.DEPENDENCIES: "dependencies",
        }

        if section in section_map:
            attr_name = section_map[section]
            if section in [
                AgentSection.CAPABILITIES,
                AgentSection.ESCALATION,
                AgentSection.KPI,
                AgentSection.DEPENDENCIES,
            ]:
                # Parse list content
                setattr(agent_def, attr_name, self._parse_list_content(content))
            else:
                setattr(agent_def, attr_name, content.strip())

        # Special handling for complex sections
        elif section == AgentSection.WHEN_TO_USE:
            agent_def.when_to_use = self._parse_when_to_use(content)
        elif section == AgentSection.AUTHORITY:
            agent_def.authority = self._parse_authority(content)
        elif section == AgentSection.WORKFLOWS:
            agent_def.workflows = self._parse_workflows(content)

        # Update raw section
        agent_def.raw_sections[section.value] = content

        # Increment version
        if increment_version:
            agent_def.metadata.increment_serial_version()
            agent_def.metadata.last_updated = datetime.now()

        # Write back
        return self.update_agent(name, {}, increment_version=False)

    def delete_agent(self, name: str) -> bool:
        """
        Delete an agent definition.

        Args:
            name: Agent name

        Returns:
            True if deleted, False otherwise
        """
        agent_path = self._find_agent_file(name)
        if not agent_path:
            return False

        try:
            agent_path.unlink()
            self._clear_agent_cache(name)
            logger.info(f"Deleted agent '{name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting agent '{name}': {e}")
            return False

    def list_agents(self, location: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all available agents.

        Args:
            location: Filter by location ("project", "framework", or None for all)

        Returns:
            Dictionary of agent info
        """
        agents = {}

        # Check framework agents
        if location in [None, "framework"]:
            for agent_file in self.framework_dir.glob("*.md"):
                if agent_file.name != "base_agent.md":
                    agent_name = agent_file.stem
                    agent_def = self.read_agent(agent_name)
                    if agent_def:
                        agents[agent_name] = {
                            "location": "framework",
                            "path": str(agent_file),
                            "version": agent_def.metadata.version,
                            "type": agent_def.metadata.type.value,
                            "specializations": agent_def.metadata.specializations,
                        }

        # Check project agents
        if location in [None, "project"] and self.project_dir.exists():
            for agent_file in self.project_dir.glob("*.md"):
                agent_name = agent_file.stem
                agent_def = self.read_agent(agent_name)
                if agent_def:
                    agents[agent_name] = {
                        "location": "project",
                        "path": str(agent_file),
                        "version": agent_def.metadata.version,
                        "type": agent_def.metadata.type.value,
                        "specializations": agent_def.metadata.specializations,
                    }

        return agents

    def get_agent_api(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent data in API-friendly format.

        Args:
            name: Agent name

        Returns:
            Agent data dictionary or None
        """
        agent_def = self.read_agent(name)
        if not agent_def:
            return None

        return agent_def.to_dict()

    # Private helper methods

    def _find_agent_file(self, name: str) -> Optional[Path]:
        """Find agent file in project or framework directories."""
        # Check project first (higher precedence)
        if self.project_dir.exists():
            project_path = self.project_dir / f"{name}.md"
            if project_path.exists():
                return project_path

        # Check framework
        framework_path = self.framework_dir / f"{name}.md"
        if framework_path.exists():
            return framework_path

        return None

    def _parse_agent_markdown(
        self, content: str, name: str, file_path: str
    ) -> AgentDefinition:
        """Parse markdown content into AgentDefinition."""
        # Parse frontmatter
        post = frontmatter.loads(content)

        # Extract metadata
        metadata = AgentMetadata(
            type=AgentType(post.metadata.get("type", "core")),
            model_preference=post.metadata.get("model_preference", "claude-3-sonnet"),
            version=post.metadata.get("version", "1.0.0"),
            last_updated=post.metadata.get("last_updated"),
            author=post.metadata.get("author"),
            tags=post.metadata.get("tags", []),
            specializations=post.metadata.get("specializations", []),
        )

        # Extract version from content if not in frontmatter
        if not post.metadata.get("version"):
            version = self.version_manager.extract_version_from_markdown(content)
            if version:
                metadata.version = version

        # Parse sections
        sections = self._extract_sections(post.content)

        # Extract title
        title_match = re.search(r"^#\s+(.+)$", post.content, re.MULTILINE)
        title = title_match.group(1) if title_match else name.replace("-", " ").title()

        # Build definition
        return AgentDefinition(
            name=name,
            title=title,
            file_path=file_path,
            metadata=metadata,
            primary_role=sections.get("Primary Role", ""),
            when_to_use=self._parse_when_to_use(
                sections.get("When to Use This Agent", "")
            ),
            capabilities=self._parse_list_content(
                sections.get("Core Capabilities", "")
            ),
            authority=self._parse_authority(
                sections.get("Authority & Permissions", "")
            ),
            workflows=self._parse_workflows(
                sections.get("Agent-Specific Workflows", "")
            ),
            escalation_triggers=self._parse_list_content(
                sections.get("Unique Escalation Triggers", "")
            ),
            kpis=self._parse_list_content(
                sections.get("Key Performance Indicators", "")
            ),
            dependencies=self._parse_list_content(
                sections.get("Critical Dependencies", "")
            ),
            tools_commands=sections.get("Specialized Tools/Commands", ""),
            raw_content=content,
            raw_sections=sections,
        )

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract sections from markdown content."""
        sections = {}
        current_section = None
        current_content = []

        # Split into lines
        lines = content.split("\n")

        for line in lines:
            # Check if this is a section header
            header_match = re.match(r"^##\s+(?:🎯|🔧|🔑|📋|🚨|📊|🔄|🛠️)?\s*(.+)$", line)
            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = header_match.group(1).strip()
                current_content = []
            # Add to current section
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _parse_list_content(self, content: str) -> List[str]:
        """Parse bullet point or numbered list content."""
        items = []
        for line in content.split("\n"):
            # Match bullet points or numbered items
            match = re.match(r"^[-*•]\s+(.+)$|^\d+\.\s+(.+)$", line.strip())
            if match:
                item = match.group(1) or match.group(2)
                items.append(item.strip())
        return items

    def _parse_when_to_use(self, content: str) -> Dict[str, List[str]]:
        """Parse When to Use section."""
        result = {"select": [], "do_not_select": []}
        current_mode = None

        for line in content.split("\n"):
            if (
                "Select this agent when:" in line
                or "**Select this agent when:**" in line
            ):
                current_mode = "select"
            elif "Do NOT select for:" in line or "**Do NOT select for:**" in line:
                current_mode = "do_not_select"
            elif current_mode and line.strip().startswith("-"):
                item = line.strip()[1:].strip()
                result[current_mode].append(item)

        return result

    def _parse_authority(self, content: str) -> AgentPermissions:
        """Parse Authority & Permissions section."""
        permissions = AgentPermissions()
        current_section = None

        for line in content.split("\n"):
            if "Exclusive Write Access" in line:
                current_section = "write"
            elif "Forbidden Operations" in line:
                current_section = "forbidden"
            elif "Read Access" in line:
                current_section = "read"
            elif current_section and line.strip().startswith("-"):
                item = line.strip()[1:].strip()
                # Remove inline comments
                item = re.sub(r"\s*#.*$", "", item).strip()

                if current_section == "write":
                    permissions.exclusive_write_access.append(item)
                elif current_section == "forbidden":
                    permissions.forbidden_operations.append(item)
                elif current_section == "read":
                    permissions.read_access.append(item)

        return permissions

    def _parse_workflows(self, content: str) -> List[AgentWorkflow]:
        """Parse workflows from YAML blocks."""
        workflows = []

        # Find all YAML blocks
        yaml_blocks = re.findall(r"```yaml\n(.*?)\n```", content, re.DOTALL)

        for block in yaml_blocks:
            try:
                data = yaml.safe_load(block)
                if isinstance(data, dict) and all(
                    k in data for k in ["trigger", "process", "output"]
                ):
                    # Extract workflow name from preceding heading if available
                    name_match = re.search(
                        r"###\s+(.+)\n```yaml\n" + re.escape(block), content
                    )
                    name = name_match.group(1) if name_match else "Unnamed Workflow"

                    workflow = AgentWorkflow(
                        name=name,
                        trigger=data["trigger"],
                        process=(
                            data["process"]
                            if isinstance(data["process"], list)
                            else [data["process"]]
                        ),
                        output=data["output"],
                        raw_yaml=block,
                    )
                    workflows.append(workflow)
            except yaml.YAMLError:
                logger.warning("Failed to parse YAML workflow block")

        return workflows

    def _definition_to_markdown(self, definition: AgentDefinition) -> str:
        """Convert AgentDefinition back to markdown."""
        # Start with frontmatter
        frontmatter_data = {
            "type": definition.metadata.type.value,
            "model_preference": definition.metadata.model_preference,
            "version": definition.metadata.version,
            "last_updated": definition.metadata.last_updated,
            "author": definition.metadata.author,
            "tags": definition.metadata.tags,
            "specializations": definition.metadata.specializations,
        }

        # Remove None values
        frontmatter_data = {k: v for k, v in frontmatter_data.items() if v is not None}

        # Build content
        content = []
        content.append(f"# {definition.title}\n")

        # Primary Role
        content.append("## 🎯 Primary Role")
        content.append(definition.primary_role)
        content.append("")

        # When to Use
        content.append("## 🎯 When to Use This Agent")
        content.append("")
        content.append("**Select this agent when:**")
        for item in definition.when_to_use.get("select", []):
            content.append(f"- {item}")
        content.append("")
        content.append("**Do NOT select for:**")
        for item in definition.when_to_use.get("do_not_select", []):
            content.append(f"- {item}")
        content.append("")

        # Capabilities
        content.append("## 🔧 Core Capabilities")
        for capability in definition.capabilities:
            content.append(f"- {capability}")
        content.append("")

        # Authority
        content.append("## 🔑 Authority & Permissions")
        content.append("")
        content.append("### ✅ Exclusive Write Access")
        for item in definition.authority.exclusive_write_access:
            content.append(f"- {item}")
        content.append("")
        content.append("### ❌ Forbidden Operations")
        for item in definition.authority.forbidden_operations:
            content.append(f"- {item}")
        content.append("")

        # Workflows
        if definition.workflows:
            content.append("## 📋 Agent-Specific Workflows")
            content.append("")
            for workflow in definition.workflows:
                content.append(f"### {workflow.name}")
                content.append("```yaml")
                yaml_content = {
                    "trigger": workflow.trigger,
                    "process": workflow.process,
                    "output": workflow.output,
                }
                content.append(
                    yaml.dump(yaml_content, default_flow_style=False).strip()
                )
                content.append("```")
                content.append("")

        # Escalation
        if definition.escalation_triggers:
            content.append("## 🚨 Unique Escalation Triggers")
            for trigger in definition.escalation_triggers:
                content.append(f"- {trigger}")
            content.append("")

        # KPIs
        if definition.kpis:
            content.append("## 📊 Key Performance Indicators")
            for i, kpi in enumerate(definition.kpis, 1):
                content.append(f"{i}. {kpi}")
            content.append("")

        # Dependencies
        if definition.dependencies:
            content.append("## 🔄 Critical Dependencies")
            for dep in definition.dependencies:
                content.append(f"- {dep}")
            content.append("")

        # Tools
        if definition.tools_commands:
            content.append("## 🛠️ Specialized Tools/Commands")
            content.append(definition.tools_commands)
            content.append("")

        # Footer
        content.append("---")
        content.append(f"**Agent Type**: {definition.metadata.type.value}")
        content.append(f"**Model Preference**: {definition.metadata.model_preference}")
        content.append(f"**Version**: {definition.metadata.version}")
        if definition.metadata.last_updated:
            content.append(
                f"**Last Updated**: {definition.metadata.last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Combine with frontmatter
        post = frontmatter.Post("\n".join(content), **frontmatter_data)
        return frontmatter.dumps(post)

    def _clear_agent_cache(self, name: str):
        """Clear cache for a specific agent."""
        try:
            cache_key = f"agent_prompt:{name}:md"
            self.cache.invalidate(cache_key)
        except Exception as e:
            logger.warning(f"Failed to clear cache for agent '{name}': {e}")
