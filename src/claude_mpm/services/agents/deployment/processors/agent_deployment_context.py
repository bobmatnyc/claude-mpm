"""Agent deployment context for individual agent processing."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AgentDeploymentContext:
    """Context for deploying a single agent.

    This context contains all the information needed to process
    and deploy a single agent template.
    """

    # Agent identification
    agent_name: str
    template_file: Path
    target_file: Path

    # Deployment configuration
    force_rebuild: bool = False
    deployment_mode: str = "update"
    source_info: str = "unknown"  # Source of the agent (system/project/user)

    # Base agent data
    base_agent_data: Optional[Dict[str, Any]] = None
    base_agent_version: Optional[tuple] = None

    # Target directory
    agents_dir: Path = None

    # Processing flags
    validate_before_deployment: bool = True
    collect_metrics: bool = True

    def __post_init__(self):
        """Post-initialization validation."""
        if self.agents_dir is None and self.target_file:
            self.agents_dir = self.target_file.parent

        if self.agent_name is None and self.template_file:
            self.agent_name = self.template_file.stem

        if self.target_file is None and self.agents_dir and self.agent_name:
            self.target_file = self.agents_dir / f"{self.agent_name}.md"

    @classmethod
    def from_template_file(
        cls,
        template_file: Path,
        agents_dir: Path,
        base_agent_data: Dict[str, Any],
        base_agent_version: tuple,
        force_rebuild: bool = False,
        deployment_mode: str = "update",
        source_info: str = "unknown",
    ) -> "AgentDeploymentContext":
        """Create context from template file.

        Args:
            template_file: Agent template file
            agents_dir: Target agents directory
            base_agent_data: Base agent data
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode
            source_info: Source of the agent (system/project/user)

        Returns:
            AgentDeploymentContext instance
        """
        agent_name = template_file.stem
        target_file = agents_dir / f"{agent_name}.md"

        return cls(
            agent_name=agent_name,
            template_file=template_file,
            target_file=target_file,
            force_rebuild=force_rebuild,
            deployment_mode=deployment_mode,
            base_agent_data=base_agent_data,
            base_agent_version=base_agent_version,
            agents_dir=agents_dir,
            source_info=source_info,
        )

    def is_update(self) -> bool:
        """Check if this is an update (target file exists).

        Returns:
            True if target file exists
        """
        return self.target_file.exists()

    def is_project_deployment(self) -> bool:
        """Check if this is a project deployment.

        Returns:
            True if deployment mode is project
        """
        return self.deployment_mode == "project"
