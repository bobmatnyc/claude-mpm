"""Interface adapter for AgentDeploymentService compliance."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.interfaces import AgentDeploymentInterface
from claude_mpm.core.logger import get_logger


class AgentDeploymentInterfaceAdapter(AgentDeploymentInterface):
    """Adapter to make AgentDeploymentService compliant with AgentDeploymentInterface.

    This adapter bridges the gap between the current implementation's method
    signatures and the required interface signatures, providing a clean
    interface compliance layer.
    """

    def __init__(self, deployment_service):
        """Initialize the interface adapter.

        Args:
            deployment_service: The actual deployment service implementation
        """
        self.deployment_service = deployment_service
        self.logger = get_logger(__name__)

    def deploy_agents(
        self, force: bool = False, include_all: bool = False
    ) -> Dict[str, Any]:
        """Deploy agents to target environment.

        This method adapts the interface signature to the actual implementation.

        Args:
            force: Force deployment even if agents already exist
            include_all: Include all agents, ignoring exclusion lists

        Returns:
            Dictionary with deployment results and status
        """
        try:
            # Map interface parameters to implementation parameters
            force_rebuild = force

            # Determine deployment mode based on include_all
            deployment_mode = "project" if include_all else "update"

            # Call the actual implementation
            results = self.deployment_service.deploy_agents(
                target_dir=None,  # Use default target directory
                force_rebuild=force_rebuild,
                deployment_mode=deployment_mode,
                config=None,  # Use default configuration
                use_async=False,  # Default to sync for interface compliance
            )

            # Ensure the result has the expected structure
            if not isinstance(results, dict):
                return {
                    "success": False,
                    "error": "Invalid result format from deployment service",
                    "deployed": [],
                    "updated": [],
                    "migrated": [],
                    "skipped": [],
                    "errors": ["Invalid result format"],
                }

            # Add interface compliance metadata
            results["interface_version"] = "1.0.0"
            results["adapter_used"] = True

            return results

        except Exception as e:
            self.logger.error(
                f"Interface adapter deployment failed: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [str(e)],
                "interface_version": "1.0.0",
                "adapter_used": True,
            }

    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent configuration and structure.

        Args:
            agent_path: Path to agent configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            # Delegate to the actual implementation
            return self.deployment_service.validate_agent(agent_path)
        except Exception as e:
            self.logger.error(f"Agent validation failed: {e}", exc_info=True)
            return False, [f"Validation error: {e!s}"]

    def clean_deployment(self, preserve_user_agents: bool = True) -> bool:
        """Clean up deployed agents.

        Args:
            preserve_user_agents: Whether to keep user-created agents

        Returns:
            True if cleanup successful
        """
        try:
            # Check if the deployment service has a clean_deployment method
            if hasattr(self.deployment_service, "clean_deployment"):
                # Call the existing method (it has a different signature)
                result = self.deployment_service.clean_deployment()

                # The existing method returns a dict, we need to return a bool
                if isinstance(result, dict):
                    return result.get("success", False)
                return bool(result)
            # Implement basic cleanup logic if method doesn't exist
            return self._basic_cleanup(preserve_user_agents)

        except Exception as e:
            self.logger.error(f"Deployment cleanup failed: {e}", exc_info=True)
            return False

    def _basic_cleanup(self, preserve_user_agents: bool) -> bool:
        """Basic cleanup implementation.

        Args:
            preserve_user_agents: Whether to keep user-created agents

        Returns:
            True if cleanup successful
        """
        try:
            # Get the working directory from the deployment service
            working_dir = getattr(
                self.deployment_service, "working_directory", Path.cwd()
            )
            agents_dir = working_dir / ".claude" / "agents"

            if not agents_dir.exists():
                self.logger.info("No agents directory to clean")
                return True

            cleaned_count = 0

            # Clean up agent files
            for agent_file in agents_dir.glob("*.md"):
                try:
                    if preserve_user_agents:
                        # Check if this is a system agent (authored by claude-mpm)
                        content = agent_file.read_text(encoding="utf-8")
                        if (
                            "author: claude-mpm" not in content
                            and "author: 'claude-mpm'" not in content
                        ):
                            self.logger.debug(
                                f"Preserving user agent: {agent_file.name}"
                            )
                            continue

                    # Remove the agent file
                    agent_file.unlink()
                    cleaned_count += 1
                    self.logger.debug(f"Cleaned agent: {agent_file.name}")

                except Exception as e:
                    self.logger.warning(f"Failed to clean agent {agent_file.name}: {e}")

            self.logger.info(f"Cleaned {cleaned_count} agent files")
            return True

        except Exception as e:
            self.logger.error(f"Basic cleanup failed: {e}", exc_info=True)
            return False

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics.

        Returns:
            Dictionary with deployment status information
        """
        try:
            # Delegate to the actual implementation
            status = self.deployment_service.get_deployment_status()

            # Ensure the result is a dictionary
            if not isinstance(status, dict):
                return {
                    "status": OperationResult.UNKNOWN,
                    "error": "Invalid status format from deployment service",
                    "interface_version": "1.0.0",
                    "adapter_used": True,
                }

            # Add interface compliance metadata
            status["interface_version"] = "1.0.0"
            status["adapter_used"] = True

            return status

        except Exception as e:
            self.logger.error(f"Failed to get deployment status: {e}", exc_info=True)
            return {
                "status": OperationResult.ERROR,
                "error": str(e),
                "interface_version": "1.0.0",
                "adapter_used": True,
            }

    def get_wrapped_service(self):
        """Get the wrapped deployment service.

        Returns:
            The actual deployment service implementation
        """
        return self.deployment_service
