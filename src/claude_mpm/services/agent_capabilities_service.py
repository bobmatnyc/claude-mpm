from pathlib import Path

"""Agent capabilities service for discovering and generating agent capability descriptions.

This service handles:
1. Agent discovery from multiple directories (system, user, project)
2. Agent categorization based on content and naming
3. Generation of capability descriptions for Claude
4. Fallback capabilities when no agents are found

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""


from claude_mpm.core.base_service import BaseService
from claude_mpm.services.core.interfaces import AgentCapabilitiesInterface


class AgentCapabilitiesService(BaseService, AgentCapabilitiesInterface):
    """Service for discovering and generating agent capability descriptions."""

    def __init__(self):
        """Initialize the agent capabilities service."""
        super().__init__(name="agent_capabilities_service")

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def generate_agent_capabilities(self, agent_type: str = "general") -> str:
        """Generate formatted agent capabilities for Claude.

        Args:
            agent_type: Type of agent to generate capabilities for

        Returns:
            Formatted capabilities string for Claude consumption
        """
        # Delegate to the existing implementation
        return self.generate_deployed_agent_capabilities()

    def generate_deployed_agent_capabilities(self) -> str:
        """Generate agent capabilities from deployed agents following Claude Code's hierarchy.

        Follows the agent precedence order:
        1. Project agents (.claude/agents/) - highest priority
        2. User agents (~/.config/claude/agents/) - middle priority
        3. System agents (claude-desktop installation) - lowest priority

        Project agents override user/system agents with the same ID.

        Returns:
            str: Formatted agent capabilities description
        """
        try:
            # Track discovered agents by ID to handle overrides
            discovered_agents = {}

            # 1. First read system agents (lowest priority)
            system_agents_dirs = [
                Path.home() / ".claude" / "agents",  # Claude MPM system agents
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "agents",  # macOS
                Path.home() / ".config" / "claude" / "agents",  # Linux
                Path.home() / "AppData" / "Roaming" / "Claude" / "agents",  # Windows
            ]

            for system_dir in system_agents_dirs:
                if system_dir.exists():
                    self._discover_agents_from_dir(
                        system_dir, discovered_agents, "system"
                    )
                    break

            # 2. Then read user agents (middle priority, overrides system)
            user_agents_dir = Path.home() / ".config" / "claude" / "agents"
            if user_agents_dir.exists():
                self._discover_agents_from_dir(
                    user_agents_dir, discovered_agents, "user"
                )

            # 3. Finally read project agents (highest priority, overrides all)
            project_agents_dir = Path.cwd() / ".claude" / "agents"
            if project_agents_dir.exists():
                self._discover_agents_from_dir(
                    project_agents_dir, discovered_agents, "project"
                )

            if not discovered_agents:
                self.logger.warning("No agents found in any tier")
                return self._get_fallback_capabilities()

            # Build capabilities section from discovered agents using list and join for better performance
            section_parts = [
                "\n## Available Agent Capabilities\n\n",
                "You have the following specialized agents available for delegation:\n\n",
            ]

            # Group agents by category
            agents_by_category = {}
            for _agent_id, agent_info in discovered_agents.items():
                category = agent_info["category"]
                if category not in agents_by_category:
                    agents_by_category[category] = []
                agents_by_category[category].append(agent_info)

            # Output agents by category
            for category in sorted(agents_by_category.keys()):
                section_parts.append(f"\n### {category} Agents\n")
                for agent in sorted(
                    agents_by_category[category], key=lambda x: x["name"]
                ):
                    tier_indicator = (
                        f" [{agent['tier']}]" if agent["tier"] != "project" else ""
                    )
                    section_parts.append(
                        f"- **{agent['name']}** (`{agent['id']}`{tier_indicator}): {agent['description']}\n"
                    )

            # Add summary
            section_parts.append(
                f"\n**Total Available Agents**: {len(discovered_agents)}\n"
            )

            # Show tier distribution
            tier_counts = {}
            for agent in discovered_agents.values():
                tier = agent["tier"]
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

            if len(tier_counts) > 1:
                section_parts.append("**Agent Sources**: ")
                tier_summary = []
                for tier in ["project", "user", "system"]:
                    if tier in tier_counts:
                        tier_summary.append(f"{tier_counts[tier]} {tier}")
                section_parts.append(", ".join(tier_summary) + "\n")

            section_parts.append(
                "Use the agent ID in parentheses when delegating tasks via the Task tool.\n"
            )

            # Join all parts for final section
            section = "".join(section_parts)

            self.logger.info(
                f"Generated capabilities for {len(discovered_agents)} agents "
                f"(project: {tier_counts.get('project', 0)}, "
                f"user: {tier_counts.get('user', 0)}, "
                f"system: {tier_counts.get('system', 0)})"
            )
            return section

        except Exception as e:
            self.logger.error(f"Failed to generate deployed agent capabilities: {e}")
            return self._get_fallback_capabilities()

    def _discover_agents_from_dir(
        self, agents_dir: Path, discovered_agents: dict, tier: str
    ):
        """Discover agents from a specific directory and add/override in discovered_agents.

        Args:
            agents_dir: Directory to search for agent .md files
            discovered_agents: Dictionary to update with discovered agents
            tier: The tier this directory represents (system/user/project)
        """
        if not agents_dir.exists():
            return

        agent_files = list(agents_dir.glob("*.md"))
        for agent_file in sorted(agent_files):
            try:
                agent_id = agent_file.stem

                # Read agent content
                content = agent_file.read_text(encoding="utf-8")

                # Extract name and description from content
                lines = content.split("\n")
                name = agent_id.replace("-", " ").replace("_", " ").title()
                description = f"Specialized agent for {agent_id.replace('-', ' ')}"

                # Try to extract better name and description from content
                for line in lines:
                    line = line.strip()
                    if line.startswith("# "):
                        name = line[2:].strip()
                    elif line.startswith("Description:"):
                        description = line[12:].strip()
                    elif "description" in line.lower() and ":" in line:
                        description = line.split(":", 1)[1].strip()

                # Categorize the agent
                category = self._categorize_agent(agent_id, content)

                # Add/override in discovered agents (higher tier overrides lower)
                discovered_agents[agent_id] = {
                    "id": agent_id,
                    "name": name,
                    "description": description,
                    "category": category,
                    "tier": tier,
                    "path": str(agent_file),
                }

                self.logger.debug(f"Discovered {tier} agent: {agent_id} ({category})")

            except Exception as e:
                self.logger.debug(f"Could not parse agent {agent_file}: {e}")
                continue

    def _categorize_agent(self, agent_id: str, content: str) -> str:
        """Categorize an agent based on its ID and content."""
        agent_id_lower = agent_id.lower()
        content_lower = content.lower()

        if "engineer" in agent_id_lower or "engineering" in content_lower:
            return "Development"
        if "research" in agent_id_lower or "research" in content_lower:
            return "Research"
        if (
            "qa" in agent_id_lower
            or "test" in agent_id_lower
            or "quality" in content_lower
        ):
            return "Quality Assurance"
        if "doc" in agent_id_lower or "documentation" in content_lower:
            return "Documentation"
        if "security" in agent_id_lower or "security" in content_lower:
            return "Security"
        if "data" in agent_id_lower or "database" in content_lower:
            return "Data"
        if (
            "ops" in agent_id_lower
            or "deploy" in agent_id_lower
            or "operations" in content_lower
        ):
            return "Operations"
        if "git" in agent_id_lower or "version" in content_lower:
            return "Version Control"
        return "General"

    def _get_fallback_capabilities(self) -> str:
        """Return fallback agent capabilities when deployed agents can't be read."""
        return """
## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer Agent**: Code implementation and development
- **Research Agent**: Investigation and analysis
- **QA Agent**: Testing and quality assurance
- **Documentation Agent**: Documentation creation and maintenance
- **Security Agent**: Security analysis and protection
- **Data Engineer Agent**: Data management and pipelines
- **Ops Agent**: Deployment and operations
- **Version Control Agent**: Git operations and version management

Use these agents to delegate specialized work via the Task tool.
"""
