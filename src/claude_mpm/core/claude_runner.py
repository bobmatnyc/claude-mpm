"""Claude runner with both exec and subprocess launch methods."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import uuid
from claude_mpm.config.paths import paths

# Core imports that don't cause circular dependencies
from claude_mpm.core.config import Config
from claude_mpm.core.logging_config import get_logger, log_operation, log_performance_context
from claude_mpm.core.logger import get_project_logger, ProjectLogger
from claude_mpm.core.container import get_container, ServiceLifetime
from claude_mpm.core.interfaces import (
    AgentDeploymentInterface,
    TicketManagerInterface, 
    HookServiceInterface
)

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from claude_mpm.services.agents.deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.services.hook_service import HookService


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
        websocket_port: int = 8765
    ):
        """Initialize the Claude runner."""
        self.enable_tickets = enable_tickets
        self.log_level = log_level
        self.logger = get_logger(__name__)
        self.claude_args = claude_args or []
        self.launch_method = launch_method
        self.enable_websocket = enable_websocket
        self.websocket_port = websocket_port
        
        # Initialize project logger for session logging
        self.project_logger = None
        if log_level != "OFF":
            try:
                self.project_logger = get_project_logger(log_level)
                self.project_logger.log_system(
                    f"Initializing ClaudeRunner with {launch_method} launcher",
                    level="INFO",
                    component="runner"
                )
            except ImportError as e:
                self.logger.warning(f"Project logger module not available: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize project logger: {e}")
        
        # Initialize services using dependency injection
        # Determine the user's working directory from environment
        user_working_dir = None
        if 'CLAUDE_MPM_USER_PWD' in os.environ:
            user_working_dir = Path(os.environ['CLAUDE_MPM_USER_PWD'])
            self.logger.info(f"Using user working directory from CLAUDE_MPM_USER_PWD", extra={"directory": str(user_working_dir)})
        
        # Get DI container and resolve services
        container = get_container()
        
        # Register and resolve deployment service
        if not container.is_registered(AgentDeploymentInterface):
            # Lazy import to avoid circular dependencies
            from claude_mpm.services.agents.deployment import AgentDeploymentService
            container.register_factory(
                AgentDeploymentInterface,
                lambda c: AgentDeploymentService(working_directory=user_working_dir),
                lifetime=ServiceLifetime.SINGLETON
            )
        
        try:
            self.deployment_service = container.get(AgentDeploymentInterface)
        except Exception as e:
            self.logger.error(f"Failed to resolve AgentDeploymentService", exc_info=True)
            raise RuntimeError(f"Agent deployment service initialization failed: {e}") from e
        
        # Initialize ticket manager if enabled using DI
        if enable_tickets:
            if not container.is_registered(TicketManagerInterface):
                # Lazy import to avoid circular dependencies
                from claude_mpm.services.ticket_manager import TicketManager
                container.register_singleton(TicketManagerInterface, TicketManager)
            
            try:
                self.ticket_manager = container.get(TicketManagerInterface)
            except Exception as e:
                self.logger.warning("Failed to initialize TicketManager", exc_info=True)
                self.ticket_manager = None
                self.enable_tickets = False
        else:
            self.ticket_manager = None
        
        # Initialize configuration
        try:
            self.config = Config()
        except FileNotFoundError as e:
            self.logger.warning("Configuration file not found, using defaults", extra={"error": str(e)})
            self.config = Config()  # Will use defaults
        except Exception as e:
            self.logger.error("Failed to load configuration", exc_info=True)
            raise RuntimeError(f"Configuration initialization failed: {e}") from e
        
        # Initialize response logging if enabled
        self.response_logger = None
        response_config = self.config.get('response_logging', {})
        if response_config.get('enabled', False):
            try:
                from claude_mpm.services.claude_session_logger import get_session_logger
                self.response_logger = get_session_logger(self.config)
                if self.project_logger:
                    self.project_logger.log_system(
                        "Response logging initialized",
                        level="INFO",
                        component="logging"
                    )
            except Exception as e:
                self.logger.warning("Failed to initialize response logger", exc_info=True)
        
        # Initialize hook service using DI
        if not container.is_registered(HookServiceInterface):
            # Lazy import to avoid circular dependencies
            from claude_mpm.services.hook_service import HookService
            container.register_factory(
                HookServiceInterface,
                lambda c: HookService(self.config),
                lifetime=ServiceLifetime.SINGLETON
            )
        
        try:
            self.hook_service = container.get(HookServiceInterface)
            self._register_memory_hooks()
        except Exception as e:
            self.logger.warning("Failed to initialize hook service", exc_info=True)
            self.hook_service = None
        
        # Load system instructions
        self.system_instructions = self._load_system_instructions()
        
        # Track if we need to create session logs
        self.session_log_file = None
        if self.project_logger and log_level != "OFF":
            try:
                # Create a system.jsonl file in the session directory
                self.session_log_file = self.project_logger.session_dir / "system.jsonl"
                self._log_session_event({
                    "event": "session_start",
                    "runner": "ClaudeRunner",
                    "enable_tickets": enable_tickets,
                    "log_level": log_level,
                    "launch_method": launch_method
                })
            except PermissionError as e:
                self.logger.debug(f"Permission denied creating session log file: {e}")
            except OSError as e:
                self.logger.debug(f"OS error creating session log file: {e}")
            except Exception as e:
                self.logger.debug(f"Failed to create session log file: {e}")
        
        # Initialize Socket.IO server reference
        self.websocket_server = None
    
    def setup_agents(self) -> bool:
        """Deploy native agents to .claude/agents/."""
        try:
            if self.project_logger:
                self.project_logger.log_system(
                    "Starting agent deployment",
                    level="INFO",
                    component="deployment"
                )
            
            results = self.deployment_service.deploy_agents()
            
            if results["deployed"] or results.get("updated", []):
                deployed_count = len(results['deployed'])
                updated_count = len(results.get('updated', []))
                
                if deployed_count > 0:
                    print(f"✓ Deployed {deployed_count} native agents")
                if updated_count > 0:
                    print(f"✓ Updated {updated_count} agents")
                
                if self.project_logger:
                    self.project_logger.log_system(
                        f"Agent deployment successful: {deployed_count} deployed, {updated_count} updated",
                        level="INFO",
                        component="deployment"
                    )
                    
                # Set Claude environment
                self.deployment_service.set_claude_environment()
                return True
            else:
                self.logger.info("All agents already up to date")
                if self.project_logger:
                    self.project_logger.log_system(
                        "All agents already up to date",
                        level="INFO",
                        component="deployment"
                    )
                return True
                
        
        except PermissionError as e:
            error_msg = f"Permission denied deploying agents to .claude/agents/: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            print("💡 Try running with appropriate permissions or check directory ownership")
            if self.project_logger:
                self.project_logger.log_system(error_msg, level="ERROR", component="deployment")
            return False
        
        except FileNotFoundError as e:
            error_msg = f"Agent files not found: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            print("💡 Ensure claude-mpm is properly installed")
            if self.project_logger:
                self.project_logger.log_system(error_msg, level="ERROR", component="deployment")
            return False
        
        except ImportError as e:
            error_msg = f"Missing required module for agent deployment: {e}"
            self.logger.error(error_msg)
            print(f"⚠️  {error_msg}")
            print("💡 Some agent features may be limited")
            if self.project_logger:
                self.project_logger.log_system(error_msg, level="WARNING", component="deployment")
            return False
        
        except Exception as e:
            error_msg = f"Unexpected error during agent deployment: {e}"
            self.logger.error(error_msg)
            print(f"⚠️  {error_msg}")
            if self.project_logger:
                self.project_logger.log_system(error_msg, level="ERROR", component="deployment")
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
            if 'CLAUDE_MPM_USER_PWD' in os.environ:
                project_dir = Path(os.environ['CLAUDE_MPM_USER_PWD'])
            else:
                project_dir = Path.cwd()
            
            project_agents_dir = project_dir / ".claude-mpm" / "agents"
            
            # Create directory if it doesn't exist
            project_agents_dir.mkdir(parents=True, exist_ok=True)
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Ensuring agents are available in project: {project_agents_dir}",
                    level="INFO",
                    component="deployment"
                )
            
            # Deploy agents to project's .claude/agents directory (not .claude-mpm)
            # This ensures all system agents are deployed regardless of version
            # .claude-mpm/agents/ should only contain JSON source templates
            # .claude/agents/ should contain the built MD files for Claude Code
            results = self.deployment_service.deploy_agents(
                target_dir=project_dir / ".claude",
                force_rebuild=False,
                deployment_mode="project"
            )
            
            if results["deployed"] or results.get("updated", []):
                deployed_count = len(results['deployed'])
                updated_count = len(results.get('updated', []))
                
                if deployed_count > 0:
                    self.logger.info(f"Deployed {deployed_count} agents to project")
                if updated_count > 0:
                    self.logger.info(f"Updated {updated_count} agents in project")
                    
                return True
            elif results.get("skipped", []):
                # Agents already exist and are current
                self.logger.debug(f"Project agents up to date: {len(results['skipped'])} agents")
                return True
            else:
                self.logger.warning("No agents deployed to project")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to ensure project agents: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Failed to ensure project agents: {e}",
                    level="ERROR",
                    component="deployment"
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
            if 'CLAUDE_MPM_USER_PWD' in os.environ:
                project_dir = Path(os.environ['CLAUDE_MPM_USER_PWD'])
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
            
            self.logger.info(f"Deploying {len(json_files)} project agents to .claude/agents/")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Deploying project agents from {project_agents_dir} to {claude_agents_dir}",
                    level="INFO",
                    component="deployment"
                )
            
            deployed_count = 0
            updated_count = 0
            errors = []
            
            # Deploy each JSON agent
            # CRITICAL: PM (Project Manager) must NEVER be deployed as it's the main Claude instance
            EXCLUDED_AGENTS = {'pm', 'project_manager'}
            
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
                working_directory=project_dir  # Pass the project directory
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
                        self.logger.info(f"Skipping {agent_name} (PM is the main Claude instance)")
                        continue
                    
                    target_file = claude_agents_dir / f"{agent_name}.md"
                    
                    # Check if agent needs update
                    needs_update = True
                    if target_file.exists():
                        # Check if it's a project agent (has project marker)
                        existing_content = target_file.read_text()
                        if "author: claude-mpm-project" in existing_content or "source: project" in existing_content:
                            # Compare modification times
                            if target_file.stat().st_mtime >= json_file.stat().st_mtime:
                                needs_update = False
                                self.logger.debug(f"Project agent {agent_name} is up to date")
                    
                    if needs_update:
                        # Build the agent markdown using the pre-initialized service and base agent data
                        agent_content = project_deployment._build_agent_markdown(
                            agent_name, json_file, base_agent_data
                        )
                        
                        # Mark as project agent
                        agent_content = agent_content.replace(
                            "author: claude-mpm",
                            "author: claude-mpm-project"
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
                print(f"✓ Deployed {deployed_count} project agents, updated {updated_count}")
                if self.project_logger:
                    self.project_logger.log_system(
                        f"Project agent deployment: {deployed_count} deployed, {updated_count} updated",
                        level="INFO",
                        component="deployment"
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
                self.project_logger.log_system(error_msg, level="ERROR", component="deployment")
            return False
    
    def run_interactive(self, initial_context: Optional[str] = None):
        """Run Claude in interactive mode.
        
        WHY: This method now delegates to InteractiveSession class for better
        maintainability and reduced complexity. The session class handles all
        the details while this method provides the simple interface.
        
        DESIGN DECISION: Using delegation pattern to reduce complexity from
        39 to <10 and lines from 262 to <80, while maintaining 100% backward
        compatibility. All functionality including response logging through
        the hook system is preserved.
        
        The hook system continues to capture Claude events (UserPromptSubmit,
        PreToolUse, PostToolUse, Task delegations) directly from Claude Code,
        providing comprehensive event capture without process control overhead.
        
        Args:
            initial_context: Optional initial context to pass to Claude
        """
        from claude_mpm.core.interactive_session import InteractiveSession
        
        # Create session handler
        session = InteractiveSession(self)
        
        try:
            # Step 1: Initialize session
            success, error = session.initialize_interactive_session()
            if not success:
                self.logger.error(f"Failed to initialize interactive session: {error}")
                return
            
            # Step 2: Set up environment
            success, environment = session.setup_interactive_environment()
            if not success:
                self.logger.error("Failed to setup interactive environment")
                return
            
            # Step 3: Handle interactive input/output
            # This is where the actual Claude process runs
            session.handle_interactive_input(environment)
            
        finally:
            # Step 4: Clean up session
            session.cleanup_interactive_session()
    
    def run_oneshot(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt and return success status.
        
        WHY: This method now delegates to OneshotSession class for better
        maintainability and reduced complexity. The session class handles
        all the details while this method provides the simple interface.
        
        DESIGN DECISION: Using delegation pattern to reduce complexity from
        50 to <10 and lines from 332 to <80, while maintaining 100% backward
        compatibility. All functionality is preserved through the session class.
        
        Args:
            prompt: The command or prompt to execute
            context: Optional context to prepend to the prompt
            
        Returns:
            bool: True if successful, False otherwise
        """
        from claude_mpm.core.oneshot_session import OneshotSession
        
        # Create session handler
        session = OneshotSession(self)
        
        try:
            # Step 1: Initialize session
            success, error = session.initialize_session(prompt)
            if not success:
                return False
            
            # Special case: MPM commands return early
            if error is None and prompt.strip().startswith("/mpm:"):
                return success
            
            # Step 2: Deploy agents
            if not session.deploy_agents():
                self.logger.warning("Agent deployment had issues, continuing...")
            
            # Step 3: Set up infrastructure
            infrastructure = session.setup_infrastructure()
            
            # Step 4: Execute command
            success, response = session.execute_command(prompt, context, infrastructure)
            
            return success
            
        finally:
            # Step 5: Clean up session
            session.cleanup_session()
    
    def _extract_tickets(self, text: str):
        """Extract tickets from Claude's response."""
        if not self.ticket_manager:
            return
            
        try:
            # Use the ticket manager's extraction logic if available
            if hasattr(self.ticket_manager, 'extract_tickets_from_text'):
                tickets = self.ticket_manager.extract_tickets_from_text(text)
                if tickets:
                    print(f"\n📋 Extracted {len(tickets)} tickets")
                    for ticket in tickets[:3]:  # Show first 3
                        print(f"  - [{ticket.get('id', 'N/A')}] {ticket.get('title', 'No title')}")
                    if len(tickets) > 3:
                        print(f"  ... and {len(tickets) - 3} more")
            else:
                self.logger.debug("Ticket extraction method not available")
        except AttributeError as e:
            self.logger.debug(f"Ticket manager missing expected method: {e}")
        except TypeError as e:
            self.logger.debug(f"Invalid ticket data format: {e}")
        except Exception as e:
            self.logger.debug(f"Unexpected error during ticket extraction: {e}")

    def _load_system_instructions(self) -> Optional[str]:
        """Load and process system instructions from agents/INSTRUCTIONS.md.
        
        Implements project > framework precedence:
        1. First check for project-specific instructions in .claude-mpm/agents/INSTRUCTIONS.md
        2. If not found, fall back to framework instructions in src/claude_mpm/agents/INSTRUCTIONS.md
        
        WHY: Allows projects to override the default PM instructions with project-specific
        guidance, while maintaining backward compatibility with the framework defaults.
        
        DESIGN DECISION: Using CLAUDE_MPM_USER_PWD environment variable to locate the
        correct project directory, ensuring we check the right location even when
        claude-mpm is invoked from a different directory.
        """
        try:
            # Determine the user's project directory
            if 'CLAUDE_MPM_USER_PWD' in os.environ:
                project_dir = Path(os.environ['CLAUDE_MPM_USER_PWD'])
            else:
                project_dir = Path.cwd()
            
            # Check for project-specific INSTRUCTIONS.md first
            project_instructions_path = project_dir / ".claude-mpm" / "agents" / "INSTRUCTIONS.md"
            
            instructions_path = None
            instructions_source = None
            
            if project_instructions_path.exists():
                instructions_path = project_instructions_path
                instructions_source = "PROJECT"
                self.logger.info(f"Found project-specific INSTRUCTIONS.md: {instructions_path}")
            else:
                # Fall back to framework instructions
                module_path = Path(__file__).parent.parent
                framework_instructions_path = module_path / "agents" / "INSTRUCTIONS.md"
                
                if framework_instructions_path.exists():
                    instructions_path = framework_instructions_path
                    instructions_source = "FRAMEWORK"
                    self.logger.info(f"Using framework INSTRUCTIONS.md: {instructions_path}")
                else:
                    self.logger.warning(f"No INSTRUCTIONS.md found in project or framework")
                    return None
            
            # Read raw instructions
            raw_instructions = instructions_path.read_text()
            
            # Strip HTML metadata comments before processing
            raw_instructions = self._strip_metadata_comments(raw_instructions)
            
            # Process template variables if ContentAssembler is available
            try:
                from claude_mpm.services.framework_claude_md_generator.content_assembler import ContentAssembler
                assembler = ContentAssembler()
                processed_instructions = assembler.apply_template_variables(raw_instructions)
                
                # Append BASE_PM.md framework requirements with dynamic content
                base_pm_path = Path(__file__).parent.parent / "agents" / "BASE_PM.md"
                if base_pm_path.exists():
                    base_pm_content = base_pm_path.read_text()
                    
                    # Strip metadata comments from BASE_PM.md as well
                    base_pm_content = self._strip_metadata_comments(base_pm_content)
                    
                    # Process BASE_PM.md with dynamic content injection
                    base_pm_content = self._process_base_pm_content(base_pm_content)
                    
                    processed_instructions += f"\n\n{base_pm_content}"
                    self.logger.info(f"Appended BASE_PM.md with dynamic capabilities from deployed agents")
                
                self.logger.info(f"Loaded and processed {instructions_source} PM instructions")
                return processed_instructions
            except ImportError:
                self.logger.warning("ContentAssembler not available, using raw instructions")
                self.logger.info(f"Loaded {instructions_source} PM instructions (raw)")
                return raw_instructions
            except Exception as e:
                self.logger.warning(f"Failed to process template variables: {e}, using raw instructions")
                self.logger.info(f"Loaded {instructions_source} PM instructions (raw, processing failed)")
                return raw_instructions
            
        except Exception as e:
            self.logger.error(f"Failed to load system instructions: {e}")
            return None

    def _process_base_pm_content(self, base_pm_content: str) -> str:
        """Process BASE_PM.md content with dynamic injections.
        
        This method replaces template variables in BASE_PM.md with:
        - {{agent-capabilities}}: List of deployed agents from .claude/agents/
        - {{current-date}}: Today's date for temporal context
        """
        from datetime import datetime
        
        # Replace {{current-date}} with actual date
        current_date = datetime.now().strftime('%Y-%m-%d')
        base_pm_content = base_pm_content.replace('{{current-date}}', current_date)
        
        # Replace {{agent-capabilities}} with deployed agents
        if '{{agent-capabilities}}' in base_pm_content:
            capabilities_section = self._generate_deployed_agent_capabilities()
            base_pm_content = base_pm_content.replace('{{agent-capabilities}}', capabilities_section)
        
        return base_pm_content
    
    def _strip_metadata_comments(self, content: str) -> str:
        """Strip HTML metadata comments from content.
        
        Removes comments like:
        <!-- FRAMEWORK_VERSION: 0010 -->
        <!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->
        <!-- WORKFLOW_VERSION: ... -->
        <!-- PROJECT_WORKFLOW_VERSION: ... -->
        <!-- CUSTOM_PROJECT_WORKFLOW -->
        
        WHY: These metadata comments are useful for internal tracking but should not
        appear in the final instructions passed to Claude via --append-system-prompt.
        They clutter the instructions and provide no value to the Claude agent.
        
        DESIGN DECISION: Using regex to remove all HTML comments that contain known
        metadata patterns. Also removes any resulting leading blank lines.
        """
        import re
        
        # Remove HTML comments that contain metadata
        patterns_to_strip = [
            'FRAMEWORK_VERSION',
            'LAST_MODIFIED', 
            'WORKFLOW_VERSION',
            'PROJECT_WORKFLOW_VERSION',
            'CUSTOM_PROJECT_WORKFLOW',
            'AGENT_VERSION',
            'METADATA_VERSION'
        ]
        
        # Build regex pattern to match any of these metadata comments
        pattern = r'<!--\s*(' + '|'.join(patterns_to_strip) + r')[^>]*-->\n?'
        cleaned = re.sub(pattern, '', content)
        
        # Also remove any leading blank lines that might result
        cleaned = cleaned.lstrip('\n')
        
        return cleaned
    
    def _generate_deployed_agent_capabilities(self) -> str:
        """Generate agent capabilities from deployed agents following Claude Code's hierarchy.
        
        Follows the agent precedence order:
        1. Project agents (.claude/agents/) - highest priority
        2. User agents (~/.config/claude/agents/) - middle priority  
        3. System agents (claude-desktop installation) - lowest priority
        
        Project agents override user/system agents with the same ID.
        """
        try:
            # Track discovered agents by ID to handle overrides
            discovered_agents = {}
            
            # 1. First read system agents (lowest priority)
            system_agents_dirs = [
                Path.home() / "Library" / "Application Support" / "Claude" / "agents",  # macOS
                Path.home() / ".config" / "claude" / "agents",  # Linux
                Path.home() / "AppData" / "Roaming" / "Claude" / "agents",  # Windows
            ]
            
            for system_dir in system_agents_dirs:
                if system_dir.exists():
                    self._discover_agents_from_dir(system_dir, discovered_agents, "system")
                    break
            
            # 2. Then read user agents (middle priority, overrides system)
            user_agents_dir = Path.home() / ".config" / "claude" / "agents"
            if user_agents_dir.exists():
                self._discover_agents_from_dir(user_agents_dir, discovered_agents, "user")
            
            # 3. Finally read project agents (highest priority, overrides all)
            project_agents_dir = Path.cwd() / ".claude" / "agents"
            if project_agents_dir.exists():
                self._discover_agents_from_dir(project_agents_dir, discovered_agents, "project")
            
            if not discovered_agents:
                self.logger.warning("No agents found in any tier")
                return self._get_fallback_capabilities()
            
            # Build capabilities section from discovered agents
            section = "\n## Available Agent Capabilities\n\n"
            section += "You have the following specialized agents available for delegation:\n\n"
            
            # Group agents by category
            agents_by_category = {}
            for agent_id, agent_info in discovered_agents.items():
                category = agent_info['category']
                if category not in agents_by_category:
                    agents_by_category[category] = []
                agents_by_category[category].append(agent_info)
            
            # Output agents by category
            for category in sorted(agents_by_category.keys()):
                section += f"\n### {category} Agents\n"
                for agent in sorted(agents_by_category[category], key=lambda x: x['name']):
                    tier_indicator = f" [{agent['tier']}]" if agent['tier'] != 'project' else ""
                    section += f"- **{agent['name']}** (`{agent['id']}`{tier_indicator}): {agent['description']}\n"
            
            # Add summary
            section += f"\n**Total Available Agents**: {len(discovered_agents)}\n"
            
            # Show tier distribution
            tier_counts = {}
            for agent in discovered_agents.values():
                tier = agent['tier']
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            if len(tier_counts) > 1:
                section += f"**Agent Sources**: "
                tier_summary = []
                for tier in ['project', 'user', 'system']:
                    if tier in tier_counts:
                        tier_summary.append(f"{tier_counts[tier]} {tier}")
                section += ", ".join(tier_summary) + "\n"
            
            section += "Use the agent ID in parentheses when delegating tasks via the Task tool.\n"
            
            self.logger.info(f"Generated capabilities for {len(discovered_agents)} agents " +
                           f"(project: {tier_counts.get('project', 0)}, " +
                           f"user: {tier_counts.get('user', 0)}, " +
                           f"system: {tier_counts.get('system', 0)})")
            return section
            
        except Exception as e:
            self.logger.error(f"Failed to generate deployed agent capabilities: {e}")
            return self._get_fallback_capabilities()
    
    def _discover_agents_from_dir(self, agents_dir: Path, discovered_agents: dict, tier: str):
        """Discover agents from a specific directory and add/override in discovered_agents.
        
        Args:
            agents_dir: Directory to search for agent .md files
            discovered_agents: Dictionary to update with discovered agents
            tier: The tier this directory represents (system/user/project)
        """
        if not agents_dir.exists():
            return
        
        agent_files = list(agents_dir.glob("*.md"))
        for agent_file in sorted(agent_files):
            agent_id = agent_file.stem
            
            # Skip pm.md if it exists (PM is not a deployable agent)
            if agent_id.lower() == 'pm':
                continue
            
            # Read agent content and extract metadata
            try:
                content = agent_file.read_text()
                import re
                
                # Check for YAML frontmatter
                name = agent_id.replace('_', ' ').title()
                desc = "Specialized agent for delegation"
                
                if content.startswith('---'):
                    # Parse YAML frontmatter
                    frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                    if frontmatter_match:
                        frontmatter = frontmatter_match.group(1)
                        # Extract name from frontmatter
                        name_fm_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
                        if name_fm_match:
                            name_value = name_fm_match.group(1).strip()
                            # Format the name nicely
                            name = name_value.replace('_', ' ').title()
                        
                        # Extract description from frontmatter
                        desc_fm_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
                        if desc_fm_match:
                            desc = desc_fm_match.group(1).strip()
                else:
                    # No frontmatter, extract from content
                    name_match = re.search(r'^#\s+(.+?)(?:\s+Agent)?$', content, re.MULTILINE)
                    if name_match:
                        name = name_match.group(1)
                    
                    # Get first non-heading line after the title
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('#'):
                            # Found title, look for description after it
                            for desc_line in lines[i+1:]:
                                desc_line = desc_line.strip()
                                if desc_line and not desc_line.startswith('#'):
                                    desc = desc_line
                                    break
                            break
                
                # Categorize based on agent name/type
                category = self._categorize_agent(agent_id, content)
                
                # Add or override agent in discovered_agents
                discovered_agents[agent_id] = {
                    'id': agent_id,
                    'name': name,
                    'description': desc[:150] + '...' if len(desc) > 150 else desc,
                    'category': category,
                    'tier': tier,
                    'path': str(agent_file)
                }
                
                self.logger.debug(f"Discovered {tier} agent: {agent_id} from {agent_file}")
                
            except Exception as e:
                self.logger.debug(f"Could not parse agent {agent_file}: {e}")
                continue
    def _categorize_agent(self, agent_id: str, content: str) -> str:
        """Categorize an agent based on its ID and content."""
        agent_id_lower = agent_id.lower()
        content_lower = content.lower()
        
        if 'engineer' in agent_id_lower or 'engineering' in content_lower:
            return "Engineering"
        elif 'research' in agent_id_lower or 'analysis' in content_lower or 'analyzer' in agent_id_lower:
            return "Research"
        elif 'qa' in agent_id_lower or 'quality' in content_lower or 'test' in agent_id_lower:
            return "Quality"
        elif 'security' in agent_id_lower or 'security' in content_lower:
            return "Security"
        elif 'doc' in agent_id_lower or 'documentation' in content_lower:
            return "Documentation"
        elif 'data' in agent_id_lower:
            return "Data"
        elif 'ops' in agent_id_lower or 'deploy' in agent_id_lower or 'operations' in content_lower:
            return "Operations"
        elif 'version' in agent_id_lower or 'git' in content_lower:
            return "Version Control"
        else:
            return "General"
    
    def _get_fallback_capabilities(self) -> str:
        """Return fallback agent capabilities when deployed agents can't be read."""
        return """
## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer Agent**: Code implementation and development
- **Research Agent**: Investigation and analysis
- **QA Agent**: Testing and quality assurance
- **Documentation Agent**: Documentation creation and maintenance
- **Security Agent**: Security analysis and protection
- **Data Engineer Agent**: Data management and pipelines
- **Ops Agent**: Deployment and operations
- **Version Control Agent**: Git operations and version management

Use these agents to delegate specialized work via the Task tool.
"""
    
    def _generate_agent_capabilities_section(self, agents: dict) -> str:
        """Generate dynamic agent capabilities section from available agents."""
        if not agents:
            return ""
        
        # Build capabilities section
        section = "\n\n## Available Agent Capabilities\n\n"
        section += "You have the following specialized agents available for delegation:\n\n"
        
        # Group agents by category
        categories = {}
        for agent_id, info in agents.items():
            category = info.get('category', 'general')
            if category not in categories:
                categories[category] = []
            categories[category].append((agent_id, info))
        
        # List agents by category
        for category in sorted(categories.keys()):
            section += f"\n### {category.title()} Agents\n"
            for agent_id, info in sorted(categories[category]):
                name = info.get('name', agent_id)
                desc = info.get('description', 'Specialized agent')
                tools = info.get('tools', [])
                section += f"- **{name}** (`{agent_id}`): {desc}\n"
                if tools:
                    section += f"  - Tools: {', '.join(tools[:5])}"
                    if len(tools) > 5:
                        section += f" (+{len(tools)-5} more)"
                    section += "\n"
        
        # Add summary
        section += f"\n**Total Available Agents**: {len(agents)}\n"
        section += "Use the agent ID in parentheses when delegating tasks via the Task tool.\n"
        
        return section
    
    def _create_system_prompt(self) -> str:
        """Create the complete system prompt including instructions."""
        if self.system_instructions:
            return self.system_instructions
        else:
            # Fallback to basic context
            return create_simple_context()
    
    def _contains_delegation(self, text: str) -> bool:
        """Check if text contains signs of agent delegation."""
        # Look for common delegation patterns
        delegation_patterns = [
            "Task(",
            "subagent_type=",
            "delegating to",
            "asking the",
            "engineer agent",
            "qa agent",
            "documentation agent",
            "research agent",
            "security agent",
            "ops agent",
            "version_control agent",
            "data_engineer agent"
        ]
        
        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in delegation_patterns)
    
    def _extract_agent_from_response(self, text: str) -> Optional[str]:
        """Try to extract agent name from delegation response."""
        # Look for common patterns
        import re
        
        # Pattern 1: subagent_type="agent_name"
        match = re.search(r'subagent_type=["\']([^"\']*)["\'\)]', text)
        if match:
            return match.group(1)
        
        # Pattern 2: "engineer agent" etc
        agent_names = [
            "engineer", "qa", "documentation", "research", 
            "security", "ops", "version_control", "data_engineer"
        ]
        text_lower = text.lower()
        for agent in agent_names:
            if f"{agent} agent" in text_lower or f"agent: {agent}" in text_lower:
                return agent
        
        return None
    
    def _handle_mpm_command(self, prompt: str) -> bool:
        """Handle /mpm: commands directly without going to Claude."""
        try:
            # Extract command and arguments
            command_line = prompt[5:].strip()  # Remove "/mpm:"
            parts = command_line.split()
            
            if not parts:
                print("No command specified. Available commands: test")
                return True
            
            command = parts[0]
            args = parts[1:]
            
            # Handle commands
            if command == "test":
                print("Hello World")
                if self.project_logger:
                    self.project_logger.log_system(
                        "Executed /mpm:test command",
                        level="INFO",
                        component="command"
                    )
                return True
            elif command == "agents":
                # Handle agents command - display deployed agent versions
                # WHY: This provides users with a quick way to check deployed agent versions
                # directly from within Claude Code, maintaining consistency with CLI behavior
                try:
                    from claude_mpm.cli import _get_agent_versions_display
                    agent_versions = _get_agent_versions_display()
                    if agent_versions:
                        print(agent_versions)
                    else:
                        print("No deployed agents found")
                        print("\nTo deploy agents, run: claude-mpm --mpm:agents deploy")
                    
                    if self.project_logger:
                        self.project_logger.log_system(
                            "Executed /mpm:agents command",
                            level="INFO",
                            component="command"
                        )
                    return True
                except ImportError as e:
                    print(f"Error: CLI module not available: {e}")
                    return False
                except Exception as e:
                    print(f"Error getting agent versions: {e}")
                    return False
            else:
                print(f"Unknown command: {command}")
                print("Available commands: test, agents")
                return True
                
        except KeyboardInterrupt:
            print("\nCommand interrupted")
            return False
        except Exception as e:
            print(f"Error executing command: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Failed to execute /mpm: command: {e}",
                    level="ERROR",
                    component="command"
                )
            return False
    
    def _log_session_event(self, event_data: dict):
        """Log an event to the session log file."""
        if self.session_log_file:
            try:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    **event_data
                }
                
                with open(self.session_log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except (OSError, IOError) as e:
                self.logger.debug(f"IO error logging session event: {e}")
            except Exception as e:
                self.logger.debug(f"Failed to log session event: {e}")
    
    def _get_version(self) -> str:
        """
        Robust version determination with build number tracking.
        
        WHY: The version display is critical for debugging and user experience.
        This implementation ensures we always show the correct version with build
        number for precise tracking of code changes.
        
        DESIGN DECISION: We combine semantic version with build number:
        - Semantic version (X.Y.Z) for API compatibility tracking
        - Build number for fine-grained code change tracking
        - Format: vX.Y.Z-BBBBB (5-digit zero-padded build number)
        
        Returns version string formatted as "vX.Y.Z-BBBBB"
        """
        version = "0.0.0"
        method_used = "default"
        build_number = None
        
        # Method 1: Try package import (fastest, most common)
        try:
            from claude_mpm import __version__
            version = __version__
            method_used = "package_import"
            self.logger.debug(f"Version obtained via package import: {version}")
            # If version already includes build number (PEP 440 format), extract it
            if '+build.' in version:
                parts = version.split('+build.')
                version = parts[0]  # Base version without build
                build_number = int(parts[1]) if len(parts) > 1 else None
                self.logger.debug(f"Extracted base version: {version}, build: {build_number}")
        except ImportError as e:
            self.logger.debug(f"Package import failed: {e}")
        except Exception as e:
            self.logger.warning(f"Unexpected error in package import: {e}")
        
        # Method 2: Try importlib.metadata (standard for installed packages)
        if version == "0.0.0":
            try:
                import importlib.metadata
                version = importlib.metadata.version('claude-mpm')
                method_used = "importlib_metadata"
                self.logger.debug(f"Version obtained via importlib.metadata: {version}")
            except importlib.metadata.PackageNotFoundError:
                self.logger.debug("Package not found in importlib.metadata (likely development install)")
            except ImportError:
                self.logger.debug("importlib.metadata not available (Python < 3.8)")
            except Exception as e:
                self.logger.warning(f"Unexpected error in importlib.metadata: {e}")
        
        # Method 3: Try reading VERSION file directly (development fallback)
        if version == "0.0.0":
            try:
                # Use centralized path management for VERSION file
                if paths.version_file.exists():
                    version = paths.version_file.read_text().strip()
                    method_used = "version_file"
                    self.logger.debug(f"Version obtained via VERSION file: {version}")
                else:
                    self.logger.debug(f"VERSION file not found at: {paths.version_file}")
            except Exception as e:
                self.logger.warning(f"Failed to read VERSION file: {e}")
        
        # Try to read build number (only if not already obtained from version string)
        if build_number is None:
            try:
                build_file = paths.project_root / "BUILD_NUMBER"
                if build_file.exists():
                    build_content = build_file.read_text().strip()
                    build_number = int(build_content)
                    self.logger.debug(f"Build number obtained from file: {build_number}")
            except (ValueError, IOError) as e:
                self.logger.debug(f"Could not read BUILD_NUMBER: {e}")
                build_number = None
            except Exception as e:
                self.logger.debug(f"Unexpected error reading BUILD_NUMBER: {e}")
                build_number = None
        
        # Log final result
        if version == "0.0.0":
            self.logger.error(
                "All version detection methods failed. This indicates a packaging or installation issue."
            )
        else:
            self.logger.debug(f"Final version: {version} (method: {method_used})")
        
        # Format version with build number if available
        # For development: Use PEP 440 format (e.g., "3.9.5+build.275")
        # For UI/logging: Use dash format (e.g., "v3.9.5-build.275")
        # For PyPI releases: Use clean version (e.g., "3.9.5")
        
        # Determine formatting context (default to UI format for claude_runner)
        if build_number is not None:
            # UI/logging format with 'v' prefix and dash separator
            return f"v{version}-build.{build_number}"
        else:
            return f"v{version}"
    
    def _register_memory_hooks(self):
        """Register memory integration hooks with the hook service.
        
        WHY: This activates the memory system by registering hooks that automatically
        inject agent memory before delegation and extract learnings after delegation.
        This is the critical connection point between the memory system and the CLI.
        
        DESIGN DECISION: We register hooks here instead of in __init__ to ensure
        all services are initialized first. Hooks are only registered if the memory
        system is enabled in configuration.
        """
        try:
            # Only register if memory system is enabled
            if not self.config.get('memory.enabled', True):
                self.logger.debug("Memory system disabled - skipping hook registration")
                return
            
            # Import hook classes (lazy import to avoid circular dependencies)
            try:
                from claude_mpm.hooks.memory_integration_hook import (
                    MemoryPreDelegationHook,
                    MemoryPostDelegationHook
                )
            except ImportError as e:
                self.logger.warning(f"Memory integration hooks not available: {e}")
                return
            
            # Register pre-delegation hook for memory injection
            pre_hook = MemoryPreDelegationHook(self.config)
            success = self.hook_service.register_hook(pre_hook)
            if success:
                self.logger.info(f"✅ Registered memory pre-delegation hook (priority: {pre_hook.priority})")
            else:
                self.logger.warning("❌ Failed to register memory pre-delegation hook")
            
            # Register post-delegation hook if auto-learning is enabled
            if self.config.get('memory.auto_learning', True):  # Default to True now
                post_hook = MemoryPostDelegationHook(self.config)
                success = self.hook_service.register_hook(post_hook)
                if success:
                    self.logger.info(f"✅ Registered memory post-delegation hook (priority: {post_hook.priority})")
                else:
                    self.logger.warning("❌ Failed to register memory post-delegation hook")
            else:
                self.logger.info("ℹ️  Auto-learning disabled - skipping post-delegation hook")
            
            # Log summary of registered hooks
            hooks = self.hook_service.list_hooks()
            pre_count = len(hooks.get('pre_delegation', []))
            post_count = len(hooks.get('post_delegation', []))
            self.logger.info(f"📋 Hook Service initialized: {pre_count} pre-delegation, {post_count} post-delegation hooks")
            
        except AttributeError as e:
            self.logger.warning(f"Hook service not initialized properly: {e}")
        except Exception as e:
            self.logger.error(f"❌ Failed to register memory hooks: {e}")
            # Don't fail the entire initialization - memory system is optional
    
    def _launch_subprocess_interactive(self, cmd: list, env: dict):
        """Launch Claude as a subprocess with PTY for interactive mode.
        
        WHY: This method launches Claude as a subprocess when explicitly requested
        (via --launch-method subprocess). Subprocess mode maintains the parent process,
        which can be useful for:
        1. Maintaining WebSocket connections and monitoring
        2. Providing proper cleanup and error handling
        3. Debugging and development scenarios
        
        DESIGN DECISION: We use PTY (pseudo-terminal) to maintain full interactive
        capabilities. Response logging is handled through the hook system, not I/O
        interception, for better performance and compatibility.
        """
        import pty
        import select
        import termios
        import tty
        import signal
        
        # Note: Response logging is handled through the hook system,
        # not through I/O interception (better performance)
        
        # Save original terminal settings
        original_tty = None
        if sys.stdin.isatty():
            original_tty = termios.tcgetattr(sys.stdin)
        
        # Create PTY
        master_fd, slave_fd = pty.openpty()
        
        try:
            # Start Claude process
            process = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env
            )
            
            # Close slave in parent
            os.close(slave_fd)
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Claude subprocess started with PID {process.pid}",
                    level="INFO",
                    component="subprocess"
                )
            
            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="running",
                    pid=process.pid,
                    message="Claude subprocess started"
                )
            
            # Set terminal to raw mode for proper interaction
            if sys.stdin.isatty():
                tty.setraw(sys.stdin)
            
            # Handle Ctrl+C gracefully
            def signal_handler(signum, frame):
                if process.poll() is None:
                    process.terminate()
                raise KeyboardInterrupt()
            
            signal.signal(signal.SIGINT, signal_handler)
            
            # I/O loop
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    break
                
                # Check for data from Claude or stdin
                r, _, _ = select.select([master_fd, sys.stdin], [], [], 0)
                
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            os.write(sys.stdout.fileno(), data)
                            # Broadcast output to WebSocket clients
                            if self.websocket_server:
                                try:
                                    # Decode and send
                                    output = data.decode('utf-8', errors='replace')
                                    self.websocket_server.claude_output(output, "stdout")
                                except Exception as e:
                                    self.logger.debug(f"Failed to broadcast output: {e}")
                        else:
                            break  # EOF
                    except OSError:
                        break
                
                if sys.stdin in r:
                    try:
                        data = os.read(sys.stdin.fileno(), 4096)
                        if data:
                            os.write(master_fd, data)
                    except OSError:
                        break
            
            # Wait for process to complete
            process.wait()
            
            # Note: Response logging is handled through the hook system
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Claude subprocess exited with code {process.returncode}",
                    level="INFO",
                    component="subprocess"
                )
            
            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="stopped",
                    message=f"Claude subprocess exited with code {process.returncode}"
                )
            
        finally:
            # Restore terminal
            if original_tty and sys.stdin.isatty():
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_tty)
            
            # Close PTY
            try:
                os.close(master_fd)
            except:
                pass
            
            # Ensure process is terminated
            if 'process' in locals() and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            
            # End WebSocket session if in subprocess mode
            if self.websocket_server:
                self.websocket_server.session_ended()


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