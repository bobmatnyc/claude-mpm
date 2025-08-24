"""Agent processor for individual agent deployment operations."""

import time

from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.core.logger import get_logger

from .agent_deployment_context import AgentDeploymentContext
from .agent_deployment_result import AgentDeploymentResult


class AgentProcessor:
    """Processor for deploying individual agents.

    This class handles the processing and deployment of a single agent,
    including update checking, building, and deployment.
    """

    def __init__(self, template_builder, version_manager):
        """Initialize the agent processor.

        Args:
            template_builder: Template builder service
            version_manager: Version manager service
        """
        self.template_builder = template_builder
        self.version_manager = version_manager
        self.logger = get_logger(__name__)

    def process_agent(self, context: AgentDeploymentContext) -> AgentDeploymentResult:
        """Process and deploy a single agent.

        Args:
            context: Agent deployment context

        Returns:
            AgentDeploymentResult with deployment outcome
        """
        start_time = time.time()

        try:
            self.logger.debug(f"Processing agent: {context.agent_name}")

            # Check if agent needs update
            needs_update, is_migration, reason = self._check_update_status(context)

            # Skip if exists and doesn't need update (only in update mode)
            if (
                context.target_file.exists()
                and not needs_update
                and not context.is_project_deployment()
            ):
                self.logger.debug(f"Skipped up-to-date agent: {context.agent_name}")
                return AgentDeploymentResult.skipped(
                    context.agent_name,
                    context.template_file,
                    context.target_file,
                    reason="Agent is up-to-date",
                )

            # Build the agent
            agent_content = self._build_agent_content(context)

            # Deploy the agent
            self._deploy_agent_content(context, agent_content)

            # Calculate deployment time
            deployment_time_ms = (time.time() - start_time) * 1000

            # Determine result type
            if is_migration:
                self.logger.info(f"Successfully migrated agent: {context.agent_name}")
                return AgentDeploymentResult.migrated(
                    context.agent_name,
                    context.template_file,
                    context.target_file,
                    deployment_time_ms,
                    reason,
                )
            if context.is_update():
                self.logger.debug(f"Updated agent: {context.agent_name}")
                return AgentDeploymentResult.updated(
                    context.agent_name,
                    context.template_file,
                    context.target_file,
                    deployment_time_ms,
                    reason,
                )
            self.logger.debug(f"Deployed new agent: {context.agent_name}")
            return AgentDeploymentResult.deployed(
                context.agent_name,
                context.template_file,
                context.target_file,
                deployment_time_ms,
            )

        except AgentDeploymentError as e:
            # Re-raise our custom exceptions
            deployment_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Agent deployment error for {context.agent_name}: {e!s}")
            return AgentDeploymentResult.failed(
                context.agent_name,
                context.template_file,
                context.target_file,
                str(e),
                deployment_time_ms,
            )
        except Exception as e:
            # Wrap generic exceptions with context
            deployment_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Failed to process {context.agent_name}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return AgentDeploymentResult.failed(
                context.agent_name,
                context.template_file,
                context.target_file,
                error_msg,
                deployment_time_ms,
            )

    def _check_update_status(self, context: AgentDeploymentContext) -> tuple:
        """Check if agent needs update and determine status.

        Args:
            context: Agent deployment context

        Returns:
            Tuple of (needs_update, is_migration, reason)
        """
        needs_update = context.force_rebuild
        is_migration = False
        reason = ""

        # In project deployment mode, always deploy regardless of version
        if context.is_project_deployment():
            if context.target_file.exists():
                needs_update = True
                reason = "Project deployment mode"
                self.logger.debug(
                    f"Project deployment mode: will deploy {context.agent_name}"
                )
            else:
                needs_update = True
                reason = "New agent in project mode"
        elif not needs_update:
            # Check if target file exists
            if not context.target_file.exists():
                # File doesn't exist, needs to be deployed
                needs_update = True
                reason = "New agent deployment"
                self.logger.debug(
                    f"Agent {context.agent_name} doesn't exist, will deploy"
                )
            else:
                # File exists, check version compatibility
                needs_update, reason = self.version_manager.check_agent_needs_update(
                    context.target_file,
                    context.template_file,
                    context.base_agent_version,
                )
                if needs_update:
                    # Check if this is a migration from old format
                    if "migration needed" in reason:
                        is_migration = True
                        self.logger.info(
                            f"Migration needed for agent {context.agent_name}: {reason}"
                        )
                    else:
                        self.logger.info(
                            f"Agent {context.agent_name} needs update: {reason}"
                        )

        return needs_update, is_migration, reason

    def _build_agent_content(self, context: AgentDeploymentContext) -> str:
        """Build agent content from template.

        Args:
            context: Agent deployment context

        Returns:
            Built agent content as markdown with YAML frontmatter

        Raises:
            AgentDeploymentError: If building fails
        """
        try:
            return self.template_builder.build_agent_markdown(
                context.agent_name,
                context.template_file,
                context.base_agent_data,
                context.source_info,
            )
        except Exception as e:
            raise AgentDeploymentError(
                f"Failed to build agent {context.agent_name}: {e}"
            ) from e

    def _deploy_agent_content(
        self, context: AgentDeploymentContext, content: str
    ) -> None:
        """Deploy agent content to target file.

        Args:
            context: Agent deployment context
            content: Agent content to deploy

        Raises:
            AgentDeploymentError: If deployment fails
        """
        try:
            # Ensure target directory exists
            context.target_file.parent.mkdir(parents=True, exist_ok=True)

            # Write the agent file
            context.target_file.write_text(content, encoding="utf-8")

            self.logger.debug(f"Successfully wrote agent file: {context.target_file}")

        except Exception as e:
            raise AgentDeploymentError(
                f"Failed to write agent {context.agent_name} to {context.target_file}: {e}"
            ) from e

    def validate_agent(self, context: AgentDeploymentContext) -> bool:
        """Validate agent template before processing.

        Args:
            context: Agent deployment context

        Returns:
            True if agent is valid
        """
        try:
            # Check if template file exists and is readable
            if not context.template_file.exists():
                self.logger.error(
                    f"Template file does not exist: {context.template_file}"
                )
                return False

            if not context.template_file.is_file():
                self.logger.error(
                    f"Template path is not a file: {context.template_file}"
                )
                return False

            # Check if we can read the template
            try:
                context.template_file.read_text(encoding="utf-8")
            except Exception as e:
                self.logger.error(
                    f"Cannot read template file {context.template_file}: {e}"
                )
                return False

            # Check if target directory is writable
            if context.target_file.parent.exists():
                if not context.target_file.parent.is_dir():
                    self.logger.error(
                        f"Target parent is not a directory: {context.target_file.parent}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error for agent {context.agent_name}: {e}")
            return False
