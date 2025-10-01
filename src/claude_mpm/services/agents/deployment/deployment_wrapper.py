"""Temporary wrapper to provide backward compatibility for CLI commands."""

import contextlib
from pathlib import Path
from typing import Any, Dict

from claude_mpm.services.agents.deployment import AgentDeploymentService


class DeploymentServiceWrapper:
    """Wrapper to provide backward-compatible methods for the CLI."""

    def __init__(self, deployment_service: AgentDeploymentService):
        """Initialize wrapper with actual deployment service."""
        self.service = deployment_service
        # Pass through all attributes
        for attr in dir(deployment_service):
            if not attr.startswith("_") and not hasattr(self, attr):
                setattr(self, attr, getattr(deployment_service, attr))

    def deploy_system_agents(self, force: bool = False) -> Dict[str, Any]:
        """Deploy system agents only.

        Args:
            force: Force rebuild even if agents are up to date

        Returns:
            Deployment results
        """
        # Deploy agents with default target (system agents location)
        result = self.service.deploy_agents(
            force_rebuild=force, deployment_mode="update"
        )

        # Transform result to expected format
        return {
            "deployed_count": len(result.get("deployed", []))
            + len(result.get("updated", [])),
            "deployed": result.get("deployed", []),
            "updated": result.get("updated", []),
            "errors": result.get("errors", []),
            "target_dir": result.get("target_dir", ""),
        }

    def deploy_project_agents(self, force: bool = False) -> Dict[str, Any]:
        """Deploy project agents only.

        Args:
            force: Force rebuild even if agents are up to date

        Returns:
            Deployment results
        """
        # Check if project agents directory exists
        project_dir = Path.cwd() / ".claude-mpm" / "agents"
        if not project_dir.exists():
            return {
                "deployed_count": 0,
                "deployed": [],
                "updated": [],
                "errors": [],
                "target_dir": "",
            }

        # For now, return empty result as project agents are handled differently
        return {
            "deployed_count": 0,
            "deployed": [],
            "updated": [],
            "errors": [],
            "target_dir": str(project_dir),
        }

    def get_agent_details(self, agent_name: str) -> Dict[str, Any]:
        """Get detailed information for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent details dictionary or empty dict if not found
        """
        try:
            # Try to get from list of available agents
            available_agents = self.service.list_available_agents()
            for agent in available_agents:
                if agent.get("name") == agent_name:
                    # Get template path for the agent
                    templates_dir = self.service.templates_dir
                    agent_path = templates_dir / f"{agent_name}.md"

                    # Read agent content if file exists
                    if agent_path.exists():
                        with agent_path.open() as f:
                            content = f.read()

                        # Parse metadata from content
                        import yaml

                        metadata = {}
                        if content.startswith("---"):
                            # Extract frontmatter
                            parts = content.split("---", 2)
                            if len(parts) >= 2:
                                with contextlib.suppress(yaml.YAMLError):
                                    metadata = yaml.safe_load(parts[1])

                        return {
                            "name": agent_name,
                            "path": str(agent_path),
                            "type": agent.get("type", "agent"),
                            "version": metadata.get("version", "1.0.0"),
                            "description": metadata.get("description", ""),
                            "specializations": metadata.get("specializations", []),
                            "metadata": metadata,
                            "content": content,
                            "exists": True,
                        }

            # Agent not found in available agents
            return {
                "name": agent_name,
                "exists": False,
                "error": f"Agent '{agent_name}' not found",
            }

        except Exception as e:
            # Return error information
            return {"name": agent_name, "exists": False, "error": str(e)}
