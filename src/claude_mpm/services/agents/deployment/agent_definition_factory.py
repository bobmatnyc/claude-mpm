"""Agent definition factory for lifecycle manager.

This module provides factory functionality for creating AgentDefinition objects
from lifecycle manager parameters. Extracted to reduce complexity.
"""

from claude_mpm.core.unified_agent_registry import AgentSourceType
from claude_mpm.models.agent_definition import (
    AgentDefinition,
    AgentMetadata,
    AgentPermissions,
    AgentRole,
)
from claude_mpm.services.agents.registry.modification_tracker import ModificationTier


class AgentDefinitionFactory:
    """Factory for creating AgentDefinition objects."""

    def create_agent_definition(
        self,
        agent_name: str,
        agent_content: str,
        tier: ModificationTier,
        agent_type: str,
        **kwargs,
    ) -> AgentDefinition:
        """
        Create an AgentDefinition from lifecycle parameters.

        This method bridges the gap between the lifecycle manager's parameters
        and the AgentManager's expected AgentDefinition model.

        DESIGN DECISION: Creating a minimal AgentDefinition here because:
        - The full markdown parsing happens in AgentManager
        - We only need to provide the essential metadata
        - This keeps the lifecycle manager focused on orchestration

        Args:
            agent_name: Name of the agent
            agent_content: Content of the agent
            tier: Modification tier
            agent_type: Type of agent
            **kwargs: Additional parameters

        Returns:
            AgentDefinition object
        """
        # Map tier to AgentSourceType
        source_map = {
            ModificationTier.USER: AgentSourceType.CUSTOM,
            ModificationTier.PROJECT: AgentSourceType.PROJECT,
            ModificationTier.SYSTEM: AgentSourceType.SYSTEM,
        }

        # Create metadata
        metadata = AgentMetadata(
            role=AgentRole.from_frontmatter(agent_type)
            if agent_type
            else AgentRole.OTHER,
            source=source_map.get(tier, AgentSourceType.CUSTOM),
            model_preference=kwargs.get("model_preference", "claude-3-sonnet"),
            version="1.0.0",
            author=kwargs.get("author", "claude-mpm"),
            tags=kwargs.get("tags", []),
            specializations=kwargs.get("specializations", []),
        )

        # Create minimal definition
        return AgentDefinition(
            name=agent_name,
            title=agent_name.replace("-", " ").title(),
            file_path="",  # Will be set by AgentManager
            metadata=metadata,
            primary_role=kwargs.get("primary_role", f"{agent_name} agent"),
            when_to_use={"select": [], "do_not_select": []},
            capabilities=[],
            authority=AgentPermissions(),
            workflows=[],
            escalation_triggers=[],
            kpis=[],
            dependencies=[],
            tools_commands="",
            raw_content=agent_content,
        )
