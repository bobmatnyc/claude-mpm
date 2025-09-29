"""Agent Capabilities Content Generator.

This service generates markdown content for agent capabilities section
from discovered deployed agents.
"""

from typing import Any, Dict, List

from jinja2 import Template

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class AgentCapabilitiesGenerator:
    """Generates markdown content for agent capabilities section."""

    def __init__(self):
        """Initialize the generator with default template."""
        self.template = self._load_template()
        logger.debug("Initialized AgentCapabilitiesGenerator")

    def generate_capabilities_section(
        self, deployed_agents: List[Dict[str, Any]]
    ) -> str:
        """Generate the complete agent capabilities markdown section.

        Args:
            deployed_agents: List of agent information dictionaries

        Returns:
            Generated markdown content for agent capabilities
        """
        try:
            # Group agents by source tier for organized display
            agents_by_tier = self._group_by_tier(deployed_agents)

            # Generate core agent list
            core_agent_list = self._generate_core_agent_list(deployed_agents)

            # Generate detailed capabilities
            detailed_capabilities = self._generate_detailed_capabilities(
                deployed_agents
            )

            # Render template
            return self.template.render(
                core_agents=core_agent_list,
                detailed_capabilities=detailed_capabilities,
                agents_by_tier=agents_by_tier,
                total_agents=len(deployed_agents),
            )

        except Exception as e:
            logger.error(f"Failed to generate capabilities section: {e}")
            # Return fallback content on error
            return self._generate_fallback_content()

    def _group_by_tier(
        self, agents: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group agents by their source tier.

        Args:
            agents: List of agent information dictionaries

        Returns:
            Dictionary mapping tiers to lists of agents
        """
        tiers = {"system": [], "user": [], "project": []}

        for agent in agents:
            tier = agent.get("source_tier", "system")
            if tier in tiers:
                tiers[tier].append(agent)
            else:
                # Handle unknown tiers gracefully
                tiers["system"].append(agent)
                logger.warning(
                    f"Unknown source tier '{tier}' for agent {agent.get('id')}, defaulting to system"
                )

        return tiers

    def _generate_core_agent_list(self, agents: List[Dict[str, Any]]) -> str:
        """Generate comma-separated list of core agent IDs.

        Args:
            agents: List of agent information dictionaries

        Returns:
            Comma-separated string of agent IDs
        """
        agent_ids = [agent["id"] for agent in agents]
        return ", ".join(sorted(agent_ids))

    def _generate_detailed_capabilities(
        self, agents: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Generate detailed capability descriptions for each agent.

        Args:
            agents: List of agent information dictionaries

        Returns:
            List of capability dictionaries for template rendering
        """
        capabilities = []

        for agent in sorted(agents, key=lambda a: a["id"]):
            # Extract key capabilities
            specializations = agent.get("specializations", [])
            when_to_use = agent.get("capabilities", {}).get("when_to_use", [])

            # Create capability summary
            if when_to_use:
                capability_text = "; ".join(when_to_use[:2])  # First 2 items
            elif specializations:
                capability_text = ", ".join(
                    specializations[:3]
                )  # First 3 specializations
            else:
                capability_text = agent.get("description", "General purpose agent")

            # Truncate long capability text
            if len(capability_text) > 100:
                capability_text = capability_text[:97] + "..."

            # Clean up the agent name for TodoWrite usage
            clean_name = agent["name"].replace(" Agent", "").replace("-", " ")

            capabilities.append(
                {
                    "name": clean_name,  # Clean name for TodoWrite
                    "id": agent["id"],  # Agent ID for Task tool
                    "capability_text": capability_text,
                    "tools": ", ".join(agent.get("tools", [])[:5]),  # First 5 tools
                }
            )

        return capabilities

    def _load_template(self) -> Template:
        """Load the Jinja2 template for agent capabilities.

        Returns:
            Configured Jinja2 template
        """
        template_content = """
## Available Agent Capabilities

You have the following specialized agents available for delegation:

{% if agents_by_tier.project %}
### Project-Specific Agents
{% for agent in agents_by_tier.project %}
- **{{ agent.name|replace(' Agent', '')|replace('-', ' ') }}** (`{{ agent.id }}`): {{ agent.description }}
{% endfor %}

{% endif %}
### Engineering Agents
{% for cap in detailed_capabilities %}
{% if cap.id in ['engineer', 'data_engineer', 'documentation', 'ops', 'security', 'ticketing', 'version_control', 'web_ui'] %}
- **{{ cap.name }}** (`{{ cap.id }}`): {{ cap.capability_text }}
{% endif %}
{% endfor %}

### Research Agents
{% for cap in detailed_capabilities %}
{% if cap.id in ['code_analyzer', 'qa', 'research', 'web_qa'] %}
- **{{ cap.name }}** (`{{ cap.id }}`): {{ cap.capability_text }}
{% endif %}
{% endfor %}

**Total Available Agents**: {{ total_agents }}
Use the agent ID in parentheses when delegating tasks via the Task tool.
""".strip()

        return Template(template_content)

    def _generate_fallback_content(self) -> str:
        """Generate fallback content when agent discovery fails.

        Returns:
            Static fallback markdown content
        """
        logger.warning("Using fallback content due to generation failure")
        return """
## Agent Names & Capabilities
**Core Agents**: research, engineer, qa, documentation, security, ops, version_control, data_engineer

**Agent Capabilities**:
- **Research**: Codebase analysis, best practices, technical investigation
- **Engineer**: Implementation, refactoring, debugging
- **QA**: Quality assurance, testing, code review
- **Documentation**: Technical writing, API docs, user guides
- **Security**: Security analysis, vulnerability assessment
- **Ops**: Operations, deployment, infrastructure
- **Version Control**: Git operations, branch management
- **Data Engineer**: Data pipelines, ETL, database operations

*Note: Unable to dynamically generate agent list. Using default agents.*
""".strip()
