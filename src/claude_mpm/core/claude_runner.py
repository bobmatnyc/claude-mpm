"""Claude runner with both exec and subprocess launch methods."""

import os
from pathlib import Path
from typing import Optional

# Core imports that don't cause circular dependencies
from claude_mpm.core.container import get_container
from claude_mpm.core.interfaces import (
    AgentDeploymentInterface,
)
from claude_mpm.core.logging_config import (
    get_logger,
)
from claude_mpm.services.core.interfaces import (
    RunnerConfigurationInterface,
)

# Type checking imports to avoid circular dependencies


class ClaudeRunner:
    """
    Claude runner that replaces the entire orchestrator system.

    This does exactly what we need:
    1. Deploy native agents to .claude/agents/
    2. Run Claude CLI with either exec or subprocess
    3. Extract tickets if needed
    4. Handle both interactive and non-interactive modes

    Supports two launch methods:
    - exec: Replace current process (default for backward compatibility)
    - subprocess: Launch as child process for more control
    """

    def __init__(
        self,
        enable_tickets: bool = True,
        log_level: str = "OFF",
        claude_args: Optional[list] = None,
        launch_method: str = "exec",  # "exec" or "subprocess"
        enable_websocket: bool = False,
        websocket_port: int = 8765,
    ):
        """Initialize the Claude runner."""
        self.logger = get_logger(__name__)

        # Initialize configuration service
        container = get_container()
        if not container.is_registered(RunnerConfigurationInterface):
            from claude_mpm.services.runner_configuration_service import (
                RunnerConfigurationService,
            )

            container.register_singleton(
                RunnerConfigurationInterface, RunnerConfigurationService
            )

        try:
            self.configuration_service = container.get(RunnerConfigurationInterface)
        except Exception as e:
            self.logger.error(
                "Failed to initialize configuration service", exc_info=True
            )
            raise RuntimeError(
                f"Configuration service initialization failed: {e}"
            ) from e

        # Initialize configuration using the service
        config_data = self.configuration_service.initialize_configuration(
            enable_tickets=enable_tickets,
            log_level=log_level,
            claude_args=claude_args,
            launch_method=launch_method,
            enable_websocket=enable_websocket,
            websocket_port=websocket_port,
        )

        # Set configuration attributes
        self.enable_tickets = config_data["enable_tickets"]
        self.log_level = config_data["log_level"]
        self.claude_args = config_data["claude_args"]
        self.launch_method = config_data["launch_method"]
        self.enable_websocket = config_data["enable_websocket"]
        self.websocket_port = config_data["websocket_port"]
        self.config = config_data["config"]

        # Initialize project logger using the service
        self.project_logger = self.configuration_service.initialize_project_logger(
            self.log_level
        )

        # Initialize services using dependency injection and configuration service
        user_working_dir = self.configuration_service.get_user_working_directory()

        # Register core services
        self.configuration_service.register_core_services(container, user_working_dir)

        try:
            self.deployment_service = container.get(AgentDeploymentInterface)
        except Exception as e:
            self.logger.error("Failed to resolve AgentDeploymentService", exc_info=True)
            raise RuntimeError(
                f"Agent deployment service initialization failed: {e}"
            ) from e

        # Ticket manager disabled - use claude-mpm tickets CLI commands instead
        self.ticket_manager = None
        self.enable_tickets = False

        # Initialize response logger using configuration service
        self.response_logger = self.configuration_service.initialize_response_logger(
            self.config, self.project_logger
        )

        # Initialize hook service using configuration service
        self.hook_service = self.configuration_service.register_hook_service(
            container, self.config
        )

        # Initialize memory hook service using configuration service
        self.memory_hook_service = (
            self.configuration_service.register_memory_hook_service(
                container, self.hook_service
            )
        )
        if self.memory_hook_service:
            self.memory_hook_service.register_memory_hooks()

        # Initialize agent capabilities service using configuration service
        self.agent_capabilities_service = (
            self.configuration_service.register_agent_capabilities_service(container)
        )

        # Initialize system instructions service using configuration service
        self.system_instructions_service = (
            self.configuration_service.register_system_instructions_service(
                container, self.agent_capabilities_service
            )
        )

        # Initialize Socket.IO server reference first
        self.websocket_server = None

        # Initialize subprocess launcher service using configuration service
        self.subprocess_launcher_service = (
            self.configuration_service.register_subprocess_launcher_service(
                container, self.project_logger, self.websocket_server
            )
        )

        # Initialize version service using configuration service
        self.version_service = self.configuration_service.register_version_service(
            container
        )

        # Initialize command handler service using configuration service
        self.command_handler_service = (
            self.configuration_service.register_command_handler_service(
                container, self.project_logger
            )
        )

        # Initialize session management service using configuration service
        # Note: This must be done after other services are initialized since it depends on the runner
        self.session_management_service = (
            self.configuration_service.register_session_management_service(
                container, self
            )
        )

        # Initialize utility service using configuration service
        self.utility_service = self.configuration_service.register_utility_service(
            container
        )

        # Load system instructions using the service
        if self.system_instructions_service:
            self.system_instructions = (
                self.system_instructions_service.load_system_instructions()
            )
        else:
            self.system_instructions = self._load_system_instructions()

        # Deploy output style early (before Claude Code launches)
        # This ensures the "Claude MPM" output style is active on startup
        self._deploy_output_style()

        # Create session log file using configuration service
        self.session_log_file = self.configuration_service.create_session_log_file(
            self.project_logger, self.log_level, config_data
        )

        # Log session start event if we have a session log file
        if self.session_log_file:
            self._log_session_event(
                {
                    "event": "session_start",
                    "runner": "ClaudeRunner",
                    "enable_tickets": self.enable_tickets,
                    "log_level": self.log_level,
                    "launch_method": self.launch_method,
                }
            )

    def setup_agents(self) -> bool:
        """Deploy native agents to .claude/agents/."""
        try:
            if self.project_logger:
                self.project_logger.log_system(
                    "Starting agent deployment", level="INFO", component="deployment"
                )

            results = self.deployment_service.deploy_agents()

            if results["deployed"] or results.get("updated", []):
                deployed_count = len(results["deployed"])
                updated_count = len(results.get("updated", []))

                if deployed_count > 0:
                    print(f"✓ Deployed {deployed_count} native agents")
                if updated_count > 0:
                    print(f"✓ Updated {updated_count} agents")

                if self.project_logger:
                    self.project_logger.log_system(
                        f"Agent deployment successful: {deployed_count} deployed, {updated_count} updated",
                        level="INFO",
                        component="deployment",
                    )

                # Set Claude environment
                self.deployment_service.set_claude_environment()
                return True
            self.logger.info("All agents already up to date")
            if self.project_logger:
                self.project_logger.log_system(
                    "All agents already up to date",
                    level="INFO",
                    component="deployment",
                )
            return True

        except PermissionError as e:
            error_msg = f"Permission denied deploying agents to .claude/agents/: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            print(
                "💡 Try running with appropriate permissions or check directory ownership"
            )
            if self.project_logger:
                self.project_logger.log_system(
                    error_msg, level="ERROR", component="deployment"
                )
            return False

        except FileNotFoundError as e:
            error_msg = f"Agent files not found: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            print("💡 Ensure claude-mpm is properly installed")
            if self.project_logger:
                self.project_logger.log_system(
                    error_msg, level="ERROR", component="deployment"
                )
            return False

        except ImportError as e:
            error_msg = f"Missing required module for agent deployment: {e}"
            self.logger.error(error_msg)
            print(f"⚠️  {error_msg}")
            print("💡 Some agent features may be limited")
            if self.project_logger:
                self.project_logger.log_system(
                    error_msg, level="WARNING", component="deployment"
                )
            return False

        except Exception as e:
            error_msg = f"Unexpected error during agent deployment: {e}"
            self.logger.error(error_msg)
            print(f"⚠️  {error_msg}")
            if self.project_logger:
                self.project_logger.log_system(
                    error_msg, level="ERROR", component="deployment"
                )
            # Continue without agents rather than failing completely
            return False

    def ensure_project_agents(self) -> bool:
        """Ensure system agents are available in the project directory.

        Deploys system agents to project's .claude/agents/ directory
        if they don't exist or are outdated. This ensures agents are
        available for Claude Code to use. Project-specific JSON templates
        should be placed in .claude-mpm/agents/.

        Returns:
            bool: True if agents are available, False on error
        """
        try:
            # Use the correct user directory, not the framework directory
            if "CLAUDE_MPM_USER_PWD" in os.environ:
                project_dir = Path(os.environ["CLAUDE_MPM_USER_PWD"])
            else:
                project_dir = Path.cwd()

            project_agents_dir = project_dir / ".claude-mpm" / "agents"

            # Create directory if it doesn't exist
            project_agents_dir.mkdir(parents=True, exist_ok=True)

            if self.project_logger:
                self.project_logger.log_system(
                    f"Ensuring agents are available in project: {project_agents_dir}",
                    level="INFO",
                    component="deployment",
                )

            # Deploy agents to project's .claude/agents directory (not .claude-mpm)
            # This ensures all system agents are deployed regardless of version
            # .claude-mpm/agents/ should only contain JSON source templates
            # .claude/agents/ should contain the built MD files for Claude Code
            results = self.deployment_service.deploy_agents(
                target_dir=project_dir / ".claude",
                force_rebuild=False,
                deployment_mode="project",
            )

            if results["deployed"] or results.get("updated", []):
                deployed_count = len(results["deployed"])
                updated_count = len(results.get("updated", []))

                if deployed_count > 0:
                    self.logger.info(f"Deployed {deployed_count} agents to project")
                if updated_count > 0:
                    self.logger.info(f"Updated {updated_count} agents in project")

                return True
            if results.get("skipped", []):
                # Agents already exist and are current
                self.logger.debug(
                    f"Project agents up to date: {len(results['skipped'])} agents"
                )
                return True
            self.logger.warning("No agents deployed to project")
            return False

        except Exception as e:
            self.logger.error(f"Failed to ensure project agents: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Failed to ensure project agents: {e}",
                    level="ERROR",
                    component="deployment",
                )
            return False

    def deploy_project_agents_to_claude(self) -> bool:
        """Deploy project agents from .claude-mpm/agents/ to .claude/agents/.

        This method handles the deployment of project-specific agents (JSON format)
        from the project's agents directory to Claude's agent directory.
        Project agents take precedence over system agents.

        WHY: Project agents allow teams to define custom, project-specific agents
        that override system agents. These are stored in JSON format in
        .claude-mpm/agents/ and need to be deployed to .claude/agents/
        as MD files for Claude to use them.

        Returns:
            bool: True if deployment successful or no agents to deploy, False on error
        """
        try:
            # Use the correct user directory, not the framework directory
            if "CLAUDE_MPM_USER_PWD" in os.environ:
                project_dir = Path(os.environ["CLAUDE_MPM_USER_PWD"])
            else:
                project_dir = Path.cwd()

            project_agents_dir = project_dir / ".claude-mpm" / "agents"
            claude_agents_dir = project_dir / ".claude" / "agents"

            # Check if project agents directory exists
            if not project_agents_dir.exists():
                self.logger.debug("No project agents directory found")
                return True  # Not an error - just no project agents

            # Get JSON agent files from agents directory
            json_files = list(project_agents_dir.glob("*.json"))
            if not json_files:
                self.logger.debug("No JSON agents in project")
                return True

            # Create .claude/agents directory if needed
            claude_agents_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(
                f"Deploying {len(json_files)} project agents to .claude/agents/"
            )
            if self.project_logger:
                self.project_logger.log_system(
                    f"Deploying project agents from {project_agents_dir} to {claude_agents_dir}",
                    level="INFO",
                    component="deployment",
                )

            deployed_count = 0
            updated_count = 0
            errors = []

            # Deploy each JSON agent
            # CRITICAL: PM (Project Manager) must NEVER be deployed as it's the main Claude instance
            EXCLUDED_AGENTS = {"pm", "project_manager"}

            # Initialize deployment service with proper base agent path
            # Use the existing deployment service's base agent path if available
            base_agent_path = project_agents_dir / "base_agent.json"
            if not base_agent_path.exists():
                # Fall back to system base agent
                base_agent_path = self.deployment_service.base_agent_path

            # Lazy import to avoid circular dependencies
            from claude_mpm.services.agents.deployment import AgentDeploymentService

            # Create a single deployment service instance for all agents
            project_deployment = AgentDeploymentService(
                templates_dir=project_agents_dir,
                base_agent_path=base_agent_path,
                working_directory=project_dir,  # Pass the project directory
            )

            # Load base agent data once
            base_agent_data = {}
            if base_agent_path and base_agent_path.exists():
                try:
                    import json

                    base_agent_data = json.loads(base_agent_path.read_text())
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")

            for json_file in json_files:
                try:
                    agent_name = json_file.stem

                    # Skip PM agent - it's the main Claude instance, not a subagent
                    if agent_name.lower() in EXCLUDED_AGENTS:
                        self.logger.info(
                            f"Skipping {agent_name} (PM is the main Claude instance)"
                        )
                        continue

                    target_file = claude_agents_dir / f"{agent_name}.md"

                    # Check if agent needs update
                    needs_update = True
                    if target_file.exists():
                        # Check if it's a project agent (has project marker)
                        existing_content = target_file.read_text()
                        if (
                            "author: claude-mpm-project" in existing_content
                            or "source: project" in existing_content
                        ):
                            # Compare modification times
                            if target_file.stat().st_mtime >= json_file.stat().st_mtime:
                                needs_update = False
                                self.logger.debug(
                                    f"Project agent {agent_name} is up to date"
                                )

                    if needs_update:
                        # Build the agent markdown using the pre-initialized service and base agent data
                        # Use template_builder service instead of removed _build_agent_markdown method
                        agent_content = (
                            project_deployment.template_builder.build_agent_markdown(
                                agent_name,
                                json_file,
                                base_agent_data,
                                source_info="project",
                            )
                        )

                        # Mark as project agent
                        agent_content = agent_content.replace(
                            "author: claude-mpm", "author: claude-mpm-project"
                        )

                        # Write the agent file
                        is_update = target_file.exists()
                        target_file.write_text(agent_content)

                        if is_update:
                            updated_count += 1
                            self.logger.info(f"Updated project agent: {agent_name}")
                        else:
                            deployed_count += 1
                            self.logger.info(f"Deployed project agent: {agent_name}")

                except Exception as e:
                    error_msg = f"Failed to deploy project agent {json_file.name}: {e}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

            # Report results
            if deployed_count > 0 or updated_count > 0:
                print(
                    f"✓ Deployed {deployed_count} project agents, updated {updated_count}"
                )
                if self.project_logger:
                    self.project_logger.log_system(
                        f"Project agent deployment: {deployed_count} deployed, {updated_count} updated",
                        level="INFO",
                        component="deployment",
                    )

            if errors:
                for error in errors:
                    print(f"⚠️  {error}")
                return False

            return True

        except Exception as e:
            error_msg = f"Failed to deploy project agents: {e}"
            self.logger.error(error_msg)
            print(f"⚠️  {error_msg}")
            if self.project_logger:
                self.project_logger.log_system(
                    error_msg, level="ERROR", component="deployment"
                )
            return False

    def run_interactive(self, initial_context: Optional[str] = None):
        """Run Claude in interactive mode using the session management service.

        Delegates to the SessionManagementService for session orchestration.

        Args:
            initial_context: Optional initial context to pass to Claude
        """
        if self.session_management_service:
            self.session_management_service.run_interactive_session(initial_context)
        else:
            self.logger.error("Session management service not available")
            print("Error: Session management service not available")

    def run_oneshot(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt using the session management service.

        Delegates to the SessionManagementService for session orchestration.

        Args:
            prompt: The command or prompt to execute
            context: Optional context to prepend to the prompt

        Returns:
            bool: True if successful, False otherwise
        """
        if self.session_management_service:
            return self.session_management_service.run_oneshot_session(prompt, context)
        self.logger.error("Session management service not available")
        print("Error: Session management service not available")
        return False

    def _extract_tickets(self, text: str):
        """Extract tickets from Claude's response (disabled - use claude-mpm tickets CLI)."""
        # Ticket extraction disabled - users should use claude-mpm tickets CLI commands

    def _load_system_instructions(self) -> Optional[str]:
        """Load and process system instructions.

        Delegates to the SystemInstructionsService for loading and processing.
        """
        if self.system_instructions_service:
            return self.system_instructions_service.load_system_instructions()
        # Fallback if service is not available
        self.logger.warning(
            "System instructions service not available, using basic fallback"
        )
        return None

    def _process_base_pm_content(self, base_pm_content: str) -> str:
        """Process BASE_PM.md content with dynamic injections.

        Delegates to the SystemInstructionsService for processing.
        """
        if self.system_instructions_service:
            return self.system_instructions_service.process_base_pm_content(
                base_pm_content
            )
        # Fallback if service is not available
        self.logger.warning(
            "System instructions service not available for BASE_PM processing"
        )
        return base_pm_content

    def _strip_metadata_comments(self, content: str) -> str:
        """Strip HTML metadata comments from content.

        Delegates to the SystemInstructionsService for processing.
        """
        if self.system_instructions_service:
            return self.system_instructions_service.strip_metadata_comments(content)
        # Fallback if service is not available
        self.logger.warning(
            "System instructions service not available for metadata stripping"
        )
        return content

    def _generate_deployed_agent_capabilities(self) -> str:
        """Generate agent capabilities from deployed agents.

        Delegates to the AgentCapabilitiesService for agent discovery and formatting.
        """
        if self.agent_capabilities_service:
            return (
                self.agent_capabilities_service.generate_deployed_agent_capabilities()
            )
        # Fallback if service is not available
        self.logger.warning("Agent capabilities service not available, using fallback")
        return self._get_fallback_capabilities()

    def _get_fallback_capabilities(self) -> str:
        """Return fallback agent capabilities when deployed agents can't be read."""
        # Delegate to the service if available, otherwise use basic fallback
        if self.agent_capabilities_service:
            return self.agent_capabilities_service._get_fallback_capabilities()
        return """
## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer Agent**: Code implementation and development
- **Research Agent**: Investigation and analysis
- **QA Agent**: Testing and quality assurance
- **Documentation Agent**: Documentation creation and maintenance

Use these agents to delegate specialized work via the Task tool.
"""

    def _create_system_prompt(self) -> str:
        """Create the complete system prompt including instructions.

        Delegates to the SystemInstructionsService for prompt creation.
        """
        if self.system_instructions_service:
            return self.system_instructions_service.create_system_prompt(
                self.system_instructions
            )
        # Fallback if service is not available
        if self.system_instructions:
            return self.system_instructions
        return create_simple_context()

    def _contains_delegation(self, text: str) -> bool:
        """Check if text contains signs of agent delegation using the utility service."""
        if self.utility_service:
            return self.utility_service.contains_delegation(text)
        # Fallback if service not available
        return False

    def _extract_agent_from_response(self, text: str) -> Optional[str]:
        """Try to extract agent name from delegation response using the utility service."""
        if self.utility_service:
            return self.utility_service.extract_agent_from_response(text)
        # Fallback if service not available
        return None

    def _handle_mpm_command(self, prompt: str) -> bool:
        """Handle /mpm: commands using the command handler service.

        Delegates to the CommandHandlerService for command processing.
        """
        if self.command_handler_service:
            return self.command_handler_service.handle_mpm_command(prompt)
        # Fallback if service not available
        print("Command handler service not available")
        return False

    def _log_session_event(self, event_data: dict):
        """Log an event to the session log file using the utility service."""
        if self.utility_service:
            self.utility_service.log_session_event(self.session_log_file, event_data)
        else:
            # Fallback if service not available
            self.logger.debug("Utility service not available for session logging")

    def _get_version(self) -> str:
        """Get version string using the version service.

        Delegates to the VersionService for version detection and formatting.
        """
        if self.version_service:
            return self.version_service.get_version()
        # Fallback if service not available
        return "v0.0.0"

    def _deploy_output_style(self) -> None:
        """Deploy the Claude MPM output style before Claude Code launches.

        This method ensures the output style is set to "Claude MPM" on startup
        by deploying the style file and updating Claude Code settings.
        Only works for Claude Code >= 1.0.83.
        """
        try:
            from claude_mpm.core.output_style_manager import OutputStyleManager

            # Create OutputStyleManager instance
            output_style_manager = OutputStyleManager()

            # Check if Claude Code supports output styles
            if not output_style_manager.supports_output_styles():
                self.logger.debug(
                    f"Claude Code version {output_style_manager.claude_version or 'unknown'} "
                    "does not support output styles (requires >= 1.0.83)"
                )
                return

            # Check if output style is already deployed and active
            settings_file = Path.home() / ".claude" / "settings.json"
            if settings_file.exists():
                try:
                    import json

                    settings = json.loads(settings_file.read_text())
                    if settings.get("activeOutputStyle") == "claude-mpm":
                        # Already active, check if file exists
                        output_style_file = (
                            Path.home() / ".claude" / "output-styles" / "claude-mpm.md"
                        )
                        if output_style_file.exists():
                            self.logger.debug(
                                "Output style 'Claude MPM' already deployed and active"
                            )
                            return
                except Exception:
                    pass  # Continue with deployment if we can't read settings

            # Read the OUTPUT_STYLE.md content if it exists
            output_style_path = (
                Path(__file__).parent.parent / "agents" / "OUTPUT_STYLE.md"
            )

            if output_style_path.exists():
                # Use existing OUTPUT_STYLE.md content
                output_style_content = output_style_path.read_text()
                self.logger.debug("Using existing OUTPUT_STYLE.md content")
            else:
                # Extract output style content from framework instructions
                output_style_content = (
                    output_style_manager.extract_output_style_content()
                )
                self.logger.debug("Extracted output style from framework instructions")

            # Deploy the output style
            deployed = output_style_manager.deploy_output_style(output_style_content)

            if deployed:
                self.logger.info(
                    "✅ Output style 'Claude MPM' deployed and activated on startup"
                )
                if self.project_logger:
                    self.project_logger.log_system(
                        "Output style 'Claude MPM' deployed and activated on startup",
                        level="INFO",
                        component="output_style",
                    )
            else:
                self.logger.warning("Failed to deploy output style")

        except ImportError as e:
            self.logger.warning(f"Could not import OutputStyleManager: {e}")
        except Exception as e:
            # Don't fail startup if output style deployment fails
            self.logger.warning(f"Error deploying output style: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Output style deployment error: {e}",
                    level="WARNING",
                    component="output_style",
                )

    def _launch_subprocess_interactive(self, cmd: list, env: dict):
        """Launch Claude as a subprocess with PTY for interactive mode.

        Delegates to the SubprocessLauncherService for subprocess management.
        """
        if self.subprocess_launcher_service:
            self.subprocess_launcher_service.launch_subprocess_interactive(cmd, env)
        else:
            # Fallback if service is not available
            self.logger.warning(
                "Subprocess launcher service not available, cannot launch subprocess"
            )
            raise RuntimeError("Subprocess launcher service not available")


def create_simple_context() -> str:
    """Create basic context for Claude."""
    return """You are Claude Code running in Claude MPM (Multi-Agent Project Manager).

You have access to native subagents via the Task tool with subagent_type parameter:
- engineer: For coding, implementation, and technical tasks
- qa: For testing, validation, and quality assurance
- documentation: For docs, guides, and explanations
- research: For investigation and analysis
- security: For security-related tasks
- ops: For deployment and infrastructure
- version-control: For git and version management
- data-engineer: For data processing and APIs

Use these agents by calling: Task(description="task description", subagent_type="agent_name")

IMPORTANT: The Task tool accepts both naming formats:
- Capitalized format: "Research", "Engineer", "QA", "Version Control", "Data Engineer"
- Lowercase format: "research", "engineer", "qa", "version-control", "data-engineer"

Both formats work correctly. When you see capitalized names (matching TodoWrite prefixes),
automatically normalize them to lowercase-hyphenated format for the Task tool.

Work efficiently and delegate appropriately to subagents when needed."""


# Backward compatibility alias
SimpleClaudeRunner = ClaudeRunner


# Convenience functions for backward compatibility
def run_claude_interactive(context: Optional[str] = None):
    """Run Claude interactively with optional context."""
    runner = ClaudeRunner()
    if context is None:
        context = create_simple_context()
    runner.run_interactive(context)


def run_claude_oneshot(prompt: str, context: Optional[str] = None) -> bool:
    """Run Claude with a single prompt."""
    runner = ClaudeRunner()
    if context is None:
        context = create_simple_context()
    return runner.run_oneshot(prompt, context)
