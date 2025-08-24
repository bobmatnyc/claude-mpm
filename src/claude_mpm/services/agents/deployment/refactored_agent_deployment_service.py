"""Refactored Agent Deployment Service using new architecture."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.interfaces import AgentDeploymentInterface
from claude_mpm.core.logger import get_logger

from .config import DeploymentConfigManager
from .facade import DeploymentFacade
from .pipeline import (
    DeploymentPipelineBuilder,
    DeploymentPipelineExecutor,
)
from .results import DeploymentResultBuilder

# Import refactored components
from .strategies import DeploymentContext, DeploymentStrategySelector
from .validation import DeploymentValidator


class RefactoredAgentDeploymentService(AgentDeploymentInterface):
    """Refactored Agent Deployment Service.

    This service uses the new modular architecture with:
    - Strategy pattern for deployment types
    - Pipeline pattern for deployment flow
    - Facade pattern for async/sync execution
    - Dedicated validation and processing components
    """

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        base_agent_path: Optional[Path] = None,
        working_directory: Optional[Path] = None,
    ):
        """Initialize the refactored deployment service.

        Args:
            templates_dir: Directory containing agent templates
            base_agent_path: Path to base agent configuration
            working_directory: Working directory for deployment
        """
        self.logger = get_logger(__name__)

        # Set up directories
        self.working_directory = working_directory or Path.cwd()
        self.templates_dir = templates_dir or self.working_directory / "agents"
        self.base_agent_path = (
            base_agent_path or self.working_directory / "base_agent.md"
        )

        # Initialize components
        self.strategy_selector = DeploymentStrategySelector()
        self.config_manager = DeploymentConfigManager()
        self.validator = DeploymentValidator()
        self.result_builder = DeploymentResultBuilder()

        # Initialize pipeline components
        self.pipeline_builder = DeploymentPipelineBuilder()
        self.pipeline_executor = DeploymentPipelineExecutor()

        # Initialize facade for async/sync execution
        self.deployment_facade = DeploymentFacade(
            self.pipeline_builder, self.pipeline_executor
        )

        self.logger.info("Refactored deployment service initialized")
        self.logger.info(f"Templates directory: {self.templates_dir}")
        self.logger.info(f"Base agent path: {self.base_agent_path}")
        self.logger.info(f"Working directory: {self.working_directory}")

    def deploy_agents(
        self, force: bool = False, include_all: bool = False
    ) -> Dict[str, Any]:
        """Deploy agents to target environment.

        Args:
            force: Force deployment even if agents already exist
            include_all: Include all agents, ignoring exclusion lists

        Returns:
            Dictionary with deployment results and status
        """
        try:
            self.logger.info(
                f"Starting agent deployment (force={force}, include_all={include_all})"
            )

            # Create deployment context
            deployment_context = DeploymentContext(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_directory,
                force_rebuild=force,
                deployment_mode="project" if include_all else "update",
            )

            # Select deployment strategy
            strategy = self.strategy_selector.select_strategy(deployment_context)
            self.logger.info(
                f"Selected deployment strategy: {strategy.__class__.__name__}"
            )

            # Use facade to execute deployment
            results = self.deployment_facade.deploy_agents(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_directory,
                target_dir=strategy.determine_target_directory(deployment_context),
                force_rebuild=force,
                deployment_mode=deployment_context.deployment_mode,
                config=None,  # Use default configuration
                use_async=False,  # Default to sync for interface compliance
            )

            # Ensure success field is present
            if "success" not in results:
                results["success"] = not bool(results.get("errors", []))

            self.logger.info(f"Deployment completed: {results.get('success', False)}")
            return results

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [str(e)],
                "metadata": {
                    "service_version": "refactored-1.0.0",
                    "error_type": type(e).__name__,
                },
            }

    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent configuration and structure.

        Args:
            agent_path: Path to agent configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            # Use the validation service
            if agent_path.suffix == ".json":
                # Template file validation
                result = self.validator.template_validator.validate_template_file(
                    agent_path
                )
            else:
                # Agent file validation
                result = self.validator.agent_validator.validate_agent_file(agent_path)

            # Convert validation result to interface format
            errors = [str(issue) for issue in result.errors]
            return result.is_valid, errors

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
            self.logger.info(
                f"Cleaning deployment (preserve_user_agents={preserve_user_agents})"
            )

            # Find agents directory
            agents_dir = self.working_directory / ".claude" / "agents"

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
            self.logger.error(f"Deployment cleanup failed: {e}", exc_info=True)
            return False

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics.

        Returns:
            Dictionary with deployment status information
        """
        try:
            # Get metrics from the result builder
            metrics_data = self.result_builder.metrics.get_summary()

            # Get available executors from facade
            available_executors = self.deployment_facade.get_available_executors()

            # Build status information
            return {
                "service_version": "refactored-1.0.0",
                "status": "ready",
                "templates_dir": str(self.templates_dir),
                "base_agent_path": str(self.base_agent_path),
                "working_directory": str(self.working_directory),
                "metrics": metrics_data,
                "available_executors": available_executors,
                "components": {
                    "strategy_selector": True,
                    "config_manager": True,
                    "validator": True,
                    "pipeline_builder": True,
                    "pipeline_executor": True,
                    "deployment_facade": True,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get deployment status: {e}", exc_info=True)
            return {
                "service_version": "refactored-1.0.0",
                "status": "error",
                "error": str(e),
            }

    # Additional convenience methods for enhanced functionality

    def deploy_agents_async(
        self, force: bool = False, include_all: bool = False
    ) -> Dict[str, Any]:
        """Deploy agents using async execution if available.

        Args:
            force: Force deployment even if agents already exist
            include_all: Include all agents, ignoring exclusion lists

        Returns:
            Dictionary with deployment results and status
        """
        try:
            # Create deployment context
            deployment_context = DeploymentContext(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_directory,
                force_rebuild=force,
                deployment_mode="project" if include_all else "update",
            )

            # Select deployment strategy
            strategy = self.strategy_selector.select_strategy(deployment_context)

            # Use facade with synchronous deployment for reliability
            return self.deployment_facade.deploy_agents(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_directory,
                target_dir=strategy.determine_target_directory(deployment_context),
                force_rebuild=force,
                deployment_mode=deployment_context.deployment_mode,
                config=None,
                use_async=False,  # Use synchronous deployment to ensure agents are ready when Claude Code launches
            )

        except Exception as e:
            self.logger.error(f"Async deployment failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "deployed": [],
                "updated": [],
                "migrated": [],
                "skipped": [],
                "errors": [str(e)],
            }
