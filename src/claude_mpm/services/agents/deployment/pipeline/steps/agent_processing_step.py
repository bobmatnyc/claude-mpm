"""Agent processing step for deployment pipeline."""

import time
from pathlib import Path

from claude_mpm.services.agents.deployment.processors import (
    AgentDeploymentContext,
    AgentDeploymentResult,
    AgentProcessor,
)

from .base_step import BaseDeploymentStep, StepResult, StepStatus


class AgentProcessingStep(BaseDeploymentStep):
    """Step to process and deploy individual agents."""

    def __init__(self, template_builder, version_manager):
        super().__init__(
            name="Agent Processing",
            description="Process and deploy individual agent templates",
        )
        self.processor = AgentProcessor(template_builder, version_manager)

    def execute(self, context) -> StepResult:
        """Execute agent processing step.

        Args:
            context: Pipeline context

        Returns:
            Result of agent processing
        """
        start_time = time.time()

        try:
            if not context.template_files:
                self.logger.warning("No template files to process")
                return StepResult(
                    status=StepStatus.SKIPPED,
                    message="No template files found to process",
                    execution_time=time.time() - start_time,
                )

            # Initialize results tracking
            processed_count = 0
            failed_count = 0

            # Process each template file
            for template_file in context.template_files:
                try:
                    # Determine source for this agent
                    agent_name = template_file.stem
                    # Use source from context if available (multi-source deployment), otherwise determine it
                    if context.agent_sources and agent_name in context.agent_sources:
                        source_info = context.agent_sources[agent_name]
                    else:
                        source_info = self._determine_agent_source(template_file)

                    # Create agent deployment context
                    agent_context = AgentDeploymentContext.from_template_file(
                        template_file=template_file,
                        agents_dir=context.actual_target_dir,
                        base_agent_data=context.base_agent_data or {},
                        base_agent_version=context.base_agent_version or (1, 0, 0),
                        force_rebuild=context.force_rebuild,
                        deployment_mode=context.deployment_mode,
                        source_info=source_info,
                    )

                    # Validate agent if requested
                    if context.should_repair_existing_agents:
                        if not self.processor.validate_agent(agent_context):
                            self.logger.warning(
                                f"Agent validation failed: {agent_context.agent_name}"
                            )
                            context.add_warning(
                                f"Agent validation failed: {agent_context.agent_name}"
                            )
                            failed_count += 1
                            continue

                    # Process the agent
                    result = self.processor.process_agent(agent_context)

                    # Update context results based on outcome
                    self._update_context_with_result(context, result)

                    if result.is_successful():
                        processed_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    error_msg = f"Failed to process agent {template_file.stem}: {e!s}"
                    self.logger.error(error_msg, exc_info=True)
                    context.add_error(error_msg)
                    failed_count += 1

            # Calculate execution time
            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            # Determine step status
            if failed_count == 0:
                status = StepStatus.SUCCESS
                message = f"Successfully processed {processed_count} agents in {execution_time:.3f}s"
            elif processed_count > 0:
                status = StepStatus.WARNING
                message = f"Processed {processed_count} agents with {failed_count} failures in {execution_time:.3f}s"
            else:
                status = StepStatus.FAILURE
                message = f"Failed to process any agents ({failed_count} failures) in {execution_time:.3f}s"

            self.logger.info(message)

            return StepResult(
                status=status, message=message, execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            context.step_timings[self.name] = execution_time

            error_msg = f"Agent processing step failed: {e!s}"
            self.logger.error(error_msg, exc_info=True)
            context.add_error(error_msg)

            return StepResult(
                status=StepStatus.FAILURE,
                message=error_msg,
                error=e,
                execution_time=execution_time,
            )

    def _update_context_with_result(
        self, context, result: AgentDeploymentResult
    ) -> None:
        """Update pipeline context with agent deployment result.

        Args:
            context: Pipeline context
            result: Agent deployment result
        """
        # Ensure results structure exists
        if "deployed" not in context.results:
            context.results["deployed"] = []
        if "updated" not in context.results:
            context.results["updated"] = []
        if "migrated" not in context.results:
            context.results["migrated"] = []
        if "skipped" not in context.results:
            context.results["skipped"] = []
        if "errors" not in context.results:
            context.results["errors"] = []

        # Add result to appropriate list
        result_dict = result.to_dict()

        if result.status.value == "deployed":
            context.results["deployed"].append(result_dict)
        elif result.status.value == "updated":
            context.results["updated"].append(result_dict)
        elif result.status.value == "migrated":
            context.results["migrated"].append(result_dict)
        elif result.status.value == "skipped":
            context.results["skipped"].append(result.agent_name)
        elif result.status.value == "failed":
            context.results["errors"].append(
                result.error_message or f"Failed to deploy {result.agent_name}"
            )

    def should_execute(self, context) -> bool:
        """Check if this step should be executed.

        Args:
            context: Pipeline context

        Returns:
            True if there are template files to process
        """
        return bool(context.template_files)

    def can_continue_on_failure(self) -> bool:
        """Agent processing failures should not stop the pipeline.

        Individual agent failures are tracked but don't prevent
        other agents from being processed.

        Returns:
            True - continue on failure
        """
        return True

    def get_dependencies(self) -> list:
        """This step depends on target directory setup.

        Returns:
            List of required step classes
        """
        from .target_directory_step import TargetDirectorySetupStep

        return [TargetDirectorySetupStep]

    def _determine_agent_source(self, template_path: Path) -> str:
        """Determine the source of an agent from its template path.

        Args:
            template_path: Path to the agent template

        Returns:
            Source string (system/project/user/unknown)
        """
        template_str = str(template_path.resolve())

        # Check if it's a system template
        if (
            "/claude_mpm/agents/templates/" in template_str
            or "/src/claude_mpm/agents/templates/" in template_str
        ):
            return "system"

        # Check if it's a project agent
        if "/.claude-mpm/agents/" in template_str:
            # Check if it's in the current working directory
            try:
                from pathlib import Path

                cwd = Path.cwd()
                if str(cwd) in template_str:
                    return "project"
            except:
                pass

        # Check if it's a user agent
        if "/.claude/agents/" in template_str:
            return "user"

        return "unknown"
