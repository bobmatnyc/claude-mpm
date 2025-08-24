"""Temporary wrapper to provide backward compatibility for CLI commands."""

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
