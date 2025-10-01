"""JSON template processor for agent configurations."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger

# Import resource handling for packaged installations
try:
    from importlib.resources import files
except ImportError:
    try:
        from importlib_resources import files
    except ImportError:
        files = None


class TemplateProcessor:
    """Processes JSON template files for agent configurations."""

    def __init__(self, framework_path: Optional[Path] = None):
        """Initialize the template processor.

        Args:
            framework_path: Path to framework installation
        """
        self.logger = get_logger("template_processor")
        self.framework_path = framework_path

    def load_template(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load JSON template for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Template data or None if not found
        """
        try:
            # Check if we have a framework path
            if not self.framework_path or self.framework_path == Path("__PACKAGED__"):
                return self._load_packaged_template(agent_name)

            # For development mode, load from filesystem
            return self._load_filesystem_template(agent_name)

        except Exception as e:
            self.logger.debug(f"Could not load template for {agent_name}: {e}")
            return None

    def _load_packaged_template(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load template from packaged installation.

        Args:
            agent_name: Name of the agent

        Returns:
            Template data or None if not found
        """
        if not files:
            return None

        try:
            templates_package = files("claude_mpm.agents.templates")
            template_file = templates_package / f"{agent_name}.json"

            if template_file.is_file():
                template_content = template_file.read_text()
                return json.loads(template_content)
        except Exception as e:
            self.logger.debug(f"Could not load packaged template for {agent_name}: {e}")

        return None

    def _load_filesystem_template(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load template from filesystem.

        Args:
            agent_name: Name of the agent

        Returns:
            Template data or None if not found
        """
        templates_dir = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "templates"
        )

        # Try exact match first
        template_file = templates_dir / f"{agent_name}.json"
        if template_file.exists():
            with template_file.open() as f:
                return json.load(f)

        # Try alternative naming variations
        alternative_names = self._get_alternative_names(agent_name)
        for alt_name in alternative_names:
            alt_file = templates_dir / f"{alt_name}.json"
            if alt_file.exists():
                with alt_file.open() as f:
                    return json.load(f)

        return None

    def _get_alternative_names(self, agent_name: str) -> List[str]:
        """Get alternative naming variations for an agent.

        Args:
            agent_name: Original agent name

        Returns:
            List of alternative names to try
        """
        # Remove duplicates by using a set
        return list(
            {
                agent_name.replace("-", "_"),  # api-qa -> api_qa
                agent_name.replace("_", "-"),  # api_qa -> api-qa
                agent_name.replace("-", ""),  # api-qa -> apiqa
                agent_name.replace("_", ""),  # api_qa -> apiqa
                agent_name.replace("-agent", ""),  # research-agent -> research
                agent_name.replace("_agent", ""),  # research_agent -> research
                agent_name + "_agent",  # research -> research_agent
                agent_name + "-agent",  # research -> research-agent
            }
        )

    def extract_routing(
        self, template_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract routing information from template.

        Args:
            template_data: Template data

        Returns:
            Routing information or None
        """
        return template_data.get("routing")

    def extract_memory_routing(
        self, template_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract memory routing information from template.

        Args:
            template_data: Template data

        Returns:
            Memory routing information or None
        """
        return template_data.get("memory_routing")

    def extract_tools(self, template_data: Dict[str, Any]) -> str:
        """Extract tools string from template data.

        Args:
            template_data: Template data

        Returns:
            Tools string for display
        """
        capabilities = template_data.get("capabilities", {})
        tools = capabilities.get("tools", "*")

        if tools == "*":
            return "All Tools"
        if isinstance(tools, list):
            return ", ".join(tools) if tools else "Standard Tools"
        if isinstance(tools, str):
            return tools
        return "Standard Tools"

    def extract_metadata(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract agent metadata from template.

        Args:
            template_data: Template data

        Returns:
            Dictionary with extracted metadata
        """
        metadata = template_data.get("metadata", {})
        agent_id = template_data.get("agent_id", "unknown")

        return {
            "id": agent_id,
            "display_name": metadata.get("name", agent_id.replace("_", " ").title()),
            "description": metadata.get("description", f"Agent {agent_id}"),
            "authority": metadata.get("authority"),
            "primary_function": metadata.get("primary_function"),
            "handoff_to": metadata.get("handoff_to"),
            "model": template_data.get("model", {}).get("model"),
            "tools": self.extract_tools(template_data),
            "routing": self.extract_routing(template_data),
            "memory_routing": self.extract_memory_routing(template_data),
            "author": template_data.get("author", "unknown"),
            "version": template_data.get("agent_version", "1.0.0"),
        }

    def process_local_templates(self) -> Dict[str, Dict[str, Any]]:
        """Process all local JSON templates.

        Returns:
            Dictionary mapping agent IDs to processed metadata
        """
        local_agents = {}

        # Check for local JSON templates in priority order
        template_dirs = [
            Path.cwd() / ".claude-mpm" / "agents",  # Project local agents
            Path.home() / ".claude-mpm" / "agents",  # User local agents
        ]

        for priority, template_dir in enumerate(template_dirs):
            if not template_dir.exists():
                continue

            for json_file in template_dir.glob("*.json"):
                try:
                    with json_file.open() as f:
                        template_data = json.load(f)

                    agent_metadata = self.extract_metadata(template_data)
                    agent_id = agent_metadata["id"]

                    # Skip if already found at higher priority
                    if agent_id in local_agents:
                        continue

                    # Add local-specific fields
                    agent_metadata["is_local"] = True
                    agent_metadata["tier"] = "project" if priority == 0 else "user"
                    agent_metadata["source_file"] = str(json_file)

                    local_agents[agent_id] = agent_metadata
                    self.logger.debug(
                        f"Processed local template: {agent_id} from {template_dir}"
                    )

                except Exception as e:
                    self.logger.warning(f"Failed to process template {json_file}: {e}")

        return local_agents
