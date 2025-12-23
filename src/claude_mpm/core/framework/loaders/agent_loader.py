"""Loader for agent discovery and management."""

from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from claude_mpm.core.logging_utils import get_logger


class AgentLoader:
    """Handles agent discovery and loading from various sources."""

    def __init__(self, framework_path: Optional[Path] = None):
        """Initialize the agent loader.

        Args:
            framework_path: Path to framework installation
        """
        self.logger = get_logger("agent_loader")
        self.framework_path = framework_path

    def get_deployed_agents(self) -> Set[str]:
        """
        Get a set of deployed agent names from .claude/agents/ directories.

        Returns:
            Set of agent names (file stems) that are deployed
        """
        self.logger.debug("Scanning for deployed agents")
        deployed = set()

        # Check multiple locations for deployed agents
        agents_dirs = [
            Path.cwd() / ".claude" / "agents",  # Project-specific agents
            Path.home() / ".claude" / "agents",  # User's system agents
        ]

        for agents_dir in agents_dirs:
            if agents_dir.exists():
                for agent_file in agents_dir.glob("*.md"):
                    if not agent_file.name.startswith("."):
                        # Use stem to get agent name without extension
                        deployed.add(agent_file.stem)
                        self.logger.debug(
                            f"Found deployed agent: {agent_file.stem} in {agents_dir}"
                        )

        self.logger.debug(f"Total deployed agents found: {len(deployed)}")
        return deployed

    def load_single_agent(
        self, agent_file: Path
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Load a single agent file.

        Args:
            agent_file: Path to the agent file

        Returns:
            Tuple of (agent_name, agent_content) or (None, None) on failure
        """
        try:
            agent_name = agent_file.stem
            # Skip README files
            if agent_name.upper() == "README":
                return None, None
            content = agent_file.read_text()
            self.logger.debug(f"Loaded agent: {agent_name}")
            return agent_name, content
        except Exception as e:
            self.logger.error(f"Failed to load agent {agent_file}: {e}")
            return None, None

    def load_agents_directory(
        self,
        agents_dir: Optional[Path],
        templates_dir: Optional[Path] = None,
        main_dir: Optional[Path] = None,
    ) -> Dict[str, str]:
        """
        Load agent definitions from the appropriate directory.

        Args:
            agents_dir: Primary agents directory to load from
            templates_dir: Templates directory path
            main_dir: Main agents directory path

        Returns:
            Dictionary mapping agent names to their content
        """
        agents = {}

        if not agents_dir or not agents_dir.exists():
            return agents

        # Load all agent files
        for agent_file in agents_dir.glob("*.md"):
            agent_name, agent_content = self.load_single_agent(agent_file)
            if agent_name and agent_content:
                agents[agent_name] = agent_content

        # If we used templates dir, also check main dir for base_agent.md
        if (
            agents_dir == templates_dir
            and main_dir
            and main_dir.exists()
            and "base_agent" not in agents
        ):
            base_agent_file = main_dir / "base_agent.md"
            if base_agent_file.exists():
                agent_name, agent_content = self.load_single_agent(base_agent_file)
                if agent_name and agent_content:
                    agents[agent_name] = agent_content

        return agents

    def discover_local_json_templates(self) -> Dict[str, Dict[str, Any]]:
        """Discover local JSON agent templates.

        NOTE: This method is kept for backward compatibility but is deprecated.
        The new architecture uses SOURCE (~/.claude-mpm/cache/agents/)
        and DEPLOYMENT (.claude/agents/) locations only.

        Returns:
            Dictionary mapping agent IDs to agent metadata
        """
        import json

        local_agents = {}

        # Check for local JSON templates in priority order
        # NOTE: These directories are deprecated in the simplified architecture
        template_dirs = [
            Path.cwd() / ".claude-mpm" / "agents",  # Deprecated: Project local agents
            Path.home() / ".claude-mpm" / "agents",  # Deprecated: User local agents
        ]

        for priority, template_dir in enumerate(template_dirs):
            if not template_dir.exists():
                continue

            for json_file in template_dir.glob("*.json"):
                try:
                    with json_file.open() as f:
                        template_data = json.load(f)

                    # Extract agent metadata
                    agent_id = template_data.get("agent_id", json_file.stem)

                    # Skip if already found at higher priority
                    if agent_id in local_agents:
                        continue

                    # Extract metadata
                    metadata = template_data.get("metadata", {})

                    # Build agent data in expected format
                    agent_data = {
                        "id": agent_id,
                        "display_name": metadata.get(
                            "name", agent_id.replace("_", " ").title()
                        ),
                        "description": metadata.get(
                            "description", f"Local {agent_id} agent"
                        ),
                        "tools": self._extract_tools_from_template(template_data),
                        "is_local": True,
                        "tier": "project" if priority == 0 else "user",
                        "author": template_data.get("author", "local"),
                        "version": template_data.get("agent_version", "1.0.0"),
                    }

                    # Add routing data if present
                    if "routing" in template_data:
                        agent_data["routing"] = template_data["routing"]

                    # Add memory routing if present
                    if "memory_routing" in template_data:
                        agent_data["memory_routing"] = template_data["memory_routing"]

                    local_agents[agent_id] = agent_data
                    self.logger.debug(
                        f"Discovered local JSON agent: {agent_id} from {template_dir}"
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse local JSON template {json_file}: {e}"
                    )

        return local_agents

    def _extract_tools_from_template(self, template_data: Dict[str, Any]) -> str:
        """Extract tools string from template data.

        Args:
            template_data: JSON template data

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
            if "," in tools:
                return tools
            return tools
        return "Standard Tools"
